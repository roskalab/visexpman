from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
            
class Fullfield10min(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.DELAY_BEFORE_START=30
        self.ON_TIME = 2 #s
        self.PERIOD_TIME = 30 #s
        self.DURATION = 600.0
        self.BACKGROUND_COLOR=0.0
        self.COLOR=1.0
        self.runnable = 'FlashedShapeExp2'        
        self._create_parameters_from_locals(locals())

class FlashedShapeExp2(experiment.Experiment):
    def run(self):
        nreps=int(self.experiment_config.DURATION/self.experiment_config.PERIOD_TIME)
        self.show_fullscreen(duration = self.experiment_config.DELAY_BEFORE_START, color =  self.experiment_config.BACKGROUND_COLOR)
        for repetitions in range(nreps):
          self.show_fullscreen(duration = self.experiment_config.ON_TIME, color =  self.experiment_config.COLOR)
          self.show_fullscreen(duration = self.experiment_config.PERIOD_TIME-self.experiment_config.ON_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
          if self.abort:
            break
