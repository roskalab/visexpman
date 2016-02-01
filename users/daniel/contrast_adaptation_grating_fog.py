from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
import numpy
import time
import random
import copy


class ContrastGrating0DegFog(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.COLOR_BASELINE = 0.5#
        self.PAUSE_BETWEEN_GRATING=0.0
        self.SPEED=1500
        self.WHITE_BAR_WIDTH = 300.0
        self.DUTY_CYCLE = 3.0
        self.CONTRAST_TIMING = [
                [1.0, 20.0],#contrast,duration in seconds
                [0.1, 15.0],
                ]
        self.REPEATS=1
        self.ORIENTATION=float(self.__class__.__name__.split('Grating')[1].split('Deg')[0])
        self.runnable='ContrastGrating'
        
class ContrastGrating090DegFog(ContrastGrating0DegFog):
    pass

class ContrastGrating180DegFog(ContrastGrating0DegFog):
    pass
    
class ContrastGrating270DegFog(ContrastGrating0DegFog):
    pass

class ContrastGrating045DegFog(ContrastGrating0DegFog):
    pass
    
class ContrastGrating135DegFog(ContrastGrating0DegFog):
    pass

class ContrastGrating225DegFog(ContrastGrating0DegFog):
    pass

class ContrastGrating315DegFog(ContrastGrating0DegFog):
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
