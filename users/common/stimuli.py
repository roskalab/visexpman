'''
Most common stimulus patterns. Users should subclass these
'''

import numpy
import copy
import time
import random
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class MovingBarTemplate(experiment.Stimulus):
    def default_stimulus_configuration(self):
        self.BAR_WIDTH=5.0
        self.BAR_HEIGHT=5.0
        self.SPEED=100
        self.DIRECTIONS=range(0,360,45)
        self.COLOR=1.0
        self.BACKGROUND=0.0
        self.PAUSE_BETWEEN_SWEEPS=0.0
        self.REPETITIONS=1
        
    def calculate_stimulus_duration(self):
        trajectories, trajectory_directions, self.duration = self.moving_shape_trajectory(**self._call_params(duration_only=True))

    def _call_params(self,duration_only=False):
        p={}
        p['size']=utils.rc((self.BAR_WIDTH,self.BAR_HEIGHT))
        p['speeds']=self.SPEED if isinstance(self.SPEED,list) else [self.SPEED]
        p['directions']=self.DIRECTIONS
        p['pause']=self.PAUSE_BETWEEN_SWEEPS
        p['repetition']=self.REPETITIONS
        p['shape_starts_from_edge']=True
        if not duration_only:
            p['shape']='rect'
            p['color']=self.COLOR
            p['background_color']=self.BACKGROUND
            p['block_trigger']=True
        return p
        
    def run(self):
        self.moving_shape(**self._call_params())
        
        
class SpotWaveform(experiment.Experiment):
    '''
        Expected parameters:
        FREQUENCIES
        DURATION
        PAUSE
        BACKGROUND
        AMPLITUDES
        SPOT_DIAMETERS
        WAVEFORM
    '''
    def prepare(self):
        self.intensities = []
        n_sample = self.experiment_config.DURATION*self.machine_config.SCREEN_EXPECTED_FRAME_RATE
        for amplitude in self.experiment_config.AMPLITUDES:
            for frq in self.experiment_config.FREQUENCIES:
                self.intensities.append(numpy.array([utils.generate_waveform(self.experiment_config.WAVEFORM, n_sample, self.machine_config.SCREEN_EXPECTED_FRAME_RATE/frq,  float(amplitude),  offset = float(self.experiment_config.BACKGROUND))]).T)

    def run(self):
        for spot_diameter in self.experiment_config.SPOT_DIAMETERS:
            for intensities in self.intensities:
                self.show_fullscreen(color=self.experiment_config.BACKGROUND, duration = 0.5*self.experiment_config.PAUSE)
                self.show_shape(color = intensities, background_color = self.experiment_config.BACKGROUND, shape = 'spot', size = spot_diameter, block_trigger=True)
                self.show_fullscreen(color=self.experiment_config.BACKGROUND, duration = 0.5*self.experiment_config.PAUSE)
                
class MovingShapeExperiment(experiment.Experiment):
    def prepare(self):
        parameter_default_values = {
        'REPETITIONS': 1, 
        'SHAPE': 'rect', 
        'SHAPE_CONTRAST' : 1.0, 
        'SHAPE_BACKGROUND': 0.5, 
        'PAUSE_BETWEEN_DIRECTIONS' : 0.0, 
        }
        self.set_default_experiment_parameter_values(parameter_default_values)#TODO: eliminate this. Use inheritance for default values
        #Calculate duration
        trajectories, trajectory_directions, self.stimulus_duration = self.moving_shape_trajectory(\
                                    size = self.experiment_config.SHAPE_SIZE,
                                    speeds = self.experiment_config.SPEEDS,
                                    directions = self.experiment_config.DIRECTIONS,
                                    pause = self.pause_between_directions,
                                    repetition = self.experiment_config.REPETITIONS,
                                    shape_starts_from_edge = True)
        if hasattr(self.log, 'info'):
            self.log.info('Stimulus duration: {0}'.format(self.stimulus_duration), source = 'stim')

    def run(self):
        self.moving_shape(size = self.experiment_config.SHAPE_SIZE,
                                  speeds = self.experiment_config.SPEEDS,
                                  directions = self.experiment_config.DIRECTIONS,
                                  shape = self.shape,
                                  color = self.shape_contrast,
                                  background_color = self.shape_background,
                                  pause = self.pause_between_directions,
                                  repetition = self.experiment_config.REPETITIONS,
                                  block_trigger = True,
                                  shape_starts_from_edge = True)

class IncreasingSpotExperiment(experiment.Experiment):
    def prepare(self):
        if not hasattr(self.experiment_config, 'COLORS'):
            self.colors = [1.0]
        else:
            self.colors = self.experiment_config.COLORS
        if not hasattr(self.experiment_config, 'BACKGROUND'):
            self.background_color = self.machine_config.BACKGROUND_COLOR
        else:
            self.background_color = self.experiment_config.BACKGROUND
        
    def run(self):
        self.show_fullscreen(color = self.background_color, duration = self.experiment_config.OFF_TIME)
        for color in self.colors:
            self.increasing_spot(self.experiment_config.SIZES, self.experiment_config.ON_TIME, self.experiment_config.OFF_TIME,
                    color = color, background_color = self.background_color, pos = utils.rc((0,  0)), block_trigger = True)
                    
class FullFieldFlashesExperiment(experiment.Experiment):
    '''
    Expected parameters:
    Color(s)
    On time
    Off time
    N flashes
    '''
    def prepare(self):
        if not hasattr(self.experiment_config, 'COLORS'):
            self.colors = [1.0]
        else:
            self.colors = self.experiment_config.COLORS
        if len(self.colors)==1:
            self.colors = self.colors * self.experiment_config.NFLASHES
        if not hasattr(self.experiment_config, 'BACKGROUND'):
            self.background_color = self.machine_config.BACKGROUND_COLOR
        else:
            self.background_color = self.experiment_config.BACKGROUND
        
    def run(self):
        self.show_fullscreen(duration=self.experiment_config.OFF_TIME,color=self.background_color,block_trigger=True)
        for color in self.colors:
            self.show_fullscreen(duration=self.experiment_config.ON_TIME,color=color,block_trigger=True)
            self.show_fullscreen(duration=self.experiment_config.OFF_TIME,color=self.background_color,block_trigger=True)
            


class PixelSizeCalibration(experiment.Experiment):
    '''
    Helps pixel size calibration by showing 50 and 20 um circles
    '''
    def prepare(self):
        self.fragment_durations = [1.0]
        self.number_of_fragments = len(self.fragment_durations)

    def run(self):
        pattern = 0
        self.add_text('Circle at 100,100 um, diameter is 20 um.', color = (1.0,  0.0,  0.0), position = utils.cr((10.0, 30.0)))        
        while True:
            if pattern == 0:
                self.change_text(0, text = 'Circle at 100,100 um, diameter is 20 um.\n\nPress \'n\' to switch, \'s\' to stop.')
                self.show_shape(shape = 'circle', size = 20.0, pos = utils.cr((100, 100)))
            elif pattern == 1:
                self.change_text(0, text = 'Circle at 50,50 um, diameter is 50 um.\n\nPress \'n\' to switch, \'s\' to stop.')
                self.show_shape(shape = 'circle', size = 50.0, pos = utils.cr((50, 50)))
            else:
                pass
            if 'stop' in self.command_buffer:
                break
            elif 'next' in self.command_buffer:
                pattern += 1
                if pattern == 2:
                    pattern = 0
                self.command_buffer = ''

class NaturalMovieExperiment(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [len(os.listdir(self.experiment_config.FILENAME))/float(self.machine_config.SCREEN_EXPECTED_FRAME_RATE)]
        
    def run(self):
        if self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
            duration = 0
        elif self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
            raise RuntimeError('This frame rate is not possible')
        else:
            duration = 1.0/self.experiment_config.FRAME_RATE
        self.show_image(self.experiment_config.FILENAME,duration)

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

class LaserBeamStimulus(experiment.Experiment):
    def run(self):
        for i in range(self.experiment_config.REPEATS):
            if self.abort:
                break
            self.point_laser_beam(self.experiment_config.POSITIONS, self.experiment_config.JUMP_TIME, self.experiment_config.HOLD_TIME)
            
class ReceptiveFieldExplore(experiment.Experiment):
    '''
    Repeats: flash or sequence
    
    Supported use cases: fixed size squares are presented with no gaps and no overlaps. Fractional squares are not shown at the edges
    '''
    def prepare(self):
#	print self.machine_config.SCREEN_SIZE_UM
        shape_size, nrows, ncolumns, display_size, shape_colors, background_color = \
                self._parse_receptive_field_parameters(self.experiment_config.SHAPE_SIZE if hasattr(self.experiment_config, 'SHAPE_SIZE') else None,
                                                    self.experiment_config.NROWS if hasattr(self.experiment_config, 'NROWS') else None,
                                                    self.experiment_config.NCOLUMNS if hasattr(self.experiment_config, 'NCOLUMNS') else None,
                                                    self.experiment_config.DISPLAY_SIZE if hasattr(self.experiment_config, 'DISPLAY_SIZE') else None,
                                                    self.experiment_config.COLORS,
                                                    self.experiment_config.BACKGROUND_COLOR)
        self.stimulus_duration, positions= self.receptive_field_explore_durations_and_positions(shape_size=shape_size, 
                                                                            nrows = nrows,
                                                                            ncolumns = ncolumns,
                                                                            shape_colors = shape_colors,
                                                                            flash_repeat = self.experiment_config.REPEATS,
                                                                            sequence_repeat = self.experiment_config.REPEAT_SEQUENCE,
                                                                            on_time = self.experiment_config.ON_TIME,
                                                                            off_time = self.experiment_config.OFF_TIME)
        self.fragment_durations=[self.stimulus_duration]
        self.duration=self.stimulus_duration
        
            
    def run(self):
        self.receptive_field_explore(self.experiment_config.SHAPE_SIZE if hasattr(self.experiment_config, 'SHAPE_SIZE') else None, 
                                    self.experiment_config.ON_TIME,
                                    self.experiment_config.OFF_TIME,
                                    nrows = self.experiment_config.NROWS if hasattr(self.experiment_config, 'NROWS') else None,
                                    ncolumns = self.experiment_config.NCOLUMNS if hasattr(self.experiment_config, 'NCOLUMNS') else None,
                                    display_size = self.experiment_config.DISPLAY_SIZE if hasattr(self.experiment_config, 'DISPLAY_SIZE') else None,
                                    flash_repeat = self.experiment_config.REPEATS, 
                                    sequence_repeat = self.experiment_config.REPEAT_SEQUENCE,
                                    background_color = self.experiment_config.BACKGROUND_COLOR, 
                                    shape_colors = self.experiment_config.COLORS, 
                                    random_order = self.experiment_config.ENABLE_RANDOM_ORDER)
        self.show_fullscreen(color = self.experiment_config.BACKGROUND_COLOR)
        #print self.shape_size,self.machine_config.SCREEN_SIZE_UM,self.ncolumns,self.nrows
        self.user_data = { 'nrows':self.nrows,  'ncolumns': self.ncolumns,  'shape_size':self.shape_size}

class LaserPulse(experiment.Stimulus):
    def stimulus_configuration(self):
        self.INITIAL_DELAY=10.0
        self.PULSE_DURATION=[20e-3]
        self.PERIOD_TIME=[10.0]
        self.NPULSES=1
        self.LASER_AMPLITUDE=[1.0]
        self.SAMPLE_RATE=1000
        self.ZERO_VOLTAGE=0.0
        
    def calculate_waveform(self):
        init=numpy.zeros(int(self.SAMPLE_RATE*self.INITIAL_DELAY))
        pulses=[]
        if len(self.PULSE_DURATION)!=len(self.PERIOD_TIME):
            raise RuntimeError('Invalid timing configuration')
        for v in self.LASER_AMPLITUDE:
            for i in range(len(self.PULSE_DURATION)):
                pulse_duration=self.PULSE_DURATION[i]
                period_time=self.PERIOD_TIME[i]
                pulse=numpy.concatenate((numpy.ones(int(self.SAMPLE_RATE*pulse_duration)), numpy.zeros(int(self.SAMPLE_RATE*(period_time-pulse_duration)))))*v
                pulses.append(numpy.tile(pulse,self.NPULSES))
        self.waveform=numpy.concatenate(pulses)
        self.waveform=numpy.concatenate((init, self.waveform))
        self.waveform=numpy.where(self.waveform==0.0,self.ZERO_VOLTAGE,self.waveform)
        if 0:
                from pylab import plot,savefig,cla,clf
                clf()
                cla()
                plot(self.waveform);savefig('c:\\temp\\fig.png')
        timing_waveform=numpy.where(self.waveform==0,0,5)#.reshape(1,self.waveform.shape[0])
#        self.waveform=self.waveform.reshape(1,self.waveform.shape[0])
        self.combined_waveform=numpy.zeros((2,self.waveform.shape[0]))
        self.combined_waveform[0]=self.waveform
        self.combined_waveform[1]=timing_waveform

        
        

    def calculate_stimulus_duration(self):
        self.calculate_waveform()
        self.duration = self.combined_waveform.shape[1]/float(self.SAMPLE_RATE)
        
    def run(self):
        from visexpman.engine.hardware_interface import daq_instrument
        self.show_fullscreen(color=0.0,duration=0)
        daq_instrument.set_waveform('Dev1/ao0:1',self.combined_waveform,sample_rate = self.SAMPLE_RATE)
