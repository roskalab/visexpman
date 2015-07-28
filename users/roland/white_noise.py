from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
import time
import numpy
import os.path
import os
import shutil
import random

class WhiteNoiseParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.DURATION = 1.0/60.0#20#min
        self.PIXEL_SIZE =75.0
        self.FLICKERING_FREQUENCY = 60.0
        self.N_WHITE_PIXELS = False#None
        self.COLORS = [0.0, 1.0]
        self.runnable = 'WhiteNoiseExperiment'
        self._create_parameters_from_locals(locals())


        
