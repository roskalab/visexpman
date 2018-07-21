from visexpman.engine.vision_experiment import experiment

class GratingParams(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPEED=800
        self.DURATION=10
        self.WHITE_BAR_WIDTH=300
        self.runnable = 'GratingExperiment'
        self._create_parameters_from_locals(locals())
        
class GratingExperiment(experiment.Experiment):
    def prepare(self):
        self.fragment_durations=[self.experiment_config.DURATION]
        
    def run(self):
       self.show_grating(duration=self.experiment_config.DURATION,
           velocity=self.experiment_config.SPEED,
           white_bar_width=self.experiment_config.WHITE_BAR_WIDTH)

