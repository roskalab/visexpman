from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class FionaMovingBar(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.BAR_WIDTH=300#8000#um
        self.BAR_LENGHT=6000#um
        self.SPEEDS=[1200]
        self.DIRECTIONS=range(0,360,45)
        import random
        random.shuffle(self.DIRECTIONS)
        self.PAUSE=3.0#Pause between directions
        self.runnable = 'MovingBarExperiment1'
        self._create_parameters_from_locals(locals())
        self.REPEATS=3
        
class MovingBarExperiment1(experiment.Experiment):
    def prepare(self):
        #Calculate duration
        trajectories, trajectory_directions, self.stimulus_duration = self.moving_shape_trajectory(\
                                    size = utils.cr((self.experiment_config.BAR_WIDTH,self.experiment_config.BAR_LENGHT)),
                                    speeds = self.experiment_config.SPEEDS,
                                    directions = self.experiment_config.DIRECTIONS,
                                    pause = self.experiment_config.PAUSE,
                                    repetition = 1,
                                    shape_starts_from_edge = True)
        self.fragment_durations = [self.stimulus_duration]

    def run(self):
        self.moving_shape(size = utils.cr((self.experiment_config.BAR_WIDTH,self.experiment_config.BAR_LENGHT)),
                                  speeds = self.experiment_config.SPEEDS,
                                  directions = self.experiment_config.DIRECTIONS,
                                  shape = 'r',
                                  color = 1.0,
                                  background_color = 0.0,
                                  pause = self.experiment_config.PAUSE,
                                  repetition = 1,
                                  shape_starts_from_edge = True)
