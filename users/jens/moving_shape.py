from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
            
class MovingShapeParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.SHAPE_COLOR = 1.0
        self.SHAPE_BACKGROUND = 0.0
        self.SHAPE_SIZE = utils.rc((100, 100))#r: row (vertical size), c: column, horizontal size
        self.DIRECTIONS = range(0, 360, 45) #Last number os the angle step, use 90 for 4 directions
        self.SPEED = [400] #um/s
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self.runnable = 'MovingShapeExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory
####----------------------------------------------------------------------------------------------------------------------------------
class MovingShapeExperiment(experiment.Experiment): # this is an expt class, higher order, NO LIST, stimulus itself is written here
 

    def run(self): # compulsory
        self.moving_shape(size = self.experiment_config.SHAPE_SIZE,
                          speeds = self.experiment_config.SPEED,
                          directions = self.experiment_config.DIRECTIONS,
                          shape = self.experiment_config.SHAPE,
                          color = self.experiment_config.SHAPE_COLOR,
                          background_color = self.experiment_config.SHAPE_BACKGROUND,
                          pause = self.experiment_config.PAUSE_BETWEEN_DIRECTIONS)