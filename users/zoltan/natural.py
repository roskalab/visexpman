from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils,signal
import os
import numpy
import time

class NaturalMovieSv1(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.REPEATS=1
	self.DURATION = 30.0
        self.FILENAME = 'c:\\Data\\Movies\\catcam17'
        self.FILENAME = 'c:\\Data\\nn.3707-sv1_frames'
        self.FRAME_RATE=60.0
        self.STRETCH = 1.7
        self.runnable = 'NaturalMovieExperiment'
        self._create_parameters_from_locals(locals())


        
class NaturalMovieExperiment(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [len(os.listdir(self.experiment_config.FILENAME))/float(self.machine_config.SCREEN_EXPECTED_FRAME_RATE)*self.experiment_config.REPEATS]
        
    def run(self):
#        self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
        if self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
            duration = 0
        elif self.experiment_config.FRAME_RATE == self.machine_config.SCREEN_EXPECTED_FRAME_RATE:
            raise RuntimeError('This frame rate is not possible')
        else:
            duration = 1.0/self.experiment_config.FRAME_RATE
        for rep in range(self.experiment_config.REPEATS):
            #self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
            self.show_image(self.experiment_config.FILENAME,duration,stretch=self.experiment_config.STRETCH)
            #self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
