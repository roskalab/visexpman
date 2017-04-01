from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils,signal
import os
import numpy
import copy
import time

class GrayBackgndOnly_5_min(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'GrayBackgndOnly'
        self.FULLSCREEN_TIME = 300.0 # 5 Minutes
        self.FULLSCREEN_COLOR = 0.25 # Medium gray contrast
        
        self._create_parameters_from_locals(locals())

class GrayBackgndOnly_10_min(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'GrayBackgndOnly'
        self.FULLSCREEN_TIME = 600.0 # 5 Minutes
        self.FULLSCREEN_COLOR = 0.25 # Medium gray contrast
        
        self._create_parameters_from_locals(locals())

class GrayBackgndOnly_15_min(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'GrayBackgndOnly'
        self.FULLSCREEN_TIME = 900.0 # 5 Minutes
        self.FULLSCREEN_COLOR = 0.25 # Medium gray contrast
        self._create_parameters_from_locals(locals())
        
class GrayBackgndOnly(experiment.Experiment):
    def prepare(self):
         self.fragment_durations = [self.experiment_config.FULLSCREEN_TIME]
        
    def run(self):
        self.show_fullscreen(duration = self.experiment_config.FULLSCREEN_TIME,color = self.experiment_config.FULLSCREEN_COLOR)
        # You can also have control signals here. 