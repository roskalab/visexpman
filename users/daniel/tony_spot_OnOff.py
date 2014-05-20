from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
            
class SpotOnOffParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPOT_SIZE = 3500  # [100,  200,  300,  400,  500,  1000]  fullfield 2500
        self.ON_TIME = 3 #s
        self.OFF_TIME = 3 #s
        self.BACKGROUND_TIME = 3
        self.SPOT_CONTRAST_ON = [0.625, 0.75, 0.87, 0.999] #N [0.625, 0.75, 0.87, 0.999] 
        self.REPETITIONS_ALL = 5
        self.BACKGROUND_COLOR = 0.5
        self.DRUG_CONC = 0.0  
        self.BLACK = 0.01
        self.WHITE = 0.999
        
  
        self.runnable = 'FlashedImages'        
        self._create_parameters_from_locals(locals())


    
class FlashedImages(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = 4+self.experiment_config.BACKGROUND_TIME*self.experiment_config.REPETITIONS_ALL + (self.experiment_config.ON_TIME + self.experiment_config.OFF_TIME)*len(self.experiment_config.SPOT_CONTRAST_ON)*self.experiment_config.REPETITIONS_ALL
        
    def run(self):
        for repetitions in range(self.experiment_config.REPETITIONS_ALL):
            self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
            for spot_contrast_on in self.experiment_config.SPOT_CONTRAST_ON:
                spot_contrast_off = self.experiment_config.BACKGROUND_COLOR - (spot_contrast_on - self.experiment_config.BACKGROUND_COLOR)
                self.show_shape(shape = 'o', pos = self.machine_config.SCREEN_CENTER, duration = self.experiment_config.ON_TIME,  color = spot_contrast_on, 
                                        background_color = self.experiment_config.BACKGROUND_COLOR,  size = self.experiment_config.SPOT_SIZE)
                #self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
                self.show_shape(shape = 'o',  pos = self.machine_config.SCREEN_CENTER, duration = self.experiment_config.OFF_TIME,  color = spot_contrast_off, 
                                        background_color = self.experiment_config.BACKGROUND_COLOR,  size = self.experiment_config.SPOT_SIZE)
                #self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
                if self.abort:
                    break
                 
            if self.abort:
                break
            
class SpotExperiment(FlashedImages): #for legacy compatibility, experiments on 12.05.2014
    pass
