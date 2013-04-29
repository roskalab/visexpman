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
        self.SIZES = [125, 250, 375, 500, 625, 1250]
        self.ON_TIME = 2.0
        self.OFF_TIME = 5.0
        self.BACKGOUND = 0.5
        self.COLORS = [1.0, 0.0]
        self.USER_FRAGMENT_NAME = 'FILENAME'
        self.runnable = 'IncreasingSpotExperiment'
        self._create_parameters_from_locals(locals())
        
        
class IncreasingSpotExperiment(experiment.Experiment):
    def run(self):
        self.printl(self.experiment_config.USER_FRAGMENT_NAME) 
        for color in self.experiment_control.COLORS:
            self.increasing_spot(self.experiment_config.SIZES, self.experiment_config.ON_TIME, self.experiment_config.OFF_TIME,
                    color = color, background_color = self.experiment_config.BACKGROUND, pos = utils.rc((0,  0)),block_trigger = True)        
