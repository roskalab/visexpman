from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class MovingBarParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE_SIZE = utils.rc((300, 900)) #um
        self.SPEEDS = [1200] #um/s
        self.AXIS_ANGLE = 0.0
        self.SHAPE_CONTRAST = 1.0
        self.SHAPE_BACKGROUND = 0.0
        self.PAUSE_BETWEEN_DIRECTIONS = 0.0
        self.REPETITIONS = 1
        if self.AXIS_ANGLE >= 180.0:
            null_dir = self.AXIS_ANGLE-180.0
        else:
            null_dir = self.AXIS_ANGLE+180.0
#        self.DIRECTIONS = [self.AXIS_ANGLE, null_dir]
        self.DIRECTIONS = range(0,360,45)
        self.SHAPE = 'rect'
        self.runnable = 'MovingShapeExperiment'        
        self._create_parameters_from_locals(locals())
