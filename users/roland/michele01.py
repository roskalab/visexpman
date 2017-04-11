import numpy
import copy
import time
import random
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

#from stimuli import *

# ------------------------------------------------------------------------------
class MovingBar(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'MovingShapeStimulus'
        self.DIRECTIONS = range(0, 360, 45)
        self.SPEEDS = [300, 1600]  # um/s#
        self.REPETITIONS = 5
        self.SHAPE_BACKGROUND = 0.0
        self.SHAPE_CONTRAST = 1.0
        
        self.SHAPE = 'rect'
        self.SHAPE_SIZE = utils.cr((1000, 500)) #um
        self.RANDOM_DIRECTIONS = True
        self.RANDOM_SPEEDS = True        
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self._create_parameters_from_locals(locals())

# ------------------------------------------------------------------------------
class MarchingSquaresSmall(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable='ReceptiveFieldExplore'
        self.SHAPE = 'rect'
        self.COLORS = [1.0, 0.0] # black, white
        self.BACKGROUND_COLOR = 0.5 # grey
        self.SHAPE_SIZE = 100.0 # um
        self.ON_TIME = 1.0 
        self.OFF_TIME = 1.0
        self.PAUSE_BEFORE_AFTER = 2.0
        self.REPEATS = 2
        self.REPEAT_SEQUENCE = 2
        self.ENABLE_RANDOM_ORDER = True

        self._create_parameters_from_locals(locals())

# ------------------------------------------------------------------------------
class WhiteNoise(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'WhiteNoiseStimulus'
        self.DURATION_MINS = 15.0 #15 min
        self.PIXEL_SIZE = 40.0
        self.N_WHITE_PIXELS = False
        self.COLORS = [[0.0, 0.0, 0.0],[0.0, 1.0, 1.0]]

        self._create_parameters_from_locals(locals())
