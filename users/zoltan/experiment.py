
from visexpman.users.common import grating_base

class MyMovingGratingConfig(grating_base.MovingGratingNoMarchingConfig):
    pass

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
        self.pre_runnable = 'BlackPre'
        self._create_parameters_from_locals(locals())   
