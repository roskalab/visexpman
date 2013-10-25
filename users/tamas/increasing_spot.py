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
            self.SIZES = [25, 50, 100, 200, 400, 800,1600]
        self.ON_TIME = 2.0
        self.OFF_TIME = 4.0
        self.USER_FRAGMENT_NAME = 'FILENAME'
        self.runnable = 'IncreasingSpotExperiment'
        self._create_parameters_from_locals(locals())
