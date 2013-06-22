from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
import time
import numpy

class CheckerboardParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.BOARD_SIZE = 375.0#um
        self.CHECKER_SIZE = 37.5 #um
        self.BACKGROUND_COLOR = 0.5
        self.FLICKER_FREQUENCY = 1.0 #Hz
        self.CHECKERBOARD_DURATION = 10.0#sec
        self.PAUSE_BEFORE_AFTER = 2.0#sec
        
        self.USER_FRAGMENT_NAME = 'FILENAME'
        self.runnable = 'CheckerboardExperiment'
        self._create_parameters_from_locals(locals())
        
class CheckerboardExperiment(experiment.Experiment):
    def prepare(self):
        self.ncheckers = int(self.experiment_config.BOARD_SIZE / self.experiment_config.CHECKER_SIZE)
        self.ncheckers = utils.rc((self.ncheckers, self.ncheckers))
        self.nflickers = int(self.experiment_config.CHECKERBOARD_DURATION * self.experiment_config.FLICKER_FREQUENCY)
        self.colors = numpy.zeros((self.nflickers, self.ncheckers['row'], self.ncheckers['col'], 1))
        self.colors[::2,::2,::2,:] = 1
        self.colors[::2,1::2,1::2,:] = 1
        self.colors[1::2,1::2,::2,:] = 1
        self.colors[1::2,::2,1::2,:] = 1
        
    def run(self):
        self.show_fullscreen(duration = self.experiment_config.PAUSE_BEFORE_AFTER, 
                             color = self.experiment_config.BACKGROUND_COLOR)
        self.show_checkerboard(self.ncheckers, duration = 1.0/self.experiment_config.FLICKER_FREQUENCY,
                                    color = self.colors, box_size = self.experiment_config.CHECKER_SIZE,
                                    background_color = self.experiment_config.BACKGROUND_COLOR, block_trigger = True)
        self.show_fullscreen(duration = self.experiment_config.PAUSE_BEFORE_AFTER, 
                             color = self.experiment_config.BACKGROUND_COLOR)
        
