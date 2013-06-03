from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
            
class StimParam(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.TIMING = [10, 2, 20, 10, 20]
        self.FLASH_COLOR = [1.0, 0.5] 
        self.runnable = 'StimStyle'        
        self._create_parameters_from_locals(locals())

class StimStyle(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [sum(self.experiment_config.TIMING)*len(self.experiment_config.FLASH_COLOR)]
        
    def run(self):
        for color in self.experiment_config.FLASH_COLOR:  
            self.flash_stimulus(self.experiment_config.TIMING, flash_color = color,  background_color = 0.0, repeats = 1)

         
