from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random

if 0:
    class CurtainConfigNoGrating(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.SPEED = 300.0
            self.DIRECTIONS = range(0,360,45)
            self.REPEATS = 3
            self.runnable = 'CurtainExperiment'
            self._create_parameters_from_locals(locals())

    class CurtainExperiment(experiment.Experiment):
        def prepare(self):
            print self.machine_config.SCREEN_CENTER
            self.fragment_durations = self.moving_curtain(self.experiment_config.SPEED, color = 1.0, direction=0, background_color = 0.0, pause = 0.0,noshow=True).shape[0]/float(self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
            self.fragment_durations *= self.experiment_config.REPEATS * len(self.experiment_config.DIRECTIONS)
        
        def run(self):
            for rep in range(self.experiment_config.REPEATS):
                for d in self.experiment_config.DIRECTIONS:
                    self.moving_curtain(self.experiment_config.SPEED, color = 1.0, direction=d, background_color = 0.0, pause = 0.0)
            self.show_fullscreen(color = self.experiment_config.BACKGROUND_COLOR, duration = 0)

            
class ReceptiveFieldExploreAutosizeConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.AUTOSIZE_SHAPE = True
        self.SHAPE = 'rect'
        self.COLORS = [1.0]
        self.BACKGROUND_COLOR = 0.0
        self.SHAPE_SIZE = 300.0
        self.MESH_XY = utils.rc((4,4))
        self.ON_TIME = 0.5*2
        self.OFF_TIME = 0.5*6
        self.PAUSE_BEFORE_AFTER = 2.0
        self.REPEATS = 3
        self.ENABLE_ZOOM = False 
        self.SELECTED_POSITION = 1
        self.ZOOM_MESH_XY = utils.rc((3,3))
        self.ENABLE_RANDOM_ORDER = True
        if self.AUTOSIZE_SHAPE:
            self.SHAPE_SIZE = utils.rc((self.machine_config.SCREEN_SIZE_UM['row']/self.MESH_XY['row'],self.machine_config.SCREEN_SIZE_UM['col']/self.MESH_XY['col']))
        self.runnable='ReceptiveFieldExplore'
        self.pre_runnable='BlackPre'
        self._create_parameters_from_locals(locals())

class ReceptiveFieldExploreConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.COLORS = [1.0, 0.0]
        self.BACKGROUND_COLOR = 0.25
        self.SHAPE_SIZE = 300.0
        self.MESH_XY = utils.rc((8,8))
        self.ON_TIME = 0.5*2
        self.OFF_TIME = 0.5*4
        self.PAUSE_BEFORE_AFTER = 2.0
        self.REPEATS = 1#Only 1 repetition works. Otherwise datafile is not always saved by MES
        self.ENABLE_ZOOM = False 
        self.SELECTED_POSITION = 1
        self.ZOOM_MESH_XY = utils.rc((3,3))
        self.ENABLE_RANDOM_ORDER = True
        self.runnable='ReceptiveFieldExplore'
        self.pre_runnable='BlackPre'
        self._create_parameters_from_locals(locals())
        
class ReceptiveFieldExplore(experiment.Experiment):
    def calculate_positions(self, display_range, center, repeats, mesh_xy, colors=None):
        positions = []
        step = {}
        for axis in ['row', 'col']:
            step[axis] = display_range[axis]/mesh_xy[axis]
        for repeat in range(repeats):
            for row in range(mesh_xy['row']):
                for col in range(mesh_xy['col']):
                    position = utils.rc(((row+0.5) * step['row']+center['row'], (col+0.5)* step['col']+center['col']))
                    if colors is None:
                        positions.append(position)
                    else:
                        for color in colors:
                            positions.append([position, color])
        return positions, utils.rc((step['row'],step['col']))
    
    def prepare(self):
        if self.experiment_config.ENABLE_ZOOM:
            #Calculate the mesh positions for the whole screen
            positions, display_range = self.calculate_positions(self.machine_config.SCREEN_SIZE_UM, utils.rc((0,0)), 1, self.experiment_config.MESH_XY)
            zoom_center = utils.rc_add(positions[self.experiment_config.SELECTED_POSITION], utils.rc_multiply_with_constant(display_range, 0.5), '-')
            self.positions, display_range = self.calculate_positions(display_range, zoom_center, self.experiment_config.REPEATS, self.experiment_config.ZOOM_MESH_XY, self.experiment_config.COLORS)
            self.shape_size = display_range
        else:
            self.positions, display_range = self.calculate_positions(self.machine_config.SCREEN_SIZE_UM, utils.rc((0,0)), self.experiment_config.REPEATS, self.experiment_config.MESH_XY, self.experiment_config.COLORS)
            self.shape_size = self.experiment_config.SHAPE_SIZE
        if self.experiment_config.ENABLE_RANDOM_ORDER:
            import random
            random.shuffle(self.positions)
        self.fragment_durations = len(self.positions)* (self.experiment_config.ON_TIME + self.experiment_config.OFF_TIME) + 2*self.experiment_config.PAUSE_BEFORE_AFTER
        self.fragment_durations = [self.fragment_durations]
            
    def run(self):
        self.show_fullscreen(color = self.experiment_config.BACKGROUND_COLOR, duration = self.experiment_config.PAUSE_BEFORE_AFTER)
        for position_color in self.positions:
            if self.abort:
                break
            self.show_shape(shape = self.experiment_config.SHAPE,
                                    size = self.shape_size,
                                    color = position_color[1],
                                    background_color = self.experiment_config.BACKGROUND_COLOR,
                                    duration = self.experiment_config.ON_TIME,
                                    pos = position_color[0])
                                    
            self.show_fullscreen(color = self.experiment_config.BACKGROUND_COLOR, duration = self.experiment_config.OFF_TIME)
        duration = self.experiment_config.PAUSE_BEFORE_AFTER-self.experiment_config.OFF_TIME
        if duration> 0:
            self.show_fullscreen(color = self.experiment_config.BACKGROUND_COLOR, duration = duration)
             

            
class StimParam(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.TIMING = [10, 2, 20, 10, 20]
        self.FLASH_COLOR = [1.0, 0.5] 
        self.runnable = 'StimStyle'        
        self._create_parameters_from_locals(locals())

class StimStyle(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [sum(self.experiment_config.TIMING)*len(self.experiment_config.FLASH_COLOR)]
        
    def run(self):
        for color in self.experiment_config.FLASH_COLOR:  
            self.flash_stimulus(self.experiment_config.TIMING, flash_color = color,  background_color = 0.0, repeats = 1)

         
