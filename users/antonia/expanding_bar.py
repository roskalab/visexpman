from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
import time
import numpy
import os.path
import os

            
class ExpandingBarParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.START_SIZE = utils.rc((100,100))
        self.END_SIZE = utils.rc((120,200))
        self.DURATION = 1.0
        self.PAUSE_BETWEEN_REPETITIONS = 1.0
        self.COLOR = 1.0
        self.BACKGROUND_COLOR = 0.0
        self.REPETITIONS = 4 #s
        self.runnable = 'ExpandingBarExp'
        self._create_parameters_from_locals(locals())

class ExpandingBarExp(experiment.Experiment):
    def prepare(self):
        nframes = self.experiment_config.DURATION * self.machine_config.SCREEN_EXPECTED_FRAME_RATE
        self.size_row = numpy.linspace(self.experiment_config.START_SIZE['row'],self.experiment_config.END_SIZE['row'],nframes)
        self.size_col = numpy.linspace(self.experiment_config.START_SIZE['col'],self.experiment_config.END_SIZE['col'],nframes)
        self.sizes = numpy.array([self.size_row,self.size_col]).T
        
    def run(self):
        for rep in range(self.experiment_config.REPETITIONS):
            for s_i in range(self.sizes.shape[0]):
                self.show_shape(shape='rect',color=self.experiment_config.COLOR,background_color=self.experiment_config.BACKGROUND_COLOR,size=utils.rc(tuple(self.sizes[s_i])))
                if self.abort:
                    break
            self.show_fullscreen(duration = self.experiment_config.PAUSE_BETWEEN_REPETITIONS, color=self.experiment_config.BACKGROUND_COLOR)
            if self.abort:
                break
    
if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('antonia', 'StimulusDevelopment', 'ExpandingBarParameters')
    
