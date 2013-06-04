from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random

class IntrinsicProtConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SCREEN_PER_MASK_RATIO = 3
        self.MASK_PER_GRATING_RATIO = 4
        self.MASK_SIZE = utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] / self.SCREEN_PER_MASK_RATIO, self.machine_config.SCREEN_SIZE_UM['col'] / self.SCREEN_PER_MASK_RATIO))
        self.GRATING_SIZE = self.machine_config.SCREEN_SIZE_UM['row'] / self.SCREEN_PER_MASK_RATIO/self.MASK_PER_GRATING_RATIO
        self.DUTY_CYCLE = 1.0
        self.DURATION = 30.0#30
        self.PAUSE = 5.0
        #Speeds
        #5/6 of screen is 60 degree of mouse visual field
        angular_factor = self.machine_config.SCREEN_SIZE_UM['col']*(5.0/6.0)/60.0
        self.STARTING_ANGULAR_SPEED = 10.0#degree/sec
        self.FINAL_ANGULAR_SPEED = 50.0#degree/sec
        self.SPEEDS = numpy.array([self.STARTING_ANGULAR_SPEED, self.FINAL_ANGULAR_SPEED]) * angular_factor
        self.runnable = 'IntrinsicProtocol'        
        self._create_parameters_from_locals(locals())

class IntrinsicProtocol(experiment.Experiment):
    def prepare(self):
        self.positions = [
            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] / 6, self.machine_config.SCREEN_SIZE_UM['col'] *5/ 6)), 
            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] / 2, self.machine_config.SCREEN_SIZE_UM['col'] *5/ 6)), 
            utils.rc((self.machine_config.SCREEN_SIZE_UM['row'] *5/ 6, self.machine_config.SCREEN_SIZE_UM['col'] *5/ 6))
            ]
        self.fragment_durations = [self.experiment_config.DURATION*len(self.positions)*2+self.experiment_config.PAUSE]
    
    def run(self):
        #Initial delay and flash
        self.show_fullscreen(color = 0.0, duration=self.experiment_config.PAUSE)
        self.show_fullscreen(color = 1.0, duration=1.0)
        self.show_fullscreen(color = 0.0, duration=self.experiment_config.PAUSE)
        for i in range(2):
            spd = self.experiment_config.SPEEDS
            if i ==1:
                spd = spd[::-1]
            for position in self.positions:
                self.show_grating(duration = self.experiment_config.DURATION,  
                white_bar_width = self.experiment_config.GRATING_SIZE,  
                display_area = self.experiment_config.MASK_SIZE,
                orientation = 0,  
                velocity =spd,
                color_contrast = 1.0,  
                color_offset = 0.5,  
                pos = position,
                duty_cycle = self.experiment_config.DUTY_CYCLE)
            self.show_fullscreen(color = 0.0, duration=self.experiment_config.PAUSE)
