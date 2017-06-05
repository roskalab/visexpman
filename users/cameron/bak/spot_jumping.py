from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
            
class SpotJumpParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.READ_ELECTRODE_COORDINATE = False
        self.SPOT_SIZES = [150, 250, 375, 500, 625, 1250, 3500]  # [100,  200,  300,  400,  500,  1000]  fullfield 2500
        self.ON_TIME = 2 #s
        self.BACKGROUND_TIME = 2
        self.SPOT_CONTRAST_ON = [0.99] #N [0.625, 0.75, 0.87, 0.999] 
        self.REPETITIONS_ALL = 5
        self.BACKGROUND_COLOR = 0.5
        self.DRUG_CONC = 0.0  
        self.BLACK = 0.01
        self.WHITE = 0.999
        
        self.runnable = 'SpotJumpExperiment'        
        self._create_parameters_from_locals(locals())

class SpotJumpExperiment(experiment.Experiment):
    def run(self):
        from visexpman.users.antonia.electrode_id_reader import read_single_electrode_coordinate,read_receptive_field_centers
        if self.experiment_config.READ_ELECTRODE_COORDINATE:
            coordinates = read_single_electrode_coordinate()
        else:
            coordinates,contrasts = read_receptive_field_centers()
        
        self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
        for i in range(coordinates.shape[0]):
            coordinate = coordinates[i]
            for repetitions in range(self.experiment_config.REPETITIONS_ALL):
                for spot_size in self.experiment_config.SPOT_SIZES:
                
                    self.show_shape(shape = 'o',  duration = self.experiment_config.ON_TIME, pos = utils.rc(tuple(coordinate)), color = contrasts[i],
                                     background_color = self.experiment_config.BACKGROUND_COLOR,  size = spot_size)
                    self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
                if self.abort:
                    break
                 
            if self.abort:
                break
            
  
                     
