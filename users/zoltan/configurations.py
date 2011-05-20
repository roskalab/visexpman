import visual_stimulation.configuration
import os
import generic.parameter

class TemplateConfig(visual_stimulation.configuration.VisualStimulationConfig):
    
    def _set_user_specific_parameters(self):
#        #display parameters:
#        SCREEN_RESOLUTION = [[1680, 1050],  [[200,  200],  [2000,  2000]]]
#        FULLSCR = True
#        EXPECTED_FRAME_RATE = [60.0,  FPS_RANGE]
#        MAX_FRAME_RATE = [60.0,  FPS_RANGE]
#        FRAME_DELAY_TOLERANCE = [1.0,  [1e-2,  10.0]]
#        BACKGROUND_COLOR = [[0.0, 0.0,  0.0],  COLOR_RANGE]
#        GAMMA = [1.0,  [1e-2,  10]]
#        
#        #pixel scaling
#        UM_TO_PIXEL_SCALE = [1.0,  [1e-3,  1e3]] #um / pixel        
#        
#        #parallel port
#        ENABLE_PARALLEL_PORT = True
#        ACQUISITION_TRIGGER_PIN = [0,  PIN_RANGE]
#        FRAME_TRIGGER_PIN = [2,  PIN_RANGE]
#        FRAME_TRIGGER_PULSE_WIDTH = [1e-3,  [1e-4,  1e-1]]
#        
#        #Network/UDP settings
#        SERVER_UDP_IP = '172.27.29.15'
#        WAIT_BETWEEN_UDP_SENDS = [0.05,  [0.0,  1.0]]
#        CLIENT_UDP_IP = ''
#        UDP_PORT = [446,  [300,  65000]]
#        UDP_BUFFER_SIZE = [65536,  [1,  100000000]]
#        
#        #paths
#        DEFAULT_IMAGE_PATH = 'images/default.bmp'
#        LOG_PATH = 'data'
#        STIMULATION_EXAMPLES_PATH = 'stimulus_examples'
#        STIMULATION_FOLDER_PATH = 'stimulations'
#        ARCHIVE_PATH = 'data'
#        CAPTURE_PATH = 'data'
#        BULLSEYE_PATH = 'images/bullseye.bmp'
#        TEMP_IMAGE_PATH = 'images/tmp.bmp'
#        
#        #fps calibration
#        FPS_TOLERANCE = [0,  [0,  10]]      #display parameters:        
#        FPS_CALIB_ENABLE = True
#        FPS_MIN = [8.0,  FPS_RANGE]
#        FPS_STEP = [4.0,  FPS_RANGE]
#        N_TEST_FRAMES = [3,  [0,  100]]
#        
#        #commands (including commands which are accepted only from udp interface)
#        CMD_START = 's'        
#        CMD_BULLSEYE = 'b'
#        CMD_QUIT = 'q'
#        CMD_SEND_FILE = 't'
#        CMD_SET_STIMULUS_FILE_START = '<'
#        CMD_SET_STIMULUS_FILE_END = '>'
#        CMD_GET_LOG = 'g'
#        CMD_CLEAR_LOG = 'l' # This command shall not be used because log file gets corrupted
#        CMD_SET_MEASUREMENT_ID = 'i'
#        CMD_START_TEST = 'y'
#        CMD_SET_BACKGROUND_COLOR = 'c'
#        CMD_NEXT_SEGMENT = 'n'
#        CMD_ABORT_STIMULUS = 'a'
#        
#        #debug
#        ENABLE_FRAME_CAPTURE = False
#        
#        #logging 
#        MAX_LOG_COLORS = [3,  [0,  100000]]
#        
#        #grating
#        MIN_PHASE_STEP = [0.001,  [1e-5,  1.0]]
#        GRATING_TEXTURE_RESOLUTION = [512,  [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048]]
#        
#        #user interface
#        TEXT_ENABLE = True
#        TEXT_COLOR = [[1.0,  -1.0,  -1.0] ,  [[-1.0,  -1.0,  -1.0],  [1.0,  1.0,  1.0]]]
#        TEXT_SIZE = [12,  [2,  20]]
#        
#        STATES = [['idle',  'stimulation'],  None]
#        
#        MENU_TEXT = \
#            's - start stimulus\n\
#        b - bullseye\n\
#        <filename> - load filename stimulus\n\
#        q - quit'
#        KEYS = [[CMD_START,  CMD_BULLSEYE,  CMD_QUIT,  CMD_START_TEST],  None] #valid key commands
#        MAX_MESSAGE_LENGTH = [200,  [10,  1000]] #length of message displayed on screen
#
#        #example config
#        SHOW_ALL_EXAMPLES = True
#        
#        #stimulus control
#        SEGMENT_DURATION = [100,  [1,  100000]]
#        ACTION_BETWEEN_STIMULUS = 'no' #keystroke, wait_xx in sec. no =  off
        self._set_parameters_from_locals(locals())        
        
class RemoteTesterConfig(visual_stimulation.configuration.VisualStimulationConfig):
    
    def _set_user_specific_parameters(self):                
        ENABLE_PARALLEL_PORT =False        
        FULLSCR = False
        SCREEN_RESOLUTION = [800,  600]        
        self._set_parameters_from_locals(locals())
        
class UbuntuDeveloperConfig(visual_stimulation.configuration.VisualStimulationConfig):
    
    def _set_user_specific_parameters(self):
        RUN_MODE = 'single experiment'
        RUN_MODE = 'user interface'
        SINGLE_EXPERIMENT = self.STIMULATION_FOLDER_PATH + os.sep + 'gratings_stimulus.py'
        SINGLE_EXPERIMENT = self.STIMULATION_FOLDER_PATH + os.sep + 'increasing_spot_stimulus.py'
        SINGLE_EXPERIMENT = 'MultipleDotTest'
        SINGLE_EXPERIMENT = 'ShapeTest'
#        SINGLE_EXPERIMENT = 'GratingMaskTest'
#        SINGLE_EXPERIMENT = 'DrumStimTest'
#        LOG_PATH = '../../presentinator/data/log/'
#        ARCHIVE_PATH = '../../presentinator/data'
#        CAPTURE_PATH = '../../presentinator/data/capture'
        ENABLE_PARALLEL_PORT = True
#        STIMULATION_FOLDER_PATH = 'stimulus_examples'        
        FULLSCR = True
        FULLSCR = False
#        SCREEN_RESOLUTION = [1024,  768]
        SCREEN_RESOLUTION = [800,   600]
#        SCREEN_RESOLUTION = [1680,   1050]
        ENABLE_FRAME_CAPTURE = False
        
        EXPECTED_FRAME_RATE = 75.0
        MAX_FRAME_RATE = 75.0
        FRAME_WAIT_FACTOR = 0.7

        GAMMA = 1.0
        FILTERWHEEL_ENABLE = False
        
        #multiple stimulus control
        STIMULUS_LIST = ['MyStimulus1',  'MyStimulus2']
        self.STIMULUS_LIST_p = generic.parameter.Parameter(STIMULUS_LIST )
        
        SEGMENT_DURATION = 2
        ACTION_BETWEEN_STIMULUS = 'off'
        
        self._set_parameters_from_locals(locals())
        
class WindowsDeveloperConfig(visual_stimulation.configuration.VisualStimulationConfig):
    
    def _set_user_specific_parameters(self):        
        RUN_MODE = 'single experiment'
        SINGLE_EXPERIMENT = self.STIMULATION_FOLDER_PATH + os.sep + 'checkerboard_stimulus.py'
#         RUN_MODE = 'user interface'        
#         SINGLE_EXPERIMENT = 'MultipleStimulus'
        SINGLE_EXPERIMENT = 'OpenGLTest'
        FILTERWHEEL_ENABLE = False
        LOG_PATH = self.BASE_PATH + os.sep + 'data'
#         TEXT_ENABLE = True
        ARCHIVE_PATH = self.BASE_PATH + os.sep + 'data'
        CAPTURE_PATH = self.BASE_PATH + os.sep + 'data'
        ENABLE_PARALLEL_PORT = False
        #STIMULATION_FOLDER_PATH = self.BASE_PATH + os.sep + 'stimulus_examples'
        FULLSCR = False
        SCREEN_RESOLUTION = [800, 600]
        GAMMA = 1.0
        TEXT_COLOR = [1.0, 0.0, 0.0]
        
        #multiple stimulus control
        STIMULUS_LIST = ['MyStimulus1',  'MyStimulus2']
        self.STIMULUS_LIST_p = generic.Parameter.Parameter(STIMULUS_LIST )
        
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
        EXPECTED_FRAME_RATE = 37.0
        ARCHIVE_PATH = self.BASE_PATH
        LOG_PATH = self.BASE_PATH
        
        self._set_parameters_from_locals(locals())
        
if __name__ == "__main__":
    
    c = UbuntuDeveloperConfig()
    c.print_parameters() 
    

