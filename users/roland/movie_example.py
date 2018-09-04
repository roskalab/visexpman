# -*- coding: utf-8 -*-
"""
Created on Thu Apr 13 18:58:09 2017

@author: rolandd
"""

from visexpman.engine.vision_experiment import experiment

# ------------------------------------------------------------------------------
class NaturalMovie(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.READ_ELECTRODE_COORDINATE =  False
        self.JUMPING = False
        self.FILENAME = 'c:\\Data\\movies\\catmovie1'
        self.FRAME_RATE= 30.0
        self.STRETCH = 4.573
        self.runnable = 'NaturalMovieExperiment'
        self.BACKGROUND_TIME = 0.5
        self.BACKGROUND_COLOR = 0.5
        self.REPETITIONS = 8
        self._create_parameters_from_locals(locals())

