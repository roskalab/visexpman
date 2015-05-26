from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
enable_all=False

class MovingBar(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE_SIZE = utils.cr((1000, 500)) #um
        self.SPEEDS = [1600] #um/s#
        #self.SPEEDS = [120, 200,400,1600] #um/s
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self.REPETITIONS = 10
        self.DIRECTIONS = range(0,360,45)
        self.SHAPE_BACKGROUND=0.0
        self.runnable = 'MovingShapeExperiment'
        self._create_parameters_from_locals(locals())

