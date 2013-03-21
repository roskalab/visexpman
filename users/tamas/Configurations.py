import os
import os.path
import serial
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig

class InsermSetupConfig(VisionExperimentConfig):
    '''
    '''
    def _set_user_parameters(self):
        EXPERIMENT_FILE_FORMAT = 'mat'
        if self.OS == 'win':
            PLATFORM = 'elphys'
        else:
            PLATFORM = 'standalone'
        if self.OS == 'win':
            root_folder = 'c:\\data'
        else:
            root_folder = '/mnt/datafast/debug'
            if not os.path.exists(root_folder):
                root_folder = '/mnt/rznb'
        LOG_PATH = os.path.join(root_folder, 'log')
        if not os.path.exists(LOG_PATH):
            os.mkdir(LOG_PATH)
        DATA_PATH = root_folder
        EXPERIMENT_DATA_PATH = root_folder
        EXPERIMENT_LOG_PATH = LOG_PATH
        
        #=== screen ===
        FULLSCREEN = not True#TMP1
        SCREEN_RESOLUTION = utils.cr([1024,768])
        COORDINATE_SYSTEM='center'        
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0        
        SCREEN_UM_TO_PIXEL_SCALE = 2.0#calibrated 01.03.2013
        INSERT_FLIP_DELAY = True
        FLIP_EXECUTION_TIME = -1e-3
        
        #=== hardware ===
        ENABLE_PARALLEL_PORT = (os.name == 'nt')
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 1
        
        #=== network ===
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        ENABLE_UDP = (self.OS == 'win')
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
                    'ENABLE' :  False#(self.OS == 'win')
                    },
                    {
                    'ANALOG_CONFIG' : 'ao', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 1.0,
                    'AO_SAMPLE_RATE' : 10000,
                    'AO_CHANNEL' : 'Dev1/ao0:0',
                    'MAX_VOLTAGE' : 3.0,
                    'MIN_VOLTAGE' : 0.0,
                    'DURATION_OF_AI_READ' : 1.0,
                    'ENABLE' :  False#(self.OS == 'win')
                    },
                    ]
                    
        #=== Filterwheel ===
        ENABLE_FILTERWHEEL = (self.OS == 'win')
        FILTERWHEEL_SERIAL_PORT = [{
                                    'port' :  'COM3',
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }, 
                                    {
                                    'port' :  'COM4',
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }]
        FILTERWHEEL_FILTERS = [{
                                                'ND0': 1, 
                                                'ND10': 2, 
                                                'ND20': 3, 
                                                'ND30': 4, 
                                                'ND40': 5, 
                                                'ND50': 6, 
                                                }, 
                                                {
                                                'ND0': 1, 
                                                'ND10': 2, 
                                                'ND20': 3, 
                                                'ND30': 4, 
                                                'ND40': 5, 
                                                'ND50': 6, 
                                                }]
        gamma_corr_filename = 'c:\\visexp\\gamma.hdf5'
        if os.path.exists(gamma_corr_filename):
            from visexpA.engine.datahandlers import hdf5io
            import copy
            self.GAMMA_CORRECTION = copy.deepcopy(hdf5io.read_item(gamma_corr_filename, 'gamma_correction'))
        #=== Others ===
        USER_EXPERIMENT_COMMANDS = {'stop': {'key': 's', 'domain': ['running experiment']}, }
        self._create_parameters_from_locals(locals())
        
        
if __name__ == "__main__":
    pass
