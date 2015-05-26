import numpy
import copy
import time
import random
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

from stimuli import *

# ------------------------------------------------------------------------------
class Pilot01MarchingSquaresSmall(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.COLORS = [1.0, 0.0] # black, white
        self.BACKGROUND_COLOR = 0.5 # grey
        self.SHAPE_SIZE = 150.0 # um
        self.ON_TIME = 1.0 
        self.OFF_TIME = 1.0
        self.PAUSE_BEFORE_AFTER = 2.0
        self.REPEATS = 6
        self.REPEAT_SEQUENCE = 1
        self.ENABLE_RANDOM_ORDER = True
        self.runnable='ReceptiveFieldExplore'
        self._create_parameters_from_locals(locals())

class Pilot01MarchingSquaresLarge(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.COLORS = [1.0, 0.0] # black, white
        self.BACKGROUND_COLOR = 0.5 # grey
        self.SHAPE_SIZE = 500.0 # um
        self.NROWS = 7
        self.NCOLUMNS = 7
        self.ON_TIME = 1.0 
        self.OFF_TIME = 0#1.0
        self.PAUSE_BEFORE_AFTER = 0 #2.0
        self.REPEATS = 6-5
        self.REPEAT_SEQUENCE = 1
        self.ENABLE_RANDOM_ORDER = not True
        self.OVERLAP = [200,200]
        self.runnable='ReceptiveFieldExplore'
        self._create_parameters_from_locals(locals())

# ------------------------------------------------------------------------------
class Pilot01WhiteNoiseSmall(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.DURATION = 1.0/60 #30.0/60.0 #30 min
        self.PIXEL_SIZE =50.0
        self.FLICKERING_FREQUENCY = 60.0
        self.N_WHITE_PIXELS = False#None
        self.COLORS = [0.0, 1.0]
        self.runnable = 'WhiteNoiseExperiment'
        self._create_parameters_from_locals(locals())

class Pilot01WhiteNoiseMiddle(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.DURATION = 1.0/60.0 #20.0/60.0 #20 min
        self.PIXEL_SIZE =100.0
        self.FLICKERING_FREQUENCY = 60.0
        self.N_WHITE_PIXELS = False#None
        self.COLORS = [0.0, 1.0]
        self.runnable = 'WhiteNoiseExperiment'
        self._create_parameters_from_locals(locals())

class Pilot01WhiteNoiseLarge(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.DURATION = 1.0/60.0 #15.0/60.0 #15 min
        self.PIXEL_SIZE =150.0
        self.FLICKERING_FREQUENCY = 60.0
        self.N_WHITE_PIXELS = False#None
        self.COLORS = [0.0, 1.0]
        self.runnable = 'WhiteNoiseExperiment'
        self._create_parameters_from_locals(locals())

# ------------------------------------------------------------------------------

class Pilot01FullField(experiment.ExperimentConfig):
    
    def _create_parameters(self):
        self.COLORS = [0.0, 1.0]
        self.ON_TIME = 2.0
        self.OFF_TIME = 2.0
        self.runnable = 'FullFieldFlashesExperiment'
        self._create_parameters_from_locals(locals())


# ------------------------------------------------------------------------------
class Pilot01Gratings(experiment.ExperimentConfig):
    
    def _create_parameters(self):
        self.REPEATS = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 5
        self.MARCH_TIME = 1
        self.GREY_INSTEAD_OF_MARCHING = False
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.GRATING_STAND_TIME = 1.0
        self.ORIENTATIONS = range(0,360,45)
        self.WHITE_BAR_WIDTHS = [25, 300]
        self.VELOCITIES = [100, 400, 1600]
        self.DUTY_CYCLES = [1]
        self.PAUSE_BEFORE_AFTER = 1
        
        self.runnable = 'MovingGrating'
        self._create_parameters_from_locals(locals())

