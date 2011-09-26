from visexpman.engine.visual_stimulation.configuration import VisualStimulationConfig
from visexpman.engine.generic import utils
import visexpman.engine.visual_stimulation.experiment as experiment
import time

#== Virtual reality optical setup testing ==
class VirtualRealityTestConfig(VisualStimulationConfig):
    def _set_user_parameters(self):
        dataset = 0
        RUN_MODE = 'single experiment'
        EXPERIMENT_CONFIG = 'VirtualRealityTestExperimentConfig'
        LOG_PATH = '/media/Common/visexpman_data'
        BASE_PATH= '/media/Common/visexpman_data'
        ARCHIVE_PATH = '/media/Common/visexpman_data'
        CAPTURE_PATH = '/media/Common/visexpman_data/Capture'
        ENABLE_PARALLEL_PORT = True
        UDP_ENABLE = False
        FULLSCREEN = True
        SCREEN_RESOLUTION = utils.cr([1680, 1050])
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [36.0, [0, 100]] #cm
        SCREEN_PIXEL_WIDTH = [0.0425, [0, 0.5]] # mm
        FRAME_WAIT_FACTOR = 0
        GAMMA = 1.0
        FILTERWHEEL_ENABLE = False
        TEXT_ENABLE = True
        SEGMENT_DURATION = 2
        MAXIMUM_RECORDING_DURATION = [270, [0, 10000]] #seconds
        ACTION_BETWEEN_STIMULUS = 'off'
        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        if dataset == 0:
            COORDINATE_SYSTEM='center'
        elif dataset == 1:
            COORDINATE_SYSTEM='ulcorner'
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 2
        self._create_parameters_from_locals(locals())

class VirtualRealityTestExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'GratingTest'
        self.pre_runnable = 'TestPre'
        self._create_parameters_from_locals(locals())
        
class GratingTest(experiment.Experiment):
    def run(self):
        self.show_grating(duration =300.0, profile = 'sqr', orientation = 0, velocity =50.0, white_bar_width = 100, display_area =  utils.cr((0, 0)), pos = utils.cr((0, 0)), color_contrast = 1.0)

#== For software development test ==

class VisexpRunnerTestConfig(VisualStimulationConfig):
    def _set_user_parameters(self):
        dataset = 0
        
        RUN_MODE = 'single experiment'
        
        #paths
        EXPERIMENT_CONFIG = 'TestExperimentConfig'
        LOG_PATH = '/media/Common/visexpman_data'        
        EXPERIMENT_LOG_PATH = '/media/Common/visexpman_data'
        BASE_PATH= '/media/Common/visexpman_data'
        ARCHIVE_PATH = '/media/Common/visexpman_data'
        CAPTURE_PATH = '/media/Common/visexpman_data/Capture'
        TEST_DATA_PATH = '/media/Common/visexpman_data/test'
        TMP_PATH = '/media/Common/visexpman_data/tmp'
        
        #hardware
        ENABLE_PARALLEL_PORT = True        
        UDP_ENABLE = False
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
        
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [36.0, [0, 100]] #cm
        SCREEN_PIXEL_WIDTH = [0.0425, [0, 0.5]] # mm
        FRAME_WAIT_FACTOR = 0
        
        SEGMENT_DURATION = 2
        MAXIMUM_RECORDING_DURATION = [270, [0, 10000]] #seconds
        ACTION_BETWEEN_STIMULUS = 'off'
        
        ARCHIVE_FORMAT = 'zip'
        
        USER_EXPERIMENT_COMMANDS = {'dummy': {'key': 'd', 'domain': ['running experiment']}, }
        self._create_parameters_from_locals(locals())

class TestExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'TestExp1'
        self.pre_runnable = 'TestPre'
        self._create_parameters_from_locals(locals())
        
class TestPre(experiment.PreExperiment):
    def run(self):
        self.show_fullscreen(color = (0.28, 0.29, 0.3), flip = False)

class TestExp1(experiment.Experiment):
    def run(self):
        self.log.info('%2.3f\tMy log'%time.time())
        self.show_fullscreen(duration = 1.0,  color = 0.5)
        import random
        filter = int(5 * random.Random().random()) + 1
        time.sleep(0.2)
        self.filterwheels[0].set(filter)
        self.filterwheels[0].set_filter('ND0')
        self.parallel_port.set_data_bit(0, 0)
        time.sleep(0.1)
        self.parallel_port.set_data_bit(0, 1)
        self.show_grating(duration =1.0, profile = 'sqr', orientation = 0, velocity =50.0, white_bar_width = 100, display_area =  utils.cr((0, 0)), pos = utils.cr((0, 0)), color_contrast = 1.0)
        if self.command_buffer.find('dummy') != -1:
            self.show_grating(duration =10.0, profile = 'sqr', orientation = 0, velocity =50.0, white_bar_width = 100, display_area =  utils.cr((0, 0)), pos = utils.cr((0, 0)), color_contrast = 1.0)
