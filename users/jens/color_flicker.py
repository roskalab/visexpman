from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
from visexpman.engine.hardware_interface import polychrome_interface
from visexpman.engine.hardware_interface import instrument
from visexpman.engine.generic import colors
import time
import numpy
import os.path
import os
import shutil
import random

class ColorFlickerExpConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.COLOR = 580
        self.BLACK = 680
        self.FREQUENCIES = [9, 18, 38, 62, 125] #Hz Never more than 33 Hz
#         self.FREQUENCIES = range(10, 190, 20)
        self.INTENSITY = 1.0 #0.1-1.0
        self.NUMBER_OF_PERIODS = 20#20
        self.INIT_DELAY = 4.0
        self.DELAY_BETWEEN_FREQUENCY_STEPS = 0.5
        self.SHOW_COLORS_ON_PROJECTOR  = False
        self.runnable = 'ColorFlickerExperiment'
        self._create_parameters_from_locals(locals())

class ColorFlickerExperiment(experiment.Experiment):
    def run(self):
        self.show_fullscreen(duration = self.experiment_config.INIT_DELAY,  color = 0.0, block_trigger = False, frame_trigger = False)
        self.polychrome = polychrome_interface.Polychrome(self.machine_config)
        self.polychrome.set_resting_wavelength(680)
        for frequency in self.experiment_config.FREQUENCIES:
            self.polychrome.set_intensity(self.experiment_config.INTENSITY)
            for i in range(self.experiment_config.NUMBER_OF_PERIODS):
                self.polychrome.set_wavelength(self.experiment_config.COLOR)
#                 self.parallel_port.set_data_bit(self.machine_config.FRAME_TRIGGER_PIN, 1)
                if self.experiment_config.SHOW_COLORS_ON_PROJECTOR:
                        self.show_fullscreen(duration = 0,  color = colors.wavlength2rgb(self.experiment_config.COLOR), block_trigger = False, frame_trigger = False)
                time.sleep(1.0/(frequency * 2))
#                 self.parallel_port.set_data_bit(self.machine_config.FRAME_TRIGGER_PIN, 0)
                self.polychrome.set_wavelength(self.experiment_config.BLACK)
                if self.experiment_config.SHOW_COLORS_ON_PROJECTOR:
                        self.show_fullscreen(duration = 0,  color = 0.0, block_trigger = False, frame_trigger = False)
                time.sleep(1.0/(frequency * 2))
                if self.check_abort_pressed() or self.abort:
                    break
            self.polychrome.set_intensity(0.0)
            if self.check_abort_pressed() or self.abort:
                    break
            time.sleep(self.experiment_config.DELAY_BETWEEN_FREQUENCY_STEPS)
        self.polychrome.set_intensity(0.0)
        self.show_fullscreen(duration = 0.0,  color = 0.0, block_trigger = False, frame_trigger = False)
        self.finish()
        
    def finish(self):
        self.polychrome.release_instrument()
        

