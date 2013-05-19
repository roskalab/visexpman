from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
            
class TestConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SCREEN_PER_MASK_RATIO = 3
        self.MASK_PER_GRATING_RATIO = 4
        self.NORMALIZED_SPEED = 4
        self.MASK_SIZE = utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] / self.SCREEN_PER_MASK_RATIO, self.machine_config.SCREEN_SIZE_UM['col'] / self.SCREEN_PER_MASK_RATIO))
        self.GRATING_SIZE = self.machine_config.SCREEN_SIZE_UM['row'] / self.SCREEN_PER_MASK_RATIO/self.MASK_PER_GRATING_RATIO
        self.SPEED = self.machine_config.SCREEN_SIZE_UM['row']/ (self.SCREEN_PER_MASK_RATIO * self.MASK_PER_GRATING_RATIO * self.NORMALIZED_SPEED)
        self.DUTY_CYCLE = 1.0
        self.DURATION = 20.0
        self.ORIENTATIONS = [0]
        self.INITIAL_DELAY = 2.0
        self.runnable = 'IntrinsicProtocol'        
        self._create_parameters_from_locals(locals())

class IntrinsicExpConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SCREEN_PER_MASK_RATIO = 3
        self.MASK_PER_GRATING_RATIO = 4
        self.NORMALIZED_SPEED = 4
        self.MASK_SIZE = utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] / self.SCREEN_PER_MASK_RATIO, self.machine_config.SCREEN_SIZE_UM['col'] / self.SCREEN_PER_MASK_RATIO))
        self.GRATING_SIZE = self.machine_config.SCREEN_SIZE_UM['row'] / self.SCREEN_PER_MASK_RATIO/self.MASK_PER_GRATING_RATIO
        self.SPEED = self.machine_config.SCREEN_SIZE_UM['row']/ (self.SCREEN_PER_MASK_RATIO * self.MASK_PER_GRATING_RATIO * self.NORMALIZED_SPEED)
        self.DUTY_CYCLE = 1.0
        self.DURATION = 20.0
        self.ORIENTATIONS = [0]
        self.INITIAL_DELAY = 2.0
        self.runnable = 'IntrinsicProtocol'        
        self._create_parameters_from_locals(locals())

class IntrinsicProtocol(experiment.Experiment):
    def prepare(self):
        self.positions = [
        utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] / 6, self.machine_config.SCREEN_SIZE_UM['col'] / 6)), 
        utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] / 6, self.machine_config.SCREEN_SIZE_UM['col'] / 2)), 
        utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] / 6, self.machine_config.SCREEN_SIZE_UM['col']*5 / 6))
        ]
        self.fragment_durations = [self.experiment_config.DURATION*len(self.positions)*len(self.experiment_config.ORIENTATIONS)]
    
    def run(self):
        time.sleep(self.experiment_config.INITIAL_DELAY)
        for position in self.positions:
            for ori in self.experiment_config.ORIENTATIONS:
                self.show_grating(duration = self.experiment_config.DURATION,  
                    white_bar_width = self.experiment_config.GRATING_SIZE,  
                    display_area = self.experiment_config.MASK_SIZE,
                    orientation = ori,  
                    velocity = self.experiment_config.SPEED,  
                    color_contrast = 1.0,  
                    color_offset = 0.5,  
                    pos = position,
                    duty_cycle = self.experiment_config.DUTY_CYCLE)
