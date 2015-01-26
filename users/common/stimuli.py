import numpy
import copy
import time
import random
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class SpotWaveform(experiment.Experiment):
    '''
        Expected parameters:
        FREQUENCIES
        DURATION
        PAUSE
        BACKGROUND
        AMPLITUDES
        SPOT_DIAMETERS
        WAVEFORM
    '''
    def prepare(self):
        self.intensities = []
        n_sample = self.experiment_config.DURATION*self.machine_config.SCREEN_EXPECTED_FRAME_RATE
        for amplitude in self.experiment_config.AMPLITUDES:
            for frq in self.experiment_config.FREQUENCIES:
                self.intensities.append(numpy.array([utils.generate_waveform(self.experiment_config.WAVEFORM, n_sample, self.machine_config.SCREEN_EXPECTED_FRAME_RATE/frq,  float(amplitude),  offset = float(self.experiment_config.BACKGROUND))]).T)

    def run(self):
        for spot_diameter in self.experiment_config.SPOT_DIAMETERS:
            for intensities in self.intensities:
                self.show_fullscreen(color=self.experiment_config.BACKGROUND, duration = 0.5*self.experiment_config.PAUSE)
                self.show_shape(color = intensities, background_color = self.experiment_config.BACKGROUND, shape = 'spot', size = spot_diameter, block_trigger=True)
                self.show_fullscreen(color=self.experiment_config.BACKGROUND, duration = 0.5*self.experiment_config.PAUSE)
                
class MovingShapeExperiment(experiment.Experiment):
    def prepare(self):
        parameter_default_values = {
        'REPETITIONS': 1, 
        'SHAPE': 'rect', 
        'SHAPE_CONTRAST' : 1.0, 
        'SHAPE_BACKGROUND': 0.5, 
        'PAUSE_BETWEEN_DIRECTIONS' : 0.0, 
        }
        self.set_default_experiment_parameter_values(parameter_default_values)
        #Calculate duration
        trajectories, trajectory_directions, self.stimulus_duration = self.moving_shape_trajectory(\
                                    size = self.experiment_config.SHAPE_SIZE,
                                    speeds = self.experiment_config.SPEEDS,
                                    directions = self.experiment_config.DIRECTIONS,
                                    pause = self.pause_between_directions,
                                    repetition = self.experiment_config.REPETITIONS,
                                    shape_starts_from_edge = True)
        if hasattr(self.log, 'info'):
            self.log.info('Stimulus duration: {0}'.format(self.stimulus_duration))

    def run(self):
        self.moving_shape(size = self.experiment_config.SHAPE_SIZE,
                                  speeds = self.experiment_config.SPEEDS,
                                  directions = self.experiment_config.DIRECTIONS,
                                  shape = self.shape,
                                  color = self.shape_contrast,
                                  background_color = self.shape_background,
                                  pause = self.pause_between_directions,
                                  repetition = self.experiment_config.REPETITIONS,
                                  shape_starts_from_edge = True)

class IncreasingSpotExperiment(experiment.Experiment):
    def prepare(self):
        if not hasattr(self.experiment_config, 'COLORS'):
            self.colors = [1.0]
        else:
            self.colors = self.experiment_config.COLORS
        if not hasattr(self.experiment_config, 'BACKGROUND'):
            self.background_color = self.machine_config.BACKGROUND_COLOR
        else:
            self.background_color = self.experiment_config.BACKGROUND
        
    def run(self):
        self.show_fullscreen(color = self.background_color, duration = self.experiment_config.OFF_TIME)
        for color in self.colors:
            self.increasing_spot(self.experiment_config.SIZES, self.experiment_config.ON_TIME, self.experiment_config.OFF_TIME,
                    color = color, background_color = self.background_color, pos = utils.rc((0,  0)), block_trigger = True)
                    
class FullFieldFlashesExperiment(experiment.Experiment):
    '''
    Expected parameters:
    Color(s)
    On time
    Off time
    N flashes
    '''
    def prepare(self):
        if not hasattr(self.experiment_config, 'COLORS'):
            self.colors = [1.0]
        else:
            self.colors = self.experiment_config.COLORS
        if len(self.colors)==1:
            self.colors = self.colors * self.experiment_config.NFLASHES
        if not hasattr(self.experiment_config, 'BACKGROUND'):
            self.background_color = self.machine_config.BACKGROUND_COLOR
        else:
            self.background_color = self.experiment_config.BACKGROUND
        
    def run(self):
        self.show_fullscreen(duration=self.experiment_config.OFF_TIME,color=self.background_color,block_trigger=True)
        for color in self.colors:
            self.show_fullscreen(duration=self.experiment_config.ON_TIME,color=color,block_trigger=True)
            self.show_fullscreen(duration=self.experiment_config.OFF_TIME,color=self.background_color,block_trigger=True)
            

class MovingGrating(experiment.Experiment):
    '''
    Mandatory configuration parameters:
        REPEATS
        NUMBER_OF_BAR_ADVANCE_OVER_POINT
        MARCH_TIME
        GREY_INSTEAD_OF_MARCHING
        NUMBER_OF_MARCHING_PHASES
        GRATING_STAND_TIME
        ORIENTATIONS
        WHITE_BAR_WIDTHS
        VELOCITIES
        DUTY_CYCLES
        PAUSE_BEFORE_AFTER
    Optional configuration parameters:
        ENABLE_FLASH
        PROFILE
        
    '''
    def prepare(self):
        self.marching_phases = -numpy.linspace(0, 360, self.experiment_config.NUMBER_OF_MARCHING_PHASES + 1)[:-1]        
        self.stimulus_units = []
        self.overall_duration = 0
        orientations = copy.deepcopy(self.experiment_config.ORIENTATIONS)
        for repeat in range(self.experiment_config.REPEATS):
            for velocity in self.experiment_config.VELOCITIES:
                for white_bar_width in self.experiment_config.WHITE_BAR_WIDTHS:
                    for duty_cycle in self.experiment_config.DUTY_CYCLES:
#                        if repeat > 0:
#                            random.shuffle(orientations)
                        for orientation in orientations:
                            stimulus_unit = {}
                            stimulus_unit['white_bar_width'] = white_bar_width
                            stimulus_unit['velocity'] = velocity
                            stimulus_unit['duty_cycle'] = duty_cycle
                            stimulus_unit['orientation'] = orientation
                            period_length = (duty_cycle + 1) * white_bar_width
                            required_movement = period_length * self.experiment_config.NUMBER_OF_BAR_ADVANCE_OVER_POINT
                            stimulus_unit['move_time'] = float(required_movement) / velocity
                            #round it to the multiple of frame rate
                            stimulus_unit['move_time'] = \
                                        numpy.round(stimulus_unit['move_time'] * self.machine_config.SCREEN_EXPECTED_FRAME_RATE) / self.machine_config.SCREEN_EXPECTED_FRAME_RATE
                            self.overall_duration += stimulus_unit['move_time'] + self.experiment_config.NUMBER_OF_MARCHING_PHASES * self.experiment_config.MARCH_TIME + self.experiment_config.GRATING_STAND_TIME
                            self.stimulus_units.append(stimulus_unit)
        self.period_time = self.overall_duration / self.experiment_config.REPEATS
        if hasattr(self.machine_config, 'MAXIMUM_RECORDING_DURATION') and self.period_time > self.machine_config.MAXIMUM_RECORDING_DURATION:
            raise RuntimeError('Stimulus too long')
        self.fragment_durations = self.period_time*self.experiment_config.REPEATS + 2 * self.experiment_config.PAUSE_BEFORE_AFTER 
        if hasattr(self.experiment_config,  'ENABLE_FLASH') and  self.experiment_config.ENABLE_FLASH:
            self.fragment_durations+= self.experiment_config.FLASH_REPEATS * numpy.array(self.experiment_config.TIMING).sum()
        self.fragment_durations = [self.fragment_durations]
        self.number_of_fragments = len(self.fragment_durations)
        #Group stimulus units into fragments
        segment_pointer = 0
        self.fragmented_stimulus_units = [self.stimulus_units]
        self.experiment_specific_data = {}

    def run(self, fragment_id = 0):
        #Flash
        if hasattr(self.experiment_config,  'ENABLE_FLASH') and  self.experiment_config.ENABLE_FLASH:
            self.flash_stimulus('ff', self.experiment_config.TIMING, colors = self.experiment_config.WHITE, background_color = self.experiment_config.BLACK, repeats = self.experiment_config.FLASH_REPEATS)
        if hasattr(self.experiment_config, 'PROFILE'):
            profile = self.experiment_config.PROFILE
        else:
            profile = 'sqr'
        #moving grating
        frame_counter = 0
        segment_counter = 0
        self.experiment_specific_data['segment_info'] = {} 
        is_first_dislayed = False
        orientation = None
        for stimulus_unit in self.fragmented_stimulus_units[fragment_id]:
                #Show marching grating
                if orientation != stimulus_unit['orientation']:
                    self.block_trigger_pulse()
                orientation = stimulus_unit['orientation']
                if not is_first_dislayed:
                    is_first_dislayed = True
                    static_grating_duration = self.experiment_config.PAUSE_BEFORE_AFTER + self.experiment_config.MARCH_TIME
                else:
                    static_grating_duration = self.experiment_config.MARCH_TIME
                if hasattr(self.experiment_config, 'GREY_INSTEAD_OF_MARCHING') and self.experiment_config.GREY_INSTEAD_OF_MARCHING:
                        self.show_fullscreen(color = 0.5, duration = static_grating_duration)
                else:
                    for phase in self.marching_phases:
                        self.show_grating(duration = static_grating_duration, 
                                    profile = profile, 
                                    orientation = orientation, 
                                    velocity = 0, white_bar_width = stimulus_unit['white_bar_width'],
                                    duty_cycle = stimulus_unit['duty_cycle'],
                                    starting_phase = phase)
                #Show moving grating
                self.show_grating(duration = stimulus_unit['move_time'], 
                            profile = profile, 
                            orientation = orientation, 
                            velocity = stimulus_unit['velocity'], white_bar_width = stimulus_unit['white_bar_width'],
                            duty_cycle = stimulus_unit['duty_cycle'],
                            starting_phase = self.marching_phases[-1], 
                            block_trigger=True
                            )
                #Show static grating
                if self.experiment_config.GRATING_STAND_TIME>0:
                    self.show_grating(duration = self.experiment_config.GRATING_STAND_TIME, 
                            profile = profile, 
                            orientation = orientation, 
                            velocity = 0, white_bar_width = stimulus_unit['white_bar_width'],
                            duty_cycle = stimulus_unit['duty_cycle'])
                #Save segment info to help synchronizing stimulus with measurement data
                segment_info = {}#TODO: this is obsolete, remove it
                segment_info['fragment_id'] = fragment_id
                segment_info['orientation'] = orientation
                segment_info['velocity'] = stimulus_unit['velocity']
                segment_info['white_bar_width'] = stimulus_unit['white_bar_width']
                segment_info['duty_cycle'] = stimulus_unit['duty_cycle']
                segment_info['marching_phases'] = self.marching_phases
                segment_info['marching_start_frame'] = frame_counter
                frame_counter += int(self.experiment_config.NUMBER_OF_MARCHING_PHASES * self.experiment_config.MARCH_TIME * self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
                segment_info['moving_start_frame'] = frame_counter
                frame_counter += int(stimulus_unit['move_time'] * self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
                segment_info['standing_start_frame'] = frame_counter
                frame_counter += int(self.experiment_config.GRATING_STAND_TIME * self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
                segment_info['standing_last_frame'] = frame_counter-1
                segment_id = 'segment_{0:0=3.0f}' .format(segment_counter)
                self.experiment_specific_data['segment_info'][segment_id] = segment_info#TODO:redundant data, need to be removed
                segment_counter += 1
        time.sleep(self.experiment_config.PAUSE_BEFORE_AFTER)

class PixelSizeCalibration(experiment.Experiment):
    '''
    Helps pixel size calibration by showing 50 and 20 um circles
    '''
    def prepare(self):
        self.fragment_durations = [1.0]
        self.number_of_fragments = len(self.fragment_durations)

    def run(self):
        pattern = 0
        self.add_text('Circle at 100,100 um, diameter is 20 um.', color = (1.0,  0.0,  0.0), position = utils.cr((10.0, 30.0)))        
        while True:
            if pattern == 0:
                self.change_text(0, text = 'Circle at 100,100 um, diameter is 20 um.\n\nPress \'n\' to switch, \'s\' to stop.')
                self.show_shape(shape = 'circle', size = 20.0, pos = utils.cr((100, 100)))
            elif pattern == 1:
                self.change_text(0, text = 'Circle at 50,50 um, diameter is 50 um.\n\nPress \'n\' to switch, \'s\' to stop.')
                self.show_shape(shape = 'circle', size = 50.0, pos = utils.cr((50, 50)))
            else:
                pass
            if 'stop' in self.command_buffer:
                break
            elif 'next' in self.command_buffer:
                pattern += 1
                if pattern == 2:
                    pattern = 0
                self.command_buffer = ''

class NaturalMovieExperiment(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [len(os.listdir(self.experiment_config.FILENAME))/float(self.machine_config.SCREEN_EXPECTED_FRAME_RATE)]
        
    def run(self):
        if self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
            duration = 0
        elif self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
            raise RuntimeError('This frame rate is not possible')
        else:
            duration = 1.0/self.experiment_config.FRAME_RATE
        self.show_image(self.experiment_config.FILENAME,duration)

class NaturalBarsExperiment(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [self.experiment_config.DURATION*self.experiment_config.REPEATS*len(self.experiment_config.DIRECTIONS)]
        
    def run(self):
        for rep in range(self.experiment_config.REPEATS):
            if self.abort:
                break
            for directions in self.experiment_config.DIRECTIONS:
                if self.abort:
                    break
                self.show_natural_bars(speed = self.experiment_config.SPEED, duration=self.experiment_config.DURATION, minimal_spatial_period = None, spatial_resolution = self.machine_config.SCREEN_PIXEL_TO_UM_SCALE, intensity_levels = 255, direction = directions)

class LaserBeamStimulus(experiment.Experiment):
    def run(self):
        for i in range(self.experiment_config.REPEATS):
            if self.abort:
                break
            self.point_laser_beam(self.experiment_config.POSITIONS, self.experiment_config.JUMP_TIME, self.experiment_config.HOLD_TIME)
            
class ReceptiveFieldExplore(experiment.Experiment):
    '''
    When MESH_SIZE not defined or MESH_SIZE == None: shape_size and screen size determines the mesh size
    
    Repeats: flash or sequence
    
    Supported use cases: fixed size squares are presented with no gaps and no overlaps. Fractional squares are not shown at the edges
    '''
    def calculate_positions(self, display_range, center, repeats, mesh_size, colors=None,repeat_sequence = 1):
        positions = []
        step = {}
        for axis in ['row', 'col']:
            if not hasattr(self.experiment_config, 'MESH_SIZE') or self.experiment_config.MESH_SIZE == None:
                step[axis] = self.shape_size
            else:
                step[axis] = display_range[axis]/mesh_size[axis]
        vaf = 1 if self.machine_config.VERTICAL_AXIS_POSITIVE_DIRECTION == 'up' else -1
        for repeat in range(repeat_sequence):
            for row in range(mesh_size['row']):
                for col in range(mesh_size['col']):
                    position = utils.rc((-vaf*((row+0.5) * step['row']+center['row']-int(display_range['row']*0.5/step['row'])*step['row']), 
                                (col+0.5)* step['col']+center['col']-int(display_range['col']*0.5/step['row'])*step['row']))
                    if colors is None:
                        positions.extend(repeats*[position])
                    else:
                        for color in colors:
                            positions.extend(repeats*[[position, color]])
        return positions, utils.rc((step['row'],step['col']))
    
    def prepare(self):
        if hasattr(self.experiment_config, 'ENABLE_ZOOM') and self.experiment_config.ENABLE_ZOOM:
            #Calculate the mesh positions for the whole screen
            self.shape_size = display_range
            positions, display_range = self.calculate_positions(self.machine_config.SCREEN_SIZE_UM, utils.rc((0,0)), 1, self.experiment_config.MESH_SIZE, repeat_sequence = self.experiment_config.REPEAT_SEQUENCE)
            zoom_center = utils.rc_add(positions[self.experiment_config.SELECTED_POSITION], utils.rc_multiply_with_constant(display_range, 0.5), '-')
            self.positions, display_range = self.calculate_positions(display_range, zoom_center, self.experiment_config.REPEATS, self.experiment_config.ZOOM_MESH_SIZE, self.experiment_config.COLORS, repeat_sequence = self.experiment_config.REPEAT_SEQUENCE)
        else:
            self.shape_size = self.experiment_config.SHAPE_SIZE
            if not hasattr(self.experiment_config, 'DISPLAY_AREA'):
                display_area = self.machine_config.SCREEN_SIZE_UM
            else:
                display_area = self.experiment_config.DISPLAY_AREA
            if not hasattr(self.experiment_config, 'MESH_SIZE') or self.experiment_config.MESH_SIZE == None:
                mesh_size = utils.rc_multiply_with_constant(display_area, 1.0/self.experiment_config.SHAPE_SIZE)
                mesh_size = utils.rc((numpy.floor(mesh_size['row']), numpy.floor(mesh_size['col'])))
            else:
                mesh_size =  self.experiment_config.MESH_SIZE
            self.positions, display_range = self.calculate_positions(display_area, utils.rc((0,0)), self.experiment_config.REPEATS, mesh_size, self.experiment_config.COLORS, repeat_sequence = self.experiment_config.REPEAT_SEQUENCE)
        if self.experiment_config.ENABLE_RANDOM_ORDER:
            import random
            random.seed(0)
            random.shuffle(self.positions)
        self.fragment_durations = len(self.positions)* (self.experiment_config.ON_TIME + self.experiment_config.OFF_TIME) + 2*self.experiment_config.PAUSE_BEFORE_AFTER
        self.fragment_durations = [self.fragment_durations]
        self.stimulus_duration = self.fragment_durations[0]
            
    def run(self):
        self.show_fullscreen(color = self.experiment_config.BACKGROUND_COLOR, duration = self.experiment_config.PAUSE_BEFORE_AFTER)
        for position_color in self.positions:
            if self.abort:
                break
            self.show_shape(shape = self.experiment_config.SHAPE,
                                    size = self.shape_size,
                                    color = position_color[1],
                                    background_color = self.experiment_config.BACKGROUND_COLOR,
                                    duration = self.experiment_config.ON_TIME,
                                    pos = position_color[0])
            self.show_fullscreen(color = self.experiment_config.BACKGROUND_COLOR, duration = self.experiment_config.OFF_TIME)
        timeleft = self.experiment_config.PAUSE_BEFORE_AFTER-self.experiment_config.OFF_TIME
        self.show_fullscreen(color = self.experiment_config.BACKGROUND_COLOR, duration = 0 if timeleft < 0 else timeleft)
