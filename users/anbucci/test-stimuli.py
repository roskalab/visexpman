# -*- coding: utf-8 -*-
"""
Created on Thu Aug 31 2017
@author: anbucci
"""

from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment


# -----------------------------------------------------------------------------
#15 min
class AB_WhiteNoisee(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'WhiteNoiseStimulus'
        self.DURATION_MINS = 20.0
        self.PIXEL_SIZE = [40.0]
        #self.FLICKERING_FREQUENCY = 60.0
        self.N_WHITE_PIXELS = False
        self.COLORS = [[0.0, 0.0, 0.0],[0.0, 1.0, 1.0]]  
        self._create_parameters_from_locals(locals())

# ------------------------------------------------------------------------------
#24 min
class AB_MovingGrating(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'MovingGratingStimulus'
        self.REPEATS = 8
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
class AB_MarchingSquares(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable='ReceptiveFieldExplore'
        self.SHAPE = 'rect'
        self.COLORS = [1.0, 0.0] # black, white
        self.BACKGROUND_COLOR = 0.5 # grey
        self.SHAPE_SIZE = 100.0 # um
        self.ON_TIME = 1.0 
        self.OFF_TIME = 1.0
        self.PAUSE_BEFORE_AFTER = 2.0
        self.REPEATS = 1
        self.REPEAT_SEQUENCE = 2
        self.ENABLE_RANDOM_ORDER = True
        self._create_parameters_from_locals(locals())

# -----------------------------------------------------------------------------
# moving bar
class AB_MovingBar(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'MovingShapeStimulus'
        self.DIRECTIONS = range(0, 360, 45)
        self.SPEEDS = [300, 1600]  # um/s
        self.REPETITIONS = 6
        self.SHAPE_BACKGROUND = 0.0
        self.SHAPE_CONTRAST = 1.0
        self.SHAPE = 'rect'
        self.SHAPE_SIZE = utils.cr((1000, 500)) #um
        self.RANDOM_ORDER = True
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self._create_parameters_from_locals(locals())

# -----------------------------------------------------------------------------
# chirp sweep
class AB_ChirpSweep(experiment.ExperimentConfig): 
    def _create_parameters(self):
        self.runnable = 'ChirpSweep'
        self.Chirp_Sweep = {}
        self.DURATION_BREAKS = 1.5
        self.DURATION_FULLFIELD = 4
        self.DURATION_FREQ = 8
        self.DURATION_CONTRAST = 8
        self.CONTRAST_RANGE = [0.0, 1.0]
        self.FREQUENCY_RANGE = [1.0, 4.0]
        self.STATIC_FREQUENCY = 2.0
        self.REPEATS = 5
        self.COLOR = [0, 1, 1]
        self._create_parameters_from_locals(locals())

# -----------------------------------------------------------------------------
# fingerprinting
class AB_FingerPrinting(experiment.ExperimentConfig): 
    def _create_parameters(self):
        self.runnable = 'FingerPrintingStimulus'
        self.FingerPrinting = {}
        self.FF_PAUSE_DURATION = 1.0
        self.FF_PAUSE_COLOR = 0.5
        self.DIRECTIONS = [0.0, 90.0]
        self.SPEEDS = [300.0]    
        self.DURATION = 15.0
        self.INTENSITY_LEVELS = 255
        self.REPEATS = 15
        self._create_parameters_from_locals(locals())

# -----------------------------------------------------------------------------
# moving dots
class AB_MovingDots(experiment.ExperimentConfig): 
    def _create_parameters(self):
        self.runnable = 'RandomDotsStimulus'
        self.REPEATS = 3
        self.DURATION = 10*60 # time scale wrong at this point!
        self.DIRECTIONS = []
        self.DOTSIZES = [50]
        self.DOTSIZES_MIN_MAX = []
        self.DOTDURATIONS = [0.5]
        self.DOTDURATIONS_MIN_MAX = []
        self.SPEEDS = [6]
        self.SPEEDS_MIN_MAX = []
        self.COLORS = [[1,1,1], [0,0,0]]
        self.BGCOLOR = [0.5, 0.5, 0.5]
        self.SPARSITY_FACTOR = 0.05
        self._create_parameters_from_locals(locals())


# -----------------------------------------------------------------------------
# Two pixels stimulus

class AB_TwoPixelFullField(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.CONTRASTS=[0.625, 0.75, 0.87, 0.999]
        self.ONTIME=2#seconds
        self.OFFTIME=2#seconds
        self.TIMESHIFT=-1.5#seconds
        self.PIXEL_RATIO=0.5
        self.REPEATS=5
        self.runnable='TwoPixelFullFieldE'
        self._create_parameters_from_locals(locals())

# -----------------------------------------------------------------------------
# Two pixels stimulus: modifications

class TEST_TwoPixelFullField(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.CONTRASTS=[0.625, 0.75, 0.87, 0.999]
        self.ONTIME=2#seconds
        self.OFFTIME=2#seconds
        self.TIMESHIFT= 1 #-1.5#seconds
        self.PIXEL_RATIO=0.5
        self.REPEATS=5
        self.runnable='lisaTwoPixelFullFieldE'
        self._create_parameters_from_locals(locals())

# -----------------------------------------------------------------------------


# Contrast steps

class AB_ContrastStepsParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPOT_SIZE = 4000  # fullfield 2500
        self.ON_TIME = 2 #s
        self.OFF_TIME = 2 #s
        self.BACKGROUND_TIME = 2
        self.SPOT_CONTRAST_ON = [0.5, 0.65, 0.375, 0.75, 0.25, 0.875,  0.125, 0.999, 0.01]#[0.625, 0.75, 0.87, 0.999]  #N [0.999]
        self.SPOT_CONTRAST_OFF = 0.5
        self.REPETITIONS_ALL = 1
        self.BACKGROUND_COLOR = 0.5
        self.BLACK = 0.01
        self.WHITE = 0.999
        self.runnable = 'ContrastExperiment'
        self._create_parameters_from_locals(locals())        
