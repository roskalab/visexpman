#== For automated tests ==
from visexpman.engine.visual_stimulation.configuration import VisualStimulationConfig
from visexpman.engine.generic import utils
import visexpman.engine.visual_stimulation.experiment as experiment
import time
import numpy

class VisexpAutomatedTestConfig(VisualStimulationConfig):
    def _set_user_parameters(self):
        dataset = 0        
        #paths
        EXPERIMENT_CONFIG = 'TestExperimentConfig'
        LOG_PATH = '/media/Common/visexpman_data'        
        EXPERIMENT_LOG_PATH = '/media/Common/visexpman_data'
        BASE_PATH= '/media/Common/visexpman_data'
        ARCHIVE_PATH = '/media/Common/visexpman_data'
        CAPTURE_PATH = '/media/Common/visexpman_data/Capture'
        TEST_DATA_PATH = '/media/Common/visexpman_data/test'        
        
        #hardware
        ENABLE_PARALLEL_PORT = True
        ENABLE_UDP = True
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 2
        FILTERWHEEL_ENABLE = True
        
        #screen
        FULLSCREEN = False        
        SCREEN_RESOLUTION = utils.cr([800, 600])        
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        GAMMA = 1.0        
        TEXT_ENABLE = True
        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        if dataset == 0:
            COORDINATE_SYSTEM='center'
        elif dataset == 1:
            COORDINATE_SYSTEM='ulcorner'        
        
        SEGMENT_DURATION = 2
        MAXIMUM_RECORDING_DURATION = [270, [0, 10000]] #seconds
        ACTION_BETWEEN_STIMULUS = 'off'
        
        ARCHIVE_FORMAT = 'zip'
#        ARCHIVE_FORMAT = 'hdf5'
        
        USER_EXPERIMENT_COMMANDS = {'dummy': {'key': 'd', 'domain': ['running experiment']}, }
        self._create_parameters_from_locals(locals())
        
class ShortExpTestConfig(VisualStimulationConfig):
    def _set_user_parameters(self):            
        #paths
        EXPERIMENT_CONFIG = 'ShortExperimentConfig'
        LOG_PATH = '/media/Common/visexpman_data'        
        EXPERIMENT_LOG_PATH = '/media/Common/visexpman_data'
        BASE_PATH= '/media/Common/visexpman_data'
        ARCHIVE_PATH = '/media/Common/visexpman_data'
        CAPTURE_PATH = '/media/Common/visexpman_data/Capture'
        TEST_DATA_PATH = '/media/Common/visexpman_data/test'        
        
        #hardware
        ENABLE_PARALLEL_PORT = True
        ENABLE_UDP = True
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 2
        FILTERWHEEL_ENABLE = True
        
        #screen
        FULLSCREEN = False        
        SCREEN_RESOLUTION = utils.cr([800, 600])        
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0        
        TEXT_ENABLE = True
        COORDINATE_SYSTEM='center'        
        ARCHIVE_FORMAT = 'zip'
        self._create_parameters_from_locals(locals())

class ShortExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'ShortExperiment'
        self._create_parameters_from_locals(locals())
        
class ShortExperiment(experiment.PreExperiment):
    def run(self):
        self.show_fullscreen(duration = 0.1, color = (1.0, 1.0, 1.0))
