import numpy
import copy
import time
#import random
import os
from visexpman.engine.generic import utils, signal, colors
from visexpman.engine.vision_experiment import experiment
#from visexpman.engine.generic import graphics,utils,,fileop, signal,geometry,videofile


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
        self.stimulus_frame_info.append({'super_block':'SpotWaveform', 'is_last':0, 'counter':self.frame_counter})
        for spot_diameter in self.experiment_config.SPOT_DIAMETERS:
            for intensities in self.intensities:
                self.show_fullscreen(color=self.experiment_config.BACKGROUND, duration = 0.5*self.experiment_config.PAUSE)
                self.show_shape(color = intensities, background_color = self.experiment_config.BACKGROUND, shape = 'spot', size = spot_diameter, block_trigger=True)
                self.show_fullscreen(color=self.experiment_config.BACKGROUND, duration = 0.5*self.experiment_config.PAUSE)
        self.stimulus_frame_info.append({'super_block':'SpotWaveform', 'is_last':1, 'counter':self.frame_counter})
                
class MovingShapeStimulus(experiment.Experiment):
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
            self.log.info('Stimulus duration: {0}'.format(self.stimulus_duration), source = 'stim')
    
    def run(self):
        self.stimulus_frame_info.append({'super_block':'MovingShapeStimulus', 'is_last':0, 'counter':self.frame_counter})
        self.moving_shape(size = self.experiment_config.SHAPE_SIZE,
                                  speeds = self.experiment_config.SPEEDS,
                                  directions = self.experiment_config.DIRECTIONS,
                                  shape = self.shape,
                                  color = self.shape_contrast,
                                  background_color = self.shape_background,
                                  pause = self.pause_between_directions,
                                  repetition = self.experiment_config.REPETITIONS,
                                  block_trigger = True,
                                  shape_starts_from_edge = True)
        self.stimulus_frame_info.append({'super_block':'MovingShapeStimulus', 'is_last':1, 'counter':self.frame_counter})
        
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
        self.stimulus_frame_info.append({'super_block':'IncreasingSpotExperiment', 'is_last':0, 'counter':self.frame_counter})
        self.show_fullscreen(color = self.background_color, duration = self.experiment_config.OFF_TIME)
        for color in self.colors:
            self.increasing_spot(   self.experiment_config.SIZES,
                                    self.experiment_config.ON_TIME,
                                    self.experiment_config.OFF_TIME,
                                    color = color,
                                    background_color = self.background_color,
                                    pos = utils.rc((0,  0)),
                                    block_trigger = True)
        self.stimulus_frame_info.append({'super_block':'IncreasingSpotExperiment', 'is_last':1, 'counter':self.frame_counter})

class FullFieldFlashesStimulus(experiment.Experiment):
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
        if hasattr(self.experiment_config, 'REPETITIONS'):
            self.repetitions = self.experiment_config.REPETITIONS
        else:
            self.repetitions = 1
        self.stimulus_duration = (self.experiment_config.ON_TIME+self.experiment_config.OFF_TIME)*self.repetitions*len(self.colors)

    def run(self):
        self.stimulus_frame_info.append({'super_block':'FullFieldFlashesStimulus', 'is_last':0, 'counter':self.frame_counter})
        for r in range(self.repetitions):
            self.show_fullscreen(duration=self.experiment_config.OFF_TIME,color=self.background_color,frame_trigger=True)
            for color in self.colors:
                self.block_start()
                self.show_fullscreen(duration=self.experiment_config.ON_TIME,color=color,frame_trigger=True)
                self.block_end()
                self.show_fullscreen(duration=self.experiment_config.OFF_TIME,color=self.background_color,frame_trigger=True)
        self.stimulus_frame_info.append({'super_block':'FullFieldFlashesStimulus', 'is_last':1, 'counter':self.frame_counter})
            

class MovingGratingStimulus(experiment.Experiment):
    '''
    Mandatory configuration parameters:
        REPEATS
        N_BAR_ADVANCES_OVER_POINT
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
                            required_movement = period_length * self.experiment_config.N_BAR_ADVANCES_OVER_POINT
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
        #segment_pointer = 0
        self.fragmented_stimulus_units = [self.stimulus_units]
        self.experiment_specific_data = {}
        self.stimulus_duration = self.overall_duration
        
    def run(self, fragment_id = 0):
        
        self.stimulus_frame_info.append({'super_block':'MovingGratingStimulus', 'is_last':0, 'counter':self.frame_counter})
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
                    #self.block_trigger_pulse()
                    self.block_start()
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
        self.stimulus_frame_info.append({'super_block':'MovingGratingStimulus', 'is_last':1, 'counter':self.frame_counter})

class PixelSizeCalibration(experiment.Experiment):
    '''
    Helps pixel size calibration by showing 50 and 20 um circles
    '''
    def prepare(self):
        self.fragment_durations = [1.0]
        self.number_of_fragments = len(self.fragment_durations)

    def run(self):
        self.stimulus_frame_info.append({'super_block':'PixelSizeCalibration', 'is_last':0, 'counter':self.frame_counter})
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
        self.stimulus_frame_info.append({'super_block':'PixelSizeCalibration', 'is_last':1, 'counter':self.frame_counter})

class NaturalMovieExperiment(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [len(os.listdir(self.experiment_config.FILENAME))/float(self.machine_config.SCREEN_EXPECTED_FRAME_RATE)]
        
    def run(self):
        self.stimulus_frame_info.append({'super_block':'NaturalMovieExperiment', 'is_last':0, 'counter':self.frame_counter})
        if self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
            duration = 0
        elif self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
            raise RuntimeError('This frame rate is not possible')
        else:
            duration = 1.0/self.experiment_config.FRAME_RATE
        self.show_image(self.experiment_config.FILENAME,duration)
        self.stimulus_frame_info.append({'super_block':'NaturalMovieExperiment', 'is_last':1, 'counter':self.frame_counter})

class NaturalBarsExperiment(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [self.experiment_config.DURATION*self.experiment_config.REPEATS*len(self.experiment_config.DIRECTIONS)]
        
    def run(self):
        
        self.stimulus_frame_info.append({'super_block':'NaturalBarsExperiment', 'is_last':0, 'counter':self.frame_counter})
        
        for rep in range(self.experiment_config.REPEATS):
            if self.abort:
                break
            for directions in self.experiment_config.DIRECTIONS:
                if self.abort:
                    break
                self.show_natural_bars( speed = self.experiment_config.SPEED,
                                        duration=self.experiment_config.DURATION,
                                        minimal_spatial_period = None,
                                        spatial_resolution = self.machine_config.SCREEN_PIXEL_TO_UM_SCALE,
                                        intensity_levels = 255,
                                        direction = directions)
        self.stimulus_frame_info.append({'super_block':'NaturalBarsExperiment', 'is_last':1, 'counter':self.frame_counter})

class LaserBeamStimulus(experiment.Experiment):
    def run(self):
        self.stimulus_frame_info.append({'super_block':'LaserBeamStimulus', 'is_last':0, 'counter':self.frame_counter})  
        for i in range(self.experiment_config.REPEATS):
            if self.abort:
                break
            self.point_laser_beam(self.experiment_config.POSITIONS, self.experiment_config.JUMP_TIME, self.experiment_config.HOLD_TIME)
        self.stimulus_frame_info.append({'super_block':'LaserBeamStimulus', 'is_last':1, 'counter':self.frame_counter})

class ReceptiveFieldExplore(experiment.Experiment):
    '''
    Repeats: flash or sequence
    
    Supported use cases: fixed size squares are presented with no gaps and no overlaps. Fractional squares are not shown at the edges
    '''
    def prepare(self):
        shape_size, nrows, ncolumns, display_size, shape_colors, background_color = \
                self._parse_receptive_field_parameters(self.experiment_config.SHAPE_SIZE if hasattr(self.experiment_config, 'SHAPE_SIZE') else None,
                                                    self.experiment_config.NROWS if hasattr(self.experiment_config, 'NROWS') else None,
                                                    self.experiment_config.NCOLUMNS if hasattr(self.experiment_config, 'NCOLUMNS') else None,
                                                    self.experiment_config.DISPLAY_SIZE if hasattr(self.experiment_config, 'DISPLAY_SIZE') else None,
                                                    self.experiment_config.COLORS,
                                                    self.experiment_config.BACKGROUND_COLOR)
        self.stimulus_duration, positions= self.receptive_field_explore_durations_and_positions(shape_size=shape_size, 
                                                                            nrows = nrows,
                                                                            ncolumns = ncolumns,
                                                                            shape_colors = shape_colors,
                                                                            flash_repeat = self.experiment_config.REPEATS,
                                                                            sequence_repeat = self.experiment_config.REPEAT_SEQUENCE,
                                                                            on_time = self.experiment_config.ON_TIME,
                                                                            off_time = self.experiment_config.OFF_TIME,
                                                                            overlap = self.experiment_config.OVERLAP if hasattr(self.experiment_config, 'OVERLAP') else [0,0])
        #print 'Projected Duration: ' + str(self.stimulus_duration)
        if hasattr(self.log, 'info'):
            self.log.info('Stimulus duration: {0}'.format(self.stimulus_duration), source = 'stim')

        
    def run(self):
        self.stimulus_frame_info.append({'super_block':'ReceptiveFieldExplore', 'is_last':0, 'counter':self.frame_counter})   
        self.receptive_field_explore(self.experiment_config.SHAPE_SIZE if hasattr(self.experiment_config, 'SHAPE_SIZE') else None, 
                                    self.experiment_config.ON_TIME,
                                    self.experiment_config.OFF_TIME,
                                    nrows = self.experiment_config.NROWS if hasattr(self.experiment_config, 'NROWS') else None,
                                    ncolumns = self.experiment_config.NCOLUMNS if hasattr(self.experiment_config, 'NCOLUMNS') else None,
                                    display_size = self.experiment_config.DISPLAY_SIZE if hasattr(self.experiment_config, 'DISPLAY_SIZE') else None,
                                    flash_repeat = self.experiment_config.REPEATS, 
                                    sequence_repeat = self.experiment_config.REPEAT_SEQUENCE,
                                    background_color = self.experiment_config.BACKGROUND_COLOR, 
                                    shape_colors = self.experiment_config.COLORS, 
                                    random_order = self.experiment_config.ENABLE_RANDOM_ORDER,
                                    overlap = self.experiment_config.OVERLAP if hasattr(self.experiment_config, 'OVERLAP') else [0,0],
                                    )
        self.show_fullscreen(color = self.experiment_config.BACKGROUND_COLOR)
        self.stimulus_frame_info.append({'super_block':'ReceptiveFieldExplore', 'is_last':1, 'counter':self.frame_counter})  
        self.user_data = { 'nrows':self.nrows,  'ncolumns': self.ncolumns,  'shape_size':self.shape_size}


class DashStimulus(experiment.Experiment):
    '''
        Required:
            BARSIZE:     list of 2 elements: bar width and length
            GAPSIZE:     list of 2 elements: gap width and length
            MOVINGLINES: number that specifies how many lines are skipped during movement
            DURATION:    in seconds
            SPEEDS:      list of speeds in um/s
            DIRECTIONS:  list of directions
            BAR_COLOR:   either a float of a 3 element RGB-list
            REPETITIONS: how many times sequence is repeated
    '''
    def prepare(self):
        self.bgcolor = self.config.BACKGROUND_COLOR
        if hasattr(self.experiment_config, 'BACKGROUND_COLOR'):
            self.bgcolor = colors.convert_color(self.experiment_config.BACKGROUND_COLOR, self.config)
        
        self.barcolor = self.experiment_config.BAR_COLOR
        if type(self.barcolor) is float or type(self.barcolor) is int:
            self.barcolor = colors.convert_color(self.experiment_config.BAR_COLOR, self.config)
        
        self.texture = self.create_bar(size=[128,128],
                                       bar=self.experiment_config.BARSIZE,
                                       gap=self.experiment_config.GAPSIZE,
                                       bgcolor = self.bgcolor, 
                                       barcolor=self.barcolor)
        
        self.texture_size = numpy.array(self.experiment_config.BARSIZE) + numpy.array(self.experiment_config.GAPSIZE)
        self.texture_info = {'bar_size':self.experiment_config.BARSIZE,
                             'gap_size':self.experiment_config.GAPSIZE,
                             'bar_color':self.barcolor,
                             'bgcolor':self.bgcolor,
                            }
                            
        self.stimulus_duration = len(self.experiment_config.DIRECTIONS)*\
                                 len(self.experiment_config.SPEEDS)*\
                                 self.experiment_config.DURATION*\
                                 self.experiment_config.MOVINGLINES*\
                                 self.experiment_config.REPETITIONS
    
    def run(self):
        self.stimulus_frame_info.append({'super_block':'DashStimulus', 'is_last':0, 'counter':self.frame_counter})
        
        for repeat in range(self.experiment_config.REPETITIONS):
            for speed in self.experiment_config.SPEEDS:
                for direction in self.experiment_config.DIRECTIONS:
                    self.show_dashes(texture = self.texture,
                                    texture_size = self.texture_size,
                                    texture_info = self.texture_info,
                                    movingLines = self.experiment_config.MOVINGLINES,
                                    duration = self.experiment_config.DURATION,
                                    speed = speed,
                                    direction = direction,
                                    )
        self.stimulus_frame_info.append({'super_block':'DashStimulus', 'is_last':1, 'counter':self.frame_counter})
    
    
    def create_bar(self, size, bar, gap, bgcolor = [0,0,0], barcolor = [1,1,1]):# width_ratio = 1.0, length_ratio = 1.0):
        # Create BAR texture:
        texture_W = size[0]
        texture_L = size[1]
        
        bar_ = copy.copy(bar)
        gap_ = copy.copy(gap)
        
        fw = texture_W / float(bar[0]+gap[0])
        gap_[0] = int(gap[0]*fw*0.5)*2
        bar_[0] = texture_W - gap_[0]
        
        fl = texture_L / float(bar[1]+gap[1])
        gap_[1] = int(gap[1]*fl*0.5)*2
        bar_[1] = texture_L-gap_[1]
        
        bg_color  = numpy.array([bgcolor])
        bar_color = numpy.array([barcolor])
        
        # Upper and lower gap_ between dashes
        gap_w = numpy.repeat([numpy.repeat(bg_color, texture_W, axis=0)], 0.5*gap_[0], axis=0)
        
        # Left and right gap between dashes
        gap_l = numpy.repeat(bg_color, 0.5*gap_[1], axis=0)
        # Dash itself (one dimensional)
        dash_l = numpy.repeat(bar_color, bar_[1], axis=0)
        
        # Dash and left-right gaps in 2D
        dash = numpy.repeat([numpy.concatenate((gap_l, dash_l, gap_l))], bar_[0], axis=0)
        return numpy.concatenate((gap_w, dash, gap_w)) 


class FingerPrintingStimulus(experiment.Experiment):
    '''
        Required:
            DURATION
            INTENSITY_LEVELS
            SPEEDS
            DIRECTIONS
            REPEATS
        Optional:
            SPATIAL_PERIOD
            MIN_SPATIAL_PERIOD
    '''           
    def prepare(self):
        duration = self.experiment_config.DURATION
        intensity_levels = self.experiment_config.INTENSITY_LEVELS
        try:
            spatial_resolution = self.experiment_config.SPATIAL_PERIOD
        except:
            spatial_resolution = self.machine_config.SCREEN_PIXEL_TO_UM_SCALE
        try:
            #minimal_spatial_period = self.experiment_config.MIN_SPATIAL_PERIOD
            self.experiment_config.MIN_SPATIAL_PERIOD
        except:
            self.experiment_config.MIN_SPATIAL_PERIOD = [10 * spatial_resolution]
            #minimal_spatial_period = 10 * spatial_resolution
        
        screen_size = numpy.array([self.config.SCREEN_RESOLUTION['row'], self.config.SCREEN_RESOLUTION['col']])
        
        # Create intensity profile(s):
        self.intensity_profiles = {}
        for speed in self.experiment_config.SPEEDS:
            self.intensity_profiles[speed] = {}
            for minimal_spatial_period in self.experiment_config.MIN_SPATIAL_PERIOD:
            
                intensity_profile = signal.generate_natural_stimulus_intensity_profile(duration=duration, 
                                                                                       speed=speed,
                                                                                       intensity_levels=intensity_levels,
                                                                                       minimal_spatial_period=minimal_spatial_period,
                                                                                       spatial_resolution=spatial_resolution,
                                                                                       )
                
                intensity_profile = numpy.concatenate((numpy.zeros(1.5*screen_size[1]), intensity_profile, numpy.zeros(1.5*screen_size[1])) )
                #if intensity_profile.shape[0] < self.config.SCREEN_RESOLUTION['col']:
                #    intensity_profile = numpy.tile(intensity_profile, numpy.ceil(float(self.config.SCREEN_RESOLUTION['col'])/intensity_profile.shape[0]))
                self.intensity_profiles[speed][minimal_spatial_period] = intensity_profile
            
        self.stimulus_duration = duration
        self.stimulus_duration *= len(self.experiment_config.SPEEDS) 
        self.stimulus_duration *= len(self.experiment_config.MIN_SPATIAL_PERIOD) 
        self.stimulus_duration *= self.experiment_config.REPEATS
    
    def run(self):
        self.stimulus_frame_info.append({'super_block':'FingerPrintingStimulus', 'is_last':0, 'counter':self.frame_counter})
        
        for rep in range(self.experiment_config.REPEATS):
            for speed in self.experiment_config.SPEEDS:
                for minimal_spatial_period in self.experiment_config.MIN_SPATIAL_PERIOD:
                    for direction in self.experiment_config.DIRECTIONS:
                        self.show_fingerprint(self.intensity_profiles[speed][minimal_spatial_period], speed, direction = direction, minimal_spatial_period=minimal_spatial_period, forward=True)
                        
                
        self.stimulus_frame_info.append({'super_block':'FingerPrintingStimulus', 'is_last': 1, 'counter':self.frame_counter})

class WhiteNoiseStimulus(experiment.Experiment):
    '''
        Required:
            DURATION_MINS: in minutes (!)
            PIXEL_SIZE
            COLORS
        Optional:
            FLICKERING_FREQUENCY
    '''
    def prepare(self):
        self.n_white_pixels = self.experiment_config.N_WHITE_PIXELS
        if not self.experiment_config.N_WHITE_PIXELS:
            self.n_white_pixels = None;
        self.stimulus_duration = self.experiment_config.DURATION_MINS*60.0
        
        try:
            self.flickering_frequency = self.experiment_config.FLICKERING_FREQUENCY
        except:
            self.flickering_frequency = self.config.SCREEN_EXPECTED_FRAME_RATE
        
        self.colors = self.experiment_config.COLORS
        npatterns = self.experiment_config.DURATION_MINS*60.0*self.flickering_frequency
        
        screen_size = numpy.array([self.config.SCREEN_RESOLUTION['row'], self.config.SCREEN_RESOLUTION['col']])
        pixel_size = numpy.array(self.experiment_config.PIXEL_SIZE)
        if pixel_size.shape[0] == 1:
            pixel_size = [pixel_size[0], pixel_size[0]]
        
        npixels = numpy.round(screen_size/pixel_size)
        n_channels = 1
        color = numpy.zeros((npatterns, npixels[0], npixels[1], n_channels))
        numpy.random.seed(0)
        self.textures = numpy.round(numpy.random.random(color.shape[:-1]))
        
        
    def run(self):
        #random.seed(0)
        self.stimulus_frame_info.append({'super_block':'WhiteNoiseStimulus', 'is_last':0, 'counter':self.frame_counter})
        self.white_noise(textures = self.textures, color_0 = self.colors[0], color_1 = self.colors[1])
        self.show_fullscreen(color=0.5)
        self.stimulus_frame_info.append({'super_block':'WhiteNoiseStimulus', 'is_last':1, 'counter':self.frame_counter})  
    # End of WhiteNoiseStimulus

class Chirp(experiment.Experiment):
    '''
        Required:
            DURATION: in seconds
            CONTRAST_RANGE
            FREQUENCY_RANGE
            REPEATS
        Optional:
            COLOR
    '''
    def prepare(self):
        self.repeats = self.experiment_config.REPEATS
        self.stimulus_duration = self.experiment_config.DURATION*self.experiment_config.REPEATS
        self.contrast_range = numpy.array(self.experiment_config.CONTRAST_RANGE)
        self.frequency_range = numpy.array(self.experiment_config.FREQUENCY_RANGE)
        
        if any(self.frequency_range > self.config.SCREEN_EXPECTED_FRAME_RATE):
            raise RuntimeError('This frequency range is not possible!')
        
        if hasattr(self.experiment_config, 'COLOR'):
            self.color = self.experiment_config.COLOR
        else:
            self.color = numpy.array([1.0, 1.0, 1.0])
        
    def run(self):
        
        self.stimulus_frame_info.append({'super_block':'Chirp', 'is_last':0, 'counter':self.frame_counter})
        
        for rep in range(self.experiment_config.REPEATS):
            self.chirp(stimulus_duration = self.stimulus_duration, contrast_range = self.contrast_range, frequency_range = self.frequency_range, color = self.color)         
            self.show_fullscreen(color=0.5)
        
        self.stimulus_frame_info.append({'super_block':'Chirp', 'is_last':1, 'counter':self.frame_counter})
    # End of Chirp

class ChirpSweep(experiment.Experiment):
    '''
        Similar to Chirp stimulus, but designed such that there will be a full 
        field stimulus first (contrast defined by maximal contrast_range), then
        a frequency sweep and followed by an amplitude sweep.
        During the breaks  before and after the full filed stimulus, as well as
        after the second chirp, we will display the minimal contrast value.
        (see Baden et al. 2016)
        
        Required:
            DURATION_BREAKS
            DURATION_FULLFIELD
            DURATION_FREQ
            DURATION_CONTRAST
            FREQUENCY_RANGE
            CONTRAST_RANGE
            STATIC_FREQUENCY
            REPEATS
        Optional:
            COLOR
    '''
    def prepare(self):
        self.repeats = self.experiment_config.REPEATS
        self.duration_freq = self.experiment_config.DURATION_FREQ
        self.duration_contrast = self.experiment_config.DURATION_CONTRAST
        self.duration_fullfield = self.experiment_config.DURATION_FULLFIELD
        self.duration_breaks = self.experiment_config.DURATION_BREAKS
        
        self.stimulus_duration = self.experiment_config.REPEATS*(self.duration_freq+self.duration_contrast+self.duration_fullfield+2*self.duration_breaks)
        self.contrast_range = numpy.array(self.experiment_config.CONTRAST_RANGE)
        self.frequency_range = numpy.array(self.experiment_config.FREQUENCY_RANGE)
        self.static_frequency = self.experiment_config.STATIC_FREQUENCY        
        
        if any(self.frequency_range > self.config.SCREEN_EXPECTED_FRAME_RATE):
            raise RuntimeError('This frequency range is not possible!')
        
        if hasattr(self.experiment_config, 'COLOR'):
            self.color = numpy.array(self.experiment_config.COLOR)
        else:
            self.color = numpy.array([1.0, 1.0, 1.0])
        
    def run(self):
        mid_contrast = numpy.mean(self.contrast_range)
    
        #self.stimulus_frame_info.append({'super_block':'ChirpSweep', 'is_last':0, 'counter':self.frame_counter})
        for rep in range(self.experiment_config.REPEATS):
            self.stimulus_frame_info.append({'super_block':'ChirpSweep', 'is_last':0, 'counter':self.frame_counter})
        
            # Full Field:
            self.show_fullscreen(duration = self.duration_breaks, color = self.color*self.contrast_range[0])

            self.show_fullscreen(duration = self.duration_fullfield, color = self.color*self.contrast_range[1])
            
            self.show_fullscreen(duration = self.duration_fullfield, color = self.color*self.contrast_range[0])
            
            # Frequency Chirp:
            self.show_fullscreen(duration = self.duration_breaks, color = self.color*mid_contrast) 
            self.chirp(stimulus_duration = self.duration_freq, 
                       contrast_range = numpy.array([self.contrast_range[1], self.contrast_range[1]]), 
                       frequency_range = self.frequency_range, color = self.color)
            
            # Contrast Chirp:
            self.chirp(stimulus_duration = self.duration_contrast,
                        contrast_range = self.contrast_range,
                        frequency_range = numpy.array([self.static_frequency,self.static_frequency]),
                        color = self.color)
            
            self.show_fullscreen(duration = self.duration_breaks, color = self.color*mid_contrast)
            self.show_fullscreen(duration = self.duration_breaks, color = self.color*self.contrast_range[0])
            
            self.stimulus_frame_info.append({'super_block':'ChirpSweep', 'is_last':1, 'counter':self.frame_counter})
            
        #self.stimulus_frame_info.append({'super_block':'ChirpSweep', 'is_last':1, 'counter':self.frame_counter})
    # End of ChirpSweep

class BatchStimulus(experiment.Experiment):
    '''
        Required parameters:
        VARS: dict with each 'runnable' experiment.Experiment class as first keys and
            their required variables as second keys.
            
        E.g.:
            self.VARS = {}
            self.VARS['FingerPrinting'] = {}
            self.VARS['FingerPrinting']['FF_PAUSE_DURATION'] = 1.0
            ...
            self.VARS['DashStimulus'] = {}
            self.VARS['DashStimulus']['BARSIZE'] = [25, 100]
    '''    
    
    def prepare(self):
        '''
            This function creates all the sub-stimuli and calls their 'prepare' functions.
        '''        
        print 'Preparing Batch Stimulus'
        self.stimulus_duration = 0.0
        
        self.experiments = {}
        for stimulus_name in self.experiment_config.VARS:
            print 'Adding sub-stimulus: ' + stimulus_name
            stimulus_type = self.experiment_config.STIM_TYPE_CLASS[stimulus_name]
            
            # Pass on ExperimentConfig to sub classes:
            this_config = experiment.ExperimentConfig(machine_config=None, runnable=stimulus_name)
            for var_name in self.experiment_config.VARS[stimulus_name]:
                setattr(this_config, var_name, self.experiment_config.VARS[stimulus_name][var_name])
            
            self.experiments[stimulus_name] = eval(stimulus_type)(machine_config = self.machine_config,
                                                                      digital_output = self.digital_output,
                                                                      experiment_config=this_config,
                                                                      queues = self.queues,
                                                                      parameters = self.parameters,
                                                                      log = self.log,
                                                                      )                                                    
            self.experiments[stimulus_name].prepare()
            self.stimulus_duration += self.experiments[stimulus_name].stimulus_duration
        print "Projected BatchStimulus duration: " + str(self.stimulus_duration)
        
    def run(self):
        '''
            This function iterates all sub-stimuli and calls their 'run' functions.
            
            The variable 'frame_counter' has to be passed and retrieved directly
            to/from the sub-stimulus class.
        '''
        for stimulus_name in self.experiment_config.VARS:           
            # Before starting sub_experiment, update the frame_counter:
            self.experiments[stimulus_name].frame_counter = self.frame_counter
            self.experiments[stimulus_name].run()
            self.frame_counter = self.experiments[stimulus_name].frame_counter

            for info in self.experiments[stimulus_name].stimulus_frame_info:           
                self.stimulus_frame_info.append(info)
            
            # After each sub_experiment, add one second of white fullscreen:
            self.stimulus_frame_info.append({'super_block':'FullScreen', 'is_last':0, 'counter':self.frame_counter})     
            self.show_fullscreen(duration=1.0, color=1.0, frame_trigger=True)
            self.stimulus_frame_info.append({'super_block':'FullScreen', 'is_last':1, 'counter':self.frame_counter})


