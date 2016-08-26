from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
import numpy

class LoomingConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.START_SIZE=100
        self.END_SIZE=1000
        self.DURATION = 8.0
        self.DOTCOLOR=0.0
        self.BACKGROUNDCOLOR=1.0
        self.PAUSE = 2.0
        self.REPEATS = 3
        self.runnable = 'LoomingExp'
        self._create_parameters_from_locals(locals())

class LoomingExp(experiment.Experiment):
    def run(self):
        sizes=numpy.linspace(self.experiment_config.START_SIZE, self.experiment_config.END_SIZE,self.experiment_config.DURATION*self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
        self.show_fullscreen(color=self.experiment_config.BACKGROUNDCOLOR)
        for r in range(self.experiment_config.REPEATS):
            for s in sizes:
                self.show_shape(color=self.experiment_config.DOTCOLOR,background_color=self.experiment_config.BACKGROUNDCOLOR,shape='spot', size=s)
            self.show_fullscreen(color=self.experiment_config.BACKGROUNDCOLOR, duration=self.experiment_config.PAUSE)

if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('keisuke', 'StimulusDevelopment', 'LoomingConfig')
