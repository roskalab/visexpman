from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
            
class Spot(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SIZE = utils.rc((120,120))#um, utils.rc((100,10)) (row/y, column/x) or a single number
        self.SHAPE = 'spot'#annulus, rectangle, spot
        self.POSITION = utils.rc((0, 0))#Center: 0, 0 (vertical, horizontal position)
        self.ON_TIME = 2 #s
        self.OFF_TIME = 8 #s
        self.DELAY_BEFORE_START = 10.0
        self.ANNULUS_THICKNESS = 630
        self.REPETITIONS = 1  
        self.BACKGROUND_COLOR = 0.0
        self.runnable = 'FlashedShapeExp'        
        self._create_parameters_from_locals(locals())

class FlashedShapeExp(experiment.Experiment):
    def run(self):
        self.show_fullscreen(duration = self.experiment_config.DELAY_BEFORE_START, color =  self.experiment_config.BACKGROUND_COLOR)
        for repetitions in range(self.experiment_config.REPETITIONS):
          self.show_shape(shape = self.experiment_config.SHAPE,  duration = self.experiment_config.ON_TIME,  color = 1.0, 
                                        background_color = self.experiment_config.BACKGROUND_COLOR,  size = self.experiment_config.SIZE,
                                        ring_size = self.experiment_config.ANNULUS_THICKNESS, pos = self.experiment_config.POSITION)
          self.show_fullscreen(duration = self.experiment_config.OFF_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
          if self.abort:
            break
