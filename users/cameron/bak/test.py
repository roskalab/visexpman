from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class MonkeyMovingBar(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE_SIZE = utils.cr((300, 1500)) #um
        self.SPEEDS = [800] #um/s
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self.REPETITIONS = 5
        self.DIRECTIONS = range(0,360,45)
        self.SHAPE_BACKGROUND = 0.0
        self.runnable = 'MovingShapeExperiment'        
        self._create_parameters_from_locals(locals())
        
class MovingShapeExperiment(experiment.Experiment):
    def prepare(self):
        parameter_default_values = {
        'REPETITIONS': 1, 
        'SHAPE': 'rect', 
        'SHAPE_CONTRAST' : 1.0, 
        'SHAPE_BACKGROUND': 0.5, 
        'PAUSE_BETWEEN_DIRECTIONS' : 0.0, 
        }
        self.set_default_experiment_parameter_values(parameter_default_values)
        #Calculate duration
        trajectories, trajectory_directions, self.stimulus_duration = self.moving_shape_trajectory(\
                                    size = self.experiment_config.SHAPE_SIZE,
                                    speeds = self.experiment_config.SPEEDS,
                                    directions = self.experiment_config.DIRECTIONS,
                                    pause = self.pause_between_directions)
        self.stimulus_duration *= self.repetitions
        if hasattr(self, 'log') and hasattr(self.log, 'info'):
            self.log.info('Stimulus duration: {0}'.format(self.stimulus_duration))

    def run(self):
         for repetition in range(self.repetitions):
            self.moving_shape(size = self.experiment_config.SHAPE_SIZE,
                                  speeds = self.experiment_config.SPEEDS,
                                  directions = self.experiment_config.DIRECTIONS,
                                  shape = self.shape,
                                  color = self.shape_contrast,
                                  background_color = self.shape_background,
                                  pause = self.pause_between_directions,
                                  shape_starts_from_edge = True)
