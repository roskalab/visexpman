from visexpman.engine.visual_stimulation.configuration import VisualStimulationConfig
from visexpman.engine.generic import utils
import visexpman.engine.visual_stimulation.experiment as experiment
import time
import numpy

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
