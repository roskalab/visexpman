from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
import time
import numpy

class MovingBarParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.BAR_WIDTH = 60.0 #um
        self.SPEED = 200.0#um/s
        self.REPEATS = 5
        self.INITIAL_DELAY = 5.0 #s
        self.STANDING_BAR_TIME = 2.0 #s
        self.LOOMING = False
        self.BAR_COLOR = 0.0
        
        
        self.USER_FRAGMENT_NAME = 'FILENAME'
        self.runnable = 'BarExperiment'
        self._create_parameters_from_locals(locals())
        
class LoomingBarParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.BAR_WIDTH = 60.0 #um
        self.SPEED = 200.0#um/s
        self.REPEATS = 3
        self.INITIAL_DELAY = 5.0 #s
        self.STANDING_BAR_TIME = 2.0 #s
        self.LOOMING_RANGE = 400.0 #um
        self.LOOMING = True
        self.BAR_COLOR = 0.0
        
        self.USER_FRAGMENT_NAME = 'FILENAME'
        self.runnable = 'BarExperiment'
        self._create_parameters_from_locals(locals())
        
class BarExperiment(experiment.Experiment):
    def prepare(self):
        dsize = self.experiment_config.SPEED / self.machine_config.SCREEN_EXPECTED_FRAME_RATE
        if self.experiment_config.LOOMING:
            nframes = (self.experiment_config.LOOMING_RANGE - self.experiment_config.BAR_WIDTH)/dsize
            width = numpy.linspace(self.experiment_config.BAR_WIDTH, self.experiment_config.LOOMING_RANGE, nframes)            
            self.bar_size = numpy.ones((width.shape[0], 2)) * self.machine_config.SCREEN_SIZE_UM['row']
            self.bar_size[:, 0] = width
#            self.bar_size = utils.rc(self.bar_size)
        else:
            nframes = self.machine_config.SCREEN_SIZE_UM['col']/2.0/dsize
            self.positions = []
            for i in range(2):
                if i == 0:
                    sign = 1
                else:
                    sign = -1
                positions = numpy.linspace(self.machine_config.SCREEN_CENTER['col'], self.machine_config.SCREEN_CENTER['col'] + sign * self.machine_config.SCREEN_SIZE_UM['col']/2, nframes)
                self.positions.append(numpy.ones((positions.shape[0], 2)) * self.machine_config.SCREEN_CENTER['row'])
                self.positions[-1][:, 1] = positions
                self.positions[-1] = utils.rc(self.positions[-1])
            pass
            
    def run(self):
        bar_size = utils.rc((self.machine_config.SCREEN_SIZE_UM['row'], self.experiment_config.BAR_WIDTH))
        for repeat in range(self.experiment_config.REPEATS):
            if self.experiment_config.LOOMING:
                self.static_pattern(bar_size)
                shape_positions = numpy.zeros((self.bar_size.shape[0], 2))
                shape_positions = utils.rc(shape_positions)
                self.show_shapes(shape = 'r', shape_size=self.bar_size, shape_positions=shape_positions, nshapes=1, 
                                 color = numpy.array([self.experiment_config.BAR_COLOR]), background_color = 0.5, block_trigger = True)
#                self.show_shape(shape='r', duration = self.experiment_config.STANDING_BAR_TIME, 
#                                color = self.experiment_config.BAR_COLOR, background_color = 0.5, 
#                                size = self.bar_size, block_trigger = True)
            else:
                for i in range(2):
                    self.static_pattern(bar_size)
                    self.show_shape(shape='r',
                                color = self.experiment_config.BAR_COLOR, background_color = 0.5, 
                                pos = self.positions[i],
                                size = bar_size, block_trigger = True)
        self.show_fullscreen(duration=self.experiment_config.INITIAL_DELAY, color = 0.5,block_trigger = False)
    
    def static_pattern(self, bar_size):
        self.show_fullscreen(duration=self.experiment_config.INITIAL_DELAY, color = 0.5,block_trigger = False)
        self.show_shape(shape='r', duration = self.experiment_config.STANDING_BAR_TIME, 
                                color = self.experiment_config.BAR_COLOR, background_color = 0.5, 
                                size = bar_size, block_trigger = False)
