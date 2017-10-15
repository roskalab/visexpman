from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils,signal
import os
import numpy
import time

class NaturalMovieSv1(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.REPEATS=1
	self.DURATION = 300.0
        self.FILENAME = 'c:\\Data\\movieincage_fiona'#\\Movies\\catcam17'#movieincage_fiona'
        self.FRAME_RATE=60.0
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
        self.fragment_durations = [len(os.listdir(self.experiment_config.FILENAME))/float(self.machine_config.SCREEN_EXPECTED_FRAME_RATE)]*self.experiment_config.REPEATS
        #Calculate stretch
        from PIL import Image
        frame_size=numpy.asarray(Image.open(os.path.join(self.experiment_config.FILENAME, os.listdir(self.experiment_config.FILENAME)[0]))).shape
        w=frame_size[1]
        h=frame_size[0]
        frame=numpy.array([h,w],dtype=numpy.float)
        screen=numpy.array([self.machine_config.SCREEN_RESOLUTION['row'],self.machine_config.SCREEN_RESOLUTION['col']],dtype=numpy.float)
        self.experiment_config.STRETCH=(screen/frame).max()
        self.printl((frame, screen))
        self.printl((screen/frame, (screen/frame).max()))
        
    def run(self):
#        self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
        if self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
            duration = 0
        elif self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
            raise RuntimeError('This frame rate is not possible')
        else:
            duration = 1.0/self.experiment_config.FRAME_RATE
        nframes=len(os.listdir(self.experiment_config.FILENAME))
        for rep in range(self.experiment_config.REPEATS):
            #self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
            t0=time.time()
            self.show_image(self.experiment_config.FILENAME,duration,stretch=self.experiment_config.STRETCH)
            dt=time.time()-t0
            self.printl((nframes, dt, nframes/dt))
            dfps=abs(nframes/dt-self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
            if dfps>5:
                raise RuntimeError('Frame rate error, expected: {0}, measured {1}, make sure that image frame resolution is not big'
                            .format(self.machine_config.SCREEN_EXPECTED_FRAME_RATE,nframes/dt))
            #self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
