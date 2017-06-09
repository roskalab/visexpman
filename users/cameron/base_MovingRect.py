from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
            
class MovingShapeParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'#spot
        self.SHAPE_CONTRAST = 0.999
        self.SHAPE_BACKGROUND = 0
        self.SHAPE_SIZE = utils.rc((1000, 500)) #utils.rc((100, 500)) #um
        #self.DIRECTIONS = [0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180, 195, 210, 225, 240, 255, 270, 285, 300, 315, 330, 345, 360] #[0, 180, 45, 225, 90, 270, 135, 315]
        self.DIRECTIONS = [0, 45, 90, 135, 180, 225, 270, 315, 360] #[0, 180, 45, 225, 90, 270, 135, 315]
        self.SPEED = [800, 150] #um/s 500, 700, 900, 1200, 1400, 1600 
        #self.SPEED = [3000, 1200, 2000,	2500, 800, 1500, 500,	800,	3000,	2000,	2500,	1200,	500,	1500,	500,	2500,	2000,	800,	3000,	1200,	1500,	2000,	2500,	3000,	1200,	800,	500,	1500,	1500,	500,	1200,	800,	2500,	3000,	2000,	500,	3000,	2500,	2000,	800,	1200,	1500,	1500,	1200,	500,	3000,	2500,	800,	2000,	1500,	500,	800,	2500,	1200,	2000,	3000,	1200,	1500,	2500,	500,	800,	2000,	3000,	500,	2500,	3000,	1200,	1500,	800,	2000]
        self.PAUSE_BETWEEN_DIRECTIONS = 1
        self.REPETITIONS = 3 #s
        self.FLYIN_MULTIPLIER=.8;
        self.DRUG_CONC = 0.0
        self.CENTER=utils.rc( (0,0) )
        self.runnable = 'MovExperiment'        
        self._create_parameters_from_locals(locals())

class MovExperiment(experiment.Experiment):
    def prepare(self):
        self.duration=1#TODO: add calculation
        if 0:
            #calculate movement path
            if hasattr(self.experiment_config.SHAPE_SIZE, 'dtype'):
                shape_size = self.experiment_config.SHAPE_SIZE['col']
            else:
                shape_size = self.experiment_config.SHAPE_SIZE
            self.movement = min(self.machine_config.SCREEN_SIZE_UM['row'], self.machine_config.SCREEN_SIZE_UM['col']) - shape_size
            self.trajectories = []
            for speed in self.experiment_config.SPEED:
                for direction in self.experiment_config.DIRECTIONS:
                        start_point = utils.cr((self.experiment_config.FLYIN_MULTIPLIER * self.movement * numpy.cos(numpy.radians(direction)), self.experiment_config.FLYIN_MULTIPLIER * self.movement * numpy.sin(numpy.radians(direction))))
                        end_point = utils.cr((self.experiment_config.FLYIN_MULTIPLIER * self.movement * numpy.cos(numpy.radians(direction - 180.0)), self.experiment_config.FLYIN_MULTIPLIER * self.movement * numpy.sin(numpy.radians(direction - 180.0))))
                        spatial_resolution = speed/self.machine_config.SCREEN_EXPECTED_FRAME_RATE
                        self.trajectories.append(utils.calculate_trajectory(start_point,  end_point,  spatial_resolution))

    def run(self):
        if 0:
            for repetitions in range(self.experiment_config.REPETITIONS):
                for i in range(len(self.trajectories)):
                    for position in self.trajectories[i]:
                        self.show_shape(shape = self.experiment_config.SHAPE,  
                                pos = position, 
                                color = self.experiment_config.SHAPE_CONTRAST, 
                                background_color = self.experiment_config.SHAPE_BACKGROUND,
                                orientation = self.experiment_config.DIRECTIONS[i%len(self.experiment_config.DIRECTIONS)], 
                                size = self.experiment_config.SHAPE_SIZE)
                        if self.abort:
                            break
                    self.show_fullscreen(duration = self.experiment_config.PAUSE_BETWEEN_DIRECTIONS,  color = self.experiment_config.SHAPE_BACKGROUND)
                    if self.abort:
                        break
                if self.abort:
                    break
        else:
                fid = open('C:\Users\measurement\Documents\coord.dat','r')
                coord = fid.read().split(',')
		coord = list((-int(coord[1]),-int(coord[0]))) # coordinate of center electrode
		# invert x-axis because monitor image is x-inverted relative to software orientation
		# invert y-axis because electrode positions in the software are inverted relative to software orientation
		#self.experiment_config.CENTER = tuple(coord)
		for repetitions in range(self.experiment_config.REPETITIONS):
                    self.moving_shape( self.experiment_config.SHAPE_SIZE,
                        self.experiment_config.SPEED, self.experiment_config.DIRECTIONS,
                        center= utils.rc(tuple(coord)), #self.experiment_config.CENTER,
                        shape = self.experiment_config.SHAPE,
                        color = self.experiment_config.SHAPE_CONTRAST,
                        background_color = self.experiment_config.SHAPE_BACKGROUND,
                        pause=self.experiment_config.PAUSE_BETWEEN_DIRECTIONS,
                        shape_starts_from_edge = True)


