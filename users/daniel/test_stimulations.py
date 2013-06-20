from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
import time

class PixelSizeCalibrationConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'PixelSizeCalibration'
        self._create_parameters_from_locals(locals())

class PixelSizeCalibration(experiment.Experiment):
    '''
    Helps pixel size calibration by showing 50 and 20 um circles
    '''
    def prepare(self):
        self.fragment_durations = [1.0]
        self.number_of_fragments = len(self.fragment_durations)

    def run(self):
        pattern = 0
        self.add_text('Circle at 100,100 um, diameter is 20 um.', color = (1.0,  0.0,  0.0), position = utils.cr((10.0, 30.0)))        
        while True:
            if pattern == 0:
                self.change_text(0, text = 'Circle at 100,100 um, diameter is 20 um.\n\nPress \'n\' to switch, \'s\' to stop.')
                self.show_shape(shape = 'circle', size = 20.0, pos = utils.cr((100, 100)))
            elif pattern == 1:
                self.change_text(0, text = 'Circle at 50,50 um, diameter is 50 um.\n\nPress \'n\' to switch, \'s\' to stop.')
                self.show_shape(shape = 'circle', size = 50.0, pos = utils.cr((50, 50)))
            else:
                pass
            if 'stop' in self.command_buffer:
                break
            elif 'next' in self.command_buffer:
                pattern += 1
                if pattern == 2:
                    pattern = 0
                self.command_buffer = ''
    
class IncreasingSpotParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        short = False
        if short:
            self.SIZES = [800]
        else:
            self.SIZES = [50, 100, 200, 300, 400, 500, 1000,1500]
        self.ON_TIME = 2.0
        self.OFF_TIME = 5.0
#        self.USER_FRAGMENT_NAME = 'FILENAME'
        self.runnable = 'IncreasingSpotExperiment'
        self._create_parameters_from_locals(locals())

class IncreasingSpotExperiment(experiment.Experiment):
    def run(self):
        self.increasing_spot(self.experiment_config.SIZES, self.experiment_config.ON_TIME, self.experiment_config.OFF_TIME,
                    color = 1.0, background_color = 0.0, pos = utils.rc((0,  0)),block_trigger = True)        

class MovingShapeParameters(experiment.ExperimentConfig): 
    def _create_parameters(self):
        self.SHAPE = 'spot'
        self.SHAPE_COLOR = 1.0
        self.SHAPE_BACKGROUND = 0.0
        self.SHAPE_SIZE = 300.0
        self.DIRECTIONS = range(0, 360, 45)
        self.SPEED = [400.0] 
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self.runnable = 'MovingShapeExperiment'    
        self._create_parameters_from_locals(locals())

class MovingShapeExperiment(experiment.Experiment):
    def run(self):
        self.moving_shape(self.experiment_config.SHAPE_SIZE, self.experiment_config.SPEED, self.experiment_config.DIRECTIONS, 
                shape = self.experiment_config.SHAPE, 
                color = self.experiment_config.SHAPE_COLOR, 
                background_color = self.experiment_config.SHAPE_BACKGROUND, 
                pause=self.experiment_config.PAUSE_BETWEEN_DIRECTIONS,
                block_trigger = False)
                
