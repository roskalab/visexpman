from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils,signal
import os
import numpy
import time

class LedKamill2Config(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'NaturalLedStimulation'
        self.pre_runnable = 'LedPre'
        self._create_parameters_from_locals(locals())


class NaturalLedStimulation(experiment.Experiment):
    '''
    Flashes externally connected blue led controller by generating analog control signals using daq analog output
    '''
    def prepare(self):
        self.fragment_durations = [42.0]
    
    def run(self, fragment_id = 0):
        self.show_fullscreen(color = 0.0, duration = 0.0)
        self.led_controller.set([[[10.0], 2.0, self.experiment_config.FLASH_AMPLITUDE]], 12.0)
        self.led_controller.start()
