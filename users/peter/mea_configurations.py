import os
import os.path
import serial
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig

class MEASetup(VisionExperimentConfig):
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
        ACQUISITION_TRIGGER_PIN = 4
        FRAME_TRIGGER_PIN = 6
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
        
class PetersConfig(Configuration.PresentinatorConfig):
    
    def _set_user_specific_parameters(self):
        ACQUISITION_TRIGGER_PIN = 4
        FRAME_TRIGGER_PIN = 6
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
