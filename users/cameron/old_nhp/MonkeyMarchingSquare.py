import numpy
import copy
import time
import random
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class MonkeyMarchingSquares(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.COLORS = [1.0]
        self.BACKGROUND_COLOR = 0.0
        self.SHAPE_SIZE = 200.0
        self.ON_TIME = 1.0
        self.OFF_TIME = 1.0
        self.PAUSE_BEFORE_AFTER = 2.0
        self.REPEATS = 5
        self.REPEAT_SEQUENCE = 1
        self.ENABLE_RANDOM_ORDER = False
        self.DISPLAY_AREA = utils.rc((1200,1200))
        self.runnable='ReceptiveFieldExplore1'
        self._create_parameters_from_locals(locals())
        
class ReceptiveFieldExplore1(experiment.Experiment):
    '''
    When MESH_SIZE not defined or MESH_SIZE == None: shape_size and screen size determines the mesh size
    
    Repeats: flash or sequence
    
    Supported use cases: fixed size squares are oresented with no gaps and no overlaps. Fractional squares are not shown at the edges
    '''
    def calculate_positions(self, display_range, center, repeats, mesh_size, colors=None,repeat_sequence = 1):
        positions = []
        step = {}
        for axis in ['row', 'col']:
            if not hasattr(self.experiment_config, 'MESH_SIZE') or self.experiment_config.MESH_SIZE == None:
        	    step[axis] = self.shape_size
            else:
                step[axis] = display_range[axis]/mesh_size[axis]
        vaf = 1 if self.machine_config.VERTICAL_AXIS_POSITIVE_DIRECTION == 'up' else -1
        for repeat in range(repeat_sequence):
            for row in range(mesh_size['row']):
                for col in range(mesh_size['col']):
                    position = utils.rc((-vaf*((row+0.5) * step['row']+center['row']-int(display_range['row']*0.5/step['row'])*step['row']), 
                                (col+0.5)* step['col']+center['col']-int(display_range['col']*0.5/step['row'])*step['row']))
                    if colors is None:
                        positions.extend(repeats*[position])
                    else:
                        for color in colors:
                            positions.extend(repeats*[[position, color]])
        return positions, utils.rc((step['row'],step['col']))
    
    def prepare(self):
        if hasattr(self.experiment_config, 'ENABLE_ZOOM') and self.experiment_config.ENABLE_ZOOM:
            #Calculate the mesh positions for the whole screen
            self.shape_size = display_range
            positions, display_range = self.calculate_positions(self.machine_config.SCREEN_SIZE_UM, utils.rc((0,0)), 1, self.experiment_config.MESH_SIZE, repeat_sequence = self.experiment_config.REPEAT_SEQUENCE)
            zoom_center = utils.rc_add(positions[self.experiment_config.SELECTED_POSITION], utils.rc_multiply_with_constant(display_range, 0.5), '-')
            self.positions, display_range = self.calculate_positions(display_range, zoom_center, self.experiment_config.REPEATS, self.experiment_config.ZOOM_MESH_SIZE, self.experiment_config.COLORS, repeat_sequence = self.experiment_config.REPEAT_SEQUENCE)
        else:
            self.shape_size = self.experiment_config.SHAPE_SIZE
            if not hasattr(self.experiment_config, 'DISPLAY_AREA'):
                display_area = self.machine_config.SCREEN_SIZE_UM
            else:
                display_area = self.experiment_config.DISPLAY_AREA
            if not hasattr(self.experiment_config, 'MESH_SIZE') or self.experiment_config.MESH_SIZE == None:
                mesh_size = utils.rc_multiply_with_constant(display_area, 1.0/self.experiment_config.SHAPE_SIZE)
                mesh_size = utils.rc((numpy.floor(mesh_size['row']), numpy.floor(mesh_size['col'])))
            else:
                mesh_size =  self.experiment_config.MESH_SIZE
            self.positions, display_range = self.calculate_positions(display_area, utils.rc((0,0)), self.experiment_config.REPEATS, mesh_size, self.experiment_config.COLORS, repeat_sequence = self.experiment_config.REPEAT_SEQUENCE)
        if self.experiment_config.ENABLE_RANDOM_ORDER:
            import random
            random.seed(0)
            random.shuffle(self.positions)
        self.fragment_durations = len(self.positions)* (self.experiment_config.ON_TIME + self.experiment_config.OFF_TIME) + 2*self.experiment_config.PAUSE_BEFORE_AFTER
        self.fragment_durations = [self.fragment_durations]
        self.stimulus_duration = self.fragment_durations[0]
            
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
        timeleft = self.experiment_config.PAUSE_BEFORE_AFTER-self.experiment_config.OFF_TIME
        self.show_fullscreen(color = self.experiment_config.BACKGROUND_COLOR, duration = 0 if timeleft < 0 else timeleft)
