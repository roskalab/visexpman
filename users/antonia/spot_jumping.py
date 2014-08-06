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
        self.SPOT_SIZE = 100  # [100,  200,  300,  400,  500,  1000]  fullfield 2500
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
            coordinates = read_receptive_field_centers()
        for repetitions in range(self.experiment_config.REPETITIONS_ALL):
            self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
            for coordinate in coordinates:
                for spot_contrast_on in self.experiment_config.SPOT_CONTRAST_ON:
                    self.show_shape(shape = 'o',  duration = self.experiment_config.ON_TIME, pos = utils.cr(tuple(coordinate)), color = spot_contrast_on,
                                        background_color = self.experiment_config.BACKGROUND_COLOR,  size = self.experiment_config.SPOT_SIZE)
                    if self.abort:
                        break
                 
            if self.abort:
                break
            
  
                     
