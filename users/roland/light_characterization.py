# -*- coding: utf-8 -*-
"""
Created on Wed Feb  3 13:59:41 2016

@author: rolandd
"""
from visexpman.engine.vision_experiment import experiment

#from collections import OrderedDict
#from stimuli import *

# ------------------------------------------------------------------------------

class LightCharacterizationWhite(experiment.ExperimentConfig):
    
    def _create_parameters(self):
        self.BACKGROUND = 0.5
        self.COLORS = [[1.0, 1.0, 1.0]]
        self.ON_TIME = 10.0
        self.OFF_TIME = 0.0
        self.REPETITIONS = 1
        self.runnable = 'FullFieldFlashesStimulus'
        self._create_parameters_from_locals(locals())

# ------------------------------------------------------------------------------

class LightCharacterizationBlue(experiment.ExperimentConfig):
    
    def _create_parameters(self):
        self.BACKGROUND = 0.5
        self.COLORS = [[0.0, 0.0, 1.0], [1.0, 0.0, 0.0]] # blue, red
        self.ON_TIME = 10.0
        self.OFF_TIME = 0.0
        self.REPETITIONS = 1
        self.runnable = 'FullFieldFlashesStimulus'
        self._create_parameters_from_locals(locals())
        
# ------------------------------------------------------------------------------

class LightCharacterizationBlue(experiment.ExperimentConfig):
    
    def _create_parameters(self):
        self.BACKGROUND = 0.5
        self.COLORS = [[0.0, 0.0, 1.0], [1.0, 0.0, 0.0]] # blue, red
        self.ON_TIME = 10.0
        self.OFF_TIME = 0.0
        self.REPETITIONS = 1
        self.runnable = 'FullFieldFlashesStimulus'
        self._create_parameters_from_locals(locals())