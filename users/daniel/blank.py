from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
import time
import numpy
import os.path
import os

class BlankScreenConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.DURATION=100.0
        self.runnable = 'BlankScreenExp'
        self._create_parameters_from_locals(locals())

class BlankScreenExp(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [self.experiment_config.DURATION]
        
        
    def run(self):
        self.show_fullscreen(color = 0.0, duration = self.experiment_config.DURATION)
        
