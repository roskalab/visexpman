import numpy
import os
import serial
from visexpman.engine.generic.parameter import Parameter
from visexpman.engine.vision_experiment.configuration import ElphysConfig
import visexpman.engine.vision_experiment.experiment as experiment
import visexpman.engine.hardware_interface.daq_instrument as daq_instrument
import visexpman.engine.generic.utils as utils
import scipy.interpolate

class MVSSA(ElphysConfig):
    '''
    Miguel's Electrophisology visual stimulation, standalone
    '''
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'MovingShapeParameters'
        PLATFORM = 'standalone'
        EXPERIMENT_FILE_FORMAT = 'mat'
        #=== paths/data handling ===
        v_drive_data_folder = 'C:\\Data'
        LOG_PATH = os.path.join(v_drive_data_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH
        EXPERIMENT_DATA_PATH = v_drive_data_folder
        
#        CAPTURE_PATH = os.path.join(v_drive_data_folder, 'capture')
        
        #=== screen ===
        FULLSCREEN = True
        SCREEN_RESOLUTION = utils.cr([800,600])
#        SCREEN_RESOLUTION = utils.cr([1024, 768])
        COORDINATE_SYSTEM='center'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0        
        SCREEN_UM_TO_PIXEL_SCALE = 1
        
        #=== hardware ===
        ENABLE_PARALLEL_PORT =  False#(self.OS == 'win')
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        
        #=== network ===
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        ENABLE_UDP = False#(self.OS == 'win')
  
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
        gamma_corr_filename = 'c:\\visexp\\gamma.hdf5'
        if os.path.exists(gamma_corr_filename):
            from visexpA.engine.datahandlers import hdf5io
            import copy
            self.GAMMA_CORRECTION = copy.deepcopy(hdf5io.read_item(gamma_corr_filename, 'gamma_correction'))        
        #=== Others ===
        USER_EXPERIMENT_COMMANDS = {'stop': {'key': 's', 'domain': ['running experiment']}, }

        self._create_parameters_from_locals(locals())

class MVS(ElphysConfig):
    '''
    Miguel's Electrophisology visual stimulation
    '''
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'MovingShapeParameters'
        EXPERIMENT_FILE_FORMAT = 'mat'
        #=== paths/data handling ===
        v_drive_data_folder = 'C:\\Data'
        LOG_PATH = os.path.join(v_drive_data_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH
        EXPERIMENT_DATA_PATH = v_drive_data_folder
        
#        CAPTURE_PATH = os.path.join(v_drive_data_folder, 'capture')
        
        #=== screen ===
        FULLSCREEN = True
        SCREEN_RESOLUTION = utils.cr([800,600])
#        SCREEN_RESOLUTION = utils.cr([1024, 768])
        COORDINATE_SYSTEM='center'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0        
        SCREEN_UM_TO_PIXEL_SCALE = 0.45
        
        #=== hardware ===
        ENABLE_PARALLEL_PORT = True
        ACQUISITION_TRIGGER_PIN = 1
        FRAME_TRIGGER_PIN = 3
        
        #=== network ===
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        ENABLE_UDP = True#(self.OS == 'win')
  
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
                    
        ENABLE_FILTERWHEEL = True
        FILTERWHEEL_SERIAL_PORT = [{
                                    'port' :  'COM1',
                                    'baudrate' : 9600,
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
        gamma_corr_filename = 'c:\\visexp\\gamma.hdf5'
        if os.path.exists(gamma_corr_filename):
            from visexpA.engine.datahandlers import hdf5io
            import copy
            self.GAMMA_CORRECTION = copy.deepcopy(hdf5io.read_item(gamma_corr_filename, 'gamma_correction'))
        #=== Others ===
        USER_EXPERIMENT_COMMANDS = {'stop': {'key': 's', 'domain': ['running experiment']}, 
                                    'next': {'key': 'n', 'domain': ['running experiment']},}
        self._create_parameters_from_locals(locals())
        
if __name__ == "__main__":    
    c = LaserProjectorConfig()
    c.print_parameters() 
