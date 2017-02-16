from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
from visexpman.users.common import grating_base
import numpy
import time
import random
import copy


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
        

