from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
import time
import numpy

class IncreasingAnnulusParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SIZE =1250
        self.RING_SIZES = [0, 125, 250, 375, 500, 625]
        self.ON_TIME = 2.0
        self.OFF_TIME = 5.0
        self.BACKGROUND = 0.5
        self.COLORS = [1.0, 0.0]
        self.USER_FRAGMENT_NAME = 'FILENAME'
        self.runnable = 'IncreasingAnnulusExperiment'
        self._create_parameters_from_locals(locals())
        
class IncreasingAnnulusExperiment(experiment.Experiment):
    def run(self):
        for color in self.experiment_config.COLORS:
            self.flash_stimulus('a', [self.experiment_config.ON_TIME, self.experiment_config.OFF_TIME], color, sizes = self.experiment_config.SIZE, 
                    background_color = self.experiment_config.BACKGROUND, pos = utils.rc((0,  0)),block_trigger = True, ring_sizes = numpy.array(self.experiment_config.RING_SIZES))
