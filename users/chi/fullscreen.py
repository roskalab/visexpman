from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
import time
import numpy
import os.path
import os
import shutil
import random

class FullscreenParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.DURATION = 30.0
        self.COLOR = 0.5
        self.USER_FRAGMENT_NAME = 'FILENAME'
        self.runnable = 'FullscreenExperiment'
        self._create_parameters_from_locals(locals())
        
        
class FullscreenExperiment(experiment.Experiment):
    def run(self):
        self.show_fullscreen(duration = self.experiment_config.DURATION, color = self.experiment_config.COLOR)