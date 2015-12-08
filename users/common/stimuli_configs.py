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
        self.NROWS = 7
        self.NCOLUMNS = 13
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

class ReceptiveFieldExploreNewAngle(ReceptiveFieldExploreNew):
    def _create_parameters(self):
        ReceptiveFieldExploreNew._create_parameters(self)
        self.COLORS = [0.0]
        self.BACKGROUND_COLOR = 1.0        
        self.DISPLAY_SIZE = utils.rc((53,90))
        self.NROWS = 5
        self.NCOLUMNS = 9
        self.DISPLAY_CENTER = utils.rc((0.5-0.1923,0.0))#0,0 is the screen center
        self.SIZE_DIMENSION='angle'
        
if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('test', 'StimulusDevelopment', 'TestCommonExperimentConfig')
