from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils,signal
import os
import numpy
import time

class NaturalIntensityProfileConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.MAX_AMPLITUDE = 0.5#V
        self.DURATION = 30.0
        self.REPEATS = 3
        self.MAX_FREQUENCY = 100.0
        self.runnable = 'NaturalLedStimulation'
        self.pre_runnable = 'LedPre'
        self._create_parameters_from_locals(locals())


class NaturalLedStimulation(experiment.Experiment):
    '''
    Flashes externally connected blue led controller by generating analog control signals using daq analog output
    '''
    def prepare(self):
        self.intensity_profile = signal.generate_natural_stimulus_intensity_profile(self.experiment_config.DURATION, 1.0, 
                                                    1.0/self.experiment_config.MAX_FREQUENCY, 
                                                    1.0/self.machine_config.DAQ_CONFIG[1]['SAMPLE_RATE'])*self.experiment_config.MAX_AMPLITUDE
        self.fragment_durations = [self.experiment_config.DURATION*self.experiment_config.REPEATS]
        self.save_variables(['intensity_profile'])#Save to make it available for analysis
        self.intensity_profile = numpy.append(self.intensity_profile, 0.0)
    
    def run(self, fragment_id = 0):
        self.show_fullscreen(color = 0.0, duration = 0.0)
        for rep in range(self.experiment_config.REPEATS):
            self.led_controller.set(self.intensity_profile,None)
            self.led_controller.start()
        
class NaturalMorseConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.FLASH_AMPLITUDE = 0.5#V
        self.DURATION = 30.0
        self.REPEATS = 3
        self.SHORTEST_PULSE = 1e-2
        self.runnable = 'LedMorseStimulation'
        self.pre_runnable = 'LedPre'
        self._create_parameters_from_locals(locals())
        
class LedMorseStimulation(experiment.Experiment):
    '''
    Flashes externally connected blue led controller by generating analog control signals using daq analog output
    '''
    def prepare(self):
        self.timing = signal.natural_distribution_morse(self.experiment_config.DURATION, 
                        1.0/self.machine_config.DAQ_CONFIG[1]['SAMPLE_RATE'],
                        occurence_of_longest_period = 1.0, 
                        n0 = int(self.experiment_config.SHORTEST_PULSE/( 1.0/self.machine_config.DAQ_CONFIG[1]['SAMPLE_RATE'])))[0]
        self.fragment_durations = [self.experiment_config.DURATION*self.experiment_config.REPEATS]
        timing_in_samples = numpy.array(self.timing)*self.machine_config.DAQ_CONFIG[1]['SAMPLE_RATE']
        state = False
        self.waveform = numpy.array([])
        for n in timing_in_samples:
            samples = numpy.ones(n,dtype=numpy.float64)*self.experiment_config.FLASH_AMPLITUDE
            if not state:
                samples *= 0.0
            state = not state
            self.waveform = numpy.append(self.waveform,samples)
        self.waveform = numpy.append(self.waveform, 0.0)
        self.save_variables(['timing', 'waveform'])#Save to make it available for analysis
        self.printl('Minimal time: {0} ms, maximal time: {1} ms'.format(min(self.timing)*1000,max(self.timing)*1000))
    
    def run(self, fragment_id = 0):
        self.show_fullscreen(color = 0.0, duration = 0.0)
        for rep in range(self.experiment_config.REPEATS):
            self.led_controller.set(self.waveform,None)
            self.led_controller.start()
        
