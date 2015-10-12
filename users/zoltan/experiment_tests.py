from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class NaturalBarsConfig1(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPEED = [800, 400,1500.0]#um/s
        self.SPEED = [400]
        self.REPEATS = 2 #5
        self.DIRECTIONS = [0] #range(0,360,90)
        self.DURATION = 5
        self.BACKGROUND_TIME = 0
        self.BACKGROUND_COLOR = 0.5
        self.ALWAYS_FLY_IN_OUT = not False
        self.runnable = 'NaturalBarsExperiment1'
        self._create_parameters_from_locals(locals())

class NaturalBarsExperiment1(experiment.Experiment):
    def prepare(self):
        self.stimulus_duration = self.experiment_config.DURATION
        
    def run(self):
        self.show_fullscreen(duration = self.experiment_config.DURATION, color =  self.experiment_config.BACKGROUND_COLOR)

class Flash(experiment.Stimulus):
    def stimulus_configuration(self):
        self.DURATION=0.2
        
    def calculate_stimulus_duration(self):
        self.duration=self.DURATION
        
    def run(self):
        self.show_fullscreen(color=1.0,duration=self.DURATION)

if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('zoltan', 'StimulusDevelopment', 'NaturalBarsConfig1')
