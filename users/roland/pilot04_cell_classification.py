# -*- coding: utf-8 -*-
"""
Created on Mon Jan 18 14:43:38 2016

@author: rolandd
"""
from visexpman.engine.vision_experiment import experiment

from collections import OrderedDict
#from stimuli import *

class Pilot04BatchConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        
        self.VARS = OrderedDict()
        self.STIM_TYPE_CLASS = {}
    
        self.STIM_TYPE_CLASS['FullFieldFlashes'] = 'FullFieldFlashesStimulus'
        self.VARS['FullFieldFlashes'] = {}   
        self.VARS['FullFieldFlashes']['BACKGROUND'] = 0.5
        self.VARS['FullFieldFlashes']['COLORS'] = [0.0, 1.0]
        self.VARS['FullFieldFlashes']['ON_TIME'] = 2.0
        self.VARS['FullFieldFlashes']['OFF_TIME'] = 2.0
        self.VARS['FullFieldFlashes']['REPETITIONS'] = 10
        
        self.STIM_TYPE_CLASS['FingerPrinting'] = 'FingerPrintingStimulus'
        self.VARS['FingerPrinting'] = {}
        self.VARS['FingerPrinting']['FF_PAUSE_DURATION'] = 1.0
        self.VARS['FingerPrinting']['FF_PAUSE_COLOR'] = 0.5
        self.VARS['FingerPrinting']['DIRECTIONS'] = [0.0, 90.0]
        self.VARS['FingerPrinting']['SPEEDS'] = [300.0]    
        self.VARS['FingerPrinting']['DURATION'] = 15.0
        self.VARS['FingerPrinting']['INTENSITY_LEVELS'] = 255
        self.VARS['FingerPrinting']['REPEATS'] = 2
        
        self.STIM_TYPE_CLASS['Chirp_Sweep'] = 'ChirpSweep'
        self.VARS['Chirp_Sweep'] = {}
        self.VARS['Chirp_Sweep']['DURATION_BREAKS'] = 1.5
        self.VARS['Chirp_Sweep']['DURATION_FULLFIELD'] = 4
        self.VARS['Chirp_Sweep']['DURATION_FREQ'] = 8
        self.VARS['Chirp_Sweep']['DURATION_CONTRAST'] = 8
        self.VARS['Chirp_Sweep']['CONTRAST_RANGE'] = [0.0, 1.0]
        self.VARS['Chirp_Sweep']['FREQUENCY_RANGE'] = [1.0, 4.0]
        self.VARS['Chirp_Sweep']['STATIC_FREQUENCY'] = 2.0
        self.VARS['Chirp_Sweep']['REPEATS'] = 5
        self.VARS['Chirp_Sweep']['COLOR'] = [0, 1, 1]
        
        self.STIM_TYPE_CLASS['WhiteNoise'] = 'WhiteNoiseStimulus'
        self.VARS['WhiteNoise'] = {}
        self.VARS['WhiteNoise']['DURATION_MINS'] = 30.0 # min
        self.VARS['WhiteNoise']['PIXEL_SIZE'] = [25.0] # um
        self.VARS['WhiteNoise']['N_WHITE_PIXELS'] = False
        self.VARS['WhiteNoise']['COLORS'] = [[0.0, 0.0, 0.0],[0.0, 1.0, 1.0]]
        
        self.STIM_TYPE_CLASS['WhiteNoiseGB'] = 'WhiteNoiseStimulus'
        self.VARS['WhiteNoiseGB'] = {}
        self.VARS['WhiteNoiseGB']['DURATION_MINS'] = 30.0 # min
        self.VARS['WhiteNoiseGB']['PIXEL_SIZE'] = [25.0] # um
        self.VARS['WhiteNoiseGB']['N_WHITE_PIXELS'] = False
        self.VARS['WhiteNoiseGB']['COLORS'] = [[0.0, 1.0, 0.0],[0.0, 0.0, 1.0]]
        
        self.STIM_TYPE_CLASS['Gratings'] = 'MovingGratingStimulus'
        self.VARS['Gratings'] = {}   
        self.VARS['Gratings']['REPEATS'] = 3
        self.VARS['Gratings']['N_BAR_ADVANCES_OVER_POINT'] = 10
        self.VARS['Gratings']['MARCH_TIME'] = 0.0
        self.VARS['Gratings']['GREY_INSTEAD_OF_MARCHING'] = False
        self.VARS['Gratings']['NUMBER_OF_MARCHING_PHASES'] = 1.0
        self.VARS['Gratings']['GRATING_STAND_TIME'] = 1.0
        self.VARS['Gratings']['ORIENTATIONS'] = range(0,360,45)
        self.VARS['Gratings']['WHITE_BAR_WIDTHS'] = [100]
        self.VARS['Gratings']['VELOCITIES'] = [300] #[100, 400, 1600]
        self.VARS['Gratings']['DUTY_CYCLES'] = [1]
        self.VARS['Gratings']['PAUSE_BEFORE_AFTER'] = 1.0
        
        self.STIM_TYPE_CLASS['DashStimulus'] = 'DashStimulus'
        self.VARS['DashStimulus'] = {}
        self.VARS['DashStimulus']['BARSIZE'] = [20, 50]
        self.VARS['DashStimulus']['GAPSIZE'] = [5, 30]
        self.VARS['DashStimulus']['MOVINGLINES'] = 3
        self.VARS['DashStimulus']['DURATION'] = 0.5#10.0
        self.VARS['DashStimulus']['SPEEDS'] = [300]
        self.VARS['DashStimulus']['DIRECTIONS'] = range(0,360,45)
        self.VARS['DashStimulus']['BAR_COLOR'] = 0.5 
        self.VARS['DashStimulus']['REPETITIONS'] = 1
       
        self.runnable = 'BatchStimulus'
        self._create_parameters_from_locals(locals())


class Pilot04DashStimulus(Pilot04BatchConfig):
    def _create_parameters(self):
        Pilot04BatchConfig._create_parameters(self)   
        self.sub_stimulus = 'DashStimulus'
        Pilot04BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class Pilot04FingerPrinting(Pilot04BatchConfig):
    def _create_parameters(self):
        Pilot04BatchConfig._create_parameters(self)
        self.sub_stimulus = 'FingerPrinting'
        Pilot04BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class Pilot04ChirpSweep(Pilot04BatchConfig):
    def _create_parameters(self):
        Pilot04BatchConfig._create_parameters(self)
        self.sub_stimulus = 'Chirp_Sweep'
        Pilot04BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())
        
class Pilot04WhiteNoise(Pilot04BatchConfig):
    def _create_parameters(self):
        Pilot04BatchConfig._create_parameters(self)
        self.sub_stimulus = 'WhiteNoise'
        Pilot04BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())
        
class Pilot04WhiteNoiseGB(Pilot04BatchConfig):
    def _create_parameters(self):
        Pilot04BatchConfig._create_parameters(self)
        self.sub_stimulus = 'WhiteNoiseGB'
        Pilot04BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class Pilot04FullField(Pilot04BatchConfig):
    def _create_parameters(self):
        Pilot04BatchConfig._create_parameters(self)
        self.sub_stimulus = 'FullFieldFlashes'
        Pilot04BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class Pilot04Gratings(Pilot04BatchConfig):
    def _create_parameters(self):
        Pilot04BatchConfig._create_parameters(self)
        self.sub_stimulus = 'Gratings'
        Pilot04BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())
