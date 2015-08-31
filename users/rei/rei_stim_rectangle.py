from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
            
class FlashedShapePar(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SIZE = utils.rc((60,60))#um, utils.rc((100,10)) (row/y, column/x) or a single number
        self.SHAPE = 'rectangle'#annulus, rectangle, spot
        self.POSITION = utils.rc((0, -35))#Center: 0, 0 (vertical, horizontal position)
        self.ON_TIME = 20 #s
        self.OFF_TIME = 5 #s
        self.DELAY_BEFORE_START = 10.0
        self.ANNULUS_THICKNESS = 10
        self.REPETITIONS = 3  
        self.BACKGROUND_COLOR = 1.0
        self.SHAPE_COLOR = 0.0
        self.SCREEN_COLOR_BETWEEN_FLASHES = 0.0
        self.runnable = 'FlashedShapeExp'        
        self._create_parameters_from_locals(locals())

class FlashedShapeExp(experiment.Experiment):
    def run(self):
        self.show_fullscreen(duration = self.experiment_config.DELAY_BEFORE_START, color =  self.experiment_config.SCREEN_COLOR_BETWEEN_FLASHES)
        for repetitions in range(self.experiment_config.REPETITIONS):
          self.show_shape(shape = self.experiment_config.SHAPE,  duration = self.experiment_config.ON_TIME,  color = self.experiment_config.SHAPE_COLOR, 
                                        background_color = self.experiment_config.BACKGROUND_COLOR,  size = self.experiment_config.SIZE,
                                        ring_size = self.experiment_config.ANNULUS_THICKNESS, pos = self.experiment_config.POSITION)
          self.show_fullscreen(duration = self.experiment_config.OFF_TIME, color =  self.experiment_config.SCREEN_COLOR_BETWEEN_FLASHES)
          if self.abort:
            break