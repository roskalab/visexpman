import numpy
import copy
import time
import random
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class MovingShapeExperiment1(experiment.Experiment):
    def prepare(self):
        parameter_default_values = {
        'REPETITIONS': 1, 
        'SHAPE': 'rect', 
        'SHAPE_CONTRAST' : 1.0, 
        'SHAPE_BACKGROUND': 0.5, 
        'PAUSE_BETWEEN_DIRECTIONS' : 0.0, 
        }
        self.set_default_experiment_parameter_values(parameter_default_values)        

    def run(self):
        self.show_fullscreen(duration = self.experiment_config.PAUSE_BEFORE_AFTER, color = self.experiment_config.SHAPE_BACKGROUND,frame_trigger = False)
        for repetition in range(self.repetitions):
            self.moving_shape(size = self.experiment_config.SHAPE_SIZE,
                          speeds = self.experiment_config.SPEEDS,
                          directions = self.experiment_config.DIRECTIONS,
                          shape = self.shape,
                          color = self.shape_contrast,
                          background_color = self.shape_background,
                          pause = self.pause_between_directions,
                          block_trigger = True,
                          shape_starts_from_edge = True,
                          enable_centering = True)
        self.show_fullscreen(duration = self.experiment_config.PAUSE_BEFORE_AFTER, color = self.experiment_config.SHAPE_BACKGROUND,frame_trigger = False)
        if self.experiment_config.RUN_NATURAL_BARS:
            self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
            for rep in range(self.experiment_config.NATURAL_BARS['REPEATS']):
                if self.abort:
                    break
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
                self.show_natural_bars(speed = self.experiment_config.NATURAL_BARS['SPEED'], duration=self.experiment_config.NATURAL_BARS['DURATION'], minimal_spatial_period = None, spatial_resolution = self.machine_config.SCREEN_PIXEL_TO_UM_SCALE, intensity_levels = 255, direction = 180)
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)        
            self.show_fullscreen(duration = self.experiment_config.PAUSE_BEFORE_AFTER, color = self.experiment_config.SHAPE_BACKGROUND,frame_trigger = False)

class MovingBarParameters1(experiment.ExperimentConfig):
    def _create_parameters(self):
    ################ START EDIT SECTION ################
        self.RUN_NATURAL_BARS = True
        self.NATURAL_BARS = {}
        self.NATURAL_BARS['SPEED'] = 300.0
        self.NATURAL_BARS['REPEATS'] = 5
        self.NATURAL_BARS['DURATION'] = 30.0
        
        self.PAUSE_BEFORE_AFTER = 5.0#sec
        self.SHAPE_SIZE = utils.rc((4000, 300)) #um, row colunm format
        self.SPEEDS = [1200] #um/s
        self.SHAPE_CONTRAST = 1.0
        self.SHAPE_BACKGROUND = 0.0
        self.PAUSE_BETWEEN_DIRECTIONS = 3.0
        self.REPETITIONS = 1
#        self.DIRECTIONS = [self.AXIS_ANGLE, null_dir]
        self.DIRECTIONS = range(0,360,45)
#         import random
#         random.shuffle(self.DIRECTIONS)
#         self.DIRECTIONS.reverse()
        self.DIRECTIONS.insert(0,0)
    ################ END EDIT SECTION ################
        self.SHAPE = 'rect'
        self.runnable = 'MovingShapeExperiment1'        
        self._create_parameters_from_locals(locals())
