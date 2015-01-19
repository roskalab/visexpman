from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class MonkeyMovingBar(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE_SIZE = utils.cr((500, 5000)) #um
        self.SPEEDS = [100, 200,400,1000] #um/s
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self.REPETITIONS = 1
        self.DIRECTIONS = range(0,360,45)
        self.SHAPE_BACKGROUND=0.0
        self.runnable = 'MovingShapeExperiment'        
        self._create_parameters_from_locals(locals())

class MonkeySpots(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SIZES = [25, 50, 100, 200, 400, 800,1600]#5*[800]
        self.ON_TIME = 2
        self.OFF_TIME = 4
        self.runnable = 'IncreasingSpotExperiment'        
        self._create_parameters_from_locals(locals())
