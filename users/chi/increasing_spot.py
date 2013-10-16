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
        self.BACKGROUND = 0.5
        self.COLORS = [1.0, 0.0]
        self.USER_FRAGMENT_NAME = 'FILENAME'
        self.runnable = 'IncreasingSpotExperiment'
        self._create_parameters_from_locals(locals())
