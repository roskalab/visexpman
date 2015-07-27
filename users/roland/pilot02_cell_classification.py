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

class APilot02FingerPrinting(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.FF_PAUSE_DURATION = 1.0
        self.FF_PAUSE_COLOR = 1.0
        self.DIRECTIONS = [0] #range(0,90, 45)
        self.SPEEDS = [1000] # [500, 1600]      
        self.DURATION = 6.0
        #self.SPATIAL_PERIOD = False
        #self.MIN_SPATIAL_PERIOD = False
        self.INTENSITY_LEVELS = 255        
        
        self.runnable = 'FingerPrinting'
        self._create_parameters_from_locals(locals())

