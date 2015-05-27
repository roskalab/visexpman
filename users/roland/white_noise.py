from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
import time
import numpy
import os.path
import os
import shutil
import random

class WhiteNoiseParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.DURATION = 1.0/60.0#20#min
        self.PIXEL_SIZE =75.0
        self.FLICKERING_FREQUENCY = 60.0
        self.N_WHITE_PIXELS = False#None
        self.COLORS = [0.0, 1.0]
        self.runnable = 'WhiteNoiseExperiment'
        self._create_parameters_from_locals(locals())

class WhiteNoiseExperiment(experiment.Experiment):
    def run(self):
        print 'Start WhiteNoiseExperiments.run()'
        
        random.seed(0)
        
        _n_white_pixels = self.experiment_config.N_WHITE_PIXELS
        if not self.experiment_config.N_WHITE_PIXELS:
            _n_white_pixels = None;
        
        self.block_start()        
        self.white_noise(duration = self.experiment_config.DURATION*60,
                pixel_size = self.experiment_config.PIXEL_SIZE, 
                flickering_frequency = self.experiment_config.FLICKERING_FREQUENCY, 
                colors = self.experiment_config.COLORS,
                n_on_pixels = _n_white_pixels, set_seed = False)
        self.block_end()
	self.show_fullscreen(color=0.5)
        
