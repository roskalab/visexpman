from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
import time
import numpy

class FullfieldSinewave(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.FREQUENCIES = [0.5, 1.0, 2.0]
        self.INITIAL_DELAY = 10.0
        self.SINEWAVE_DURATION = 10.0
        self.PAUSE_BETWEEN_SINEWAVES = 5.0
        self.END_PAUSE = 5.0
        self.BACKGROUND = 0.5
        self.MAX_INTENSITY = 1.0
        self.MIN_INTENSITY = 0.0
        self.USER_FRAGMENT_NAME = 'FILENAME'
        self.runnable = 'FullfieldSignalgenerator'
        self._create_parameters_from_locals(locals())
        
class FullfieldSignalgenerator(experiment.Experiment):
    def prepare(self):
        n_blocks = len(self.experiment_config.FREQUENCIES)*2+1
        self.pattern=[]
        for block_i in range(n_blocks):
            if block_i == 0:
                intensities = self.experiment_config.BACKGROUND * numpy.ones(self.machine_config.SCREEN_EXPECTED_FRAME_RATE * self.experiment_config.INITIAL_DELAY)
                block_trigger = False
            elif block_i == n_blocks - 1:
                intensities = self.experiment_config.BACKGROUND * numpy.ones(self.machine_config.SCREEN_EXPECTED_FRAME_RATE * self.experiment_config.END_PAUSE)
                block_trigger = False
            elif block_i%2==0:
                intensities = self.experiment_config.BACKGROUND * numpy.ones(self.machine_config.SCREEN_EXPECTED_FRAME_RATE * self.experiment_config.PAUSE_BETWEEN_SINEWAVES)
                block_trigger = False
            else:
                frq = self.experiment_config.FREQUENCIES[block_i/2]
                t = numpy.linspace(0, self.experiment_config.SINEWAVE_DURATION - 1.0/self.machine_config.SCREEN_EXPECTED_FRAME_RATE, self.experiment_config.SINEWAVE_DURATION * self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
                intensities = 0.5 * (self.experiment_config.MAX_INTENSITY - self.experiment_config.MIN_INTENSITY) * numpy.sin(t*2*numpy.pi*frq) + 0.5 * (self.experiment_config.MAX_INTENSITY + self.experiment_config.MIN_INTENSITY)
                block_trigger = True
            self.pattern.append((intensities, block_trigger))
        
    def run(self):
        for intensities, block_trigger in self.pattern:
            self.show_shape(shape='r', color = numpy.array([intensities]).T, size = self.machine_config.SCREEN_SIZE_UM, block_trigger = block_trigger)
        
