from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
            
class SpotWGreyParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPOT_SIZE = 500  # [100,  200,  300,  400,  500,  1000]  fullfield 2500
        self.ON_TIME = 2.0 #s
        self.OFF_TIME = 3.0 #s
        self.BACKGROUND_TIME = 5.0
        self.SPOT_CONTRAST_ON = [0.999] #N [0.6, 0.7, 0.8, 0.9, 0.99] 
        self.REPETITIONS_ALL = 2
        self.BACKGROUND_COLOR = 0.5

  
        self.runnable = 'SpotExperiment'        
        self._create_parameters_from_locals(locals())

class SpotExperiment(experiment.Experiment):
    def run(self):
        for repetitions in range(self.experiment_config.REPETITIONS_ALL):
            self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
            for spot_contrast_on in self.experiment_config.SPOT_CONTRAST_ON:
                spot_contrast_off = self.experiment_config.BACKGROUND_COLOR - (spot_contrast_on - self.experiment_config.BACKGROUND_COLOR)
                
                self.show_shape(shape = 'o',  duration = self.experiment_config.ON_TIME,  color = spot_contrast_on, 
                                        background_color = self.experiment_config.BACKGROUND_COLOR,  size = self.experiment_config.SPOT_SIZE)
                                        
                self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
                
                if self.abort:
                    break
                 
            if self.abort:
                break
            
  
        