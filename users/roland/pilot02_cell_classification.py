"""
Created on Mon Jul 27 15:43:10 2015

@author: rolandd
"""

import numpy
import copy
import time
import random
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

from stimuli import *


class APilot02BatchConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        
        self.VARS = {}
        self.VARS['FingerPrinting'] = {}
        self.VARS['FingerPrinting']['FF_PAUSE_DURATION'] = 1.0
        self.VARS['FingerPrinting']['FF_PAUSE_COLOR'] = 1.0
        self.VARS['FingerPrinting']['DIRECTIONS'] = [0] #range(0,90, 45)
        self.VARS['FingerPrinting']['SPEEDS'] = [1600] #[500, 1600]      
        self.VARS['FingerPrinting']['DURATION'] = 1.0
        self.VARS['FingerPrinting']['INTENSITY_LEVELS'] = 255        
        
        self.VARS['DashStimulus'] = {}
        self.VARS['DashStimulus']['BARSIZE'] = [25, 100]
        self.VARS['DashStimulus']['GAPSIZE'] = [5, 20]
        self.VARS['DashStimulus']['MOVINGLINES'] = 3
        self.VARS['DashStimulus']['DURATION'] = 1.0
        self.VARS['DashStimulus']['SPEEDS'] = [1600]
        self.VARS['DashStimulus']['DIRECTIONS'] = [135] #range(0, 55, 5)
        self.VARS['DashStimulus']['BAR_COLOR'] = 0.5
        
        self.runnable = 'BatchStimulus'
        self._create_parameters_from_locals(locals())


class DashStimulus(APilot02BatchConfig):
    def _create_parameters(self):
        super(AA, self)._create_parameters()
        self.runnable = 'DashStimulus'
        super(AA, self).extract_experiment_type(self)
        self._create_parameters_from_locals(locals())
        
class FingerPrinting(APilot02BatchConfig):
    def _create_parameters(self):
        super(AA, self)._create_parameters()
        self.runnable = 'DashStimulus'
        super(AA, self).extract_experiment_type(self)
        self._create_parameters_from_locals(locals())
#
#class APilot02FingerPrinting(experiment.ExperimentConfig):
#    def _create_parameters(self):
#        self.FF_PAUSE_DURATION = 1.0
#        self.FF_PAUSE_COLOR = 1.0
#        self.DIRECTIONS = [0] #range(0,90, 45)
#        self.SPEEDS = [1000] # [500, 1600]      
#        self.DURATION = 6.0
#        #self.SPATIAL_PERIOD = False
#        #self.MIN_SPATIAL_PERIOD = False
#        self.INTENSITY_LEVELS = 255        
#        
#        self.runnable = 'FingerPrinting'
#        self._create_parameters_from_locals(locals())
#
