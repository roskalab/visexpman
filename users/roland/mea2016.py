# -*- coding: utf-8 -*-
"""
Created on Mon May 2 15:36:52 2016

@author: rolandd
"""
from visexpman.engine.vision_experiment import experiment

from collections import OrderedDict

class Mea2016BatchConfig(experiment.ExperimentConfig):
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
        self.VARS['FingerPrinting']['REPEATS'] = 5
        
        self.STIM_TYPE_CLASS['WhiteNoise'] = 'WhiteNoiseStimulus'
        self.VARS['WhiteNoise'] = {}
        self.VARS['WhiteNoise']['DURATION_MINS'] = 30.0 # min
        self.VARS['WhiteNoise']['PIXEL_SIZE'] = [25.0] # um
        self.VARS['WhiteNoise']['N_WHITE_PIXELS'] = False
        self.VARS['WhiteNoise']['COLORS'] = [[0.0, 0.0, 0.0],[0.0, 1.0, 1.0]]
        
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
        
        self.STIM_TYPE_CLASS['Gratings'] = 'MovingGratingStimulus'
        self.VARS['Gratings'] = {}   
        self.VARS['Gratings']['REPEATS'] = 3
        self.VARS['Gratings']['N_BAR_ADVANCES_OVER_POINT'] = 10
        self.VARS['Gratings']['MARCH_TIME'] = 0.0
        self.VARS['Gratings']['GREY_INSTEAD_OF_MARCHING'] = False
        self.VARS['Gratings']['NUMBER_OF_MARCHING_PHASES'] = 1.0
        self.VARS['Gratings']['GRATING_STAND_TIME'] = 1.0
        self.VARS['Gratings']['ORIENTATIONS'] = range(0,360, 22.5)
        self.VARS['Gratings']['WHITE_BAR_WIDTHS'] = [100]
        self.VARS['Gratings']['VELOCITIES'] = [300]
        self.VARS['Gratings']['DUTY_CYCLES'] = [1]
        self.VARS['Gratings']['PAUSE_BEFORE_AFTER'] = 1.0
        
        self.STIM_TYPE_CLASS['DashStimulus'] = 'DashStimulus'
        self.VARS['DashStimulus'] = {}
        self.VARS['DashStimulus']['BARSIZE'] = [20, 50]
        self.VARS['DashStimulus']['GAPSIZE'] = [5, 30]
        self.VARS['DashStimulus']['MOVINGLINES'] = 3
        self.VARS['DashStimulus']['DURATION'] = 10.0
        self.VARS['DashStimulus']['SPEEDS'] = [300]
        self.VARS['DashStimulus']['DIRECTIONS'] = range(0,360,22.5)
        self.VARS['DashStimulus']['BAR_COLOR'] = 0.5
        self.VARS['DashStimulus']['REPETITIONS'] = 3 # ==> 25 min
       
        self.runnable = 'BatchStimulus'
        self._create_parameters_from_locals(locals())


class Mea2016DashStimulus(Mea2016BatchConfig):
    def _create_parameters(self):
        Mea2016BatchConfig._create_parameters(self)   
        self.sub_stimulus = 'DashStimulus'
        Mea2016BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class Mea2016FingerPrinting(Mea2016BatchConfig):
    def _create_parameters(self):
        Mea2016BatchConfig._create_parameters(self)
        self.sub_stimulus = 'FingerPrinting'
        Mea2016BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class Mea2016ChirpSweep(Mea2016BatchConfig):
    def _create_parameters(self):
        Mea2016BatchConfig._create_parameters(self)
        self.sub_stimulus = 'Chirp_Sweep'
        Mea2016BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())
        
class Mea2016WhiteNoise(Mea2016BatchConfig):
    def _create_parameters(self):
        Mea2016BatchConfig._create_parameters(self)
        self.sub_stimulus = 'WhiteNoise'
        Mea2016BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class Mea2016FullField(Mea2016BatchConfig):
    def _create_parameters(self):
        Mea2016BatchConfig._create_parameters(self)
        self.sub_stimulus = 'FullFieldFlashes'
        Mea2016BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class Mea2016Gratings(Mea2016BatchConfig):
    def _create_parameters(self):
        Mea2016BatchConfig._create_parameters(self)
        self.sub_stimulus = 'Gratings'
        Mea2016BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())
