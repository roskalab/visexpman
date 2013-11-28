from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
from visexpman.users.daniel import grating
import random

class MyGrating(grating.MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        grating.MovingGratingNoMarchingConfig._create_parameters(self)
        self.REPEATS = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.MARCH_TIME = 1.0#Before
        self.GRATING_STAND_TIME = 0.0#Afterwards
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 45)
        random.shuffle(self.ORIENTATIONS)
        self.WHITE_BAR_WIDTHS = [300.0]
        self.VELOCITIES = [1200.0]
        self.PAUSE_BEFORE_AFTER = 0.0
        self.pre_runnable='BlackPre'
        self._create_parameters_from_locals(locals())
