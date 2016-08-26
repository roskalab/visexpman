from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
import os
import numpy
import time

        
class LedConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.BEEP_AT_EXPERIMENT_START_STOP = True
        self.PAUSE_BETWEEN_FLASHES = 5.0
        self.NUMBER_OF_FLASHES = 4.0
        self.FLASH_DURATION = 1.0
        self.LED_CURRENT = 5#mA
        self.DELAY_BEFORE_FIRST_FLASH = 2.0
        self.LED_CURRENT2VOLTAGE=0.005
        self.OUTPATH='#OUTPATH'
        self.runnable = 'LedStimulation'
        self._create_parameters_from_locals(locals())
        
        
        
class LedStimulation(experiment.Experiment):
    '''
    Flashes externally connected blue led controller by generating analog control signals using daq analog output
    '''
    def prepare(self):
        self.fsample=1000
        self.waveform= numpy.concatenate((numpy.ones(self.experiment_config.FLASH_DURATION*self.fsample), numpy.zeros(self.experiment_config.PAUSE_BETWEEN_FLASHES*self.fsample)))
        self.waveform=numpy.tile(self.waveform, self.experiment_config.NUMBER_OF_FLASHES)
        self.waveform=numpy.concatenate((numpy.zeros(self.experiment_config.DELAY_BEFORE_FIRST_FLASH*self.fsample), self.waveform))
        self.waveform*=self.experiment_config.LED_CURRENT2VOLTAGE*self.experiment_config.LED_CURRENT
        self.duration=(self.experiment_config.FLASH_DURATION+self.experiment_config.PAUSE_BETWEEN_FLASHES)*self.experiment_config.NUMBER_OF_FLASHES+self.experiment_config.DELAY_BEFORE_FIRST_FLASH
        self.fragment_durations = [self.duration]
        self.number_of_fragments = 1
    
    
    def run(self, fragment_id = 0):
        self.show_fullscreen()
        if 0:
            daq_instrument.set_waveform('Dev1/ao0',numpy.array([self.waveform]),sample_rate = self.fsample)
        else:
            self.printl(self.duration)
            self.show_fullscreen(duration=self.duration)
    

