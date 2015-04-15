from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

NHP_DIRECTIONS = [0.0]

class NHPFullfieldFlashConf(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.REPEATS = 5
        self.COLORS = [0.5, 1.0, 0.5, 0.0, 0.5]
        self.TIMES = [1.0, 2.0, 2.0, 2.0, 2.0]
        self.runnable = 'NHPFullfieldFlashExp'
        self._create_parameters_from_locals(locals())
        
class NHPFullfieldFlashExp(experiment.Experiment):
    def run(self):
        for i in range(self.experiment_config.REPEATS):
            for j in range(len(self.experiment_config.TIMES)):
                self.show_fullscreen(color = self.experiment_config.COLORS[j], duration = self.experiment_config.TIMES[j])

class NHPMovingBar120(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE_SIZE = utils.cr((1000, 500)) #um
        self.SPEEDS = [int(self.__class__.__name__.replace('NHPMovingBar',  ''))] #um/s
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self.REPETITIONS = 3
        self.DIRECTIONS = NHP_DIRECTIONS
        self.SHAPE_BACKGROUND=0.0
        self.runnable = 'MovingShapeExperiment'        
        self._create_parameters_from_locals(locals())
        
class NHPMovingBar1200(NHPMovingBar120):
    pass

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
        self.REPEATS = 5
        self.REPEAT_SEQUENCE = 1
        self.ENABLE_RANDOM_ORDER = True
        self.runnable='ReceptiveFieldExplore'
        self._create_parameters_from_locals(locals())

class NHPMovingGrating120(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        try:
            self.VELOCITIY = int(self.__class__.__name__.replace('NHPMovingGrating',  ''))
        except ValueError:
            self.VELOCITIY = 0.0
        self.ORIENTATIONS = NHP_DIRECTIONS
        self.PERIOD = 600.0#um
        self.STAND_TIME = 1.0
        self.REPEATS = 5
        self.PAUSE_BEFORE_AFTER = 3.0
        self.runnable='MovingGrating'
        self._create_parameters_from_locals(locals())

class NHPMovingGrating1200(NHPMovingGrating120):
    pass
    
class NHPAdoptationStimulus(NHPMovingGrating120):
    def _create_parameters(self):
        NHPMovingGrating120._create_parameters(self)
        self.VELOCITY = 500.0
        self.ORIENTATIONS = NHP_DIRECTIONS
        self.MARCH_TIME = 0.0
        self.REPEATS = 1
        self.runnable='MovingGrating'
        self._create_parameters_from_locals(locals())

class NHPMovingGrating(experiment.Experiment):
    def prepare(self):
        if self.experiment_config.VELOCITIY == 120:
            self.sweep_duration = self.experiment_config.PERIOD * self.experiment_config.NUMBER_OF_BAR_ADVANCE_OVER_POINT/self.experiment_config.VELOCITIY
        else:
            self.sweep_duration = 8.0

    def run(self):
        self.show_fullscreen(color = 0.5, duration = self.PAUSE_BEFORE_AFTER)
        for ori in self.experiment_config.ORIENTATIONS:
            for r in range(len(self.experiment_config.REPEATS)):
                if self.experiment_config.STAND_TIME>0:
                    self.show_grating(duration = self.experiment_config.STAND_TIME,
                                        white_bar_width = 0.5 * self.experiment_config.PERIOD,
                                        orientation = ori,
                                        velocity = 0.0,
                                        is_block = False)
                self.show_grating(duration = self.sweep_duration,
                                        white_bar_width = 0.5 * self.experiment_config.PERIOD,
                                        orientation = ori,
                                        velocity = self.experiment_config.VELOCITIY,
                                        is_block = True)
