from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
from visexpman.users.daniel import grating
import random
import numpy
        
class ReceptiveFieldExploreConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.ENABLE_ELECTRODE_ROI = True
        self.COLORS = [0.0, 1.0]
        self.BACKGROUND_COLOR = 0.5
        self.SHAPE_SIZE = 100.0
        self.MESH_XY = utils.rc((int(self.machine_config.SCREEN_SIZE_UM['row']/self.SHAPE_SIZE),int(self.machine_config.SCREEN_SIZE_UM['col']/self.SHAPE_SIZE)))
        self.ON_TIME = 1.5
        self.OFF_TIME = 0.0
        self.PAUSE_BEFORE_AFTER = 2.0
        self.REPEATS = 1
        self.REPEAT_EACH = 4
        self.ENABLE_ZOOM = False
        self.SELECTED_POSITION = 1
        self.ZOOM_MESH_XY = utils.rc((3,3))
        self.ENABLE_RANDOM_ORDER = False
        self.runnable='ReceptiveFieldExplore'
        self._create_parameters_from_locals(locals())
        
class ReceptiveFieldExplore(experiment.Experiment):
    def calculate_positions(self, display_range, center, repeats, mesh_xy, colors=None, repeat_each = 1):
        positions = []
        step = {}
        for axis in ['row', 'col']:
            step[axis] = display_range[axis]/mesh_xy[axis]
        for repeat in range(repeats):
            for row in range(mesh_xy['row']):
                for col in range(mesh_xy['col']):
                    position = utils.rc(((row+0.5) * step['row']+center['row'], (col+0.5)* step['col']+center['col']))
                    if self.machine_config.COORDINATE_SYSTEM == 'center':
                        position['row'] = position['row'] - 0.5*display_range['row']
                        position['col'] = position['col'] - 0.5*display_range['col']
                    for rep_each in range(repeat_each):
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
        elif self.experiment_config.ENABLE_ELECTRODE_ROI:
            from visexpman.users.antonia.electrode_id_reader import read_electrode_coordinates
            center,size = read_electrode_coordinates()
            mesh_xy = utils.rc((int(numpy.ceil(size['row']/self.experiment_config.SHAPE_SIZE)),int(numpy.ceil(size['col']/self.experiment_config.SHAPE_SIZE))))
            print size, self.experiment_config.SHAPE_SIZE, mesh_xy
            self.positions, display_range = self.calculate_positions(size, center, 1, mesh_xy, self.experiment_config.COLORS)
            self.shape_size = self.experiment_config.SHAPE_SIZE
        else:
            self.positions, display_range = self.calculate_positions(self.machine_config.SCREEN_SIZE_UM, utils.rc((0,0)), self.experiment_config.REPEATS, self.experiment_config.MESH_XY, self.experiment_config.COLORS, self.experiment_config.REPEAT_EACH)
            self.shape_size = self.experiment_config.SHAPE_SIZE
        if self.experiment_config.ENABLE_RANDOM_ORDER:
            import random
            random.shuffle(self.positions)
        self.fragment_durations = [len(self.positions)*(self.experiment_config.ON_TIME+self.experiment_config.OFF_TIME)+self.experiment_config.PAUSE_BEFORE_AFTER*2]
        print self.fragment_durations, len(self.positions), self.experiment_config.MESH_XY
            
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
        self.show_fullscreen(color = self.experiment_config.BACKGROUND_COLOR, duration = self.experiment_config.PAUSE_BEFORE_AFTER-self.experiment_config.OFF_TIME)
