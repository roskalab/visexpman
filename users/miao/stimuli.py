from visexpman.users.common import grating
from visexpman.engine.vision_experiment import experiment

class MovingGrating(grating.MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        grating.MovingGratingNoMarchingConfig._create_parameters(self)
        self.REPEATS = 1
        self.PAUSE_BEFORE_AFTER=0.0
        self.VELOCITIES = [1200.0]#um/s
        
class ReceptiveField(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.COLORS = [1.0]
        self.BACKGROUND_COLOR = 0
        self.NROWS = 9
        self.NCOLUMNS = 16
        self.ON_TIME = 0.5
        self.OFF_TIME = 2.0
        self.REPEATS = 1
        self.REPEAT_SEQUENCE=1
        self.ENABLE_RANDOM_ORDER=False
        self.runnable='ReceptiveFieldExplore'
        self._create_parameters_from_locals(locals())
