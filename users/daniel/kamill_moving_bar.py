from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random

class KamillMovingBarsTest(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.SHAPE_COLOR = 0.999 
        self.SHAPE_BACKGROUND = 0.0
        self.SHAPE_SIZE = utils.rc((4000, 1000)) #um
        self.DIRECTIONS = range(0,360,45)#degree [0, 180, 45, 225, 90, 270, 135, 315
        self.SPEED = 300 #um/s
        self.PAUSE_BETWEEN_DIRECTIONS =2
        self.REPETITIONS_ALL = 1 #s
        
        self.runnable = 'MovingShapeExperimentOpt'        
        self._create_parameters_from_locals(locals())
            
class KamillMovingBars300(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.SHAPE_COLOR = 0.999 
        self.SHAPE_BACKGROUND = 0.0
        self.SHAPE_SIZE = utils.rc((2500, 300)) #um
        self.DIRECTIONS = [0, 90, 180, 270] #degree [0, 180, 45, 225, 90, 270, 135, 315
        self.SPEED = 100 #um/s
        self.PAUSE_BETWEEN_DIRECTIONS =2
        self.REPETITIONS_ALL = 3 #s
        
        self.runnable = 'MovingShapeExperimentOpt'        
        self._create_parameters_from_locals(locals())
     

class KamillMovingBars300unidir(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.SHAPE_COLOR = 0.999 
        self.SHAPE_BACKGROUND = 0.0
        self.SHAPE_SIZE = utils.rc((2500, 300)) #um
        self.DIRECTIONS = [0, 90] #degree [0, 180, 45, 225, 90, 270, 135, 315
        self.SPEED = 100 #um/s
        self.PAUSE_BETWEEN_DIRECTIONS =10
        self.REPETITIONS_ALL = 5 #s
        
        self.runnable = 'MovingShapeExperimentOpt'        
        self._create_parameters_from_locals(locals())

class KamillMovingBars1000(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.SHAPE_COLOR = 0.999 
        self.SHAPE_BACKGROUND = 0.0
        self.SHAPE_SIZE = utils.rc((2500, 1000)) #um
        self.DIRECTIONS = [0, 90, 180, 270] #degree [0, 180, 45, 225, 90, 270, 135, 315
        self.SPEED = 100 #um/s
        self.PAUSE_BETWEEN_DIRECTIONS =2
        self.REPETITIONS_ALL = 3 #s
        
        self.runnable = 'MovingShapeExperimentOpt'        
        self._create_parameters_from_locals(locals())
        
class MovingShapeExperimentOpt(experiment.Experiment):
    def run(self):
        for repetition in range(self.experiment_config.REPETITIONS_ALL):
            for dir in self.experiment_config.DIRECTIONS:
                self.moving_shape(size = self.experiment_config.SHAPE_SIZE,
                              speeds = self.experiment_config.SPEED,
                              directions = [dir],
                              shape = 'rect',
                              color = self.experiment_config.SHAPE_COLOR,
                              background_color = self.experiment_config.SHAPE_BACKGROUND,
                              pause = self.experiment_config.PAUSE_BETWEEN_DIRECTIONS)

        
class KamillMovingShapeExperiment(experiment.Experiment):
    def prepare(self):
        #calculate movement path
        if hasattr(self.experiment_config.SHAPE_SIZE, 'dtype'):
            shape_size = self.experiment_config.SHAPE_SIZE['col']
        else:
            shape_size = self.experiment_config.SHAPE_SIZE
        self.movement = min(self.machine_config.SCREEN_SIZE_UM['row'], self.machine_config.SCREEN_SIZE_UM['col']) + shape_size
        self.trajectories = []
        nframes = 0
        for direction in self.experiment_config.DIRECTIONS:
            if self.machine_config.COORDINATE_SYSTEM == 'ulcorner':
                start_point = utils.cr((0.5 * self.movement * numpy.cos(numpy.radians(direction)) + self.machine_config.SCREEN_CENTER['col'], 0.5 * self.movement * numpy.sin(numpy.radians(direction)) + self.machine_config.SCREEN_CENTER['col']))
                end_point = utils.cr((0.5 * self.movement * numpy.cos(numpy.radians(direction - 180.0)) + self.machine_config.SCREEN_CENTER['col'], 0.5 * self.movement * numpy.sin(numpy.radians(direction - 180.0)) + self.machine_config.SCREEN_CENTER['col']))
            elif self.machine_config.COORDINATE_SYSTEM == 'center':
                start_point = utils.cr((0.5 * self.movement * numpy.cos(numpy.radians(direction)), 0.5 * self.movement * numpy.sin(numpy.radians(direction))))
                end_point = utils.cr((0.5 * self.movement * numpy.cos(numpy.radians(direction - 180.0)), 0.5 * self.movement * numpy.sin(numpy.radians(direction - 180.0))))
            spatial_resolution = self.experiment_config.SPEED/self.machine_config.SCREEN_EXPECTED_FRAME_RATE
            self.trajectories.append(utils.calculate_trajectory(start_point,  end_point,  spatial_resolution))
            nframes += self.trajectories[-1].shape[0] + self.experiment_config.PAUSE_BETWEEN_DIRECTIONS*self.machine_config.SCREEN_EXPECTED_FRAME_RATE
        self.fragment_durations = [float(self.experiment_config.REPETITIONS_ALL*nframes)/self.machine_config.SCREEN_EXPECTED_FRAME_RATE]

    def run(self):
        for repetitions in range(self.experiment_config.REPETITIONS_ALL):
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
            if self.abort:
                break

