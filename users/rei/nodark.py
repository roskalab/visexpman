from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class NoDarkPars(experiment.ExperimentConfig):
    def _create_parameters(self):
    
        self.OFF_DIAMETER=40.0
        self.ON_DIAMETER=3250.0
        self.ON_TIME=2.0
        self.OFF_TIME=10.0
        self.runnable = 'NoDarkExperiment' 
        self._create_parameters_from_locals(locals())

class NoDarkExperiment(experiment.Experiment):
    def run(self):
        self.show_shape(shape='o',size=self.experiment_config.OFF_DIAMETER,duration=self.experiment_config.OFF_TIME)
        self.show_shape(shape='o',size=self.experiment_config.ON_DIAMETER,duration=self.experiment_config.ON_TIME)
        self.show_shape(shape='o',size=self.experiment_config.OFF_DIAMETER,duration=self.experiment_config.OFF_TIME)
        
if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    context = stimulation_tester('rei', 'StimulusDevelopment', 'NoDarkPars', ENABLE_FRAME_CAPTURE = False)
