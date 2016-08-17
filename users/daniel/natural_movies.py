from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils,signal
import os
import numpy
import copy
import time

class NaturalMovieWithGrayBackgnd(experiment.ExperimentConfig):
    def _create_parameters(self):
        # Movie Parameters
		self.MOVIE_REPEATS=1
        self.FILENAME = 'c:\\Data\\catcam17'
        self.FRAME_RATE=30.0 # Change frame rate back to 25 fps when possible (by adding images). 
        self.STRETCH = 2.75 # Covers 661 pixels vertical / 51 angular degrees. 
        self.runnable = 'NaturalMovieExperimentWithGray'
        
        # Grating Parameters
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 5
        self.MARCH_TIME = 10.0
        self.GRATING_STAND_TIME = 4.0
        
        self.ORIENTATIONS = range(0, 360, 90)
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.VELOCITIES = [1200.0]#1800
        self.DUTY_CYCLES = [3.0] #put 1.0 to a different config
        self.REPEATS = 3
        self.PAUSE_BEFORE_AFTER = 5.0
        self.COLOR_CONTRAST = 1.0
        
        self.GRATING_REPEATS = 2

        self.ENABLE_RANDOM_ORDER = True
        if self.ENABLE_RANDOM_ORDER:
            import random
            random.shuffle(self.ORIENTATIONS)
        
		# Gray Background Parameters
        self.FULLSCREEN_TIME = 180.0; # 5 Minutes
        self.FULLSCREEN_COLOR = 0.25; # Medium gray contrast
        
        self._create_parameters_from_locals(locals())
        
        
    def _create_parameters_from_locals(self, locals,  check_path = True):
        if len(locals['self'].DUTY_CYCLES)==1 and len(locals['self'].ORIENTATIONS)>1:
            locals['self'].DUTY_CYCLES=locals['self'].DUTY_CYCLES*len(locals['self'].ORIENTATIONS)
        experiment.ExperimentConfig._create_parameters_from_locals(self, locals)
        
class NaturalMovieExperimentWithGray(experiment.Experiment):
    def prepare(self):
        self.movie_fragment_durations = [len(os.listdir(self.experiment_config.FILENAME))/float(self.machine_config.SCREEN_EXPECTED_FRAME_RATE)]
        
        self.create_stimulus_units()
        
#       self.overall_duration *= len(self.experiment_config.ORIENTATIONS)
        self.period_time = self.overall_duration / self.experiment_config.GRATING_REPEATS
        self.grating_fragment_durations = self.period_time*self.experiment_config.GRATING_REPEATS + 2 * self.experiment_config.PAUSE_BEFORE_AFTER 
        if hasattr(self.experiment_config,  'ENABLE_FLASH') and  self.experiment_config.ENABLE_FLASH:
            self.grating_fragment_durations += self.experiment_config.FLASH_REPEATS * numpy.array(self.experiment_config.TIMING).sum()
        if hasattr(self.experiment_config,  'BLACK_SCREEN_DURATION'):
            self.grating_fragment_durations += self.experiment_config.BLACK_SCREEN_DURATION
        self.grating_fragment_durations = [self.grating_fragment_durations]
        self.number_of_fragments = len(self.grating_fragment_durations)
        
        #Group stimulus units into fragments
        segment_pointer = 0
        self.fragmented_stimulus_units = [self.stimulus_units]
        self.experiment_specific_data = {}
        
        self.fragment_durations = [self.movie_fragment_durations[0]*2 + self.grating_fragment_durations[0] + self.experiment_config.FULLSCREEN_TIME*4]
        
    def my_movie(self):
#        self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
        if self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
            duration = 0
        elif self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
            raise RuntimeError('This frame rate is not possible')
        else:
            duration = 1.0/self.experiment_config.FRAME_RATE
        for rep in range(self.experiment_config.MOVIE_REPEATS):
            #self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
            self.show_image(self.experiment_config.FILENAME,duration,stretch=self.experiment_config.STRETCH)
            #self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
            
    def my_grating(self,fragment_id = 0):
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
                if hasattr(self.experiment_config, 'GREY_INSTEAD_OF_MARCHING') and self.experiment_config.GREY_INSTEAD_OF_MARCHING:
                        self.show_fullscreen(color = 0, duration = static_grating_duration)
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
        
    def create_stimulus_units(self):
        '''From the parameters creates a list of dicts that will be played sequentially as grating stim
        '''
        self.marching_phases = -numpy.linspace(0, 360, self.experiment_config.NUMBER_OF_MARCHING_PHASES + 1)[:-1]        
        self.stimulus_units = []
        self.overall_duration = 0
        orientations = copy.deepcopy(self.experiment_config.ORIENTATIONS)
        if not hasattr(self.experiment_config,'PARAMETER_SEQUENCE'):
            parameter_sequence = []
            for repeat in range(self.experiment_config.GRATING_REPEATS):
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
            self.overall_duration += stimulus_unit['move_time'] + self.experiment_config.NUMBER_OF_MARCHING_PHASES * \
                                                                  self.experiment_config.MARCH_TIME + self.experiment_config.GRATING_STAND_TIME
            self.stimulus_units.append(stimulus_unit)
        
        
    def run(self):
        # Effectively, this is run when the code is called (and is required), but you don't have to run the code until 
        self.show_fullscreen(duration = self.experiment_config.FULLSCREEN_TIME,color = self.experiment_config.FULLSCREEN_COLOR)
        self.my_movie()
        self.show_fullscreen(duration = self.experiment_config.FULLSCREEN_TIME,color = self.experiment_config.FULLSCREEN_COLOR)
        self.my_grating()
        self.show_fullscreen(duration = self.experiment_config.FULLSCREEN_TIME,color = self.experiment_config.FULLSCREEN_COLOR)
        self.my_movie()
        self.show_fullscreen(duration = self.experiment_config.FULLSCREEN_TIME,color = self.experiment_config.FULLSCREEN_COLOR)
        # You can also have control signals here. 