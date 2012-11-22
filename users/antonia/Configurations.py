import numpy
import os
import serial
from visexpman.engine.generic.parameter import Parameter
from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig
import visexpman.engine.vision_experiment.experiment as experiment
import visexpman.engine.hardware_interface.daq_instrument as daq_instrument
import visexpman.engine.generic.utils as utils
import scipy.interpolate

class SPC(VisionExperimentConfig):
    '''
    Configuration for seriial port pulse generator
    '''
    def _set_user_parameters(self):
        PLATFORM = 'smallapp'
        SMALLAPP = {'NAME': 'Serial port pulse generator', }
        GUI_SIZE = utils.rc((400, 300))
        GUI_REFRESH_PERIOD = 1.0
        ##### Flowmeter parameters #######
        if os.name == 'nt':
            SERIAL_PORT = 'COM1'
        else:
            SERIAL_PORT = '/dev/ttyS0'
        self.MAX_PULSE_WIDTH = 3.0 #in seconds
        self.MIN_PULSE_WIDTH = 20.0e-3 #in seconds
        self.PULSE_OVERHEAD = 10.0e-3 #in seconds
        self._create_parameters_from_locals(locals())
        
class Debug(VisionExperimentConfig):
    '''
    Antona's Electrophisology visual stimulation
    '''
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'RandomShapeParameters'
        PLATFORM = 'elphys'
        EXPERIMENT_FILE_FORMAT = 'mat'
        #=== paths/data handling ===
        if os.name == 'nt':
            v_drive_data_folder = 'V:\\debug\\data'
        else:
            v_drive_data_folder = '/home/zoltan/visexp/debug/data'
        LOG_PATH = os.path.join(v_drive_data_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH
        EXPERIMENT_DATA_PATH = v_drive_data_folder
        ARCHIVE_PATH = v_drive_data_folder
        CAPTURE_PATH = os.path.join(v_drive_data_folder, 'capture')
        
        #=== screen ===
        FULLSCREEN = not True
        SCREEN_RESOLUTION = utils.cr([800,600])
#        SCREEN_RESOLUTION = utils.cr([1024, 768])
        COORDINATE_SYSTEM='center'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0        
        SCREEN_UM_TO_PIXEL_SCALE = 1.5
        
        #=== hardware ===
        ENABLE_PARALLEL_PORT =  (self.OS == 'win')
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        
        #=== network ===
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        ENABLE_UDP = (self.OS == 'win')
  
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
                    'ENABLE' :  (self.OS == 'win')
                    },
                    {
                    'ANALOG_CONFIG' : 'ao', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 1.0,
                    'AO_SAMPLE_RATE' : 10000,
                    'AO_CHANNEL' : 'Dev1/ao0:0',
                    'MAX_VOLTAGE' : 3.0,
                    'MIN_VOLTAGE' : 0.0,
                    'DURATION_OF_AI_READ' : 1.0,
                    'ENABLE' :  (self.OS == 'win')
                    },
                    ]
        #=== Others ===
        USER_EXPERIMENT_COMMANDS = {'stop': {'key': 's', 'domain': ['running experiment']}, }
        self.GAMMA_CORRECTION = numpy.array([
                                            [0, 12.5], 
                                            [10, 27], 
                                            [20, 55], 
                                            [30, 83], 
                                            [40, 109], 
                                            [50, 256], 
                                            [60, 351], 
                                            [70, 490], 
                                            [80, 646], 
                                            [90, 826], 
                                            [100, 950], 
                                            [110, 1088], 
                                            [120, 1245], 
                                            [130, 1340], 
                                            [140, 4590], 
                                            [150, 6528], 
                                            [160, 8390], 
                                            [170, 11530], 
                                            [180, 14170], 
                                            [190, 16400], 
                                            [200, 17680], 
                                            [210, 18790], 
                                            [220, 19160], 
                                            [230, 19250], 
                                            [240, 19250], 
                                            [255, 19260], 
                                            ])

        self._create_parameters_from_locals(locals())

class AEPHVS(VisionExperimentConfig):
    '''
    Antona's Electrophisology visual stimulation
    '''
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'ManipulationExperimentConfig'
        PLATFORM = 'elphys'
        EXPERIMENT_FILE_FORMAT = 'mat'
        #=== paths/data handling ===
        if os.name == 'nt':
            v_drive_data_folder = 'c:\\Data'
        else:
            v_drive_data_folder = '/home/zoltan/visexp/debug/data'
        LOG_PATH = os.path.join(v_drive_data_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH
        EXPERIMENT_DATA_PATH = v_drive_data_folder
        ARCHIVE_PATH = v_drive_data_folder
        CAPTURE_PATH = os.path.join(v_drive_data_folder, 'capture')
        
        #=== screen ===
        FULLSCREEN = True
        SCREEN_RESOLUTION = utils.cr([800,600])
        SCREEN_RESOLUTION = utils.cr([1024, 768])
        COORDINATE_SYSTEM='center'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0        
        SCREEN_UM_TO_PIXEL_SCALE = 1.5
        
        #=== hardware ===
        ENABLE_PARALLEL_PORT = True
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        
        #=== network ===
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        ENABLE_UDP = True
  
        #=== Filterwheel ===
        
        ENABLE_FILTERWHEEL = False
        
        #=== EphysData and stimulus Framerate recorder and LED controller ===
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
                    'ENABLE' : True
                    },
                    {
                    'ANALOG_CONFIG' : 'ao', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 1.0,
                    'AO_SAMPLE_RATE' : 10000,
                    'AO_CHANNEL' : 'Dev1/ao0:0',
                    'MAX_VOLTAGE' : 3.0,
                    'MIN_VOLTAGE' : 0.0,
                    'DURATION_OF_AI_READ' : 1.0,
                    'ENABLE' : True
                    },
                    ]
        #=== Others ===
        USER_EXPERIMENT_COMMANDS = {'stop': {'key': 's', 'domain': ['running experiment']}, }
        self._create_parameters_from_locals(locals())

if __name__ == "__main__":    
    c = LaserProjectorConfig()
    c.print_parameters() 
