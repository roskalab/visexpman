from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class FlashStimParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.REPEATS = 5
        self.ON_TIME = 2.0
        self.ON_COLOR = 1.0
        self.OFF_TIME = 4.0
        self.OFF_COLOR = 0.0
        self.PAUSE_BEFORE_AFTER = 4.0
        self.COLOR_BEFORE_AFTER=0.5
        self.runnable = 'FlashExperiment'
        self._create_parameters_from_locals(locals())

class FlashExperiment(experiment.Experiment):
    def run(self):
        self.show_fullscreen(duration = self.experiment_config.PAUSE_BEFORE_AFTER, 
                                    color = self.experiment_config.COLOR_BEFORE_AFTER, frame_trigger = False)
        for rep in range(self.experiment_config.REPEATS):
            if self.abort:
                break
            self.show_fullscreen(duration = self.experiment_config.OFF_TIME, 
                                    color = self.experiment_config.OFF_COLOR, frame_trigger = False)
            self.show_fullscreen(duration = self.experiment_config.ON_TIME, 
                                    color = self.experiment_config.ON_COLOR, frame_trigger = True)
        self.show_fullscreen(duration = self.experiment_config.PAUSE_BEFORE_AFTER, 
                                    color = self.experiment_config.COLOR_BEFORE_AFTER, frame_trigger = False)
