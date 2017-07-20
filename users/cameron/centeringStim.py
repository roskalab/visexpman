from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random 

class centeringStimParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPOT_SIZE = 10000
        self.ON_TIME = 5 #sf
        self.OFF_TIME = 5 #s
        self.BACKGROUND_TIME = 5
        self.SPOT_CONTRAST_ON = [1.0]  #N [0.999]
        self.REPETITIONS_ALL = 10
        self.BACKGROUND_COLOR = 0.0
        self.DRUG_CONC = 0.0  
        self.BLACK = 0.01
        self.WHITE = 0.999
        
  
        self.runnable = 'centeringStimExperiment'        
        self._create_parameters_from_locals(locals())

class centeringStimExperiment(experiment.Experiment):

    def prepare(self):
        self.duration=(self.experiment_config.ON_TIME+self.experiment_config.BACKGROUND_TIME)*len(self.experiment_config.SPOT_CONTRAST_ON)*self.experiment_config.REPETITIONS_ALL

    def run(self):
        for repetitions in range(self.experiment_config.REPETITIONS_ALL):
            #self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
            for spot_contrast_on in self.experiment_config.SPOT_CONTRAST_ON:
                spot_contrast_off = self.experiment_config.BACKGROUND_COLOR - (spot_contrast_on - self.experiment_config.BACKGROUND_COLOR)
                self.block_start('spot_on')
                self.show_shape(shape = 'o',  duration = self.experiment_config.ON_TIME,  color = spot_contrast_on, 
                                        background_color = self.experiment_config.BACKGROUND_COLOR,  size = self.experiment_config.SPOT_SIZE)
                self.block_end('spot_off')
                self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
                #self.show_shape(shape = 'o',  duration = self.experiment_config.OFF_TIME,  color = spot_contrast_off, 
                                        #background_color = self.experiment_config.BACKGROUND_COLOR,  size = self.experiment_config.SPOT_SIZE)
                #self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
                if self.abort:
                    break
                 
            if self.abort:
                break
            
  
             
