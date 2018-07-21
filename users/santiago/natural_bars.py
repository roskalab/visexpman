from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils,signal
import os
import numpy
import time


class NaturalBarsConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPEED = 300.0#um/s
        self.REPEATS = 5
        self.DIRECTIONS = [180]
        self.DURATION = 30.0
        self.PAUSE_BEFORE_AFTER = 5.0
        self.runnable = 'NaturalBarsExperiment'
        self._create_parameters_from_locals(locals())
        

class NaturalBarsExperiment(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [self.experiment_config.DURATION*self.experiment_config.REPEATS*len(self.experiment_config.DIRECTIONS)]
        
    def run(self):
        self.parallel_port.set_data_bit(self.config.BLOCK_TIMING_PIN, 0)
        self.show_fullscreen(duration = self.experiment_config.PAUSE_BEFORE_AFTER, color = 0,frame_timing_pulse = False)
        for rep in range(self.experiment_config.REPEATS):
            if self.abort:
                break
            for directions in self.experiment_config.DIRECTIONS:
                if self.abort:
                    break
                self.parallel_port.set_data_bit(self.config.BLOCK_TIMING_PIN, 1)
                self.show_natural_bars(speed = self.experiment_config.SPEED, duration=self.experiment_config.DURATION, minimal_spatial_period = None, spatial_resolution = self.machine_config.SCREEN_PIXEL_TO_UM_SCALE, intensity_levels = 255, direction = directions)
                self.parallel_port.set_data_bit(self.config.BLOCK_TIMING_PIN, 0)
        self.show_fullscreen(duration = self.experiment_config.PAUSE_BEFORE_AFTER, color = 0,frame_timing_pulse = False)
