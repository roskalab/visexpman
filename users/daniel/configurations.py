from visexpman.engine.generic.parameter import Parameter
from visexpman.engine.visual_stimulation.configuration import VisualStimulationConfig
import visexpman.engine.generic.utils as utils
import os
class PPRLConfig(VisualStimulationConfig):
    
    def _set_user_parameters(self):
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
        LOG_PATH = '/var/log/'
        ARCHIVE_PATH = '../../../presentinator/data'
        CAPTURE_PATH = '../../../presentinator/data/capture'
        ENABLE_PARALLEL_PORT = False
#        STIMULATION_FOLDER_PATH = 'stimulus_examples'        
        FULLSCREEN = True
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.rc([600,   800])
#        SCREEN_RESOLUTION = [1680,   1050]
        ENABLE_FRAME_CAPTURE = False
        
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        FRAME_WAIT_FACTOR = 0

        GAMMA = 1.0
        FILTERWHEEL_ENABLE = False
        
        #multiple stimulus control
        STIMULUS_LIST = ['MyStimulus1',  'MyStimulus2']
        self.STIMULUS_LIST_p = Parameter(STIMULUS_LIST )
        
        SEGMENT_DURATION = 2
        ACTION_BETWEEN_STIMULUS = 'off'

        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        
        ORIGO, HORIZONTAL_AXIS_POSITIVE_DIRECTION, VERTICAL_AXIS_POSITIVE_DIRECTION = utils.coordinate_system('corner')
            
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        
        self._set_parameters_from_locals(locals())
        
class K247AWindowsConfig(VisualStimulationConfig):
    def _set_user_specific_parameters(self):        
        RUN_MODE = 'single experiment'
        EXPERIMENT_CONFIG = 'MovingDotTestConfig'
        LOG_PATH = 'c:\\temp\\'
        BASE_PATH='c:\\Data\\stimuli\\'
        ARCHIVE_PATH = os.path.join(BASE_PATH,'archive')#'../../../presentinator/data' 
        CAPTURE_PATH = os.path.join(BASE_PATH,'capture')#'../../../presentinator/data/capture'
        ENABLE_PARALLEL_PORT = False
        UDP_ENABLE = False
#        STIMULATION_FOLDER_PATH = 'stimulus_examples'        
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.rc([768,   1024])
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [36.0, [0, 100]] #cm
        SCREEN_PIXEL_WIDTH = [0.0425, [0, 0.5]] # mm
        FRAME_WAIT_FACTOR = 0 
        GAMMA = 1.0
        FILTERWHEEL_ENABLE = False
        
        #self.STIMULUS_LIST_p = Parameter(STIMULUS_LIST ) # ez hogy kerulhet ide?  mar ertem de ez nagy kavaras!
        # nem ilyen formaban kellett volna?:STATES = [['idle',  'stimulation'],  None]
        
        SEGMENT_DURATION = 2
        MAXIMUM_RECORDING_DURATION = [270, [0, 10000]] #seconds
        ACTION_BETWEEN_STIMULUS = 'off'

        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        COORDINATE_SYSTEM='ulcorner'
            
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        VisualStimulationConfig._create_parameters_from_locals(self, locals())
        #VisualStimulationConfig._set_parameters_from_locals(self, locals())

class RC3DWindowsConfig(VisualStimulationConfig):
    #NOT TESTED
    def _set_user_parameters(self):        
        ENABLE_PARALLEL_PORT = True        
        FULLSCREEN = True
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

class MBP(VisualStimulationConfig):
    def _set_user_parameters(self):        
        RUN_MODE = 'single experiment'
        EXPERIMENT_CONFIG = 'MovingDotTestConfig'
        LOG_PATH = '/Users/hd/Documents/DataBase'
        BASE_PATH='/Users/hd/Documents/DataBase'
        ARCHIVE_PATH = os.path.join(BASE_PATH,'archive')#'../../../presentinator/data' 
        CAPTURE_PATH = os.path.join(BASE_PATH,'capture')#'../../../presentinator/data/capture'
        ENABLE_PARALLEL_PORT = False
        UDP_ENABLE = False
#        STIMULATION_FOLDER_PATH = 'stimulus_examples'        
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.rc([768,   1024])
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [36.0, [0, 100]] #cm
        SCREEN_PIXEL_WIDTH = [0.0425, [0, 0.5]] # mm
        FRAME_WAIT_FACTOR = 0 
        GAMMA = 1.0
        FILTERWHEEL_ENABLE = False
        
        #self.STIMULUS_LIST_p = Parameter(STIMULUS_LIST ) # ez hogy kerulhet ide?  mar ertem de ez nagy kavaras!
        # nem ilyen formaban kellett volna?:STATES = [['idle',  'stimulation'],  None]
        
        SEGMENT_DURATION = 2
        MAXIMUM_RECORDING_DURATION = [270, [0, 10000]] #seconds
        ACTION_BETWEEN_STIMULUS = 'off'

        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        COORDINATE_SYSTEM='ulcorner'
            
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        VisualStimulationConfig._create_parameters_from_locals(self, locals())
        #VisualStimulationConfig._set_parameters_from_locals(self, locals())

class ZoliTester(VisualStimulationConfig):
    def _set_user_parameters(self):                
        EXPERIMENT_CONFIG = 'MovingDotTestConfig'
        LOG_PATH = '/media/Common/visexpman_data/test'
        EXPERIMENT_LOG_PATH = '/media/Common/visexpman_data/test'
        ARCHIVE_PATH = '/media/Common/visexpman_data/test'
        ENABLE_PARALLEL_PORT = False
        UDP_ENABLE = False        
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.rc([768, 1024])
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [36.0, [0, 100]] #cm
        SCREEN_PIXEL_WIDTH = [0.0425, [0, 0.5]] # mm
        FRAME_WAIT_FACTOR = 0 
        GAMMA = 1.0
        FILTERWHEEL_ENABLE = False
        TEXT_ENABLE = False
        
        #self.STIMULUS_LIST_p = Parameter(STIMULUS_LIST ) # ez hogy kerulhet ide?  mar ertem de ez nagy kavaras!
        # nem ilyen formaban kellett volna?:STATES = [['idle',  'stimulation'],  None]
        
        SEGMENT_DURATION = 2
        MAXIMUM_RECORDING_DURATION = [270, [0, 10000]] #seconds
        ACTION_BETWEEN_STIMULUS = 'off'

        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        COORDINATE_SYSTEM='ulcorner'
            
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0        
        self._create_parameters_from_locals(locals())

if __name__ == "__main__":
    
    c = UbuntuDeveloperConfig()
    c.print_parameters() 
    
