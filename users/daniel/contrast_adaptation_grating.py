from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
import numpy
import time
import random
import copy


class ContrastGrating0Deg(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.COLOR_BASELINE = 0.5#
        self.PAUSE_BETWEEN_GRATING=2.0
        self.SPEED=1500
        self.WHITE_BAR_WIDTH = 300.0
        self.DUTY_CYCLE = 3.0
        self.CONTRAST_TIMING = [
                [0.1, 3.0],#contrast,duration in seconds
                [0.5, 3.0],
                [0.8, 3.0],
                ]
        self.REPEATS=1
        self.ORIENTATION=float(self.__class__.__name__.split('Grating')[1].split('Deg')[0])
        self.runnable='ContrastGrating'
        
class ContrastGrating090Deg(ContrastGrating0Deg):
    pass

class ContrastGrating180Deg(ContrastGrating0Deg):
    pass
    
class ContrastGrating270Deg(ContrastGrating0Deg):
    pass

class ContrastGrating045Deg(ContrastGrating0Deg):
    pass
    
class ContrastGrating135Deg(ContrastGrating0Deg):
    pass

class ContrastGrating225Deg(ContrastGrating0Deg):
    pass

class ContrastGrating315Deg(ContrastGrating0Deg):
    pass

class ContrastGrating(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [self.experiment_config.REPEATS*sum([ct[1]+self.experiment_config.PAUSE_BETWEEN_GRATING for ct in self.experiment_config.CONTRAST_TIMING])+self.experiment_config.PAUSE_BETWEEN_GRATING]

    def _show_grating(self,contrast,duration,speed):
        self.show_grating(duration = duration,
                        white_bar_width = self.experiment_config.WHITE_BAR_WIDTH,
                        orientation = self.experiment_config.ORIENTATION,
                        velocity =speed,
                        color_contrast = contrast,
                        color_offset = self.experiment_config.COLOR_BASELINE,
                        duty_cycle = self.experiment_config.DUTY_CYCLE)

    def run(self):
        for rep in range(self.experiment_config.REPEATS):
            for contrast, duration in self.experiment_config.CONTRAST_TIMING:
                if self.experiment_config.PAUSE_BETWEEN_GRATING>0:
                    self._show_grating(contrast,self.experiment_config.PAUSE_BETWEEN_GRATING,0)
                self._show_grating(contrast,duration,self.experiment_config.SPEED)
        self._show_grating(contrast,self.experiment_config.PAUSE_BETWEEN_GRATING,0)
