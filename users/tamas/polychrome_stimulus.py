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

class PolychromeExpConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.WAVELENGTH_RANGE_NAME = 't'
        self.WAVELENGTH_RANGES = {}
        self.WAVELENGTH_RANGES['uv'] = [330, 350, 370, 390, 410]
        self.WAVELENGTH_RANGES['m'] = [480, 500, 520, 540, 560]
        self.WAVELENGTH_RANGES['f'] = [340, 370, 405, 430, 455, 490, 520, 550]
        self.WAVELENGTH_RANGES['s'] = [[480, 1.0],  [520,  0.5],  [560, 0.7]]
        self.WAVELENGTH_RANGES['t'] = [[480, 1.0]]
        self.USE_GLOBAL_INTENSITY = True
        self.WAVELENGTH_SHUTTERING = not True
        self.OFF_WAVELENGTH = 680.0
        self.RESTING_WAVELENGTH = 680.0
        self.INTENSITY = 0.1 #0.1-1.0
        self.ON_TIME = 2.0
        self.OFF_TIME = 4.0
        self.INIT_DELAY = 4.0
        self.REPEAT = 10
        self.runnable = 'PolychromeExperiment'
        self._create_parameters_from_locals(locals())

class PolychromeExperiment(experiment.Experiment):
    def prepare(self):
        pass

    def run(self):
        self.show_fullscreen(duration = self.experiment_config.INIT_DELAY,  color = 0.0, block_trigger = False, frame_trigger = False)
        self.polychrome = polychrome_interface.Polychrome(self.machine_config)
        self.polychrome.set_resting_wavelength(self.experiment_config.RESTING_WAVELENGTH)
        if self.machine_config.ENABLE_SHUTTER:
            self.shutter = instrument.Shutter(self.machine_config)
        elif self.experiment_config.WAVELENGTH_SHUTTERING:
            self.polychrome.set_wavelength(self.experiment_config.OFF_WAVELENGTH)
            self.polychrome.set_intensity(0.0)
        else:
            self.polychrome.set_intensity(0.0)
            
        for i in range(self.experiment_config.REPEAT):
            for wl_config in self.experiment_config.WAVELENGTH_RANGES[self.experiment_config.WAVELENGTH_RANGE_NAME]:
                if isinstance(wl_config, list):
                    wavelength = wl_config[0]
                    intensity = wl_config[1]
                else:
                    wavelength = wl_config
                if self.check_abort_pressed() or self.abort:
                    break
                self.polychrome.set_wavelength(wavelength)
                #Open shutter
                if self.config.ENABLE_SHUTTER:
                    self.shutter.toggle()
                else:
                    if self.experiment_config.USE_GLOBAL_INTENSITY:
                        self.polychrome.set_intensity(self.experiment_config.INTENSITY)
                    else:
                        self.polychrome.set_intensity(intensity)
                self.printl('Setting wavelenght: {0}'.format(wavelength))
                self.show_fullscreen(duration = 0,  color = colors.wavlength2rgb(wavelength), block_trigger = False, frame_trigger = False)
                if self.machine_config.ENABLE_PARALLEL_PORT:
                    self.parallel_port.set_data_bit(self.machine_config.FRAME_TRIGGER_PIN, 1)
                time.sleep(self.experiment_config.ON_TIME)
                if self.check_abort_pressed() or self.abort:
                    break
                #close shutter
                if self.config.ENABLE_SHUTTER:
                    self.shutter.toggle()
                elif self.experiment_config.WAVELENGTH_SHUTTERING:
                    self.polychrome.set_wavelength(self.experiment_config.OFF_WAVELENGTH)
                    self.polychrome.set_intensity(0.0)#Takes 114 ms
                else:
                    self.polychrome.set_intensity(0.0)
                if self.machine_config.ENABLE_PARALLEL_PORT:
                    self.parallel_port.set_data_bit(self.machine_config.FRAME_TRIGGER_PIN, 0)
                self.show_fullscreen(duration = 0,  color = 0, block_trigger = False, frame_trigger = False)
                time.sleep(self.experiment_config.OFF_TIME)
        self.finish()
        
    def finish(self):
        self.polychrome.release_instrument()
        if self.machine_config.ENABLE_SHUTTER:
            self.shutter.release_instrument()

