import os
import os.path
import serial
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment.configuration import HiMEAConfig, MCMEAConfig

class MEASetup(HiMEAConfig):#Hierlemann machine config
    '''
    '''
    def _set_user_parameters(self):
        FULLSCR = True
        SCREEN_RESOLUTION = [800,   600]
        SCREEN_RESOLUTION = [1680,   1050]
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 30.0
        SCREEN_MAX_FRAME_RATE = 30.0

        PLATFORM = 'smallapp'
        SMALLAPP = {'NAME': 'Flowmeter logger',  'POLLER':'FlowmeterPoller'}
        if os.name == 'nt':
            root_folder = 'c:\\temp'
        else:
            root_folder = '/mnt/datafast/log'
            if not os.path.exists(root_folder):
                root_folder = '/mnt/rznb/log'
        LOG_PATH = root_folder
        DATA_PATH = root_folder
        EXPERIMENT_DATA_PATH = root_folder
        GUI_SIZE = utils.rc((400, 400))
        GUI_REFRESH_PERIOD = 0.5
        ##### Flowmeter parameters #######
        
        flowmeter_serial_port = {
                                    'port' :  'COM1',
                                    'baudrate' : 19200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                    
                                    }
                                    
        FLOWMETER = {'SERIAL_PORT' : flowmeter_serial_port,
                 'ENABLE':  (os.name == 'nt'),
                 'RESOLUTION': 5,
                 'SAMPLING_RATE': 6.25, 
                 'FACTOR': 7,
                 'TIMEOUT': 2.0,
                 }
        self.FLOW_STUCKED_LIMIT = 750.0
        self.FLOW_STUCKED_CHECK_PERIOD = 5.0
        self.FILEWRITE_PERIOD = 10.0
        
        ENABLE_PARALLEL_PORT = True
        #ACQUISITION_TRIGGER_PIN = 4 # we have to start the measurements by hand
        FRAME_TIMING_PIN = 6
        GAMMA = 1.0
        ENABLE_FILTERWHEEL = True

        FILTERWHEEL_SERIAL_PORT = [{
                                    'port' :  '/dev/ttyUSB0',
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }]
        
        self._create_parameters_from_locals(locals())
  
#######################################################################################################        
              
class MultiChannel256MeaSetup(MCMEAConfig): #David machine config
    def _set_user_parameters(self):
        EXPERIMENT_FILE_FORMAT = 'mat'
        #=== paths/data handling ===
        root = 'D:\\'
        LOG_PATH = os.path.join(root, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH
        EXPERIMENT_DATA_PATH = os.path.join(root, 'data')      #here are saved important stimulation data for each recording
        
    #        CAPTURE_PATH = os.path.join(v_drive_data_folder, 'capture')
        
        #=== screen ===
        FULLSCREEN = True # True or False
#        SCREEN_RESOLUTION = utils.cr([1280,1024]) # !!! SET IT !!!
        SCREEN_RESOLUTION = utils.cr([1024, 768])
        COORDINATE_SYSTEM='center'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0        
        SCREEN_UM_TO_PIXEL_SCALE = 0.384 #how much u is one px; if 1 micron is 1 pixel, TO USE PIXELS
        
        #=== hardware === SETTING TTL 
        ENABLE_PARALLEL_PORT =  False
        SERIAL_DIO_PORT = ['COM5','COM4']
        ACQUISITION_START_PIN = [0, [0,8]]
        # ACQUISITION_TRIGGER_PIN = 5 # THIS IS FOR STARTING RECORDING; not physical pin but data port # not used: we have to start recordings by hand
        ACQUISITION_STOP_PIN = 1 # THIS IS FOR STOP THE RECORDING; not physical pin but data port
        FRAME_TIMING_PIN = 3 # THIS IS IMPORTANT FOR STIM OPTICS; not physical pin but data port
        USER_PIN = [2, [0,8]]
        # valt user pin 5 frame trigger 6 aztan vissza
        # classical parallel port pin numbering
        
        #=== network ===
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        ENABLE_UDP = False#(self.OS == 'Windows')
    
        #=== Filterwheel ===
        ENABLE_FILTERWHEEL = False
        #=== LED controller ===
        STIM_SYNC_CHANNEL_INDEX = 1
        DAQ_CONFIG = [
                      {
                    'ANALOG_CONFIG' : 'ai', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 3.0,
                    'SAMPLE_RATE' : 10000,
                    'AI_CHANNEL' : 'Dev2/ai1:2',
                    'MAX_VOLTAGE' : 10.0,
                    'MIN_VOLTAGE' : -10.0,
                    'DURATION_OF_AI_READ' : 300.0,
                    'ENABLE' :  False#(self.OS == 'Windows')
                    },
                    {
                    'ANALOG_CONFIG' : 'ao', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 1.0,
                    'AO_SAMPLE_RATE' : 10000,
                    'AO_CHANNEL' : 'Dev1/ao0:0',
                    'MAX_VOLTAGE' : 3.0,
                    'MIN_VOLTAGE' : 0.0,
                    'DURATION_OF_AI_READ' : 1.0,
                    'ENABLE' :  False#(self.OS == 'Windows')
                    },
                    ]
        #=== Others ===
        USER_EXPERIMENT_COMMANDS = {'next': {'key': 'l', 'domain': ['running experiment']}, }
        gamma_corr_filename = 'c:\\visexp\\data\\gamma.hdf5'
        if os.path.exists(gamma_corr_filename):
            import hdf5io
            import copy
            self.GAMMA_CORRECTION = copy.deepcopy(hdf5io.read_item(gamma_corr_filename, 'gamma_correction', filelocking=False))
        self._create_parameters_from_locals(locals())
            
class PetersConfig(HiMEAConfig):
    
    def _set_user_specific_parameters(self):
        # ACQUISITION_TRIGGER_PIN = 4 # we have to start the measurements by hand
        FRAME_TIMING_PIN = 6
        RUN_MODE = 'user interface'
        LOG_PATH = '../data'
        EXPERIMENT_DATA_PATH = '../data'
        CAPTURE_PATH = '../data'
        ENABLE_PARALLEL_PORT = True
#        STIMULATION_FOLDER_PATH = 'stimulus_examples'        
        FULLSCR = True
        SCREEN_RESOLUTION = [800,   600]
        SCREEN_RESOLUTION = [1680,   1050]
        ENABLE_FRAME_CAPTURE = False
        
        SCREEN_EXPECTED_FRAME_RATE = 30.0
        SCREEN_MAX_FRAME_RATE = 30.0
        FRAME_WAIT_FACTOR = 0.7

        GAMMA = 1.0
        ENABLE_FILTERWHEEL = True

        FILTERWHEEL_SERIAL_PORT = [{
                                    'port' :  '/dev/ttyUSB0',
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }]
        
        self._set_parameters_from_locals(locals())

if __name__ == "__main__":
    c = PetersConfig()
    c.print_parameters()
