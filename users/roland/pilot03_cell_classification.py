# -*- coding: utf-8 -*-
"""
Created on Mon Jan 18 14:43:38 2016

@author: rolandd
"""
from visexpman.engine.vision_experiment import experiment

from collections import OrderedDict
#from stimuli import *

class Pilot03BatchConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        
        self.VARS = OrderedDict()
        self.STIM_TYPE_CLASS = {}
    
        self.STIM_TYPE_CLASS['FullFieldFlashes'] = 'FullFieldFlashesExperiment'
        self.VARS['FullFieldFlashes'] = {}   
        self.VARS['FullFieldFlashes']['BACKGROUND'] = 0.5
        self.VARS['FullFieldFlashes']['COLORS'] = [0.0, 1.0]
        self.VARS['FullFieldFlashes']['ON_TIME'] = 2.0
        self.VARS['FullFieldFlashes']['OFF_TIME'] = 2.0
        self.VARS['FullFieldFlashes']['REPETITIONS'] = 10
        
        self.STIM_TYPE_CLASS['FingerPrinting'] = 'FingerPrinting'
        self.VARS['FingerPrinting'] = {}
        self.VARS['FingerPrinting']['FF_PAUSE_DURATION'] = 1.0
        self.VARS['FingerPrinting']['FF_PAUSE_COLOR'] = 0.5
        self.VARS['FingerPrinting']['DIRECTIONS'] = [0.0, 90.0]
        self.VARS['FingerPrinting']['SPEEDS'] = [300.0, 1000.0] #[500, 1600]      
        self.VARS['FingerPrinting']['DURATION'] = 15.0
        self.VARS['FingerPrinting']['INTENSITY_LEVELS'] = 255
        self.VARS['FingerPrinting']['REPEATS'] = 5
        
        #self.STIM_TYPE_CLASS['Chirp_Amp'] = 'Chirp'
        #self.VARS['Chirp_Amp'] = {}
        #self.VARS['Chirp_Amp']['DURATION'] = 8
        #self.VARS['Chirp_Amp']['CONTRAST_RANGE'] = [0.0, 1.0]
        #self.VARS['Chirp_Amp']['FREQUENCY_RANGE'] = [2.0, 2.0]
        #self.VARS['Chirp_Amp']['REPEATS'] = 3
        
        #self.STIM_TYPE_CLASS['Chirp_Freq'] = 'Chirp'
        #self.VARS['Chirp_Freq'] = {}
        #self.VARS['Chirp_Freq']['DURATION'] = 8
        #self.VARS['Chirp_Freq']['CONTRAST_RANGE'] = [1.0, 1.0]
        #self.VARS['Chirp_Freq']['FREQUENCY_RANGE'] = [1.0, 4.0]
        #self.VARS['Chirp_Freq']['REPEATS'] = 5   

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
        
        self.STIM_TYPE_CLASS['Gratings'] = 'MovingGrating'
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
        self.VARS['DashStimulus']['DURATION'] = 10.0
        self.VARS['DashStimulus']['SPEEDS'] = [300]
        self.VARS['DashStimulus']['DIRECTIONS'] = range(0,360,45)
        self.VARS['DashStimulus']['BAR_COLOR'] = 0.5 
        
        self.runnable = 'BatchStimulus'
        self._create_parameters_from_locals(locals())


class Pilot03DashStimulus(Pilot03BatchConfig):
    def _create_parameters(self):
        Pilot03BatchConfig._create_parameters(self)   
        self.sub_stimulus = 'DashStimulus'
        Pilot03BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class Pilot03FingerPrinting(Pilot03BatchConfig):
    def _create_parameters(self):
        Pilot03BatchConfig._create_parameters(self)
        self.sub_stimulus = 'FingerPrinting'
        Pilot03BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

#class Pilot03ChirpAmp(Pilot03BatchConfig):
#    def _create_parameters(self):
#        Pilot03BatchConfig._create_parameters(self)
#        self.sub_stimulus = 'Chirp_Amp'
#        Pilot03BatchConfig.extract_experiment_type(self, self)
#        self._create_parameters_from_locals(locals())

#class Pilot03ChirpFreq(Pilot03BatchConfig):
#    def _create_parameters(self):
#        Pilot03BatchConfig._create_parameters(self)
#        self.sub_stimulus = 'Chirp_Freq'
#        Pilot03BatchConfig.extract_experiment_type(self, self)
#        self._create_parameters_from_locals(locals())
     
class Pilot03ChirpSweep(Pilot03BatchConfig):
    def _create_parameters(self):
        Pilot03BatchConfig._create_parameters(self)
        self.sub_stimulus = 'Chirp_Sweep'
        Pilot03BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())
        
class Pilot03WhiteNoise(Pilot03BatchConfig):
    def _create_parameters(self):
        Pilot03BatchConfig._create_parameters(self)
        self.sub_stimulus = 'WhiteNoise'
        Pilot03BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class Pilot03FullField(Pilot03BatchConfig):
    def _create_parameters(self):
        Pilot03BatchConfig._create_parameters(self)
        self.sub_stimulus = 'FullFieldFlashes'
        Pilot03BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class Pilot03Gratings(Pilot03BatchConfig):
    def _create_parameters(self):
        Pilot03BatchConfig._create_parameters(self)
        self.sub_stimulus = 'Gratings'
        Pilot03BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())
