from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils,signal,file
import os
import numpy
import time

class NaturalMovieSv1(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.REPEATS=1
	self.DURATION = 300.0
        #self.FILENAME = 'c:\\Data\\catcam17\\rotated'
        self.FILENAME = 'c:\\Data\\movieincage_fiona\\rotated'
        self.ROTATION=0
        self.FRAME_RATE=60.0
        self.VIDEO_OFFSET=0.0#seconds
        self.VIDEO_DURATION=0.0 #seconds
        sig_catcam17= (72720, 3419760788L, 1508680615.640625)
        sig_movieincage= (9840, 376030701L, 1508684084.046875)
        if 'catcam17' in self.FILENAME:
            sig=sig_catcam17
        elif 'movieincage_fiona' in self.FILENAME:
            sig=sig_movieincagesig_movieincage
        else:
            raise NotImplementedError('Signature is not generated for this folder: {0}'.format(self.FILENAME))
        self.IMAGE_FOLDER_SIGNATURE= sig
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
        fps_factor=self.machine_config.SCREEN_EXPECTED_FRAME_RATE/float(self.experiment_config.FRAME_RATE)
        self.fragment_durations = [fps_factor*len(os.listdir(self.experiment_config.FILENAME))/float(self.machine_config.SCREEN_EXPECTED_FRAME_RATE)]*self.experiment_config.REPEATS
        #Calculate stretch
        from PIL import Image
        foldname=os.path.join(self.experiment_config.FILENAME, str(self.experiment_config.ROTATION))
        frame_size=numpy.asarray(Image.open(os.path.join(foldname, os.listdir(foldname)[0]))).shape
        w=frame_size[1]
        h=frame_size[0]
        frame=numpy.array([h,w],dtype=numpy.float)
        screen=numpy.array([self.machine_config.SCREEN_RESOLUTION['row'],self.machine_config.SCREEN_RESOLUTION['col']],dtype=numpy.float)
        self.experiment_config.STRETCH=(screen/frame).max()
        self.printl((frame, screen))
        self.printl((screen/frame, (screen/frame).max()))
        self.fn=os.path.join(self.experiment_config.FILENAME, str(self.experiment_config.ROTATION))
        if not os.path.exists(self.fn):
            raise RuntimeError('Invalid rotation: {0}'.format(self.experiment_config.ROTATION))
        from visexpman.engine.generic import graphics
        if not graphics.is_valid_frame_rate(self.experiment_config.FRAME_RATE,self.machine_config.SCREEN_EXPECTED_FRAME_RATE):
            raise ValueError('Invalid FRAME_RATE value')
        #check folder signature
        sig=file.folder_signature(self.experiment_config.FILENAME)
        if sig!=self.experiment_config.IMAGE_FOLDER_SIGNATURE:
            raise RuntimeError('{0} folder\'s signature is not correct, expected signature: {1}, found: {2}'.format(self.experiment_config.FILENAME, self.experiment_config.IMAGE_FOLDER_SIGNATURE, sig))
        else:
            self.printl('Image folder signature OK: {0}'.format(sig))
        
        
    def run(self):
#        self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
        if self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
            duration = 0
        else:
            duration = 1.0/self.experiment_config.FRAME_RATE
        nframes=len(os.listdir(self.experiment_config.FILENAME))
        for rep in range(self.experiment_config.REPEATS):
            #self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
            t0=time.time()
            self.show_image(self.fn,duration,
                             stretch=self.experiment_config.STRETCH,
                             offset=self.experiment_config.VIDEO_OFFSET, 
                             length=self.experiment_config.VIDEO_DURATION)
            dt=time.time()-t0
            self.printl((nframes, dt, nframes/dt))
            dfps=abs(nframes/dt-self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
            if dfps>5:
                raise RuntimeError('Frame rate error, expected: {0}, measured {1}, make sure that image frame resolution is not big'
                            .format(self.machine_config.SCREEN_EXPECTED_FRAME_RATE,nframes/dt))
            #self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
