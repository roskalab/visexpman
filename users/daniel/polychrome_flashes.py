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

class ColorTestConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.WAVELENGTH_MIN = 600
        self.WAVELENGTH_MAX = 400
        self.WAVELENGTH_STEP = -25
        
        self.PAUSE_BETWEEN_FLASHES = 20.0
        self.NUMBER_OF_FLASHES = 1
        self.FLASH_DURATION = 1.0
        self.FLASH_AMPLITUDE = 1.0 #max 1.0
        self.DELAY_BEFORE_FIRST_FLASH = 5.0
        
        self.OFF_WAVELENGTH = 680.0
        self.RESTING_WAVELENGTH = 680.0
        self.runnable = 'PolychromeFlash'
        self._create_parameters_from_locals(locals())

class ColorFlashConfigUP(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.WAVELENGTH_MIN = 450
        self.WAVELENGTH_MAX = 530
        self.WAVELENGTH_STEP = 10
        
        self.PAUSE_BETWEEN_FLASHES = 15.0
        self.NUMBER_OF_FLASHES = 1.0
        self.FLASH_DURATION = 2.0
        self.FLASH_AMPLITUDE = 0.1 #max 1.0
        self.DELAY_BEFORE_FIRST_FLASH = 15.0
        
        self.OFF_WAVELENGTH = 680.0
        self.RESTING_WAVELENGTH = 680.0
        self.runnable = 'PolychromeFlash'
        self._create_parameters_from_locals(locals())
        
class ColorFlashConfigDown(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.WAVELENGTH_MIN = 530
        self.WAVELENGTH_MAX = 450
        self.WAVELENGTH_STEP = -10
        
        self.PAUSE_BETWEEN_FLASHES = 15.0
        self.NUMBER_OF_FLASHES = 1.0
        self.FLASH_DURATION = 2.0
        self.FLASH_AMPLITUDE = 0.1 #max 1.0
        self.DELAY_BEFORE_FIRST_FLASH = 15.0
        
        self.OFF_WAVELENGTH = 680.0
        self.RESTING_WAVELENGTH = 680.0
        self.runnable = 'PolychromeFlash'
        self._create_parameters_from_locals(locals())

class PolychromeFlash(experiment.Experiment):
    def prepare(self):
        self.wavelengths = range(self.experiment_config.WAVELENGTH_MIN, self.experiment_config.WAVELENGTH_MAX, self.experiment_config.WAVELENGTH_STEP)
        self.wavelengths.append(self.experiment_config.WAVELENGTH_MAX)
        self.fragment_durations = [self.experiment_config.DELAY_BEFORE_FIRST_FLASH + len(self.wavelengths)*(self.experiment_config.FLASH_DURATION + self.experiment_config.PAUSE_BETWEEN_FLASHES) * self.experiment_config.NUMBER_OF_FLASHES]
        self.save_variables(['wavelengths'])#Save to make it available for analysis

    def run(self):
        self.show_fullscreen(duration = self.experiment_config.DELAY_BEFORE_FIRST_FLASH,  color = 0.0, frame_trigger = False)
        self.polychrome = polychrome_interface.Polychrome(self.machine_config)
        self.polychrome.set_resting_wavelength(self.experiment_config.RESTING_WAVELENGTH)
        self.polychrome.set_wavelength(self.experiment_config.OFF_WAVELENGTH)
        self.polychrome.set_intensity(0.0)
        for wavelength in self.wavelengths:
            self.printl('Wavelenght: {0}'.format(wavelength))
            for i in range(int(self.experiment_config.NUMBER_OF_FLASHES)):
                if self.abort:
                    break
                self.polychrome.set_wavelength(wavelength)
                self.polychrome.set_intensity(self.experiment_config.FLASH_AMPLITUDE)
                self.parallel_port.set_data_bit(self.machine_config.FRAME_TRIGGER_PIN, 1)
                time.sleep(self.experiment_config.FLASH_DURATION)
                if self.abort:
                    break
                #close shutter
                self.polychrome.set_wavelength(self.experiment_config.OFF_WAVELENGTH)
                self.polychrome.set_intensity(0.0)#Takes 114 ms
                self.parallel_port.set_data_bit(self.machine_config.FRAME_TRIGGER_PIN, 0)
                self.show_fullscreen(duration = 0,  color = 0, frame_trigger = False)
                time.sleep(self.experiment_config.PAUSE_BETWEEN_FLASHES)
        self.polychrome.set_wavelength(self.experiment_config.OFF_WAVELENGTH)
        self.polychrome.set_intensity(0.0)
        self.polychrome.release_instrument()

