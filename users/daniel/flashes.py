from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
import time
import numpy
import os.path
import os

class ProjectorFlashC(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.PAUSE_BETWEEN_FLASHES = 3.0
        self.NUMBER_OF_FLASHES = 10.0
        self.FLASH_DURATION = 1.0
        self.FLASH_AMPLITUDE = 1.0 #max 1.0
        self.DELAY_BEFORE_FIRST_FLASH = 10.0
        self.FLASH_COLOR = [1.0, 1.0, 1.0] #rgb
        self.runnable = 'ProjectorFlashExp'
        self._create_parameters_from_locals(locals())

class ProjectorFlashExp(experiment.Experiment):
    def prepare(self):
        self.period_time = self.experiment_config.FLASH_DURATION + self.experiment_config.PAUSE_BETWEEN_FLASHES
        self.fragment_repeats = [self.experiment_config.NUMBER_OF_FLASHES]
        self.fragment_durations = [self.experiment_config.DELAY_BEFORE_FIRST_FLASH + self.experiment_config.NUMBER_OF_FLASHES*self.period_time]
        self.number_of_fragments = len(self.fragment_durations)
        self.color = (numpy.array(self.experiment_config.FLASH_COLOR)*self.experiment_config.FLASH_AMPLITUDE).tolist()
        
    def run(self):
        self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
        self.show_fullscreen(color = 0.0, duration = self.experiment_config.DELAY_BEFORE_FIRST_FLASH)
        for rep in range(int(self.experiment_config.NUMBER_OF_FLASHES)):
            self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
            self.show_fullscreen(color = self.color, duration = self.experiment_config.FLASH_DURATION)
            self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
            self.show_fullscreen(color = 0.0, duration = self.experiment_config.PAUSE_BETWEEN_FLASHES)
        
