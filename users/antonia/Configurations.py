import os
import serial
import Configuration
import generic.Parameter

class TemplateConfig(Configuration.PresentinatorConfig):
    
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
        
class AntoniaWindowsConfig(Configuration.PresentinatorConfig):
    def _set_user_specific_parameters(self):
        RUN_MODE = 'user interface' 
        FILTERWHEEL_ENABLE = False #First filterwheel control has to be moved back to stimulus computer       
        ENABLE_PARALLEL_PORT = True
        FULLSCR = True
        SERVER_UDP_IP = '172.27.34.12'
        ARCHIVE_PATH = self.BASE_PATH + os.sep + 'data'
        LOG_PATH = self.BASE_PATH + os.sep + 'data'
        SCREEN_RESOLUTION = [1024,  768]
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 2
        EXPECTED_FRAME_RATE = 37.5
        MAX_FRAME_RATE = 37.5
        FILTERWHEEL_SETTLING_TIME = 0.5  
        UM_TO_PIXEL_SCALE = 3.0
        FILTERWHEEL_SERIAL_PORT = [{
                                    'port' :  'COM1',
                                    'baudrate' : 9600,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    },
						{
                                    'port' :  'COM2',
                                    'baudrate' : 9600,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    },
						 ]
        self.SHUTTER_SERIAL_PORT_p = generic.Parameter.Parameter(FILTERWHEEL_SERIAL_PORT )						 
        SHUTTER_SERIAL_PORT = [{
                                    'port' :  'COM3',
                                    'baudrate' : 9600,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    },]
        
        self._set_parameters_from_locals(locals())

if __name__ == "__main__":    
    c = LaserProjectorConfig()
    c.print_parameters() 
