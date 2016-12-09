from visexpman.engine.vision_experiment import experiment
from visexpman.users.common.grating import MovingGratingNoMarchingConfig
from visexpman.engine.generic import utils
import numpy
import time
import random
import copy
        
class MovingGratingAdrian(MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        MovingGratingNoMarchingConfig._create_parameters(self)
        self.GRATING_STAND_TIME = 0.5#after
        self.MARCH_TIME = 3.0#before
        self.PAUSE_BEFORE_AFTER = 1.0
        self.REPEATS = 3
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.ENABLE_RANDOM_ORDER = False #True
        self.WHITE_BAR_WIDTHS=[150]
        if self.ENABLE_RANDOM_ORDER:
            import random
            random.shuffle(self.ORIENTATIONS)

class MovingGratingShort(MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        MovingGratingNoMarchingConfig._create_parameters(self)
        self.GRATING_STAND_TIME = 0.5#after
        self.MARCH_TIME = 3.0#before
        self.PAUSE_BEFORE_AFTER = 1.0
        self.REPEATS = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.ENABLE_RANDOM_ORDER = False #True

class MovingGratingArjun(MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        MovingGratingNoMarchingConfig._create_parameters(self)
        self.WHITE_BAR_WIDTHS=[150] #300 um is 10 cm? too big???
        self.VELOCITIES = [400.0, 1200.0, 2000.0]

class MovingGratingFast(MovingGratingArjun):
    def _create_parameters(self):
        MovingGratingArjun._create_parameters(self)
        self.VELOCITIES = [2000.0]
        
class MovingGratingMid(MovingGratingArjun):
    def _create_parameters(self):
        MovingGratingArjun._create_parameters(self)
        self.VELOCITIES = [1200.0]

class MovingGratingSlow(MovingGratingArjun):
    def _create_parameters(self):
        MovingGratingArjun._create_parameters(self)
        self.VELOCITIES = [400.0]



class MovingGratingTest(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'MovingTest'
        self._create_parameters_from_locals(locals())
        
class MovingTest(experiment.Experiment):
    def prepare(self):
        self.duration = 10.0
        
    def run(self):
        self.show_grating(duration = 10.0, 
                                orientation = 0, 
                                velocity = 100, white_bar_width = 300,
                                )
