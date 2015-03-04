'''
Commonly used "standard" stimuli
'''
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class ReceptiveFieldExploreNew(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.COLORS = [1.0]
        self.BACKGROUND_COLOR = 0.0
#        self.SHAPE_SIZE = 300.0
        self.DISPLAY_SIZE = min(self.machine_config.SCREEN_SIZE_UM['row'], self.machine_config.SCREEN_SIZE_UM['col'])
        self.DISPLAY_SIZE = utils.rc((self.DISPLAY_SIZE, self.DISPLAY_SIZE))
        self.NROWS = 8
        self.NCOLUMNS = 8
        self.ON_TIME = 1.0
        self.OFF_TIME = 2.0
        self.REPEATS = 1
        self.REPEAT_SEQUENCE = 1
        self.ENABLE_RANDOM_ORDER = not False
        self.runnable='ReceptiveFieldExplore'
        self._create_parameters_from_locals(locals())
        
        
class ReceptiveFieldExploreNewInverted(ReceptiveFieldExploreNew):
    def _create_parameters(self):
        ReceptiveFieldExploreNew._create_parameters(self)
        self.COLORS = [0.0]
        self.BACKGROUND_COLOR = 1.0

class NHPMovingBar(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE_SIZE = utils.cr((1000, 500)) #um
        self.SPEEDS = [120, 200,400,1600] #um/s
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self.REPETITIONS = 5
        self.DIRECTIONS = range(0,360,45)
        self.SHAPE_BACKGROUND=0.0
        self.runnable = 'MovingShapeExperiment'        
        self._create_parameters_from_locals(locals())

class NHPSpots(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SIZES = [25, 50, 100, 200, 400, 800,1600]
        self.ON_TIME = 2
        self.OFF_TIME = 4
        self.runnable = 'IncreasingSpotExperiment'        
        self._create_parameters_from_locals(locals())
        
class NHPMarchingSquares(experiment.ExperimentConfig):
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
        
class TESTNHPMarchingSquares(NHPMarchingSquares):
    def _create_parameters(self):
        NHPMarchingSquares._create_parameters(self)
        self.SHAPE_SIZE = 500.0
        

        
if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('test', 'StimulusDevelopment', 'TestCommonExperimentConfig')
