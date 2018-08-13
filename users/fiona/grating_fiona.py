from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
from visexpman.users.common import grating_base
import numpy
import time
import random
import copy

class MovingGratingFiona(grating_base.MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        grating_base.MovingGratingNoMarchingConfig._create_parameters(self)
        self.machine_config.TEXT_COLOR=[0.0,0.0,0.0]
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 4
        self.MARCH_TIME=4.0#
        self.GRATING_STAND_TIME = 0
        self.GREY_INSTEAD_OF_MARCHING=True
        self.GREY_INSTEAD_OF_MARCHING_COLOR=0.42
        #Grating parameters
        self.ORIENTATIONS = list(range(0, 360, 45))
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.COLOR_CONTRAST = 1.0
        self.VELOCITIES = [1200.0]#1200#1800
        #self.DUTY_CYCLES = [3.0] #put 1.0 to a different config
        self.REPEATS = 5
        self.PAUSE_BEFORE_AFTER = 5.0
        self.CLEAR_SCREEN_AT_END=True
        self.CLEAR_SCREEN_AT_END_COLOR=0
        
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.DUTY_CYCLES = [3.0]*len(self.ORIENTATIONS)
        
        self.pre_runnable = 'GreyPre'
        #self.BLACK_SCREEN_DURATION=2.0

class MovingGratingOKRFiona(grating_base.MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        grating_base.MovingGratingNoMarchingConfig._create_parameters(self)
        self.machine_config.TEXT_COLOR=[0.0,0.0,0.0]
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 10
        self.MARCH_TIME=0.0#
        self.GRATING_STAND_TIME = 0
        self.GREY_INSTEAD_OF_MARCHING=True
        self.GREY_INSTEAD_OF_MARCHING_COLOR=0.42
        #Grating parameters
        self.ORIENTATIONS = list(range(0, 360, 90))
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.COLOR_CONTRAST = 1.0
        self.VELOCITIES = [800.0]#1200#1800
        #self.DUTY_CYCLES = [3.0] #put 1.0 to a different config
        self.REPEATS = 3
        self.PAUSE_BEFORE_AFTER = 5.0
        self.CLEAR_SCREEN_AT_END=True
        self.CLEAR_SCREEN_AT_END_COLOR=0
        
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.DUTY_CYCLES = [3.0]*len(self.ORIENTATIONS)
        
        self.pre_runnable = 'GreyPre'
        self.BLACK_SCREEN_DURATION=2.0
        
class MovingStandingGratingFiona(grating_base.MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        grating_base.MovingGratingNoMarchingConfig._create_parameters(self)
        self.machine_config.TEXT_COLOR=[0.0,0.0,0.0]
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 4
        self.MARCH_TIME=3.0#
        self.GRATING_STAND_TIME = 3.0
        self.GREY_INSTEAD_OF_MARCHING=False
        self.GREY_INSTEAD_OF_MARCHING_COLOR=0.42
        #Grating parameters
        self.ORIENTATIONS = list(range(0, 360, 45))
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.COLOR_CONTRAST = 1.0
        self.VELOCITIES = [1200.0]#1800
        #self.DUTY_CYCLES = [3.0] #put 1.0 to a different config
        self.REPEATS = 3
        self.PAUSE_BEFORE_AFTER = 5.0
        self.CLEAR_SCREEN_AT_END=True
        self.CLEAR_SCREEN_AT_END_COLOR=0
        self.pre_runnable = 'GreyPre'
        self.BLACK_SCREEN_DURATION=2.0
        
        
class MovingGratingFiona3x(grating_base.MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        grating_base.MovingGratingNoMarchingConfig._create_parameters(self)
        self.machine_config.TEXT_COLOR=[0.0,0.0,0.0]
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 4
        self.MARCH_TIME=5.0#
        self.GRATING_STAND_TIME = 0#3.0
        self.GREY_INSTEAD_OF_MARCHING=True#False
        self.GREY_INSTEAD_OF_MARCHING_COLOR=0.42
        #Grating parameters
        self.ORIENTATIONS = list(range(0, 360, 45))
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.COLOR_CONTRAST = 1.0
        self.VELOCITIES = [400.0,1200.0,2400.0]#1800
        #self.DUTY_CYCLES = [3.0] #put 1.0 to a different config
        self.REPEATS = 3
        self.PAUSE_BEFORE_AFTER = 5.0
        self.CLEAR_SCREEN_AT_END=True
        self.CLEAR_SCREEN_AT_END_COLOR=0
        self.pre_runnable = 'GreyPre'
        #self.BLACK_SCREEN_DURATION=0.0
        
        
class MovingGratingFionaHC(grating_base.MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        grating_base.MovingGratingNoMarchingConfig._create_parameters(self)
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 4
        self.MARCH_TIME=4.0#4
        self.GRATING_STAND_TIME = 0
        self.GREY_INSTEAD_OF_MARCHING=True
        self.GREY_INSTEAD_OF_MARCHING_COLOR=0
        #Grating parameters
        self.ORIENTATIONS = list(range(0, 360, 45))
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.COLOR_CONTRAST = 1.0
        self.VELOCITIES = [1200.0]#1800
        #self.DUTY_CYCLES = [3.0] #put 1.0 to a different config
        self.REPEATS = 2
        self.PAUSE_BEFORE_AFTER = 5.0
        self.CLEAR_SCREEN_AT_END=True
        self.CLEAR_SCREEN_AT_END_COLOR=0.15
        self.pre_runnable = 'GreyPre'
        self.BLACK_SCREEN_DURATION=2.0
