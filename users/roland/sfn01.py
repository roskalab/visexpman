"""
Created on Mon Aug 31 10:35:00 2015
@author: rolandd
"""

from visexpman.engine.vision_experiment import experiment

from collections import OrderedDict
from stimuli import *

class SFN01BatchConfig(experiment.ExperimentConfig):
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
        
#        self.STIM_TYPE_CLASS['MarchingSquares'] = 'ReceptiveFieldExplore'
#        self.VARS['MarchingSquares'] = {}   
#        self.VARS['MarchingSquares']['SHAPE'] = 'rect'
#        self.VARS['MarchingSquares']['COLORS'] = [1.0, 0.0] # black, white
#        self.VARS['MarchingSquares']['BACKGROUND_COLOR'] = 0.5 # grey
#        self.VARS['MarchingSquares']['SHAPE_SIZE'] = 1500.0 # um
#        self.VARS['MarchingSquares']['ON_TIME'] = 1.0 
#        self.VARS['MarchingSquares']['OFF_TIME'] = 1.0
#        self.VARS['MarchingSquares']['PAUSE_BEFORE_AFTER'] = 1.0
#        self.VARS['MarchingSquares']['REPEATS'] = 1 #6
#        self.VARS['MarchingSquares']['REPEAT_SEQUENCE'] = 1
#        self.VARS['MarchingSquares']['ENABLE_RANDOM_ORDER'] = True
        
        self.STIM_TYPE_CLASS['WhiteNoise'] = 'WhiteNoiseStimulus'
        self.VARS['WhiteNoise'] = {}
        self.VARS['WhiteNoise']['DURATION_MINS'] = 30.0 # min
        self.VARS['WhiteNoise']['PIXEL_SIZE'] = [50.0] # um
        self.VARS['WhiteNoise']['N_WHITE_PIXELS'] = False
        self.VARS['WhiteNoise']['COLORS'] = [0.0, 1.0]
        
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
        
        self.STIM_TYPE_CLASS['WhiteNoise'] = 'WhiteNoiseExperiment'
        self.VARS['WhiteNoise'] = {}
        self.VARS['WhiteNoise']['DURATION_MINS'] = 0.5 #30.0 # min
        self.VARS['WhiteNoise']['PIXEL_SIZE'] = 50.0 # um
        self.VARS['WhiteNoise']['FLICKERING_FREQUENCY'] = 60.0 # Hz
        self.VARS['WhiteNoise']['N_WHITE_PIXELS'] = False
        self.VARS['WhiteNoise']['COLORS'] = [0.0, 1.0]
        
        self.STIM_TYPE_CLASS['FullFieldFlashes'] = 'FullFieldFlashesExperiment'
        self.VARS['FullFieldFlashes'] = {}   
        self.VARS['FullFieldFlashes']['BACKGROUND'] = 0.5
        self.VARS['FullFieldFlashes']['COLORS'] = [0.0, 1.0]
        self.VARS['FullFieldFlashes']['ON_TIME'] = 2.0
        self.VARS['FullFieldFlashes']['OFF_TIME'] = 1.0
        self.VARS['FullFieldFlashes']['REPETITIONS'] = 1 #10
        
        self.STIM_TYPE_CLASS['Gratings'] = 'MovingGrating'
        self.VARS['Gratings'] = {}   
        self.VARS['Gratings']['REPEATS'] = 1
        self.VARS['Gratings']['NUMBER_OF_BAR_ADVANCE_OVER_POINT'] = 5
        self.VARS['Gratings']['MARCH_TIME'] = 1
        self.VARS['Gratings']['GREY_INSTEAD_OF_MARCHING'] = False
        self.VARS['Gratings']['NUMBER_OF_MARCHING_PHASES'] = 1
        self.VARS['Gratings']['GRATING_STAND_TIME'] = 1.0
        self.VARS['Gratings']['ORIENTATIONS'] = [0.0]#range(0,360,45)
        self.VARS['Gratings']['WHITE_BAR_WIDTHS'] = [25, 300]
        self.VARS['Gratings']['VELOCITIES'] = [500] #[100, 400, 1600]
        self.VARS['Gratings']['DUTY_CYCLES'] = [1]
        self.VARS['Gratings']['PAUSE_BEFORE_AFTER'] = 1
        
        self.runnable = 'BatchStimulus'
        self._create_parameters_from_locals(locals())


class SFN01DashStimulus(SFN01BatchConfig):
    def _create_parameters(self):
        SFN01BatchConfig._create_parameters(self)   
        self.sub_stimulus = 'DashStimulus'
        SFN01BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class SFN01FingerPrinting(SFN01BatchConfig):
    def _create_parameters(self):
        SFN01BatchConfig._create_parameters(self)
        self.sub_stimulus = 'FingerPrinting'
        SFN01BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

#class SFN01MarchingSquares(SFN01BatchConfig):
#    def _create_parameters(self):
#        SFN01BatchConfig._create_parameters(self)
#        self.sub_stimulus = 'MarchingSquares'
#        SFN01BatchConfig.extract_experiment_type(self, self)
#        self._create_parameters_from_locals(locals())
        
class SFN01WhiteNoise(SFN01BatchConfig):
    def _create_parameters(self):
        SFN01BatchConfig._create_parameters(self)
        self.sub_stimulus = 'WhiteNoise'
        SFN01BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class SFN01FullField(SFN01BatchConfig):
    def _create_parameters(self):
        SFN01BatchConfig._create_parameters(self)
        self.sub_stimulus = 'FullFieldFlashes'
        SFN01BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class SFN01Gratings(SFN01BatchConfig):
    def _create_parameters(self):
        SFN01BatchConfig._create_parameters(self)
        self.sub_stimulus = 'Gratings'
        SFN01BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())
        
class SFN01WhiteNoise(SFN01BatchConfig):
    def _create_parameters(self):
        SFN01BatchConfig._create_parameters(self)
        self.sub_stimulus = 'WhiteNoise'
        SFN01BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class SFN01FullField(SFN01BatchConfig):
    def _create_parameters(self):
        SFN01BatchConfig._create_parameters(self)
        self.sub_stimulus = 'FullFieldFlashes'
        SFN01BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class SFN01Gratings(SFN01BatchConfig):
    def _create_parameters(self):
        SFN01BatchConfig._create_parameters(self)
        self.sub_stimulus = 'Gratings'
        SFN01BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())
