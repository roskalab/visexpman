import os
import serial
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig

class MEASetup(VisionExperimentConfig):
    '''
    '''
    def _set_user_parameters(self):
        PLATFORM = 'smallapp'
        SMALLAPP = {'NAME': 'Flowmeter logger',  'POLLER':'FlowmeterPoller'}
        if os.name == 'nt':
            root_folder = 'c:\\temp'
        else:
            root_folder = '/mnt/datafast/'
        LOG_PATH = root_folder
        DATA_PATH = root_folder
        GUI_SIZE = utils.rc((400, 400))
        GUI_REFRESH_PERIOD = 1.0
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
        self.FLOW_STUCKED_LIMIT = 1000.0
        self.FLOW_STUCKED_CHECK_PERIOD = 5.0
        self.FILEWRITE_PERIOD = 10.0
        
        self._create_parameters_from_locals(locals())
        
