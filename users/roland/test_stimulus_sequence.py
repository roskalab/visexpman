import numpy
import copy
import time
import random
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

#from stimuli import *

class RolandTestStimulusSequenceConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPEEDS = [2000, 4000]
        #self.OFF_TIME = 1.0
        #self.ON_TIME = 5.0
        #self.SIZES = 100
        self.REPETITIONS = 1
        self.PAUSE_BETWEEN_DIRECTIONS = 0.0
        #self.stimulus_only = True
        self.SHAPE_SIZE = 100
        self.DIRECTIONS = [0, 90, 135]
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 20
        self.SCREEN_EXPECTED_FRAME_RATE = 60
        self.PROFILE = 'sqr'
        self.SHAPE = 'rect'
        self.runnable = 'RolandTestStimulusSequence'
        print 'z'

class RolandTestStimulusSequence(experiment.Experiment):
    stimuli = []
    
    def prepare(self):
        parameter_default_values = {
        'REPETITIONS': 1, 
        'SHAPE': 'rect', 
        'SHAPE_CONTRAST' : 1.0, 
        'SHAPE_BACKGROUND': 0.5, 
        'PAUSE_BETWEEN_DIRECTIONS' : 0.0, 
        }
        self.set_default_experiment_parameter_values(parameter_default_values)
        
        print self.experiment_config.SHAPE
        print str(self.experiment_config.PROFILE)
        #self.stimuli.append( MovingShapeExperiment(experiment.Experiment) )
        #self.stimuli.append( MovingShapeExperiment(experiment.Experiment) )
        
        #for stimulus in self.stimuli:
        #    print 'x'
        #    stimulus.prepare()

    def run(self):

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
        
        stimulus_unit = {}
        stimulus_unit['white_bar_width'] = 20
        stimulus_unit['velocity'] = 500
        stimulus_unit['duty_cycle'] = 5
        stimulus_unit['orientation'] = 45
        period_length = (stimulus_unit['duty_cycle'] + 1) * stimulus_unit['white_bar_width']
        required_movement = period_length * self.experiment_config.NUMBER_OF_BAR_ADVANCE_OVER_POINT
        stimulus_unit['move_time'] = float(required_movement) / stimulus_unit['velocity']
        stimulus_unit['move_time'] = numpy.round(stimulus_unit['move_time'] * self.machine_config.SCREEN_EXPECTED_FRAME_RATE) / self.machine_config.SCREEN_EXPECTED_FRAME_RATE
        #self.overall_duration += stimulus_unit['move_time'] + self.experiment_config.NUMBER_OF_MARCHING_PHASES * self.experiment_config.MARCH_TIME + self.experiment_config.GRATING_STAND_TIME
                            
        self.show_grating(  duration = stimulus_unit['move_time'], 
                            profile = self.experiment_config.PROFILE, 
                            orientation = stimulus_unit['orientation'], 
                            velocity = stimulus_unit['velocity'], white_bar_width = stimulus_unit['white_bar_width'],
                            duty_cycle = stimulus_unit['duty_cycle'],
                            block_trigger=True
                            )
