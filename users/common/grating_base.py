from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
import numpy
import time
import random
import copy

class MovingGratingConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        #Timing        
        self.NUMBER_OF_MARCHING_PHASES = 4 #number of static bar compositions at beginning
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3 #how many times the bar hit a point -> this + speed = moving time
        self.MARCH_TIME = 2.5 # standing phase time
        self.GRATING_STAND_TIME = 2.0 #post-moving-phase time
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 45)
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.WHITE_BAR_WIDTHS = [300.0]
        self.VELOCITIES = [1200.0]
        self.DUTY_CYCLES = [2.5] #white and blck bar ratio -> number of bars 
        self.REPEATS = 3
        self.PAUSE_BEFORE_AFTER = 5.0 #very beginning and end witing time
        self.COLOR_CONTRAST = 1.0
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
        self._create_parameters_from_locals(locals())
    
    def _create_parameters_from_locals(self, locals,  check_path = True):
        if len(locals['self'].DUTY_CYCLES)==1 and len(locals['self'].ORIENTATIONS)>1:
            locals['self'].DUTY_CYCLES=locals['self'].DUTY_CYCLES*len(locals['self'].ORIENTATIONS)
        experiment.ExperimentConfig._create_parameters_from_locals(self, locals)


class MovingGratingNoMarchingConfig(MovingGratingConfig):
    def _create_parameters(self):
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 4
        self.MARCH_TIME = 4.0
        self.GRATING_STAND_TIME = 4.0
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 45)
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.VELOCITIES = [1200.0]#1800
        self.DUTY_CYCLES = [3.0] #put 1.0 to a different config
        self.REPEATS = 2
        self.PAUSE_BEFORE_AFTER = 5.0
        self.COLOR_CONTRAST = 1.0
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
#        self.pre_runnable = 'BlackPre'
        self._create_parameters_from_locals(locals())       

class BlackPre(experiment.PreExperiment):    
    def run(self):
        self.show_fullscreen(color = 0.0, duration = 0,flip=False)
                
class MovingGrating(experiment.Experiment):
    def create_stimulus_units(self):
        '''From the parameters creates a list of dicts that will be played sequentially as grating stim
        '''
        self.marching_phases = -numpy.linspace(0, 360, self.experiment_config.NUMBER_OF_MARCHING_PHASES + 1)[:-1]        
        self.stimulus_units = []
        self.overall_duration = 0
        orientations = copy.deepcopy(self.experiment_config.ORIENTATIONS)
        if not hasattr(self.experiment_config,'PARAMETER_SEQUENCE'):
            parameter_sequence = []
            for repeat in range(self.experiment_config.REPEATS):
                for velocity in self.experiment_config.VELOCITIES:
                    for white_bar_width in self.experiment_config.WHITE_BAR_WIDTHS:
                        #if repeat > 0:
    #                            random.shuffle(orientations)
                        for o1 in range(len(orientations)):
                            parameter_sequence.append((velocity, white_bar_width, o1))
        else:
            parameter_sequence = self.experiment_config.PARAMETER_SEQUENCE   # user can provide tuples of velocity, white_bar_width and orientation
        for velocity, white_bar_width, o1 in parameter_sequence:
            orientation = orientations[o1]
            duty_cycle = self.experiment_config.DUTY_CYCLES[o1]
            stimulus_unit = {}
            stimulus_unit['white_bar_width'] = white_bar_width
            stimulus_unit['velocity'] = velocity
            stimulus_unit['duty_cycle'] = duty_cycle
            stimulus_unit['orientation'] = orientation
            stimulus_unit['starting_phase']=self.experiment_config.STARTING_PHASES[o1]
            stimulus_unit['color_contrast']=self.experiment_config.COLOR_CONTRAST
            period_length = (duty_cycle + 1) * white_bar_width
            required_movement = period_length * self.experiment_config.NUMBER_OF_BAR_ADVANCE_OVER_POINT
            stimulus_unit['move_time'] = float(required_movement) / velocity
            #round it to the multiple of frame rate
            stimulus_unit['move_time'] = \
                        numpy.round(stimulus_unit['move_time'] * self.machine_config.SCREEN_EXPECTED_FRAME_RATE) / self.machine_config.SCREEN_EXPECTED_FRAME_RATE
            
            if hasattr(self.experiment_config, 'PHASES'):
                stimulus_unit['phases']=self.experiment_config.PHASES[orientation]
                stimulus_unit['move_time']=float(stimulus_unit['phases'].shape[0])/self.machine_config.SCREEN_EXPECTED_FRAME_RATE
            self.overall_duration += stimulus_unit['move_time'] + self.experiment_config.NUMBER_OF_MARCHING_PHASES * \
                                                                  self.experiment_config.MARCH_TIME + self.experiment_config.GRATING_STAND_TIME
            self.stimulus_units.append(stimulus_unit)
      
    def prepare(self):
        self.create_stimulus_units()
        
#         self.overall_duration *= len(self.experiment_config.ORIENTATIONS)
        self.period_time = self.overall_duration / self.experiment_config.REPEATS
        self.fragment_durations = self.period_time*self.experiment_config.REPEATS + 2 * self.experiment_config.PAUSE_BEFORE_AFTER 
        if hasattr(self.experiment_config,  'ENABLE_FLASH') and  self.experiment_config.ENABLE_FLASH:
            self.fragment_durations += self.experiment_config.FLASH_REPEATS * numpy.array(self.experiment_config.TIMING).sum()
        if hasattr(self.experiment_config,  'BLACK_SCREEN_DURATION'):
            self.fragment_durations += self.experiment_config.BLACK_SCREEN_DURATION
        self.fragment_durations = [self.fragment_durations]
        self.number_of_fragments = len(self.fragment_durations)
        #Group stimulus units into fragments
        segment_pointer = 0
        self.fragmented_stimulus_units = [self.stimulus_units]
        self.experiment_specific_data = {}

    def run(self, fragment_id = 0):
        import sys
        if '--MICROLED'in sys.argv:
            self.config.STIMULUS2MEMORY = True
        #Flash
        if hasattr(self.experiment_config,  'ENABLE_FLASH') and  self.experiment_config.ENABLE_FLASH:
            self.flash_stimulus(self.experiment_config.TIMING, flash_color = self.experiment_config.WHITE, background_color = self.experiment_config.BLACK, repeats = self.experiment_config.FLASH_REPEATS)
        if hasattr(self.experiment_config,  'BLACK_SCREEN_DURATION'):
            self.show_fullscreen(color = 0.0, duration = self.experiment_config.BLACK_SCREEN_DURATION)
        if hasattr(self.experiment_config, 'PROFILE'):
            profile = self.experiment_config.PROFILE
        else:
            profile = 'sqr'
        color_contrast = self.experiment_config.COLOR_CONTRAST if hasattr(self.experiment_config,'COLOR_CONTRAST') else 1.0
        #moving grating
        frame_counter = 0
        segment_counter = 0
        self.experiment_specific_data['segment_info'] = {} 
        is_first_dislayed = False
        for stimulus_unit in self.fragmented_stimulus_units[fragment_id]:
                #Show marching grating
                orientation = stimulus_unit['orientation']
                if not is_first_dislayed:
                    is_first_dislayed = True
                    static_grating_duration = self.experiment_config.PAUSE_BEFORE_AFTER + self.experiment_config.MARCH_TIME
                else:
                    static_grating_duration = self.experiment_config.MARCH_TIME
                    
                if hasattr(self.experiment_config, 'GREY_INSTEAD_OF_MARCHING_COLOR'):
                    marching_color = self.experiment_config.GREY_INSTEAD_OF_MARCHING_COLOR
                else:
                    marching_color = 0
                if hasattr(self.experiment_config, 'GREY_INSTEAD_OF_MARCHING') and self.experiment_config.GREY_INSTEAD_OF_MARCHING:
                        self.show_fullscreen(color = marching_color, duration = static_grating_duration)
                else:
                    for phase in self.marching_phases:
                        self.show_grating(duration = static_grating_duration, 
                                    profile = profile, 
                                    orientation = orientation, 
                                    velocity = 0, white_bar_width = stimulus_unit['white_bar_width'],
                                    duty_cycle = stimulus_unit['duty_cycle'],
                                    starting_phase = phase+stimulus_unit['starting_phase'],
                                    color_contrast = stimulus_unit['color_contrast'])
                #Show moving grating
                if stimulus_unit.has_key('phases'):
                    self.show_grating(
                            profile = profile, 
                            orientation = orientation, 
                            duty_cycle = stimulus_unit['duty_cycle'],
                            starting_phase = self.marching_phases[-1]+stimulus_unit['starting_phase'], 
                            color_contrast = stimulus_unit['color_contrast'],
                            phases=stimulus_unit['phases'])
                else:
                    self.show_grating(duration = stimulus_unit['move_time'], 
                            profile = profile, 
                            orientation = orientation, 
                            velocity = stimulus_unit['velocity'], white_bar_width = stimulus_unit['white_bar_width'],
                            duty_cycle = stimulus_unit['duty_cycle'],
                            starting_phase = self.marching_phases[-1]+stimulus_unit['starting_phase'], 
                            color_contrast = stimulus_unit['color_contrast']
                            )
                #Show static grating
                if self.experiment_config.GRATING_STAND_TIME>0:
                    self.show_grating(duration = self.experiment_config.GRATING_STAND_TIME, 
                            profile = profile, 
                            orientation = orientation, 
                            velocity = 0, white_bar_width = stimulus_unit['white_bar_width'],
                            duty_cycle = stimulus_unit['duty_cycle'],starting_phase = self.marching_phases[0]+stimulus_unit['starting_phase'],
                            color_contrast = stimulus_unit['color_contrast'])
                #Save segment info to help synchronizing stimulus with measurement data
                segment_info = {}
                segment_info['fragment_id'] = fragment_id
                segment_info['orientation'] = orientation
                segment_info['velocity'] = stimulus_unit['velocity']
                segment_info['white_bar_width'] = stimulus_unit['white_bar_width']
                segment_info['duty_cycle'] = stimulus_unit['duty_cycle']
                segment_info['marching_phases'] = self.marching_phases
                segment_info['starting_phases'] = self.experiment_config.STARTING_PHASES
                segment_info['marching_start_frame'] = frame_counter
                frame_counter += int(self.experiment_config.NUMBER_OF_MARCHING_PHASES * self.experiment_config.MARCH_TIME * self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
                segment_info['moving_start_frame'] = frame_counter
                frame_counter += int(stimulus_unit['move_time'] * self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
                segment_info['standing_start_frame'] = frame_counter
                frame_counter += int(self.experiment_config.GRATING_STAND_TIME * self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
                segment_info['standing_last_frame'] = frame_counter-1
                segment_id = 'segment_{0:3.0f}' .format(segment_counter)
                segment_id = segment_id.replace(' ', '0')
                self.experiment_specific_data['segment_info'][segment_id] = segment_info
                segment_counter += 1
        if '--MICROLED'in sys.argv:
            self.config.STIMULUS2MEMORY = False
            s = MicroLEDArray(self.machine_config)
            for frame_i in range(len(self.stimulus_bitmaps)):
                pixels = self.stimulus_bitmaps[frame_i]
                s.display_pixels(pixels, 1/self.machine_config.SCREEN_EXPECTED_FRAME_RATE-self.machine_config.FRAME_TRIGGER_PULSE_WIDTH)
                self._frame_trigger_pulse()
            s.release_instrument()
        time.sleep(self.experiment_config.PAUSE_BEFORE_AFTER)
        if hasattr(self.experiment_config, 'CLEAR_SCREEN_AT_END') and self.experiment_config.CLEAR_SCREEN_AT_END:
            self.show_fullscreen(color=self.experiment_config.CLEAR_SCREEN_AT_END_COLOR,duration=0)
               
class MovingGratingPre(experiment.PreExperiment):    
    def run(self):
        if hasattr(self.experiment_config, 'PROFILE'):
            profile = self.experiment_config.PROFILE
        else:
            profile = 'sqr'
        color_contrast = self.experiment_config.COLOR_CONTRAST if hasattr(self.experiment_config,'COLOR_CONTRAST') else 1.0
        self.show_grating(duration = 0, profile = profile,
                            orientation = self.experiment_config.ORIENTATIONS[0], color_contrast = color_contrast, 
                            velocity = 0, white_bar_width = self.experiment_config.WHITE_BAR_WIDTHS[0],
                            duty_cycle = self.experiment_config.DUTY_CYCLES[0], part_of_drawing_sequence = True, starting_phase = self.experiment_config.STARTING_PHASES[0])
                          

class PixelSizeCalibrationConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'PixelSizeCalibration'
        self._create_parameters_from_locals(locals())

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
                


#Support for old config classes
class GratingConfig(MovingGratingConfig):
    pass
