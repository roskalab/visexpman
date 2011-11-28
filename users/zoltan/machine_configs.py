from visexpman.engine.visual_stimulation.configuration import VisionExperimentConfig
from visexpman.engine.generic import utils
import visexpman.engine.visual_stimulation.experiment as experiment
import time
import numpy
import serial
import visexpman
import os.path
import os
import visexpman.engine.hardware_interface.daq_instrument as daq_instrument
import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner

class VS3DUS(VisionExperimentConfig):
    '''
    Visual stimulation machine of 3D microscope setup
    '''
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'MESExperimentConfig'
        
        #=== paths/data handling ===
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_DATA_PATH = unit_test_runner.TEST_working_folder
        CAPTURE_PATH = os.path.join(unit_test_runner.TEST_working_folder,'Capture')
        
        ARCHIVE_FORMAT = 'hdf5'
        
        #=== screen ===
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])
        COORDINATE_SYSTEM='center'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0        
        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        if not os.path.exists(CAPTURE_PATH) and ENABLE_FRAME_CAPTURE:
            os.mkdir(CAPTURE_PATH)
        
        #=== experiment specific ===
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [36.0, [0, 100]] #cm
        SCREEN_PIXEL_WIDTH = [0.0425, [0, 0.5]] # mm
        
        #=== Network ===
        ENABLE_UDP = False        
        
        #=== hardware ===
        ENABLE_PARALLEL_PORT = True
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 2
        
        #=== stage ===
        motor_serial_port = {
                                    'port' :  unit_test_runner.TEST_stage_com_port,
                                    'baudrate' : 19200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }
                                    
        STAGE = [[{'serial_port' : motor_serial_port,
                 'enable': not True,
                 'speed': 1000000,
                 'acceleration' : 1000000,
                 'move_timeout' : 45.0,
                 'um_per_ustep' : numpy.ones(3, dtype = numpy.float)
                 }]]
                 
        #=== Filterwheel ===
        
        ENABLE_FILTERWHEEL = False
        
        FILTERWHEEL_SERIAL_PORT = [[{
                                    'port' :  unit_test_runner.TEST_com_port,
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }]]        
                                    
        FILTERWHEEL_FILTERS = [[{
                                                'ND0': 1, 
                                                'ND10': 2, 
                                                'ND20': 3, 
                                                'ND30': 4, 
                                                'ND40': 5, 
                                                'ND50': 6, 
                                                }]]
                                                
        #=== LED controller ===
        DAQ_CONFIG = [[
                    {
                    'ANALOG_CONFIG' : 'ai', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 1.0,
                    'AI_SAMPLE_RATE' : 1000,                    
                    'AI_CHANNEL' : 'Dev1/ai0:1',
                    'MAX_VOLTAGE' : 5.0,
                    'MIN_VOLTAGE' : 0.0,
                    'DURATION_OF_AI_READ' : 1.0,
                    'ENABLE' : False
                    }
                    ]]
        
        #=== Others ===
        
        USER_EXPERIMENT_COMMANDS = {'dummy': {'key': 'd', 'domain': ['running experiment']}, }
        
        
        self._create_parameters_from_locals(locals())

class AEPHVS(VisionExperimentConfig):
    '''
    Antona's Electrophisology visual stimulation
    '''
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'TestExperimentConfig'
        
        #=== paths/data handling ===
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_DATA_PATH = unit_test_runner.TEST_working_folder
        ARCHIVE_FORMAT = 'zip'
        
        #=== screen ===
        FULLSCREEN = True
        SCREEN_RESOLUTION = utils.cr([800,600])
        SCREEN_RESOLUTION = utils.cr([1024, 768])
        COORDINATE_SYSTEM='center'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 120.0
        SCREEN_MAX_FRAME_RATE = 120.0        
        SCREEN_UM_TO_PIXEL_SCALE = 1.5
        
        #=== hardware ===
        ENABLE_PARALLEL_PORT = True
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 2
        
        #=== network ===
        SERVER_IP = ''
        ENABLE_UDP = True        
  
        #=== Filterwheel ===
        
        ENABLE_FILTERWHEEL = False
        
        FILTERWHEEL_SERIAL_PORT = [[{
                                    'port' :  'COM1',
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    },
                                    {
                                    'port' :  'COM2',
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }
                                    ]]        
                                    
        FILTERWHEEL_FILTERS = [[{
                                                'ND0': 1, 
                                                'ND10': 2, 
                                                'ND20': 3, 
                                                'ND30': 4, 
                                                'ND40': 5, 
                                                'ND50': 6, 
                                                }]]
                                                
        self.FILTERWHEEL1_IR = (0, 1)
        self.FILTERWHEEL1_ND50 = (0, 2)
        self.FILTERWHEEL1_ND0 = (0, 3)
        self.FILTER_530 = (0, 4) #green 530,590
        self.FILTER_470 = (0, 5) #blue 470
        self.FILTERWHEEL1_ND0_SECONDARY = (0, 6)
        
        self.FILTERWHEEL2_ND10 = (1, 1)
        self.FILTERWHEEL2_ND20 = (1, 2)
        self.FILTERWHEEL2_ND30 = (1, 3)
        self.FILTERWHEEL2_ND40 = (1, 4)
        self.FILTERWHEEL2_ND_INFINITY = (1, 5)
        self.FILTERWHEEL2_ND0 = (1, 6)
                                                
        #=== LED controller ===
        DAQ_CONFIG = [[
                    {
                    'ANALOG_CONFIG' : 'ao', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 1.0,
                    'AO_SAMPLE_RATE' : 10000,
                    'AO_CHANNEL' : 'Dev1/ao0:1',
                    'AI_CHANNEL' : 'Dev1/ai9:0',
                    'MAX_VOLTAGE' : 10.0,
                    'MIN_VOLTAGE' : 0.0,
                    'DURATION_OF_AI_READ' : 1.0,
                    'ENABLE' : True
                    }
                    ]]
        
        #=== Others ===
        
        USER_EXPERIMENT_COMMANDS = {'dummy': {'key': 'd', 'domain': ['running experiment']}, }        
        
        self._create_parameters_from_locals(locals())
