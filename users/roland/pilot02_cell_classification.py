"""
Created on Mon Jul 27 15:43:10 2015

@author: rolandd
"""

#import numpy
#import copy
#import time
#import random
#from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

from stimuli import *

class Pilot02BatchConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        
        self.VARS = {}
        self.STIM_TYPE_CLASS = {}
        
        self.STIM_TYPE_CLASS['FingerPrinting'] = 'FingerPrinting'
        self.VARS['FingerPrinting'] = {}
        self.VARS['FingerPrinting']['FF_PAUSE_DURATION'] = 1.0
        self.VARS['FingerPrinting']['FF_PAUSE_COLOR'] = 1.0
        self.VARS['FingerPrinting']['DIRECTIONS'] = [0] #range(0,90, 45)
        self.VARS['FingerPrinting']['SPEEDS'] = [1600] #[500, 1600]      
        self.VARS['FingerPrinting']['DURATION'] = 1.0
        self.VARS['FingerPrinting']['INTENSITY_LEVELS'] = 255        
        
        self.STIM_TYPE_CLASS['DashStimulus'] = 'DashStimulus'
        self.VARS['DashStimulus'] = {}
        self.VARS['DashStimulus']['BARSIZE'] = [25, 100]
        self.VARS['DashStimulus']['GAPSIZE'] = [5, 20]
        self.VARS['DashStimulus']['MOVINGLINES'] = 3
        self.VARS['DashStimulus']['DURATION'] = 1.0
        self.VARS['DashStimulus']['SPEEDS'] = [1600]
        self.VARS['DashStimulus']['DIRECTIONS'] = [135] #range(0, 55, 5)
        self.VARS['DashStimulus']['BAR_COLOR'] = 0.5
        
        self.STIM_TYPE_CLASS['MarchingSquares'] = 'ReceptiveFieldExplore'
        self.VARS['MarchingSquares'] = {}   
        self.VARS['MarchingSquares']['SHAPE'] = 'rect'
        self.VARS['MarchingSquares']['COLORS'] = [1.0, 0.0] # black, white
        self.VARS['MarchingSquares']['BACKGROUND_COLOR'] = 0.5 # grey
        self.VARS['MarchingSquares']['SHAPE_SIZE'] = 1500.0 # um
        self.VARS['MarchingSquares']['ON_TIME'] = 1.0 
        self.VARS['MarchingSquares']['OFF_TIME'] = 1.0
        self.VARS['MarchingSquares']['PAUSE_BEFORE_AFTER'] = 1.0
        self.VARS['MarchingSquares']['REPEATS'] = 1 #6
        self.VARS['MarchingSquares']['REPEAT_SEQUENCE'] = 1
        self.VARS['MarchingSquares']['ENABLE_RANDOM_ORDER'] = True
        
        self.runnable = 'BatchStimulus'
        self._create_parameters_from_locals(locals())


class Pilot02DashStimulus(Pilot02BatchConfig):
    def _create_parameters(self):
        Pilot02BatchConfig._create_parameters(self)   
        self.sub_stimulus = 'DashStimulus'
        Pilot02BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class Pilot02FingerPrinting(Pilot02BatchConfig):
    def _create_parameters(self):
        Pilot02BatchConfig._create_parameters(self)
        self.sub_stimulus = 'FingerPrinting'
        Pilot02BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class Pilot02MarchingSquares(Pilot02BatchConfig):
    def _create_parameters(self):
        Pilot02BatchConfig._create_parameters(self)
        self.sub_stimulus = 'MarchingSquares'
        Pilot02BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())