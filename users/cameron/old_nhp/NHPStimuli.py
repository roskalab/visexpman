import numpy
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

NHP_DIRECTIONS = [135, 90, 315, 0, 180, 45, 225, 270,
                90,   180,   270,   135,    45,   315,     0,   225,
               315,     0,    90,   270,    45,   135,   180,   225,
               270,    90,     0,   315,   180,   135,    45,   225,
                90,   270,     0,   315,   135,   180,   225,    45]
NHP_DIRECTIONS = numpy.tile(numpy.array(range(0,360,45)),5)

class NHP1MovingGrating120(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        try:
            self.VELOCITY = int(self.__class__.__name__.split('MovingGrating')[1])
        except (ValueError, IndexError) as e:
            self.VELOCITY = 0.0
        self.ORIENTATIONS = NHP_DIRECTIONS
        self.PERIOD = 600.0#um
        self.STAND_TIME = 1#.*60
        self.REPEATS = 1
        self.PAUSE_BEFORE_AFTER = 3.0
        self.runnable='NHPMovingGrating'
        self._create_parameters_from_locals(locals())

class NHP0AdoptationStimulus(NHP1MovingGrating120):
    def _create_parameters(self):
        NHP1MovingGrating120._create_parameters(self)
        self.VELOCITY = 500.0
        self.ORIENTATIONS = NHP_DIRECTIONS[:8]
        self.STAND_TIME = 0.0
        self.PAUSE_BEFORE_AFTER = 0.0
        self.REPEATS = 1
        self.runnable='NHPMovingGrating'
        self._create_parameters_from_locals(locals())
        
class NHP2MovingGrating1200(NHP1MovingGrating120):
    pass


class NHP3FullfieldFlashConf(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.REPEATS = 5
        self.COLORS = [0.5, 1.0, 0.5, 0.0, 0.5]
        self.TIMES = [1.0, 2.0, 2.0, 2.0, 2.0]
        self.runnable = 'NHPFullfieldFlashExp'
        self._create_parameters_from_locals(locals())

class NHP4MovingBar120(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE_SIZE = utils.cr((1000, 500)) #um
        self.SPEEDS = [120] #um/s
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self.REPETITIONS = 1
        self.DIRECTIONS = NHP_DIRECTIONS
        self.SHAPE_BACKGROUND=0.0
        self.runnable = 'MovingShapeExperiment'        
        self._create_parameters_from_locals(locals())
        
class NHP5MovingBar1200(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE_SIZE = utils.cr((1000, 500)) #um
        self.SPEEDS = [1200] #um/s
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self.REPETITIONS = 1
        self.DIRECTIONS = NHP_DIRECTIONS
        self.SHAPE_BACKGROUND=0.0
        self.runnable = 'MovingShapeExperiment'        
        self._create_parameters_from_locals(locals())

        
class NHP6MarchingSquares(experiment.ExperimentConfig):
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

        
class MovingShapeExperiment(experiment.Experiment):
    def prepare(self):
        parameter_default_values = {
        'REPETITIONS': 1, 
        'SHAPE': 'rect', 
        'SHAPE_CONTRAST' : 1.0, 
        'SHAPE_BACKGROUND': 0.5, 
        'PAUSE_BETWEEN_DIRECTIONS' : 0.0, 
        }
        self.set_default_experiment_parameter_values(parameter_default_values)
        #Calculate duration
        trajectories, trajectory_directions, self.stimulus_duration = self.moving_shape_trajectory(\
                                    size = self.experiment_config.SHAPE_SIZE,
                                    speeds = self.experiment_config.SPEEDS,
                                    directions = self.experiment_config.DIRECTIONS,
                                    pause = self.pause_between_directions)
        self.stimulus_duration *= self.repetitions
        if hasattr(self, 'log') and hasattr(self.log, 'info'):
            self.log.info('Stimulus duration: {0}'.format(self.stimulus_duration))

    def run(self):
        for repetition in range(self.repetitions):
            self.moving_shape(size = self.experiment_config.SHAPE_SIZE,
                                  speeds = self.experiment_config.SPEEDS,
                                  directions = self.experiment_config.DIRECTIONS,
                                  shape = self.shape,
                                  color = self.shape_contrast,
                                  background_color = self.shape_background,
                                  pause = self.pause_between_directions,
                                  shape_starts_from_edge = True)

class NHPFullfieldFlashExp(experiment.Experiment):
    def run(self):
        for i in range(self.experiment_config.REPEATS):
            for j in range(len(self.experiment_config.TIMES)):
                self.show_fullscreen(color = self.experiment_config.COLORS[j], duration = self.experiment_config.TIMES[j])


class NHPMovingGrating(experiment.Experiment):
    def prepare(self):
        if self.experiment_config.VELOCITY == 1200:
            self.sweep_duration = 8.0
        else:
            self.sweep_duration = self.experiment_config.PERIOD * self.experiment_config.NUMBER_OF_BAR_ADVANCE_OVER_POINT/self.experiment_config.VELOCITY
            

    def run(self):
        if self.experiment_config.PAUSE_BEFORE_AFTER>0:
            self.show_fullscreen(color = 0.5, duration = self.experiment_config.PAUSE_BEFORE_AFTER)
        for ori in self.experiment_config.ORIENTATIONS:
            for r in range(self.experiment_config.REPEATS):
                if self.experiment_config.STAND_TIME>0:
                    self.show_grating(duration = self.experiment_config.STAND_TIME,
                                        white_bar_width = 0.5 * self.experiment_config.PERIOD,
                                        orientation = ori,
                                        velocity = 0.0,
                                        block_trigger = False)
                self.show_grating(duration = self.sweep_duration,
                                        white_bar_width = 0.5 * self.experiment_config.PERIOD,
                                        orientation = ori,
                                        velocity = self.experiment_config.VELOCITY,
                                        block_trigger = True)
        if self.experiment_config.PAUSE_BEFORE_AFTER>0:
            self.show_fullscreen(color = 0.5, duration = self.experiment_config.PAUSE_BEFORE_AFTER)
