import numpy
import os
import serial
from visexpman.engine.generic.parameter import Parameter
from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig
import visexpman.engine.vision_experiment.experiment as experiment
import visexpman.engine.hardware_interface.daq_instrument as daq_instrument
import visexpman.engine.generic.utils as utils
import scipy.interpolate

GAMMA_CORRECTION = numpy.array([
                             [  0.00000000e+00,   4.75926056e-07],
                             [  4.00000000e-02,   9.70084315e-07],
                             [  8.00000000e-02,   1.75933961e-06],
                             [  1.20000000e-01,   3.57667056e-06],
                             [  1.60000000e-01,   6.61748944e-06],
                             [  2.00000000e-01,   1.17860093e-05],
                             [  2.40000000e-01,   1.72121837e-05],
                             [  2.80000000e-01,   2.56603000e-05],
                             [  3.20000000e-01,   3.53384444e-05],
                             [  3.60000000e-01,   4.34599444e-05],
                             [  4.00000000e-01,   5.26528222e-05],
                             [  4.40000000e-01,   6.34452074e-05],
                             [  4.80000000e-01,   7.43691019e-05],
                             [  5.20000000e-01,   8.56278222e-05],
                             [  5.60000000e-01,   1.06390446e-04],
                             [  6.00000000e-01,   1.26330113e-04],
                             [  6.40000000e-01,   1.45863593e-04],
                             [  6.80000000e-01,   1.70540444e-04],
                             [  7.20000000e-01,   2.14974389e-04],
                             [  7.60000000e-01,   2.43497463e-04],
                             [  8.00000000e-01,   2.76866574e-04],
                             [  8.40000000e-01,   3.15004444e-04],
                             [  8.80000000e-01,   3.47217093e-04],
                             [  9.20000000e-01,   3.61518019e-04],
                             [  9.60000000e-01,   3.66851130e-04],
                             [  1.00000000e+00 ,  3.66851130e-04]
                                                           ])

class MVSSA(VisionExperimentConfig):
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
        SCREEN_UM_TO_PIXEL_SCALE = 1.65
        
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
        SYNC_CHANNEL_INDEX = 1
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
        self.GAMMA_CORRECTION = GAMMA_CORRECTION
        #=== Others ===
        USER_EXPERIMENT_COMMANDS = {'stop': {'key': 's', 'domain': ['running experiment']}, }

        self._create_parameters_from_locals(locals())

class MVS(VisionExperimentConfig):
    '''
    Miguel's Electrophisology visual stimulation
    '''
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'MovingShapeParameters'
        PLATFORM = 'elphys'
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
        SCREEN_UM_TO_PIXEL_SCALE = 1.65
        
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
        SYNC_CHANNEL_INDEX = 1
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
#         self.GAMMA_CORRECTION = GAMMA_CORRECTION
        #=== Others ===
        USER_EXPERIMENT_COMMANDS = {'stop': {'key': 's', 'domain': ['running experiment']}, }
        self._create_parameters_from_locals(locals())
        
if __name__ == "__main__":    
    c = LaserProjectorConfig()
    c.print_parameters() 
