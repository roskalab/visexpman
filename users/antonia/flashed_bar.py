from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
import copy
            
class FlashedBarParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.SHAPE_COLORS = [0.0 ]
        self.BACKGROUND_COLOR = 0.5
        self.FLASH_TIME = 0.1 #.015#   1/60 s is the time resolution
        self.BACKGROUND_TIME = 1.0
        self.SHAPE_SIZE = utils.rc((2500, 133)) #um
        self.REPETITIONS_ALL = 10 #s
        self.STEP_SIZE = 33#um
        self.NUMBER_OF_POSITIONS = 7
        self.POSITIONS = self.REPETITIONS_ALL * numpy.arange(-self.NUMBER_OF_POSITIONS*self.STEP_SIZE, (self.NUMBER_OF_POSITIONS+1)*self.STEP_SIZE, self.STEP_SIZE).tolist()
        random.seed(0)
        random.shuffle(self.POSITIONS)
        self.runnable = 'FlashedBarExperiment'        
        self._create_parameters_from_locals(locals())

class FlashedBarExperiment(experiment.Experiment):
    def run(self):
        from visexpman.users.antonia.electrode_id_reader import read_electrode_coordinates
        center,size = read_electrode_coordinates()
        for shape_color in self.experiment_config.SHAPE_COLORS:
            for displacement in self.experiment_config.POSITIONS:
                position = copy.deepcopy(center)
                position['col'] += displacement
                self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
                self.show_shape(shape = self.experiment_config.SHAPE,  
                            duration = self.experiment_config.FLASH_TIME,
                            pos = position, 
                            color = shape_color, 
                            background_color = self.experiment_config.BACKGROUND_COLOR,
                            size = self.experiment_config.SHAPE_SIZE)
                if self.abort:
                    break
                 
            if self.abort:
                break
            
  
                     