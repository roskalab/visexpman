from visexpman.engine.visual_stimulation.configuration import VisualStimulationConfig
from visexpman.engine.generic import utils
import visexpman.engine.visual_stimulation.experiment as experiment
import visexpman.engine.visual_stimulation.stimulation_library as stl

class VisexpRunnerTestConfig(VisualStimulationConfig):
    def _set_user_parameters(self):
        dataset = 1
        
        RUN_MODE = 'single experiment'
        EXPERIMENT_CONFIG = 'TestExperimentConfig'
        LOG_PATH = '/media/Common/visexpman_data'
        BASE_PATH= '/media/Common/visexpman_data'
        ARCHIVE_PATH = '/media/Common/visexpman_data'
        CAPTURE_PATH = '/media/Common/visexpman_data/Capture'
        ENABLE_PARALLEL_PORT = False
        UDP_ENABLE = False
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])
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
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        self._create_parameters_from_locals(locals())

class TestExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'GratingTest'
        self.pre_runnable = 'MultipleDotTestPre'        
        self._create_parameters_from_locals(locals())
        
class MultipleDotTestPre(experiment.PreExperiment):
    def run(self):
        pass
#        print 'pre runnable'        
#TODO:        stl.show_grating(duration = 0.1, profile = 'sqr', orientation = 0, velocity = 0.0, white_bar_width = 50, display_area =  utils.cr((100, 100)), pos = utils.cr((0, 0)), color_contrast = 1.0)
