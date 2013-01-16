from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
            
class SpotParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPOT_SIZE = [300, 1500]  # [100,  200,  300,  400,  500,  1000]  fullfield 2500
        self.ON_TIME = 1 #s
        self.OFF_TIME = 1 #s
        self.BACKGROUND_TIME = 1 #s
        self.SPOT_CONTRAST_ON = [0.6, 0.65, 0.7, 0.75, 0.8, 0.85] # ON [0.525, 0.55, 0.575, 0.6, 0.625, 0.65, 0.675, 0.7, 0.725, 0.75] 
        self.REPETITIONS_ALL = 1 #s
        self.REPETITIONS_ALL_SIZES = 3  
        self.REPETITIONS_EACH_SIZE = 1  
        self.BACKGROUND_COLOR = 0.5
        self.DRUG_CONC = 0.0  
  
        self.runnable = 'SpotExperiment'        
        self._create_parameters_from_locals(locals())

class SpotExperiment(experiment.Experiment):
    def run(self):
        for repetitions in range(self.experiment_config.REPETITIONS_ALL):
            for spot_contrast_on in self.experiment_config.SPOT_CONTRAST_ON:
                spot_contrast_off = self.experiment_config.BACKGROUND_COLOR - (spot_contrast_on - self.experiment_config.BACKGROUND_COLOR)
                for rep_all_size in range(self.experiment_config.REPETITIONS_ALL_SIZES):  
                    for spot_size in self.experiment_config.SPOT_SIZE:
                        for rep_each in range(self.experiment_config.REPETITIONS_EACH_SIZE):
                            self.show_shape(shape = 'o',  duration = self.experiment_config.ON_TIME,  color = spot_contrast_on, 
                                        background_color = self.experiment_config.BACKGROUND_COLOR,  size = spot_size)
                            self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
                            self.show_shape(shape = 'o',  duration = self.experiment_config.OFF_TIME,  color = spot_contrast_off, 
                                        background_color = self.experiment_config.BACKGROUND_COLOR,  size = spot_size)
                            self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
                        if self.abort:
                            break
                    if self.abort:
                        break
                if self.abort:
                    break
            if self.abort:
                break
                
  
        
