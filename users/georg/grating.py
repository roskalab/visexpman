from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
from visexpman.users.common import grating_base
import numpy
import time
import random
import copy


        
class CurtainConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        #Timing        
        self.NUMBER_OF_MARCHING_PHASES = 1 #number of static bar compositions at beginning
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 1 #how many times the bar hit a point -> this + speed = moving time
        self.MARCH_TIME = 0.0 # standing phase time
        self.GRATING_STAND_TIME = 0.0 #post-moving-phase time
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 45)
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.WHITE_BAR_WIDTHS = [3000.0]
        self.VELOCITIES = [300.0]
        self.DUTY_CYCLES = [2]*len(self.ORIENTATIONS) #white and blck bar ratio -> number of bars 
        self.REPEATS = 2
        self.PAUSE_BEFORE_AFTER = 5.0 #very beginning and end waiting time
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
        self._create_parameters_from_locals(locals())
        
class MovingGratingGeorg(grating_base.MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        grating_base.MovingGratingNoMarchingConfig._create_parameters(self)
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.VELOCITIES = [300.0]#1800
        self.DUTY_CYCLES = [3.0] #TODO: calculate from screen diagonal
        self.REPEATS = 1
        self.PAUSE_BEFORE_AFTER = 3.0
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
        self._create_parameters_from_locals(locals())
        
