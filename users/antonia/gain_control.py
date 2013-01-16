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
    
        self.SPOT_CONTRAST = [0.1] #    
        self.SPOT_FREQUENCY = 2 #Hz
        self.BACKGRD_FREQUENCY = 0.5 #Hz                          
        self.STIMULATION_LENGTH = 40 #s
        self.REP= 1 
        self.SPOT_SIZE = [200] 
        self.BACKGRD_MID_COLOR = 0.5
         
        self.runnable = 'GainControlExperiment'        
        self._create_parameters_from_locals(locals())

class GainControlExperiment(experiment.Experiment):
    def run(self):
        for spot_contrast in self.experiment_config.SPOT_CONTRAST:
            backgrd_contrast = 1 - spot_contrast
            backgrd_colors = utils.generate_waveform('sin', self.machine_config.SCREEN_EXPECTED_FRAME_RATE * self.experiment_config.STIMULATION_LENGTH,
                        self.machine_config.SCREEN_EXPECTED_FRAME_RATE / self.experiment_config.BACKGRD_FREQUENCY,
                        backgrd_contrast,  self.experiment_config.BACKGRD_MID_COLOR)
            spot_colors=[]
            counter = 0
            period = self.machine_config.SCREEN_EXPECTED_FRAME_RATE / self.experiment_config.SPOT_FREQUENCY
            for backgrd in backgrd_colors:
                amp = spot_contrast*backgrd + backgrd                        
                spot_colors.append(.5*amp*numpy.sin(2*numpy.pi*counter/period))
                counter = counter + 1
                
            spot_colors = [sum(pair) for pair in zip(backgrd_colors, spot_colors)] 
            
            for rep_all_size in range(self.experiment_config.REP): 
                for spot_size in self.experiment_config.SPOT_SIZE:                               
                    for j in range(len(spot_colors)):
                            self.show_shape(shape = 'o',  color = spot_colors[j], 
                                background_color = backgrd_colors[j],  size = spot_size)
                    if self.abort:
                        break
                if self.abort:
                    break
            if self.abort:
                break
                
  
        
