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
        self.SPOT_SIZE = 4000  # fullfield 2500
        self.ON_TIME = 2 #s
        self.OFF_TIME = 2 #s
        self.BACKGROUND_TIME = 2
        self.SPOT_CONTRAST_ON = [0.625, 0.75, 0.87, 0.999] #[0.625, 0.75, 0.87, 0.999]  #N [0.999]
        self.REPETITIONS_ALL = 5
        self.BACKGROUND_COLOR = 0.5
        self.DRUG_CONC = 0.0  
        self.BLACK = 0.01
        self.WHITE = 0.999
        self.runnable = 'SpotExperiment'
        self._create_parameters_from_locals(locals())

class SpotExperiment(experiment.Experiment):
    def run(self):
        for repetitions in range(self.experiment_config.REPETITIONS_ALL):
            self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
            for spot_contrast_on in self.experiment_config.SPOT_CONTRAST_ON:
                spot_contrast_off = self.experiment_config.BACKGROUND_COLOR - (spot_contrast_on - self.experiment_config.BACKGROUND_COLOR)
                self.show_shape(shape = 'o',  duration = self.experiment_config.ON_TIME,  color = spot_contrast_on, 
                                        background_color = self.experiment_config.BACKGROUND_COLOR,  size = self.experiment_config.SPOT_SIZE)
                #self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
                self.show_shape(shape = 'o',  duration = self.experiment_config.OFF_TIME,  color = spot_contrast_off, 
                                        background_color = self.experiment_config.BACKGROUND_COLOR,  size = self.experiment_config.SPOT_SIZE)
                #self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
                if self.abort:
                    break
                 
            if self.abort:
                break
            
  
            
# class SpotOnOffParameters(experiment.ExperimentConfig):
#     def _create_parameters(self):
#         self.SPOT_SIZE = 2500  # [100,  200,  300,  400,  500,  1000]  fullfield 2500
#         self.ON_TIME = 2 #s
#         self.OFF_TIME = 2 #s
#         self.BACKGROUND_TIME = 2
#         self.SPOT_CONTRAST_ON = [0.625, 0.75, 0.87, 0.999] #N [0.625, 0.75, 0.87, 0.999] 
#         self.REPETITIONS_ALL = 5
#         self.BACKGROUND_COLOR = 0.5
#         self.DRUG_CONC = 0.0  
#         self.BLACK = 0.01
#         self.WHITE = 0.999
#         
#   
#         self.runnable = 'SpotExperiment'        
#         self._create_parameters_from_locals(locals())
# 
# class SpotExperiment(experiment.Experiment):
#     def run(self):
#         for repetitions in range(self.experiment_config.REPETITIONS_ALL):
#             self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
#             for spot_contrast_on in self.experiment_config.SPOT_CONTRAST_ON:
#                 spot_contrast_off = self.experiment_config.BACKGROUND_COLOR - (spot_contrast_on - self.experiment_config.BACKGROUND_COLOR)
#                 self.show_shape(shape = 'o',  duration = self.experiment_config.ON_TIME,  color = spot_contrast_on, 
#                                         background_color = self.experiment_config.BACKGROUND_COLOR,  size = self.experiment_config.SPOT_SIZE)
#                 #self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
#                 self.show_shape(shape = 'o',  duration = self.experiment_config.OFF_TIME,  color = spot_contrast_off, 
#                                         background_color = self.experiment_config.BACKGROUND_COLOR,  size = self.experiment_config.SPOT_SIZE)
#                 #self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
#                 if self.abort:
#                     break
#                  
#             if self.abort:
#                 break
#             
#   
#                      

if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('antonia', 'StimulusDevelopment', 'SpotOnOffParameters')
