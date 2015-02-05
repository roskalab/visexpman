'''
Commonly used "standard" stimuli
'''
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class MonkeyMovingBar(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE_SIZE = utils.cr((1000, 500)) #um
        self.SPEEDS = [120, 200,400,1600] #um/s
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self.REPETITIONS = 5
        self.DIRECTIONS = range(0,360,45)
        self.SHAPE_BACKGROUND=0.0
        self.runnable = 'MovingShapeExperiment'        
        self._create_parameters_from_locals(locals())

class MonkeySpots(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SIZES = [25, 50, 100, 200, 400, 800,1600]
        self.ON_TIME = 2
        self.OFF_TIME = 4
        self.runnable = 'IncreasingSpotExperiment'        
        self._create_parameters_from_locals(locals())
        
class MonkeyMarchingSquares(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.COLORS = [1.0]
        self.BACKGROUND_COLOR = 0.0
        self.SHAPE_SIZE = 200.0
        self.ON_TIME = 1.0
        self.OFF_TIME = 1.0
        self.PAUSE_BEFORE_AFTER = 2.0
        self.REPEATS = 2
        self.REPEAT_SEQUENCE = 1
        self.ENABLE_RANDOM_ORDER = False
        self.runnable='ReceptiveFieldExplore'
        self._create_parameters_from_locals(locals())
        
if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('test', 'StimulusDevelopment', 'TestCommonExperimentConfig')
