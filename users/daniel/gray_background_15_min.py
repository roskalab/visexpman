from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils,signal
import os
import numpy
import copy
import time

class GrayBackgndOnly(experiment.ExperimentConfig):
    def _create_parameters(self):
		self.runnable = 'GrayBackgndOnly'
        self.FULLSCREEN_TIME = 900.0; # 5 Minutes
        self.FULLSCREEN_COLOR = 0.25; # Medium gray contrast
        
        self._create_parameters_from_locals(locals())
        
        
    def _create_parameters_from_locals(self, locals,  check_path = True):
        if len(locals['self'].DUTY_CYCLES)==1 and len(locals['self'].ORIENTATIONS)>1:
            locals['self'].DUTY_CYCLES=locals['self'].DUTY_CYCLES*len(locals['self'].ORIENTATIONS)
        experiment.ExperimentConfig._create_parameters_from_locals(self, locals)

        
        
class GrayBackgndOnly(experiment.Experiment):
    def prepare(self):
         self.fragment_durations = [self.experiment_config.FULLSCREEN_TIME]
        
    def run(self):
        self.show_fullscreen(duration = self.experiment_config.FULLSCREEN_TIME,color = self.experiment_config.FULLSCREEN_COLOR)
        # You can also have control signals here. 