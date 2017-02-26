from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
from visexpman.users.daniel import grating_base
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
        
        
class CurtainConfigKamill(experiment.ExperimentConfig):
    def _create_parameters(self):
        #Timing        
        self.NUMBER_OF_MARCHING_PHASES = 1 #number of static bar compositions at beginning
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 1 #how many times the bar hit a point -> this + speed = moving time
        self.MARCH_TIME = 2.0 # standing phase time
        self.GRATING_STAND_TIME = 5.0 #post-moving-phase time
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 45)
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.WHITE_BAR_WIDTHS = [1000.0]
        self.VELOCITIES = [300.0]
        self.DUTY_CYCLES = [2]*len(self.ORIENTATIONS) #white and blck bar ratio -> number of bars 
        self.REPEATS = 2
        self.PAUSE_BEFORE_AFTER = 5.0 #very beginning and end waiting time
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
        self._create_parameters_from_locals(locals())
        
        
if 0:
    class MovingGratingConfigFindOrientation(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.REPEATS = 5
            self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 2
            self.TUNING_SPEEDS = [800.0, 400.0,100.0]
            self.TUNING_WHITE_BAR_WIDTHS = [150.0, 300.0, 600.0, 1000.0]
            self.TUNING_ORIENTATION = 90.0
            self.MARCH_TIME = 1.0
            self.GREY_INSTEAD_OF_MARCHING=True
            self.GREY_INSTEAD_OF_MARCHING_COLOR=0
            
            self.NUMBER_OF_MARCHING_PHASES = 0
            self.GRATING_STAND_TIME = 0
            self.ORIENTATIONS = range(0, 360, 45)
            self.WHITE_BAR_WIDTHS = [300.0]
            self.VELOCITIES = [800.0]
            self.DUTY_CYCLES = [self.machine_config.SCREEN_SIZE_UM['col']*1.414/self.WHITE_BAR_WIDTHS] 
            self.PAUSE_BEFORE_AFTER = 0.0
            self.runnable = 'MovingGrating'
            self.pre_runnable = 'MovingGratingPre'
            self._create_parameters_from_locals(locals())
            
    class MovingGratingTuning(MovingGratingConfigFindOrientation):
        def _create_parameters(self):
            MovingGratingConfigFindOrientation._create_parameters(self)
            self.VELOCITIES = self.TUNING_SPEEDS
            self.WHITE_BAR_WIDTHS = self.TUNING_WHITE_BAR_WIDTHS
            self.ORIENTATIONS = [self.TUNING_ORIENTATION]
            self.DUTY_CYCLES = [1.0]
            self.REPEATS = 3
            self._create_parameters_from_locals(locals())

class MovingGratingNoMHor300umsConfig(grating_base.MovingGratingConfig):
    def _create_parameters(self):
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 4
        self.MARCH_TIME = 4.0
        self.GRATING_STAND_TIME = 4.0
        #Grating parameters
        self.ORIENTATIONS = [0, 180]
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.VELOCITIES = [300.0]#1800
        self.DUTY_CYCLES = [3.0] #put 1.0 to a different config
        self.REPEATS = 2
        self.PAUSE_BEFORE_AFTER = 3.0
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
#        self.pre_runnable = 'BlackPre'
        self._create_parameters_from_locals(locals())
        
class MovingGratingNoMarchHor3or5or800umsConfig(MovingGratingNoMHor300umsConfig):
    def _create_parameters(self):
        MovingGratingNoMHor300umsConfig._create_parameters(self)
        self.VELOCITIES = [300., 500., 800.0]
             
class MovingGratingNoMarchHor35812umsConfig(MovingGratingNoMHor300umsConfig):
    def _create_parameters(self):
        MovingGratingNoMHor300umsConfig._create_parameters(self)
        self.VELOCITIES = [300., 500., 800.0, 1200.]
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.COLOR_CONTRAST = 1.0
        
class MovingGratingNoMarchHor35812umsConfig(MovingGratingNoMHor300umsConfig):
    def _create_parameters(self):
        MovingGratingNoMHor300umsConfig._create_parameters(self)
        self.VELOCITIES = [300., 500., 800.0, 1200.]
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.COLOR_CONTRAST = 1.0
        self.REPEATS = 1

class MovingGratingNoMarch05Hor35812umsConfig(MovingGratingNoMHor300umsConfig):
    def _create_parameters(self):
        MovingGratingNoMHor300umsConfig._create_parameters(self)
        self.VELOCITIES = [300., 500., 800.0, 1200.]
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.COLOR_CONTRAST = 0.5


class MovingGratingNoMHor500umsConfig(MovingGratingNoMHor300umsConfig):
    def _create_parameters(self):
        MovingGratingNoMHor300umsConfig._create_parameters(self)
        self.VELOCITIES = [500.0]

class MovingGratingLongSpeedTuningConfig(MovingGratingNoMarchHor35812umsConfig):
    def _create_parameters(self):
        MovingGratingNoMarchHor35812umsConfig._create_parameters(self)
        self.VELOCITIES = [1200, 1200, 300, 300, 800, 800, 500, 500]
        self.REPEATS = 1
        self.ORIENTATIONS = range(0,360,45)
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.DUTY_CYCLES = [3.0]*len(self.ORIENTATIONS)
        
        
class MovingGratingLongSpeedTuning180Config(MovingGratingNoMarchHor35812umsConfig):
    def _create_parameters(self):
        MovingGratingNoMarchHor35812umsConfig._create_parameters(self)
        self.VELOCITIES = [1200, 1200, 300, 300, 800, 800, 500, 500]
        self.REPEATS = 1
        self.ORIENTATIONS = [180, 225, 270, 315, 0, 45, 90, 135]
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.DUTY_CYCLES = [3.0]*len(self.ORIENTATIONS)

       
class MovingGratingNoMarching6xConfig(grating_base.MovingGratingConfig):
    def _create_parameters(self):
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.MARCH_TIME = 4.0
        self.GRATING_STAND_TIME = 3.5
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 45)
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.COLOR_CONTRAST = 1.0
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.VELOCITIES = [1200.0]#1800
        self.DUTY_CYCLES = [3.0] #put 1.0 to a different config
        self.REPEATS = 6
        self.PAUSE_BEFORE_AFTER = 3.0
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
#        self.pre_runnable = 'BlackPre'
        self._create_parameters_from_locals(locals())

class MovingGratingNoMarch3x180Config(grating_base.MovingGratingConfig):
    def _create_parameters(self):
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.MARCH_TIME = 4.0
        self.GRATING_STAND_TIME = 3.5
        #Grating parameters
        self.ORIENTATIONS = [180, 225, 270, 315, 0, 45, 90, 135]
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.COLOR_CONTRAST = 1.0
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.VELOCITIES = [1200.0]#1800
        self.DUTY_CYCLES = [3.0] #put 1.0 to a different config
        self.REPEATS = 3
        self.PAUSE_BEFORE_AFTER = 3.0
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
#        self.pre_runnable = 'BlackPre'
        self._create_parameters_from_locals(locals())

class MovingGratingNoMarch3xConfig(grating_base.MovingGratingConfig):
    def _create_parameters(self):
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.MARCH_TIME = 4.0
        self.GRATING_STAND_TIME = 3.5
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 45)
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.COLOR_CONTRAST = 1.0
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.VELOCITIES = [1200.0]#1800
        self.DUTY_CYCLES = [3.0] #put 1.0 to a different config
        self.REPEATS = 3
        self.PAUSE_BEFORE_AFTER = 3.0
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
#        self.pre_runnable = 'BlackPre'
        self._create_parameters_from_locals(locals())
        
class MovingGratingNoMarch180Config(grating_base.MovingGratingConfig):
    def _create_parameters(self):
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.MARCH_TIME = 4.0
        self.GRATING_STAND_TIME = 3.5
        #Grating parameters
        self.ORIENTATIONS = [180, 225, 270, 315, 0, 45, 90, 135]
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.COLOR_CONTRAST = 1.0
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.VELOCITIES = [1200.0]#1800
        self.DUTY_CYCLES = [3.0] #put 1.0 to a different config
        self.REPEATS = 2
        self.PAUSE_BEFORE_AFTER = 3.0
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
#        self.pre_runnable = 'BlackPre'
        self._create_parameters_from_locals(locals())
        
class MovingGrating50pConfig(grating_base.MovingGratingConfig):
    def _create_parameters(self):
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 5
        self.MARCH_TIME = 4.0
        self.GRATING_STAND_TIME = 4.0
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 45)
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.VELOCITIES = [800.0]#1800
        self.DUTY_CYCLES = [1.0] #put 1.0 to a different config
        self.REPEATS = 2
        self.PAUSE_BEFORE_AFTER = 5.0
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
#        self.pre_runnable = 'BlackPre'
        self._create_parameters_from_locals(locals())

class MovingGratingAdrian(grating_base.MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        grating_base.MovingGratingNoMarchingConfig._create_parameters(self)
        self.GRATING_STAND_TIME = 0.5#after
        self.MARCH_TIME = 3.0#before
        self.PAUSE_BEFORE_AFTER = 1.0
        self.REPEATS = 3
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.ENABLE_RANDOM_ORDER = False #True
        if self.ENABLE_RANDOM_ORDER:
            import random
            random.shuffle(self.ORIENTATIONS)
            
class MovingGratingAdrianSpeed(grating_base.MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        grating_base.MovingGratingNoMarchingConfig._create_parameters(self)
        self.GRATING_STAND_TIME = 0.5#after
        self.MARCH_TIME = 3.0#before
        self.PAUSE_BEFORE_AFTER = 1.0
        self.REPEATS = 3
        self.VELOCITIES = [400.0, 1200.0, 2000.0]#1800
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.ENABLE_RANDOM_ORDER = False #True
        
class MovingGratingTest(grating_base.MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        grating_base.MovingGratingNoMarchingConfig._create_parameters(self)
        self.GRATING_STAND_TIME = 0.0#after
        self.MARCH_TIME = 0.0#before
        self.PAUSE_BEFORE_AFTER = 1.0
        self.REPEATS = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 100
        self.ENABLE_RANDOM_ORDER = False #True
        self.WHITE_BAR_WIDTHS=[50, 100]
        self.ORIENTATIONS = range(0, 90, 90)
        self.VELOCITIES = [200, 2000.0, 2800]#1800
        self.DUTY_CYCLES = [2.0]
        if self.ENABLE_RANDOM_ORDER:
            import random
            random.shuffle(self.ORIENTATIONS)

        
class MovingGratingNoMarchingBlackPreConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 4
        self.MARCH_TIME = 4.0
        self.GRATING_STAND_TIME = 4.0
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 45)
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.VELOCITIES = [1200.0]#1800
        self.DUTY_CYCLES = [3.0] #put 1.0 to a different config
        self.REPEATS = 2
        self.PAUSE_BEFORE_AFTER = 5.0
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'BlackPre'
        self._create_parameters_from_locals(locals())
if 1:       
    class MovingGratingWithFlashConfig(grating_base.MovingGratingNoMarchingConfig):
        def _create_parameters(self):
            grating_base.MovingGratingNoMarchingConfig._create_parameters(self)
            #Flash config
            self.ENABLE_FLASH = True
            self.FLASH_DURATION = 5.0
            self.TIMING = [2.0, self.FLASH_DURATION, 7.0, self.FLASH_DURATION, 7.0]
            self.FLASH_REPEATS = 1
            self.BLACK = 0.0
            self.WHITE = 1.0
            self.PAUSE_BEFORE_AFTER = 12.0
if 0:            
    class MovingGratingSineConfig(grating_base.MovingGratingNoMarchingConfig):
        def _create_parameters(self):
            grating_base.MovingGratingNoMarchingConfig._create_parameters(self)
            self.PROFILE = 'sin'
            self.DUTY_CYCLES = [1.0] #put 1.0 to a different config
            self.runnable = 'MovingGrating'
            self.pre_runnable = 'MovingGratingPre'
    #         self._create_parameters_from_locals(locals())
        
if 0:
    class MovingGratingNoMarchingNoStandingConfig(experiment.ExperimentConfig):
        def _create_parameters(self):
            #Timing
            self.NUMBER_OF_MARCHING_PHASES = 1
            self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 4
            self.MARCH_TIME = 0.0
            self.GRATING_STAND_TIME = 0.0
            #Grating parameters
            self.ORIENTATIONS = range(0, 360, 90)
            self.WHITE_BAR_WIDTHS = [300.0]#300
            self.VELOCITIES = [1000.0]#1800
            self.DUTY_CYCLES = [3.0] #put 1.0 to a different config
            self.REPEATS = 1
            self.PAUSE_BEFORE_AFTER = 0.0
            
            self.runnable = 'MovingGrating'
            self.pre_runnable = 'MovingGratingPre'
            self._create_parameters_from_locals(locals())
if 1:
    class ZoltanMovingGratingConfig(grating_base.MovingGratingNoMarchingConfig):
        def _create_parameters(self):
            grating_base.MovingGratingNoMarchingConfig._create_parameters(self)
            self.ENABLE_FLASH = False
            #Timing
            self.NUMBER_OF_MARCHING_PHASES = 1
            self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 1
            self.MARCH_TIME = 0.5
            self.GRATING_STAND_TIME = 0.5
            #Grating parameters        
            self.ORIENTATIONS = [0,45,90,135,180,225,270,315][::2]
            self.WHITE_BAR_WIDTHS = [300.0]#300
            self.PAUSE_BEFORE_AFTER = 0.0
            self.REPEATS = 1
            self.runnable = 'MovingGrating'
            self.pre_runnable = 'MovingGratingPre'
            self._create_parameters_from_locals(locals())        
        
class MovingGratingSpeed100ums(grating_base.MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        grating_base.MovingGratingNoMarchingConfig._create_parameters(self)
        self.VELOCITIES = [100.0]
        self.WHITE_BAR_WIDTHS = [200.0]
        self.DUTY_CYCLES = [1.0]
        self.REPEATS = 1
                
class MovingGratingSpeed300ums(grating_base.MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        grating_base.MovingGratingNoMarchingConfig._create_parameters(self)
        self.VELOCITIES = [300.0]
        self.WHITE_BAR_WIDTHS = [300.0]
        ddiag = self.machine_config.SCREEN_SIZE_UM['col']*1.414/self.WHITE_BAR_WIDTHS
        dhoriz = self.machine_config.SCREEN_SIZE_UM['col']*1.03/self.WHITE_BAR_WIDTHS
        dvert  = self.machine_config.SCREEN_SIZE_UM['row']*1.03/self.WHITE_BAR_WIDTHS
        self.DUTY_CYCLES = [dhoriz, ddiag, dvert, ddiag, dhoriz, ddiag, dvert, ddiag]
        self.STARTING_PHASES = [360/d1 for d1 in self.DUTY_CYCLES]
        self.REPEATS = 2
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 1
        self.PAUSE_BEFORE_AFTER = 0.0 #very beginning and end waiting time
        self.GRATING_STAND_TIME = 0.0 #post-moving-phase time
        
class MovingGratingSpeed800ums(grating_base.MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        grating_base.MovingGratingNoMarchingConfig._create_parameters(self)
        self.VELOCITIES = [800.0]
        self.WHITE_BAR_WIDTHS = [200.0]
        self.DUTY_CYCLES = [1.0]
        self.REPEATS = 2
        
class MovingGratingSpeed1200ums(grating_base.MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        grating_base.MovingGratingNoMarchingConfig._create_parameters(self)
        self.VELOCITIES = [1200.0]
        self.WHITE_BAR_WIDTHS = [200.0]
        self.DUTY_CYCLES = [1.0]
        self.REPEATS = 2
