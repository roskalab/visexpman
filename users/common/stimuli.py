'''
Most common stimulus patterns. Users should subclass these
'''

import numpy
import copy
import time
import random
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class LaserPulseC(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.INITIAL_DELAY=10.0
        self.PULSE_DURATION=[20e-3]
        self.PERIOD_TIME=[10.0]
        self.NPULSES=1
        self.LASER_AMPLITUDE=[1.0]
        self.SAMPLE_RATE=1000
        self.ZERO_VOLTAGE=0.0
        self.runnable = 'LaserPulseE'
        self._create_parameters_from_locals(locals())


class LaserPulseE(experiment.Experiment):
    def calculate_waveform(self):
        ec=self.experiment_config
        init=numpy.zeros(int(ec.SAMPLE_RATE*ec.INITIAL_DELAY))
        pulses=[]
        if len(ec.PULSE_DURATION)!=len(ec.PERIOD_TIME):
            raise RuntimeError('Invalid timing configuration')
        for v in ec.LASER_AMPLITUDE:
            for i in range(len(ec.PULSE_DURATION)):
                pulse_duration=ec.PULSE_DURATION[i]
                period_time=ec.PERIOD_TIME[i]
                pulse=numpy.concatenate((numpy.ones(int(ec.SAMPLE_RATE*pulse_duration)), numpy.zeros(int(ec.SAMPLE_RATE*(period_time-pulse_duration)))))*v
                pulses.append(numpy.tile(pulse,ec.NPULSES))
        self.waveform=numpy.concatenate(pulses)
        self.waveform=numpy.concatenate((init, self.waveform))
        timing_waveform=numpy.where(self.waveform==0,0,5)#.reshape(1,self.waveform.shape[0])
        self.waveform=numpy.where(self.waveform==0.0,ec.ZERO_VOLTAGE,self.waveform)
#        self.waveform=self.waveform.reshape(1,self.waveform.shape[0])
        self.combined_waveform=numpy.zeros((2,self.waveform.shape[0]))
        self.combined_waveform[0]=self.waveform
        self.combined_waveform[1]=timing_waveform
        #self.printl((self.combined_waveform.shape, len(pulses)))


    def prepare(self):
        self.calculate_waveform()
        self.duration = self.combined_waveform.shape[1]/float(self.experiment_config.SAMPLE_RATE)
        self.fragment_durations=[self.duration]
        
    def run(self):
        from visexpman.engine.hardware_interface import daq_instrument
        self._frame_trigger_pulse()
        self.show_fullscreen(color=0.0,duration=0)
#        self.block_start('laser')
        daq_instrument.set_waveform('Dev1/ao0:1',self.combined_waveform,sample_rate = self.experiment_config.SAMPLE_RATE)
        self.show_fullscreen(color=0.0, duration=0)
#        self.block_end('laser')
