# -*- coding: utf-8 -*-
"""
Created on Thu Aug 31 2017
@author: annalisa
"""

from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils

# -----------------------------------------------------------------------------
class WhiteNoiseLong(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'WhiteNoiseStimulus'
        self.DURATION_MINS = 30.0 
        self.PIXEL_SIZE = [40.0]
        #self.FLICKERING_FREQUENCY = 60.0
        self.N_WHITE_PIXELS = False
        self.COLORS = [[0.0, 0.0, 0.0],[0.0, 1.0, 1.0]]
        self._create_parameters_from_locals(locals())

