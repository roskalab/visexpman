import numpy
import copy
import time
import random
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

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

    def run(self):
        self.show_fullscreen(duration = self.experiment_config.PAUSE_BEFORE_AFTER, color = self.experiment_config.SHAPE_BACKGROUND,frame_trigger = False)
        for repetition in range(self.repetitions):
            self.moving_shape(size = self.experiment_config.SHAPE_SIZE,
                          speeds = self.experiment_config.SPEEDS,
                          directions = self.experiment_config.DIRECTIONS,
                          shape = self.shape,
                          color = self.shape_contrast,
                          background_color = self.shape_background,
                          pause = self.pause_between_directions,
                          block_trigger = True,
                          enable_centering = True)
        self.show_fullscreen(duration = self.experiment_config.PAUSE_BEFORE_AFTER, color = self.experiment_config.SHAPE_BACKGROUND,frame_trigger = False)

class MovingBarParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.PAUSE_BEFORE_AFTER = 2.0#sec
        self.SHAPE_SIZE = utils.rc((300, 900)) #um
        self.SPEEDS = [1200] #um/s
        self.AXIS_ANGLE = 0.0
        self.SHAPE_CONTRAST = 1.0
        self.SHAPE_BACKGROUND = 0.0
        self.PAUSE_BETWEEN_DIRECTIONS = 3.0
        self.REPETITIONS = 1
        if self.AXIS_ANGLE >= 180.0:
            null_dir = self.AXIS_ANGLE-180.0
        else:
            null_dir = self.AXIS_ANGLE+180.0
#        self.DIRECTIONS = [self.AXIS_ANGLE, null_dir]
        self.DIRECTIONS = range(0,360,45)
        self.SHAPE = 'rect'
        self.runnable = 'MovingShapeExperiment'        
        self._create_parameters_from_locals(locals())
