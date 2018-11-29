# -*- coding: utf-8 -*-
"""
Created on Thu Aug 31 2017
@author: matej
"""

from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

# -----------------------------------------------------------------------------
#30 min
class WhiteNoiseLong(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'WhiteNoiseStimulus'
        self.DURATION_MINS = 30.0 
        self.PIXEL_SIZE = [40.0]
        #self.FLICKERING_FREQUENCY = 60.0
        self.N_WHITE_PIXELS = False
        self.COLORS = [[0.0, 0.0, 0.0],[0.0, 1.0, 1.0]]
        self._create_parameters_from_locals(locals())

# -----------------------------------------------------------------------------
#30 min
class WhiteNoiseShort(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'WhiteNoiseStimulus'
        self.DURATION_MINS = 5.0
        self.PIXEL_SIZE = [40.0]
        #self.FLICKERING_FREQUENCY = 60.0
        self.N_WHITE_PIXELS = False
        self.COLORS = [[0.0, 0.0, 0.0],[0.0, 1.0, 1.0]]  
        self._create_parameters_from_locals(locals())

# ------------------------------------------------------------------------------
#24 min
class MovingGratingLong(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'MovingGratingStimulus'
        self.REPEATS = 10
        self.N_BAR_ADVANCES_OVER_POINT = 20
        self.MARCH_TIME = 0.0
        self.GREY_INSTEAD_OF_MARCHING = False
        self.NUMBER_OF_MARCHING_PHASES = 1.0
        self.GRATING_STAND_TIME = 1.0
        self.ORIENTATIONS = range(0,360, 45)
        self.WHITE_BAR_WIDTHS = [100]
        self.VELOCITIES = [300, 1500]
        self.DUTY_CYCLES = [1]
        self.PAUSE_BEFORE_AFTER = 1.0
        self._create_parameters_from_locals(locals())


# ------------------------------------------------------------------------------
#24 min
class MovingGratingShort(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'MovingGratingStimulus'
        self.REPEATS = 10
        self.N_BAR_ADVANCES_OVER_POINT = 20
        self.MARCH_TIME = 0.0
        self.GREY_INSTEAD_OF_MARCHING = False
        self.NUMBER_OF_MARCHING_PHASES = 1.0
        self.GRATING_STAND_TIME = 1.0
        self.ORIENTATIONS = range(0,360, 45)
        self.WHITE_BAR_WIDTHS = [100]
        self.VELOCITIES = [300, 1500]
        self.DUTY_CYCLES = [1]
        self.PAUSE_BEFORE_AFTER = 1.0
        self._create_parameters_from_locals(locals())

# -----------------------------------------------------------------------------
#27 min
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

# -----------------------------------------------------------------------------
#10 sec
class FullFieldFlashes(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable='FullFieldFlashesStimulus'
        self.SHAPE = 'rect'
        self.COLORS = [0.0, 1.0] # white, black
        self.BACKGROUND_COLOR = 0.5 # grey
        #self.SHAPE_SIZE = 100.0 # um
        self.ON_TIME = 2.0 
        self.OFF_TIME = 2.0
        self.REPEATS = 20
        self._create_parameters_from_locals(locals())

# -----------------------------------------------------------------------------
# not working
class MovingBar(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'MovingShapeStimulus'
        self.SHAPE_SIZE = utils.cr((1000, 500)) #um
        self.SPEEDS = [1600] #um/s#
        #self.SPEEDS = [120, 200,400,1600] #um/s
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self.RANDOM_DIRECTIONS = True
        self.REPETITIONS = 10
        self.DIRECTIONS = range(0,360,45)
        self.SHAPE = 'rect'
        self.SHAPE_BACKGROUND=0.0
        self.SHAPE_CONTRAST = 1.0
        self._create_parameters_from_locals(locals())