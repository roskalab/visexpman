from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
            
class RandomShapeParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.SHAPE_COLOR = 0.9
        self.SHAPE_BACKGROUND = 0.1
        self.SHAPE_SIZE = 100 #um
        self.PAUSE = 0.0
        self.DISPLAY_TIME = 1.0
        self.GRID_SIZE = utils.rc((4, 4))
        self.GRID_STEP = 100
        self.RANDOM_ORDER = False
        self.runnable = 'RandomShapeExperiment'
        self._create_parameters_from_locals(locals())

class RandomShapeExperiment(experiment.Experiment):
    def prepare(self):
        #calculate grid cooridnates
        self.positions = []
        grid_size = utils.rc_multiply_with_constant(utils.rc_add(self.experiment_config.GRID_SIZE, utils.rc((1, 1)), '-'), 0.5 * self.experiment_config.GRID_STEP)
        for row in range(self.experiment_config.GRID_SIZE['row']):
            for col in range(self.experiment_config.GRID_SIZE['col']):
                self.positions.append(utils.rc((\
                                           row * self.experiment_config.GRID_STEP - grid_size['row'], \
                                           col * self.experiment_config.GRID_STEP - grid_size['col'])))
                                           
        self.order = list(range(len(self.positions)))
        if self.experiment_config.RANDOM_ORDER:
            random.seed(0)
            random.shuffle(self.order)

    def run(self):
        for index in self.order:
            self.show_shape(duration = self.experiment_config.DISPLAY_TIME, 
                            shape = self.experiment_config.SHAPE,  
                            pos = self.positions[index], 
                            color = self.experiment_config.SHAPE_COLOR, 
                            background_color = self.experiment_config.SHAPE_BACKGROUND,
                            size = self.experiment_config.SHAPE_SIZE)
            if self.abort:
                break
            self.show_fullscreen(duration = self.experiment_config.PAUSE,  color = self.experiment_config.SHAPE_BACKGROUND)
            if self.abort:
                break
                
