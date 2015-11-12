from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
import os
import numpy
import time

class IRLaserRandomConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.PRESENTATION_RATE = 40#Hz
        self.FILENAME=os.path.join(os.path.dirname(__file__),'stateBoolean.h5')
        self.FLASH_AMPLITUDE = 5.0 #V max 10.0
        self.DELAY_BEFORE_FIRST_FLASH = 5.0
        self.runnable = 'IRLaserRandomStimulation'
        self._create_parameters_from_locals(locals())
                
class IRLaserRandomStimulation(experiment.Experiment):
    '''
    Flashes externally connected blue led controller by generating analog control signals using daq analog output
    '''
    def prepare(self):
        import tables
        h=tables.open_file(self.experiment_config.FILENAME)
        self.states=h.root.stateBoolean.read().flatten()
        h.close()
        state_nsamples=self.machine_config.DAQ_CONFIG[1]['AO_SAMPLE_RATE']/self.experiment_config.PRESENTATION_RATE
        self.waveform=numpy.repeat(self.states,state_nsamples)*self.experiment_config.FLASH_AMPLITUDE
        self.waveform=self.waveform.reshape(1,self.waveform.shape[0])
    
    def run(self, fragment_id = 0):
        self.show_fullscreen(color=0.0,duration=self.experiment_config.DELAY_BEFORE_FIRST_FLASH)
        daq_instrument.set_waveform(self.machine_config.DAQ_CONFIG[1]['AO_CHANNEL'],self.waveform,sample_rate = self.machine_config.DAQ_CONFIG[1]['AO_SAMPLE_RATE'])
