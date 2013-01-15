from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
import pylab
            
class MovingShapeParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'spot'
        self.SHAPE_COLOR = 0.9
        self.SHAPE_BACKGROUND = 0.1
        self.SHAPE_SIZE = utils.rc((100, 100)) #um
        self.DIRECTIONS = [0, 45, 90, 135, 180, 225, 360] #degree
        self.SPEED = 200 #um/s
        self.PAUSE_BETWEEN_DIRECTIONS = 0.0
        self.runnable = 'MovingShapeExperiment'        
        self._create_parameters_from_locals(locals())

class MovingShapeExperiment(experiment.Experiment):
    def prepare(self):
        #calculate movement path
        if hasattr(self.experiment_config.SHAPE_SIZE, 'dtype'):
            shape_size = self.experiment_config.SHAPE_SIZE['col']
        else:
            shape_size = self.experiment_config.SHAPE_SIZE
        self.movement = min(self.machine_config.SCREEN_SIZE_UM['row'], self.machine_config.SCREEN_SIZE_UM['col']) - shape_size
        self.trajectories = []
        for direction in self.experiment_config.DIRECTIONS:
            start_point = utils.cr((0.5 * self.movement * numpy.cos(numpy.radians(direction)), 0.5 * self.movement * numpy.sin(numpy.radians(direction))))
            end_point = utils.cr((0.5 * self.movement * numpy.cos(numpy.radians(direction - 180.0)), 0.5 * self.movement * numpy.sin(numpy.radians(direction - 180.0))))
            spatial_resolution = self.experiment_config.SPEED/self.machine_config.SCREEN_EXPECTED_FRAME_RATE
            self.trajectories.append(utils.calculate_trajectory(start_point,  end_point,  spatial_resolution))

    def run(self):
        for i in range(len(self.trajectories)):
            for position in self.trajectories[i]:
                self.show_shape(shape = self.experiment_config.SHAPE,  
                            pos = position, 
                            color = self.experiment_config.SHAPE_COLOR, 
                            background_color = self.experiment_config.SHAPE_BACKGROUND,
                            orientation = self.experiment_config.DIRECTIONS[i], 
                            size = self.experiment_config.SHAPE_SIZE)
                if self.abort:
                    break
            self.show_fullscreen(duration = self.experiment_config.PAUSE_BETWEEN_DIRECTIONS,  color = self.experiment_config.SHAPE_BACKGROUND)
            if self.abort:
                break