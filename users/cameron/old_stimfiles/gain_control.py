from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
            
class GainControlParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        
        self.CONTRAST = [0.1, 1]
        self.FREQUENCY = 0.5                           
        self.STIMULATION_LENGTH = 5#s
        self.REP= 5 
        self.BACKGRD_MID_COLOR = 0.5
         
        self.runnable = 'GainControlExperiment'        
        self._create_parameters_from_locals(locals())

class GainControlExperiment(experiment.Experiment):
    def run(self):
        for rep_all_size in range(self.experiment_config.REP):  
            for backgrd_contrast in(self.experiment_config.CONTRAST):
                backgrd_colors = utils.generate_waveform('sin', self.machine_config.SCREEN_EXPECTED_FRAME_RATE * self.experiment_config.STIMULATION_LENGTH,
                        self.machine_config.SCREEN_EXPECTED_FRAME_RATE / self.experiment_config.FREQUENCY,
                        backgrd_contrast,  self.experiment_config.BACKGRD_MID_COLOR)                        
                for j in range(len(backgrd_colors)):
                    self.show_shape(shape = 'o',  color = backgrd_colors[j], 
                                    background_color = backgrd_colors[j],  size = 2500)
                    if self.abort:
                        break
                if self.abort:
                    break
            
                

        
