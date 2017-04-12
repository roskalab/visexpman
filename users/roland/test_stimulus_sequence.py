import numpy
import copy
import time
import random
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

#from stimuli import *

# ------------------------------------------------------------------------------
class xMovingBar(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'MovingShapeStimulus'
        self.DIRECTIONS = range(0, 360, 45)
        self.SPEEDS = [500, 1600]  # um/s#
        self.REPETITIONS = 1
        self.SHAPE_BACKGROUND = 0.0
        self.SHAPE_CONTRAST = 1.0
        
        self.SHAPE = 'rect'
        self.SHAPE_SIZE = utils.cr((1000, 500)) #um
        self.RANDOM_DIRECTIONS = True
        self.RANDOM_SPEEDS = True        
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self._create_parameters_from_locals(locals())

# ------------------------------------------------------------------------------
class xMarchingSquaresSmall(experiment.ExperimentConfig):
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
class xWhiteNoise(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'WhiteNoiseStimulus'
        self.DURATION_MINS = 0.2 #15 min
        self.PIXEL_SIZE =  [40.0]
        self.N_WHITE_PIXELS = False
        self.COLORS = [[0.0, 0.0, 0.0],[0.0, 1.0, 1.0]]
        
        self._create_parameters_from_locals(locals())

# ------------------------------------------------------------------------------
class xColoredNoise(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'ColoredNoiseStimulus'
        self.DURATION_MINS = 0.1 #15 min
        self.PIXEL_SIZE =  [40.0]
        #self.N_WHITE_PIXELS = False
        #self.COLORS = [[0.0, 0.0, 0.0],[0.0, 1.0, 1.0]]
        self.RED = False
        self.GREEN = True
        self.BLUE = True   
        
        self._create_parameters_from_locals(locals())
