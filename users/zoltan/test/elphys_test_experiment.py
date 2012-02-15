from visexpman.engine.vision_experiment import experiment

class ElphysPlatformExpConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'ElphysPlatformExperiment'
        self._create_parameters_from_locals(locals())

class ElphysPlatformExperiment(experiment.Experiment):
    def prepare(self):
        self.number_of_fragments = 1
        self.fragment_durations = [3.0] * self.number_of_fragments

    def run(self, fragment_id = 0):
        self.show_fullscreen(duration = self.fragment_durations[fragment_id], color = 1.0)
