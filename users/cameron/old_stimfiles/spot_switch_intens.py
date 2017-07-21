from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
            
class SpotSwitchParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPOT_SIZE = [500] 
        self.BACKGROUND_TIME_INITIAL = 1 #s
        self.BACKGROUND_TIME = 0.5 #s
        self.SPOT_ON_TIME = 20.5
        self.SPOT_OFF_TIME = 0  #s
        self.SPOT_ON_INTENSITY = [0.999] # ON [0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8, 0.1, 0.9, 0.01, 0.999]
        self.REPETITIONS_ALL = 1              
        self.REPETITIONS_ALL_INTENSITY = 1  
        self.REPETITIONS_EACH_INTENSITY = 1
        self.CONTRAST = [0.4] # [0.3, 0.4, 0.5, 0.6, 0.7]
        self.DRUG_CONC = 0.0  
        
        self.runnable = 'SpotExperiment'        
        self._create_parameters_from_locals(locals())

class SpotSwitchExperiment(experiment.Experiment):
    def run(self):
        for rep_all in range(self.experiment_config.REPETITIONS_ALL):
            for contrast in self.experiment_config.CONTRAST:
                for rep_all_intensities in range(self.experiment_config.REPETITIONS_ALL_INTENSITY):
                    for spot_size in self.experiment_config.SPOT_SIZE:  
                        for spot_ON_intensity in self.experiment_config.SPOT_ON_INTENSITY:
                            background_intensity = spot_ON_intensity/(contrast+1.0)
                            # spot_OFF_intensity = background_intensity*-contrast + background_intensity
                            for rep_each in range(self.experiment_config.REPETITIONS_EACH_INTENSITY):
                                self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME_INITIAL, color = background_intensity)
                                self.show_shape(shape = 'o',  duration = self.experiment_config.SPOT_ON_TIME,  color = spot_ON_intensity, 
                                        background_color = background_intensity,  size = spot_size)
                                self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  background_intensity)
                                # self.show_shape(shape = 'o',  duration = self.experiment_config.SPOT_OFF_TIME,  color = spot_OFF_intensity, 
                                        # background_color = background_intensity,  size = spot_size)
                                # self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  background_intensity)
                            if self.abort:
                                break
                        if self.abort:
                            break
                    if self.abort:
                        break
                if self.abort:
                    break
            if self.abort:
                break