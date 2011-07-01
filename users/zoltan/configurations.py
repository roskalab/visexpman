import visual_stimulation.configuration
import os
import generic.parameter
import generic.utils as utils
import generic.configuration

GEOMETRY_PRECISION = 3

class GraphicsTestConfig(generic.configuration.Config):
    def _create_application_parameters(self):
        FPS_RANGE = (1.0,  200.0) 
        COLOR_RANGE = [[0.0, 0.0,  0.0],  [1.0, 1.0,  1.0]]
        
        SCREEN_RESOLUTION = utils.rc([768, 1024])        
        FULLSCREEN = False
        SCREEN_EXPECTED_FRAME_RATE = [60.0,  FPS_RANGE]
        SCREEN_MAX_FRAME_RATE = [60.0,  FPS_RANGE]        
        BACKGROUND_COLOR = [[0.0, 0.0,  0.0],  COLOR_RANGE]
        FRAME_WAIT_FACTOR = [1.0,  [0.0,  1.0]]
        FLIP_EXECUTION_TIME = [0*1e-3, [0.0, 1.0]]
        COORDINATE_SYSTEM = 'center' #ulcorner
#        COORDINATE_SYSTEM = 'ulcorner'

     
        
        self._create_parameters_from_locals(locals())
        
    def _calculate_parameters(self):
        self.ORIGO, self.HORIZONTAL_AXIS_POSITIVE_DIRECTION, self.VERTICAL_AXIS_POSITIVE_DIRECTION= utils.coordinate_system(self.COORDINATE_SYSTEM, self.SCREEN_RESOLUTION)

class VRConfig(visual_stimulation.configuration.VisualStimulationConfig):
    def _set_user_specific_parameters(self):
        FULLSCR = True
        BACKGROUND_COLOR = [0.0,  0.0, 0.0]
        SCREEN_RESOLUTION = utils.cr([800, 600])
        SCREEN_RESOLUTION = utils.cr([1600, 900])
#        SCREEN_RESOLUTION = utils.cr([1680, 1050])
#        SCREEN_RESOLUTION = utils.cr([3280, 1050])
        self._set_parameters_from_locals(locals())
        
class UbuntuDeveloperConfig(visual_stimulation.configuration.VisualStimulationConfig):
    
    def _set_user_specific_parameters(self):
        RUN_MODE = 'single experiment'
#        RUN_MODE = 'user interface'
        EXPERIMENT = self.STIMULATION_FOLDER_PATH + os.sep + 'gratings_stimulus.py'
        EXPERIMENT = self.STIMULATION_FOLDER_PATH + os.sep + 'increasing_spot_stimulus.py'
        EXPERIMENT = 'MultipleDotTest'
        EXPERIMENT_CONFIG = 'DotsExperimentConfig'
        PRE_EXPERIMENT = 'Pre'
        ENABLE_PRE_EXPERIMENT = True
#        EXPERIMENT = 'ShapeTest'
#        SINGLE_EXPERIMENT = 'GratingMaskTest'
#        SINGLE_EXPERIMENT = 'DrumStimTest'
        LOG_PATH = '../../../presentinator/data/log/'
        ARCHIVE_PATH = '../../../presentinator/data'
        CAPTURE_PATH = '../../../presentinator/data/capture'
        ENABLE_PARALLEL_PORT = True
#        STIMULATION_FOLDER_PATH = 'stimulus_examples'        
        FULLSCR = True
        FULLSCR = False
#        SCREEN_RESOLUTION = [1024,  768]
        SCREEN_RESOLUTION = utils.rc([600,   800])
#        SCREEN_RESOLUTION = [1680,   1050]
        ENABLE_FRAME_CAPTURE = False
        
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        FRAME_WAIT_FACTOR = 0.7

        GAMMA = 1.0
        FILTERWHEEL_ENABLE = False
        
        #multiple stimulus control
        STIMULUS_LIST = ['MyStimulus1',  'MyStimulus2']
        self.STIMULUS_LIST_p = generic.parameter.Parameter(STIMULUS_LIST )
        
        SEGMENT_DURATION = 2
        ACTION_BETWEEN_STIMULUS = 'off'

        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        corner = False
        if corner:
            ORIGO = utils.cr((-0.5 * SCREEN_RESOLUTION['col'], 0.5 * SCREEN_RESOLUTION['row']))
            HORIZONTAL_AXIS_POSITIVE_DIRECTION = 'right'
            VERTICAL_AXIS_POSITIVE_DIRECTION = 'down'
        else:
            ORIGO = utils.cr((0, 0))
            HORIZONTAL_AXIS_POSITIVE_DIRECTION = 'right'
            VERTICAL_AXIS_POSITIVE_DIRECTION = 'up'
            
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        
        self._set_parameters_from_locals(locals())
        
class WindowsDeveloperConfig(visual_stimulation.configuration.VisualStimulationConfig):
    
    def _set_user_specific_parameters(self):        
        RUN_MODE = 'single experiment'
        EXPERIMENT = 'MultipleDotTest'
        EXPERIMENT_CONFIG = 'DotsExperimentConfig'
        PRE_EXPERIMENT = 'Pre'
        ENABLE_PRE_EXPERIMENT = True
#        EXPERIMENT = self.STIMULATION_FOLDER_PATH + os.sep + 'checkerboard_stimulus.py'
#         RUN_MODE = 'user interface'        
#         EXPERIMENT = 'MultipleStimulus'
#        EXPERIMENT = 'OpenGLTest'
        FILTERWHEEL_ENABLE = False
        LOG_PATH = '..' + os.sep + 'data'
#         TEXT_ENABLE = True
        ARCHIVE_PATH = '..' + os.sep + 'data'
        CAPTURE_PATH = '..' + os.sep + 'data'
        ENABLE_PARALLEL_PORT = False
        #STIMULATION_FOLDER_PATH = self.BASE_PATH + os.sep + 'stimulus_examples'
        FULLSCR = False
        SCREEN_RESOLUTION = [800, 600]
        GAMMA = 1.0
        TEXT_COLOR = [1.0, 0.0, 0.0]
        
        #multiple stimulus control
        STIMULUS_LIST = ['MyStimulus1',  'MyStimulus2']
        self.STIMULUS_LIST_p = generic.parameter.Parameter(STIMULUS_LIST )
        
        SEGMENT_DURATION = 2
        ACTION_BETWEEN_STIMULUS = 'no'
        
        self._set_parameters_from_locals(locals())

class WindowsConfig(visual_stimulation.configuration.VisualStimulationConfig):
    #NOT TESTED
    def _set_user_specific_parameters(self):        
        ENABLE_PARALLEL_PORT = True        
        FULLSCR = True
        SCREEN_RESOLUTION = [1600,  1200]
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 2
        SERVER_UDP_IP = '172.27.26.10'
        ARCHIVE_PATH = self.BASE_PATH
        LOG_PATH = self.BASE_PATH
        #test steps:
        # 1. frame rate 60
        # 2. parallel port OK
        # 3 network control
        # 4 stimulus types
        
        self._set_parameters_from_locals(locals())

class LaserProjectorConfig(visual_stimulation.configuration.VisualStimulationConfig):
    #NOT TESTED
    def _set_user_specific_parameters(self):        
        SCREEN_RESOLUTION = [800, 600]
        FULLSCR = True
        ENABLE_PARALLEL_PORT = True
        ACQUISITION_TRIGGER_PIN = 6
        FRAME_TRIGGER_PIN = 7
        TEXT_ENABLE = True
        SCREEN_EXPECTED_FRAME_RATE = 37.0
        ARCHIVE_PATH = self.BASE_PATH
        LOG_PATH = self.BASE_PATH
        
        self._set_parameters_from_locals(locals())
        
if __name__ == "__main__":
    
    c = UbuntuDeveloperConfig()
    c.print_parameters() 
    
