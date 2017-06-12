import numpy
from visexpman.users.common import grating_base

class MyMovingGratingConfig(grating_base.MovingGratingNoMarchingConfig):
    pass

class ZoltanMovingGratingConfig(grating_base.MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        grating_base.MovingGratingNoMarchingConfig._create_parameters(self)
        self.ENABLE_FLASH = False
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 6
        self.MARCH_TIME = 3
        self.GRATING_STAND_TIME = 0.5
        #Grating parameters        
        self.ORIENTATIONS = [0,45,90,135,180,225,270,315][::2]
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.PAUSE_BEFORE_AFTER = 0.0
        self.REPEATS = 1
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'BlackPre'
        self._create_parameters_from_locals(locals())   

class ZoltanMovingGratingConfig1(ZoltanMovingGratingConfig):
    def _create_parameters(self):
        ZoltanMovingGratingConfig._create_parameters(self)
        self.ORIENTATIONS = [0,45,90,135,180,225,270,315]


class PhasesGratingConfig(grating_base.MovingGratingConfig):
    def _create_parameters(self):
        grating_base.MovingGratingConfig._create_parameters(self)
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.MARCH_TIME = 4.0
        self.GRATING_STAND_TIME = 4.0
        #Grating parameters
        self.ORIENTATIONS = [0, 180]
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.DUTY_CYCLES = [3.0] #put 1.0 to a different config
        self.REPEATS = 2
        self.PAUSE_BEFORE_AFTER = 3.0
        self.PHASES={}
        for o in self.ORIENTATIONS:
            duration=5.0#sec
            f=1
            self.PHASES[o]=100*numpy.sin(f*numpy.linspace(0,1,int(duration*self.machine_config.SCREEN_EXPECTED_FRAME_RATE))*numpy.pi*2)
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
        self._create_parameters_from_locals(locals())
