import numpy
import copy
import time
import random
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

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
        for color in self.colors:
            self.increasing_spot(self.experiment_config.SIZES, self.experiment_config.ON_TIME, self.experiment_config.OFF_TIME,
                    color = color, background_color = self.background_color, pos = utils.rc((0,  0)), block_trigger = True)

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
        for stimulus_unit in self.fragmented_stimulus_units[fragment_id]:
                #Show marching grating
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
                            starting_phase = 1/(1+stimulus_unit['duty_cycle'])*360, 
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
                segment_id = 'segment_{0:3.0f}' .format(segment_counter)
                segment_id = segment_id.replace(' ', '0')
                self.experiment_specific_data['segment_info'][segment_id] = segment_info
                segment_counter += 1
        time.sleep(self.experiment_config.PAUSE_BEFORE_AFTER)
