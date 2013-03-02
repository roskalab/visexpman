from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
import time
import numpy
import os.path
import os
import shutil
import random

class IncreasingSpotParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        short = False
        if short:
            self.SIZES = [800]
        else:
            self.SIZES = [50, 800]
        self.ON_TIME = 2.0
        self.OFF_TIME = 4.0
        self.USER_FRAGMENT_NAME = 'FILENAME'
        self.runnable = 'IncreasingSpotExperiment'
        self._create_parameters_from_locals(locals())
        
        
class IncreasingSpotExperiment(experiment.Experiment):
    def run(self):
        self.printl(self.experiment_config.USER_FRAGMENT_NAME) 
        self.increasing_spot(self.experiment_config.SIZES, self.experiment_config.ON_TIME, self.experiment_config.OFF_TIME,
                    color = 1.0, background_color = 0.0, pos = utils.rc((0,  0)),block_trigger = True)        
