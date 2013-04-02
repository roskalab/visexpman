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

class RainbowExpConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.WAVELENGTH_RANGE = [390, 680]
        self.INTENSITY = 1.0 #0.1-1.0
        self.SWEEP_TIME = 100.0
        self.WAVELENGTH_STEP = 10 #nm
        self.INIT_DELAY = 4.0
        self.REPEAT = 1
        self.SHOW_COLORS_ON_PROJECTOR  = False
        self.runnable = 'RainbowExperiment'
        self._create_parameters_from_locals(locals())

class RainbowExperiment(experiment.Experiment):

    def run(self):
        self.show_fullscreen(duration = self.experiment_config.INIT_DELAY,  color = 0.0, block_trigger = False, frame_trigger = False)
        self.wavelengths = numpy.arange(self.experiment_config.WAVELENGTH_RANGE[0], 
                                        self.experiment_config.WAVELENGTH_RANGE[1] + self.experiment_config.WAVELENGTH_STEP, 
                                        self.experiment_config.WAVELENGTH_STEP)
        self.time_per_step = self.experiment_config.SWEEP_TIME / float(self.wavelengths.shape[0])
        self.polychrome = polychrome_interface.Polychrome(self.machine_config)
        self.polychrome.set_intensity(self.experiment_config.INTENSITY)
        for wavelength in self.wavelengths:
            self.parallel_port.set_data_bit(self.machine_config.FRAME_TRIGGER_PIN, 1)
            self.polychrome.set_wavelength(wavelength)
            if self.experiment_config.SHOW_COLORS_ON_PROJECTOR:
                    self.show_fullscreen(duration = 0,  color = colors.wavlength2rgb(wavelength), block_trigger = False, frame_trigger = False)
            time.sleep(self.time_per_step)
            self.parallel_port.set_data_bit(self.machine_config.FRAME_TRIGGER_PIN, 0)
            if self.check_abort_pressed() or self.abort:
                break
        self.polychrome.set_intensity(0.0)
        self.finish()
        
    def finish(self):
        self.polychrome.release_instrument()

