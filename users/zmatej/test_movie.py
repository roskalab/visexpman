# -*- coding: utf-8 -*-
"""
Created on Thu Nov 22 2017
@author: matej
"""

from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class NaturalMovieSv1(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.READ_ELECTRODE_COORDINATE =  False
        self.JUMPING = False
        self.FILENAME = '../../LightStimuli/NaturalMovies/catmovie1'
        self.FRAME_RATE= 30.0
        self.STRETCH = 4.573
        self.runnable = 'NaturalMovieExperiment'
        self.BACKGROUND_TIME = 0.5
        self.BACKGROUND_COLOR = 0.5
        self.REPETITIONS = 8
        self._create_parameters_from_locals(locals())


