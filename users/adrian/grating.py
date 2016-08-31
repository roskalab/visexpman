from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
import numpy
import time
import random
import copy

class MovingGratingConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        #Timing        
        self.NUMBER_OF_MARCHING_PHASES = 4 #number of static bar compositions at beginning
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3 #how many times the bar hit a point -> this + speed = moving time
        self.MARCH_TIME = 2.5 # standing phase time
        self.GRATING_STAND_TIME = 2.0 #post-moving-phase time
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 45)
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.WHITE_BAR_WIDTHS = [300.0]
        self.VELOCITIES = [1200.0]
        self.DUTY_CYCLES = [2.5] #white and blck bar ratio -> number of bars 
        self.REPEATS = 3
        self.PAUSE_BEFORE_AFTER = 5.0 #very beginning and end witing time
        self.COLOR_CONTRAST = 1.0
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
        self._create_parameters_from_locals(locals())
    
    def _create_parameters_from_locals(self, locals,  check_path = True):
        if len(locals['self'].DUTY_CYCLES)==1 and len(locals['self'].ORIENTATIONS)>1:
            locals['self'].DUTY_CYCLES=locals['self'].DUTY_CYCLES*len(locals['self'].ORIENTATIONS)
        experiment.ExperimentConfig._create_parameters_from_locals(self, locals)

class MovingGratingNoMarchingConfig(MovingGratingConfig):
    def _create_parameters(self):
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 4
        self.MARCH_TIME = 4.0
        self.GRATING_STAND_TIME = 4.0
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 45)
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.VELOCITIES = [1200.0]#1800
        self.DUTY_CYCLES = [3.0] #put 1.0 to a different config
        self.REPEATS = 2
        self.PAUSE_BEFORE_AFTER = 5.0
        self.COLOR_CONTRAST = 1.0
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
#        self.pre_runnable = 'BlackPre'
        self._create_parameters_from_locals(locals())
        
class MovingGratingAdrian(MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        MovingGratingNoMarchingConfig._create_parameters(self)
        self.GRATING_STAND_TIME = 0.5#after
        self.MARCH_TIME = 3.0#before
        self.PAUSE_BEFORE_AFTER = 1.0
        self.REPEATS = 3
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.ENABLE_RANDOM_ORDER = False #True
        if self.ENABLE_RANDOM_ORDER:
            import random
            random.shuffle(self.ORIENTATIONS)


