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
        self.SQUARE_COLOR = 0.5
        
        self.USER_FRAGMENT_NAME = 'FILENAME'
        self.runnable = 'CheckerboardExperiment'
        self._create_parameters_from_locals(locals())
        
class CheckerboardExperiment(experiment.Experiment):
    def prepare(self):
        self.ncheckers = int(self.experiment_config.BOARD_SIZE / self.experiment_config.CHECKER_SIZE)
        self.ncheckers = utils.rc((self.ncheckers, self.ncheckers))
        self.nflickers = int(self.experiment_config.CHECKERBOARD_DURATION * self.experiment_config.FLICKER_FREQUENCY)
        self.patterns = numpy.zeros((2,1, self.ncheckers['row'], self.ncheckers['col'], 1))
        self.patterns[0,0,::2,::2,:] = self.experiment_config.SQUARE_COLOR
        self.patterns[0,0,1::2,1::2,:] = self.experiment_config.SQUARE_COLOR
        self.patterns[1,0,1::2,::2,:] = self.experiment_config.SQUARE_COLOR
        self.patterns[1,0,::2,1::2,:] = self.experiment_config.SQUARE_COLOR
        
    def run(self):
        self.show_fullscreen(duration = self.experiment_config.PAUSE_BEFORE_AFTER, 
                             color = self.experiment_config.BACKGROUND_COLOR)
        for i in range(self.nflickers):
            t0 = time.time()
            self.show_checkerboard(self.ncheckers, duration = 1.0/self.experiment_config.FLICKER_FREQUENCY,
                                    color = self.patterns[i%2], box_size = self.experiment_config.CHECKER_SIZE,
                                    background_color = self.experiment_config.BACKGROUND_COLOR, block_trigger = True)
            wait = 1.0/self.experiment_config.FLICKER_FREQUENCY - (time.time()-t0)
#             time.sleep(wait)
        self.show_fullscreen(duration = self.experiment_config.PAUSE_BEFORE_AFTER, 
                             color = self.experiment_config.BACKGROUND_COLOR)
        
