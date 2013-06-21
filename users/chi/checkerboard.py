from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
import time
import numpy

class CheckerboardParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.BOARD_SIZE = 75.0#um
        self.CHECKER_SIZE = 37.5 #um
        self.BACKGROUND_COLOR = 0.5
        self.FLICKER_FREQUENCY = 1.0 #Hz
        self.CHECKERBOARD_DURATION = 10.0#sec
        self.PAUSE_BEFORE_AFTER = 2.0
        
        self.USER_FRAGMENT_NAME = 'FILENAME'
        self.runnable = 'CheckerboardExperiment'
        self._create_parameters_from_locals(locals())
        
class CheckerboardExperiment(experiment.Experiment):
    def run(self):
        #NOT READY
        self.show_fullscreen(duration = 0, color = background_color, save_frame_info = False, frame_trigger = False)
        self.show_checkerboard(npixels, duration = 0, color = color, box_size = pixel_size, save_frame_info = True)
        
