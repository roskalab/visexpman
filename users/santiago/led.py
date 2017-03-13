import PyDAQmx
import PyDAQmx.DAQmxConstants as DAQmxConstants
import PyDAQmx.DAQmxTypes as DAQmxTypes
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
import os
import numpy
import time

        
class LedConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
#### EDIT FROM HERE
        self.PAUSE_BETWEEN_FLASHES = 15.0
        self.NUMBER_OF_FLASHES = 3.0
        self.FLASH_DURATION = 0.5
        self.LED_CURRENT = 950#mA
        self.DELAY_BEFORE_FIRST_FLASH = 10.0
#### EDIT UNTIL HERE
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
        self.amplitude=self.experiment_config.LED_CURRENT2VOLTAGE*self.experiment_config.LED_CURRENT
        
    def _set_voltage(self,v):
        timeout=1
        self.analog_output.WriteAnalogF64(1,
                                        True,
                                        timeout,
                                        DAQmxConstants.DAQmx_Val_GroupByChannel,
                                        numpy.ones((1,1))*v,
                                        None,
                                        None)
    
    
    def run(self, fragment_id = 0):
        self.show_fullscreen()
        if 0:
            daq_instrument.set_waveform('Dev1/ao0',numpy.array([self.waveform]),sample_rate = self.fsample)
        else:
            self.analog_output = PyDAQmx.Task()
            self.analog_output.CreateAOVoltageChan('Dev1/ao0',
                                        'ao',
                                        0, 
                                        5, 
                                        DAQmxConstants.DAQmx_Val_Volts,
                                        None)
            self._set_voltage(0)
            time.sleep(self.experiment_config.DELAY_BEFORE_FIRST_FLASH)
            for i in range(int(self.experiment_config.NUMBER_OF_FLASHES)):
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
                self._set_voltage(self.amplitude)
                time.sleep(self.experiment_config.FLASH_DURATION)
                if self.abort:
                    break
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
                self._set_voltage(0)
                time.sleep(self.experiment_config.PAUSE_BETWEEN_FLASHES)
                if self.abort:
                    break
            self.analog_output.WaitUntilTaskDone(1.0)
            self.analog_output.StopTask()
            self.analog_output.ClearTask()
            
    

