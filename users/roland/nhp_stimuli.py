from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

NHP_DIRECTIONS = [135, 90, 315, 0, 180, 45, 225, 270,
                90,   180,   270,   135,    45,   315,     0,   225,
               315,     0,    90,   270,    45,   135,   180,   225,
               270,    90,     0,   315,   180,   135,    45,   225,
                90,   270,     0,   315,   135,   180,   225,    45]

class NHP1MovingGrating120(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        try:
            self.VELOCITY = int(self.__class__.__name__.split('MovingGrating')[1])
        except (ValueError, IndexError) as e:
            self.VELOCITY = 0.0
        self.ORIENTATIONS = NHP_DIRECTIONS
        self.PERIOD = 600.0#um
        self.STAND_TIME = 1.0
        self.REPEATS = 1
        self.PAUSE_BEFORE_AFTER = 3.0
        self.runnable='NHPMovingGrating'
        self._create_parameters_from_locals(locals())

class NHP0AdoptationStimulus(NHP1MovingGrating120):
    def _create_parameters(self):
        NHP1MovingGrating120._create_parameters(self)
        self.VELOCITY = 500.0
        self.ORIENTATIONS = NHP_DIRECTIONS[:8]
        self.STAND_TIME = 1.0
        self.PAUSE_BEFORE_AFTER = 0.0
        self.REPEATS = 1
        self.runnable='NHPMovingGrating'
        self._create_parameters_from_locals(locals())
        
class NHP2MovingGrating1200(NHP1MovingGrating120):
    pass


class NHP3FullfieldFlashConf(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.REPEATS = 5
        self.COLORS = [0.5, 1.0, 0.5, 0.0, 0.5]
        self.TIMES = [1.0, 2.0, 2.0, 2.0, 2.0]
        self.runnable = 'NHPFullfieldFlashExp'
        self._create_parameters_from_locals(locals())
        
class NHP4MovingBar120(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE_SIZE = utils.cr((1000, 500)) #um
        self.SPEEDS = [int(self.__class__.__name__.split('MovingBar')[1])] #um/s
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self.REPETITIONS = 1
        self.DIRECTIONS = NHP_DIRECTIONS
        self.SHAPE_BACKGROUND=0.0
        self.runnable = 'MovingShapeExperiment'        
        self._create_parameters_from_locals(locals())
        
class NHP5MovingBar1200(NHP4MovingBar120):
    pass

class NHP6MarchingSquares(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.COLORS = [1.0]
        self.BACKGROUND_COLOR = 0.5
        self.SHAPE_SIZE = 200.0
        self.ON_TIME = 1.0
        self.OFF_TIME = 1.0
        self.PAUSE_BEFORE_AFTER = 2.0
        self.REPEATS = 5
        self.REPEAT_SEQUENCE = 1
        self.ENABLE_RANDOM_ORDER = False
        self.runnable='ReceptiveFieldExplore'
        self._create_parameters_from_locals(locals())


class NHPSpots(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SIZES = [25, 50, 100, 200, 400, 800,1600]
        self.ON_TIME = 2
        self.OFF_TIME = 4
        self.runnable = 'IncreasingSpotExperiment'        
        self._create_parameters_from_locals(locals())
                    
class NHPFullfieldFlashExp(experiment.Experiment):
    def run(self):
        for i in range(self.experiment_config.REPEATS):
            for j in range(len(self.experiment_config.TIMES)):
                self.show_fullscreen(color = self.experiment_config.COLORS[j], duration = self.experiment_config.TIMES[j])


class NHPMovingGrating(experiment.Experiment):
    def prepare(self):
        if self.experiment_config.VELOCITY == 1200:
            self.sweep_duration = 8.0
        else:
            self.sweep_duration = self.experiment_config.PERIOD * self.experiment_config.NUMBER_OF_BAR_ADVANCE_OVER_POINT/self.experiment_config.VELOCITY

    def run(self):
        if self.experiment_config.PAUSE_BEFORE_AFTER>0:
            self.show_fullscreen(color = 0.5, duration = self.experiment_config.PAUSE_BEFORE_AFTER)
        for ori in self.experiment_config.ORIENTATIONS:
            for r in range(self.experiment_config.REPEATS):
                if self.experiment_config.STAND_TIME>0:
                    self.show_grating(duration = self.experiment_config.STAND_TIME,
                                        white_bar_width = 0.5 * self.experiment_config.PERIOD,
                                        orientation = ori,
                                        velocity = 0.0,
                                        is_block = False)
                self.show_grating(duration = self.sweep_duration,
                                        white_bar_width = 0.5 * self.experiment_config.PERIOD,
                                        orientation = ori,
                                        velocity = self.experiment_config.VELOCITY,
                                        is_block = True)
        if self.experiment_config.PAUSE_BEFORE_AFTER>0:
            self.show_fullscreen(color = 0.5, duration = self.experiment_config.PAUSE_BEFORE_AFTER)
if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('test', 'StimulusDevelopment', 'NHP2MovingGrating120')
