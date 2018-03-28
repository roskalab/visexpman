# -*- coding: utf-8 -*-
"""
Created on Thu Apr 13 18:58:09 2017

@author: rolandd
"""

from visexpman.engine.vision_experiment import experiment

# ------------------------------------------------------------------------------
class SC04FingerPrinting(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'FingerPrintingStimulus'
        
        self.FF_PAUSE_DURATION = 1.0
        self.FF_PAUSE_COLOR = 0.5
        self.DIRECTIONS = [0.0, 90.0]
        self.SPEEDS = [300.0]    
        self.DURATION = 15.0
        self.INTENSITY_LEVELS = 255
        self.REPEATS = 15
        self._create_parameters_from_locals(locals())

# ------------------------------------------------------------------------------
class SC04ChirpSweep(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'ChirpSweep'
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

## -----------------------------------------------------------------------------
class SC04NewRandomDots(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'RandomDotsStimulus'
        self.REPEATS = 1
        self.DURATION = 7.5*60 # time scale wrong at this point!
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
class SC04WhiteNoise(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'WhiteNoiseStimulus'
        self.DURATION_MINS = 15.0 # 15 min
        self.PIXEL_SIZE = [40.0]
        #self.FLICKERING_FREQUENCY = 60.0
        self.N_WHITE_PIXELS = False
        self.COLORS = [[0.0, 0.0, 0.0],[0.0, 1.0, 1.0]]
        self._create_parameters_from_locals(locals())

# -----------------------------------------------------------------------------
class SC04ColoredNoise(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'ColoredNoiseStimulus'
        self.DURATION_MINS = 15.0  # 15 min
        self.PIXEL_SIZE = [40.0] # um
        self.RED = False
        self.GREEN = True
        self.BLUE = True
        self._create_parameters_from_locals(locals())

# ------------------------------------------------------------------------------
class SC05MovingBar(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'MovingShapeStimulus'
        self.DIRECTIONS = range(0, 360, 45)
        self.SPEEDS = [300, 1600]  # um/s#
        self.REPETITIONS = 5 #6
        self.SHAPE_BACKGROUND = 0.0
        self.SHAPE_CONTRAST = 1.0
        self.SHAPE = 'rect'
        self.SHAPE_SIZE = utils.cr((1000, 500)) #um
        self.RANDOM_ORDER = True
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self._create_parameters_from_locals(locals())
        
# ------------------------------------------------------------------------------
class SC04MovingGrating(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'MovingGratingStimulus'
        self.REPEATS = 5 # s?
        self.N_BAR_ADVANCES_OVER_POINT = 20
        self.MARCH_TIME = 0 # Does nothing: remove eventually!
        self.GREY_INSTEAD_OF_MARCHING = False
        self.NUMBER_OF_MARCHING_PHASES = 1.0
        self.GRATING_STAND_TIME = 0.5 # s?
        self.ORIENTATIONS = range(0,360, 45)
        self.WHITE_BAR_WIDTHS = [100]
        self.VELOCITIES = [300, 1000]
        self.DUTY_CYCLES = [1] # determines how far the bars are separated
        self.PAUSE_BEFORE_AFTER = 0.5
        self.RANDOM_ORDER = True
        
        self._create_parameters_from_locals(locals())


        


