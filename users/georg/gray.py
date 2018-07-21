from visexpman.engine.vision_experiment import experiment

class GrayBackgndOnly5min(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.FULLSCREEN_TIME = 300.0
        self.FULLSCREEN_COLOR = 0.5
        self.runnable = 'GrayBackgndOnly'
        self._create_parameters_from_locals(locals())
        
class GrayBackgndOnly(experiment.Experiment):    
    def prepare(self):
        self.duration=self.experiment_config.FULLSCREEN_TIME

    def run(self):
        self.show_fullscreen(duration = self.experiment_config.FULLSCREEN_TIME, color = self.experiment_config.FULLSCREEN_COLOR)
