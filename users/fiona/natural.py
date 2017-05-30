from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils,signal
import os
import numpy
import time

class NaturalMovieSv1(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.REPEATS=5
	self.DURATION = 30.0
        self.FILENAME = 'c:\\Data\\movieincage_fiona'
        self.FRAME_RATE=60.0
        self.STRETCH = 1.7
        self.runnable = 'NaturalMovieExperiment'
        self._create_parameters_from_locals(locals())

class NaturalBarsConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPEED = 300.0#um/s
        self.REPEATS = 2#5
        self.DIRECTIONS = range(0,360,90)
        self.DURATION = 30.0
        self.runnable = 'NaturalBarsExperiment'
        self._create_parameters_from_locals(locals())

class NaturalIntensityProfileConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.MAX_AMPLITUDE = 0.5#V
        self.DURATION = 30.0
        self.REPEATS = 3
        self.MAX_FREQUENCY = 100.0
        self.runnable = 'NaturalLedStimulation'
        self.pre_runnable = 'LedPre'
        self._create_parameters_from_locals(locals())

class NaturalBarsExperiment(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [self.experiment_config.DURATION*self.experiment_config.REPEATS*len(self.experiment_config.DIRECTIONS)]
        
    def run(self):
        for rep in range(self.experiment_config.REPEATS):
            if self.abort:
                break
            for directions in self.experiment_config.DIRECTIONS:
                if self.abort:
                    break
                self.show_natural_bars(speed = self.experiment_config.SPEED, duration=self.experiment_config.DURATION, minimal_spatial_period = None, spatial_resolution = self.machine_config.SCREEN_PIXEL_TO_UM_SCALE, intensity_levels = 255, direction = directions)

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
        
class LedWaveformConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.VOLTAGES = [0, 3, 0]
        self.TIMINGS = [1000,  1000, 1000]
        self.REPEATS = 1
        self.runnable = 'LedWaveformStimulation'
        self.pre_runnable = 'LedPre'
        self._create_parameters_from_locals(locals())

        
class LedWaveformStimulation(experiment.Experiment):
    def prepare(self):
        self.waveform = numpy.array([])
        for i in range(len(self.experiment_config.TIMINGS)):
            samples = numpy.ones(self.experiment_config.TIMINGS[i]/1000.0*self.machine_config.DAQ_CONFIG[1]['SAMPLE_RATE'])
            samples *= self.experiment_config.VOLTAGES[i]
            self.waveform = numpy.append(self.waveform,samples)
        self.fragment_durations = [self.waveform.shape[0]/float(self.machine_config.DAQ_CONFIG[1]['SAMPLE_RATE'])]
        
    def run(self, fragment_id = 0):
        self.show_fullscreen(color = 0.0, duration = 0.0)
        for rep in range(self.experiment_config.REPEATS):
            self.led_controller.set(self.waveform,None)
            self.led_controller.start()
        
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
        
class NaturalMovieExperiment(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [len(os.listdir(self.experiment_config.FILENAME))/float(self.machine_config.SCREEN_EXPECTED_FRAME_RATE)]
        
    def run(self):
#        self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
        if self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
            duration = 0
        elif self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
            raise RuntimeError('This frame rate is not possible')
        else:
            duration = 1.0/self.experiment_config.FRAME_RATE
        for rep in range(self.experiment_config.REPEATS):
            #self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
            self.show_image(self.experiment_config.FILENAME,duration,stretch=self.experiment_config.STRETCH)
            #self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
