from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
from visexpman.users.common import grating_base
import numpy
import time
import random
import copy


class MovingGratingQuickMarchConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 4 #number of static bar compositions at beginning
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3 #how many times the bar hit a point -> this + speed = moving time
        self.MARCH_TIME = 2 # standing phase time
        self.GRATING_STAND_TIME = 2.0 #post-moving-phase time
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 45)
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.WHITE_BAR_WIDTHS = [300.0]
        self.VELOCITIES = [1200.0]
        self.DUTY_CYCLES = [3.] #white and blck bar ratio -> number of bars
        self.REPEATS = 2
        self.PAUSE_BEFORE_AFTER = 1.0 #very beginning and end witing time
        self.COLOR_CONTRAST = 1.0
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
        self._create_parameters_from_locals(locals())

class PhasesGratingConfig(grating_base.MovingGratingConfig):
    def _create_parameters(self):
        grating_base.MovingGratingConfig._create_parameters(self)
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.MARCH_TIME = 4.0
        self.GRATING_STAND_TIME = 4.0
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 45)
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.DUTY_CYCLES = [6.0] #put 1.0 to a different config
        self.REPEATS = 2
        self.PAUSE_BEFORE_AFTER = 2.0
        self.PHASES={}
        for o in self.ORIENTATIONS:
            duration=5.0#sec
            f=5
            self.PHASES[o]=1500*numpy.sin(f*numpy.linspace(0,1,int(duration*self.machine_config.SCREEN_EXPECTED_FRAME_RATE))*numpy.pi*2)
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
        self._create_parameters_from_locals(locals())
        
class MovingGratingExpAccConfig(grating_base.MovingGratingConfig):
    def _create_parameters(self):
        grating_base.MovingGratingConfig._create_parameters(self)
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3 #how many times the bar hit a point -> this + speed = moving time
        self.MARCH_TIME = 0
        self.GRATING_STAND_TIME = 0
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 45)
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.DUTY_CYCLES = [6.0] #put 1.0 to a different config
        self.REPEATS = 2
        self.PAUSE_BEFORE_AFTER = 3.0
        self.PHASES={}
        self.STARTING_PHASES = []
        for oi, o in enumerate(self.ORIENTATIONS):
            duration=5.0#sec
            f=[0.1,1,4]
            es = [50,9,2.4]
            for n in range(self.NUMBER_OF_BAR_ADVANCE_OVER_POINT):
                interval = 4*(self.WHITE_BAR_WIDTHS[0]*self.DUTY_CYCLES[0]) * \
                    1./(1.+numpy.exp(-f[n]*numpy.linspace(-es,es,int(duration*self.machine_config.SCREEN_EXPECTED_FRAME_RATE))))
                if o not in self.PHASES:
                    self.STARTING_PHASES.append(interval[0])
                self.PHASES[o] = numpy.concatenate([self.PHASES[o], self.PHASES[o][-1] + interval]) if o in self.PHASES else interval
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
        self._create_parameters_from_locals(locals())
        
class MovingGratingStartStopConfig(grating_base.MovingGratingConfig):
    def _create_parameters(self):
        grating_base.MovingGratingConfig._create_parameters(self)
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 2 #how many times the bar hit a point -> this + speed = moving time
        self.MARCH_TIME = 2.
        self.GRATING_STAND_TIME = 0.
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 45)
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.DUTY_CYCLES = [6.0] #put 1.0 to a different config
        self.REPEATS = 2
        self.PAUSE_BEFORE_AFTER = 2.0
        self.PHASES={}
        self.STARTING_PHASES = []
        for oi, o in enumerate(self.ORIENTATIONS):
            duration=[1.5,6.]#sec
            p1 = 2.
            for d1 in duration:
                for n in range(self.NUMBER_OF_BAR_ADVANCE_OVER_POINT):
                    interval = 0.5*(self.WHITE_BAR_WIDTHS[0]*self.DUTY_CYCLES[0]) * \
                        (-numpy.cos(numpy.linspace(0, numpy.pi, int(d1*self.machine_config.SCREEN_EXPECTED_FRAME_RATE)))+1)
                    pause = numpy.ones((int(p1*self.machine_config.SCREEN_EXPECTED_FRAME_RATE),)) * interval[-1]
                    ip = numpy.concatenate([interval, pause])
                    if o not in self.PHASES:
                        self.STARTING_PHASES.append(ip[0])
                    self.PHASES[o] = numpy.concatenate([self.PHASES[o], self.PHASES[o][-1] + ip]) if o in self.PHASES else ip
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
        self._create_parameters_from_locals(locals())
        
        
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
        
class MovingGratingQuickSpeedTuningConfig(MovingGratingNoMarchHor35812umsConfig):
    def _create_parameters(self):
        MovingGratingNoMarchHor35812umsConfig._create_parameters(self)
        self.VELOCITIES = [1200, 300, 1200, 300]
        self.REPEATS = 1
        self.ORIENTATIONS = range(0,360,45)
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.DUTY_CYCLES = [3.0]*len(self.ORIENTATIONS)
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 1
        
        
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

class MovingGrating3xCardinalConfig(grating_base.MovingGratingConfig):
    def _create_parameters(self):
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.MARCH_TIME = 4.0
        self.GRATING_STAND_TIME = 3.5
        #Grating parameters
        self.ORIENTATIONS = [0, 90, 180, 270]
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

class MovingGrating3xCardinal180Config(grating_base.MovingGratingConfig):
    def _create_parameters(self):
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.MARCH_TIME = 4.0
        self.GRATING_STAND_TIME = 3.5
        #Grating parameters
        self.ORIENTATIONS = [180, 90, 0, 270]
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
