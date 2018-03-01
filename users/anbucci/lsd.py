# -*- coding: utf-8 -*-
"""
Created on Thu Aug 31 2017
@author: anbucci
"""

from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils

# -----------------------------------------------------------------------------
class LSDFullFieldFlashes(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable='FullFieldTestFlicker'
        #self.SHAPE = 'rect'
        #self.COLORS = [0.0, 1.0] # white, black
        #self.BACKGROUND_COLOR = 0.5 # grey
        #self.SHAPE_SIZE = 100.0 # um
        #self.ON_TIME = 1 #1.0/60.0 
        #self.OFF_TIME = 1 # 1.0/60.0
        self.REPETITIONS = 2000000
        self._create_parameters_from_locals(locals())

