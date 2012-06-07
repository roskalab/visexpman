import os
import os.path
import serial
import numpy
import time

from visexpman.engine.generic.parameter import Parameter
from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig
from visexpman.engine.generic import utils
from visexpman.engine.generic import file

class PPRLConfig(VisionExperimentConfig):
    
    def _set_user_parameters(self):
        EXPERIMENT = 'MultipleDotTest'
        EXPERIMENT_CONFIG = 'DotsExperimentConfig'
        LOG_PATH = '/var/log/'
        EXPERIMENT_DATA_PATH = '../../../presentinator/data'
        CAPTURE_PATH = '../../../presentinator/data/capture'
        ENABLE_PARALLEL_PORT = False
#        STIMULATION_FOLDER_PATH = 'stimulus_examples'        
        FULLSCREEN = True
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.rc([600,   800])
#        SCREEN_RESOLUTION = [1680,   1050]
        ENABLE_FRAME_CAPTURE = False
        
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        FRAME_WAIT_FACTOR = 0

        GAMMA = 1.0
        ENABLE_FILTERWHEEL = False
        
        #multiple stimulus control
        STIMULUS_LIST = ['MyStimulus1',  'MyStimulus2']
        self.STIMULUS_LIST_p = Parameter(STIMULUS_LIST )
        
        SEGMENT_DURATION = 2
        ACTION_BETWEEN_STIMULUS = 'off'

        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        
        ORIGO, HORIZONTAL_AXIS_POSITIVE_DIRECTION, VERTICAL_AXIS_POSITIVE_DIRECTION = utils.coordinate_system('corner')
            
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        
        self._set_parameters_from_locals(locals())
        
class K247AWindowsConfig(VisionExperimentConfig):
    def _set_user_parameters(self):        
        RUN_MODE = 'single experiment'
        EXPERIMENT_CONFIG = 'MovingDotTestConfig'
        LOG_PATH = 'c:\\temp\\'
        BASE_PATH='c:\\Data\\stimuli\\'
        EXPERIMENT_DATA_PATH = os.path.join(BASE_PATH,'archive')#'../../../presentinator/data' 
        CAPTURE_PATH = os.path.join(BASE_PATH,'capture')#'../../../presentinator/data/capture'
        ENABLE_PARALLEL_PORT = False
        ENABLE_UDP = False
#        STIMULATION_FOLDER_PATH = 'stimulus_examples'        
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.rc([768,   1024])
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [36.0, [0, 100]] #cm
        SCREEN_PIXEL_WIDTH = [0.0425, [0, 0.5]] # mm
        FRAME_WAIT_FACTOR = 0 
        GAMMA = 1.0
        ENABLE_FILTERWHEEL = False
        
        #self.STIMULUS_LIST_p = Parameter(STIMULUS_LIST ) # ez hogy kerulhet ide?  mar ertem de ez nagy kavaras!
        # nem ilyen formaban kellett volna?:STATES = [['idle',  'stimulation'],  None]
        
        SEGMENT_DURATION = 2
        MAXIMUM_RECORDING_DURATION = [270, [0, 10000]] #seconds

        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        COORDINATE_SYSTEM='ulcorner'
            
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        VisionExperimentConfig._create_parameters_from_locals(self, locals())
        #VisionExperimentConfig._set_parameters_from_locals(self, locals())

class RC3DWindowsConfig(VisionExperimentConfig):
    #NOT TESTED
    def _set_user_parameters(self):        
        ENABLE_PARALLEL_PORT = True        
        FULLSCREEN = True
        SCREEN_RESOLUTION = [1600,  1200]
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 2        
        EXPERIMENT_DATA_PATH = self.BASE_PATH
        LOG_PATH = self.BASE_PATH
        #test steps:
        # 1. frame rate 60
        # 2. parallel port OK
        # 3 network control
        # 4 stimulus types
        
        self._set_parameters_from_locals(locals())

class MBP(VisionExperimentConfig):
    def _set_user_parameters(self):        
        
        EXPERIMENT_CONFIG = 'MovingDotConfig'
        PLATFORM = 'standalone'

        #### Paths ####
        LOG_PATH = '/Users/hd/Documents/DataBase'
        #LOG_PATH = 'v:\\debug\\data\\log'
        EXPERIMENT_LOG_PATH = LOG_PATH
        BASE_PATH='/Users/hd/Documents/DataBase'
        #BASE_PATH='v:\\debug\\data'
        ARCHIVE_PATH = os.path.join(BASE_PATH,'archive')
        MES_DATA_FOLDER = ARCHIVE_PATH
        CAPTURE_PATH = os.path.join(BASE_PATH,'capture')
        
        EXPERIMENT_DATA_PATH = os.path.join(BASE_PATH,'archive')#'../../../presentinator/data' 
        
        FULLSCREEN = False
        ENABLE_PARALLEL_PORT = False
        ENABLE_UDP = False
        SCREEN_RESOLUTION = utils.rc([600,   800])
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [280.0, [0, 300]] #mm
        SCREEN_PIXEL_WIDTH = [0.56, [0, 0.99]] # mm, must be measured by hand (depends on how far the projector is from the screen)
        degrees = 10.0*1/300 # 300 um on the retina corresponds to 10 visual degrees.  
        SCREEN_UM_TO_PIXEL_SCALE = numpy.tan(numpy.pi/180*degrees)*SCREEN_DISTANCE_FROM_MOUSE_EYE[0]/SCREEN_PIXEL_WIDTH[0] #1 um on the retina is this many pixels on the screen
        MAXIMUM_RECORDING_DURATION = [87, [0, 10000]] #seconds #SEGMENT_DURATION nincs tobbe
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        COORDINATE_SYSTEM='ulcorner'
            
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        #=== Network ===
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = True
        #=== stage ===
        motor_serial_port = {
                                    'port' :  'COM1',
                                    'baudrate' : 19200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                    
                                    }
                                    
        STAGE = [{'SERIAL_PORT' : motor_serial_port,
                 'enable': False,
                 'SPEED': 800,
                 'ACCELERATION' : 200,
                 'MOVE_TIMEOUT' : 45.0,
                 'UM_PER_USTEP' : (1.0/51.0)*numpy.ones(3, dtype = numpy.float)
                 }]
        #=== DAQ ===
        SYNC_CHANNEL_INDEX = 1
        DAQ_CONFIG = [
                    {
                    'ANALOG_CONFIG' : 'ai', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 3.0,
                    'SAMPLE_RATE' : 5000,
                    'AI_CHANNEL' : 'Dev1/ai0:2',
                    'MAX_VOLTAGE' : 10.0,
                    'MIN_VOLTAGE' : -10.0,
                    'DURATION_OF_AI_READ' : 2*MAXIMUM_RECORDING_DURATION[0],
                    'ENABLE' : False
                    },
                    {
                    'ANALOG_CONFIG' : 'ao', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 3.0,
                    'SAMPLE_RATE' : 1000,
                    'AO_CHANNEL' : 'Dev1/ao0',
                    'MAX_VOLTAGE' : 10.0,
                    'MIN_VOLTAGE' : 0.0,
                    
                    'ENABLE' : False
                    }
                    ]
        
        #=== Others ===
        
        USER_EXPERIMENT_COMMANDS = {'stop': {'key': 's', 'domain': ['running experiment']}, 
                                    'next': {'key': 'n', 'domain': ['running experiment']},}
        
        
        VisionExperimentConfig._create_parameters_from_locals(self, locals())
        #VisionExperimentConfig._set_parameters_from_locals(self, locals())
        
class DebugOnLaptop(VisionExperimentConfig):
    '''
    Windows development machine
    '''
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'GratingConfig'
        EXPERIMENT_CONFIG = 'ShortMovingDotConfig'
#        EXPERIMENT_CONFIG = 'Dummy'
        #=== paths/data handling ===
        use_drive = 'v'
        if os.name == 'nt':
            if use_drive == 'g':
                root_folder = 'g:\\User\\Zoltan'
            elif use_drive =='v':
                root_folder = 'V:\\'
            elif use_drive =='c':
                root_folder = 'c:\\_del'
        else:
            root_folder = '/home/zoltan/visexp/' 
        drive_data_folder = os.path.join(root_folder, 'debug', 'data')
        LOG_PATH = os.path.join(drive_data_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = drive_data_folder
        if use_drive == 'g':
            MES_DATA_FOLDER = 'g:\\User\\Zoltan\\data'
        elif use_drive =='v':
            MES_DATA_FOLDER = 'V:\\debug\\data'
        self.CONTEXT_NAME = 'gui_dev.hdf5'
        CONTEXT_PATH = os.path.join(root_folder, 'context')
        CAPTURE_PATH = os.path.join(drive_data_folder, 'capture')
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        #Create folders that does not exists
        for folder in [LOG_PATH, EXPERIMENT_DATA_PATH, EXPERIMENT_LOG_PATH, MES_DATA_FOLDER, CONTEXT_PATH, CAPTURE_PATH]:
            file.mkdir_notexists(folder)
        
        #=== screen ===
        FULLSCREEN = not True
        SCREEN_RESOLUTION = utils.cr([800, 600])
        COORDINATE_SYSTEM='ulcorner'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0        
        
        #=== experiment specific ===
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [280.0, [0, 300]] #mm
        SCREEN_PIXEL_WIDTH = [0.56, [0, 0.99]] # mm, must be measured by hand (depends on how far the projector is from the screen)
        degrees = 10.0*1/300 # 300 um on the retina corresponds to 10 visual degrees.  
        SCREEN_UM_TO_PIXEL_SCALE = numpy.tan(numpy.pi/180*degrees)*SCREEN_DISTANCE_FROM_MOUSE_EYE[0]/SCREEN_PIXEL_WIDTH[0] #1 um on the retina is this many pixels on the screen        
        MAXIMUM_RECORDING_DURATION = [100, [0, 10000]] #100
        MES_TIMEOUT = 10.0
        PLATFORM = 'standalone'
#        PLATFORM = 'mes'
        
        #=== Network ===
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = True
        #=== hardware ===
        ENABLE_PARALLEL_PORT = False
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        FRAME_TRIGGER_PULSE_WIDTH = 1e-3
        
        #=== stage ===
        motor_serial_port = {
                                    'port' :  'COM1',
                                    'baudrate' : 19200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                    
                                    }
                                    
        STAGE = [{'SERIAL_PORT' : motor_serial_port,
                 'ENABLE': False,
                 'SPEED': 800,
                 'ACCELERATION' : 200,
                 'MOVE_TIMEOUT' : 45.0,
                 'UM_PER_USTEP' : (1.0/51.0)*numpy.ones(3, dtype = numpy.float)
                 }]
                 
                                                
        #=== DAQ ===
        SYNC_CHANNEL_INDEX = 1
        DAQ_CONFIG = [
                    {
                    'ANALOG_CONFIG' : 'ai', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 3.0,
                    'SAMPLE_RATE' : 5000,
                    'AI_CHANNEL' : 'Dev1/ai0:2',
                    'MAX_VOLTAGE' : 10.0,
                    'MIN_VOLTAGE' : -10.0,
                    'DURATION_OF_AI_READ' : 2*MAXIMUM_RECORDING_DURATION[0],
                    'ENABLE' : False
                    },
                    {
                    'ANALOG_CONFIG' : 'ao', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 3.0,
                    'SAMPLE_RATE' : 1000,
                    'AO_CHANNEL' : 'Dev1/ao0',
                    'MAX_VOLTAGE' : 10.0,
                    'MIN_VOLTAGE' : 0.0,
                    'ENABLE' : False
                    }
                    ]
        
        #=== Others ===
        
        USER_EXPERIMENT_COMMANDS = {'stop': {'key': 's', 'domain': ['running experiment']}, 
                                    'next': {'key': 'n', 'domain': ['running experiment']},}
        
        self._create_parameters_from_locals(locals())
        
class Debug(VisionExperimentConfig):
    '''
    Windows development machine
    '''
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'GratingConfig'
        EXPERIMENT_CONFIG = 'PixelSizeCalibrationConfig'
        EXPERIMENT_CONFIG = 'LedStimulationConfig'
        EXPERIMENT_CONFIG = 'MovingDotConfig'
        EXPERIMENT_CONFIG = 'Dummy'
#        EXPERIMENT_CONFIG = 'ShortMovingDotConfig'
        PLATFORM = 'standalone'
        PLATFORM = 'mes'
        PARSE_PERIOD = 2.0
        CELL_MERGE_DISTANCE = 3.0
        ENABLE_FRAGMENT_CHECK = True
        ENABLE_MESEXTRACTOR = True
        #MES scanning config
        XZ_SCAN_CONFIG = {'LINE_LENGTH':1.0, 'Z_PIXEL_SIZE' : 33.0, 'Z_RESOLUTION':3, 'Z_RANGE':80.0}
        #=== paths/data handling ===
        use_drive = 'v'
        if os.name == 'nt':
            if use_drive == 'g':
                root_folder = 'g:\\User\\Zoltan'
            elif use_drive =='v':
                root_folder = 'V:\\'
            elif use_drive =='r':
                root_folder = 'R:\\'
        else:
            if use_drive =='v':
                root_folder = '/mnt/datafast/'
            elif use_drive =='r':
                root_folder = '/mnt/rzws/'
                    
        drive_data_folder = os.path.join(root_folder, 'debug', 'data')
        LOG_PATH = os.path.join(drive_data_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = drive_data_folder
        if use_drive == 'g':
            MES_DATA_FOLDER = 'g:\\User\\Zoltan\\data'
        elif use_drive =='v':
            MES_DATA_FOLDER = 'V:\\debug\\data'
        elif use_drive =='r':
            MES_DATA_FOLDER = 'R:\\debug\\data'
        self.CONTEXT_NAME = 'gui_dev.hdf5'
        CONTEXT_PATH = os.path.join(root_folder, 'context')
        CAPTURE_PATH = os.path.join(drive_data_folder, 'capture')
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        
        #=== screen ===
        FULLSCREEN = not True
        SCREEN_RESOLUTION = utils.cr([800, 600])
        COORDINATE_SYSTEM='ulcorner'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        
        #=== experiment specific ===
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [280.0, [0, 300]] #mm
        SCREEN_PIXEL_WIDTH = [0.56, [0, 0.99]] # mm, must be measured by hand (depends on how far the projector is from the screen)
        degrees = 10.0*1/300 # 300 um on the retina corresponds to 10 visual degrees.  
        SCREEN_UM_TO_PIXEL_SCALE = numpy.tan(numpy.pi/180*degrees)*SCREEN_DISTANCE_FROM_MOUSE_EYE[0]/SCREEN_PIXEL_WIDTH[0] #1 um on the retina is this many pixels on the screen
        MAXIMUM_RECORDING_DURATION = [900.0, [0, 10000]] #100
        MES_TIMEOUT = 15.0
        
        #=== Network ===
        ENABLE_UDP = False
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = '172.27.27.221'#'172.27.25.220' .1: production
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = True
        self.COMMAND_RELAY_SERVER['ENABLE'] = True
        #=== hardware ===
        ENABLE_PARALLEL_PORT = (self.OS == 'win')
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        FRAME_TRIGGER_PULSE_WIDTH = 1e-3
        
        #=== stage ===
        motor_serial_port = {
                                    'port' :  'COM1',
                                    'baudrate' : 19200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                    
                                    }
                                    
        STAGE = [{'SERIAL_PORT' : motor_serial_port,
                 'ENABLE': (self.OS == 'win'),
                 'SPEED': 2000,
                 'ACCELERATION' : 1000,
                 'MOVE_TIMEOUT' : 45.0,
                 'UM_PER_USTEP' : numpy.ones(3, dtype = numpy.float)*(1.0/51.0)
                 }]

        #=== DAQ ===
        SYNC_CHANNEL_INDEX = 1
        DAQ_CONFIG = [
                    {
                    'ANALOG_CONFIG' : 'ai', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 3.0,
                    'SAMPLE_RATE' : 5000,
                    'AI_CHANNEL' : 'Dev1/ai0:2',
                    'MAX_VOLTAGE' : 10.0,
                    'MIN_VOLTAGE' : -10.0,
                    'DURATION_OF_AI_READ' : 2*MAXIMUM_RECORDING_DURATION[0],
                    'ENABLE' : (self.OS == 'win')
                    },
                    {
                    'ANALOG_CONFIG' : 'ao', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 3.0,
                    'SAMPLE_RATE' : 1000,
                    'AO_CHANNEL' : 'Dev1/ao0',
                    'MAX_VOLTAGE' : 10.0,
                    'MIN_VOLTAGE' : 0.0,
                    
                    'ENABLE' : (self.OS == 'win')
                    }
                    ]
        
        #=== Others ===
        USER_EXPERIMENT_COMMANDS = {'stop': {'key': 's', 'domain': ['running experiment']}, 
                                    'next': {'key': 'n', 'domain': ['running experiment']},}
                                    
        MAX_REALIGNMENT_OFFSET = 100.0
        ACCEPTABLE_REALIGNMENT_OFFSET = 5.0
        REALIGNMENT_XY_THRESHOLD = 2.0
        REALIGNMENT_Z_THRESHOLD = 1.0
        
        self.ROI = {}
        self.ROI['process'] = 'all'
        self.ROI['overwrite'] = True
        self.ROI['rawdata_filter']= {'width':13, 
            'spatial_width':1,
            'ncpus':16, 
            'thr':2.5,
            'separation_width':1, 
            'spatial_connectivity':1, 
            'transfermode': 'file'
                                     }

        self._create_parameters_from_locals(locals())
        
class RcMicroscopeSetup(VisionExperimentConfig):
    '''
    Visual stimulation machine of 3D microscope setup
    '''
    def _set_user_parameters(self):
        GUI_REFRESH_PERIOD = 5
        ENABLE_MESEXTRACTOR = True
        ENABLE_CELL_DETECTION = True
        EXPERIMENT_CONFIG = 'MovingDotConfig'
        
        MES_TIMEOUT = 15.0
        PARSE_PERIOD = 2.0
        CELL_MERGE_DISTANCE = 3.0
        #MES scanning config
        XZ_SCAN_CONFIG = {'LINE_LENGTH':20.0, 'Z_PIXEL_SIZE' : 33.0, 'Z_RESOLUTION':3, 'Z_RANGE':80.0}
        ENABLE_ZIGZAG_CORRECTION = True
        #=== paths/data handling ===
        if os.name == 'nt':            
            v_drive_folder = 'V:\\'
        else:            
            v_drive_folder = '/mnt/datafast'
        v_drive_data_folder = os.path.join(v_drive_folder,  'experiment_data')
        LOG_PATH = os.path.join(v_drive_data_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = v_drive_data_folder
        MES_DATA_FOLDER = 'V:\\experiment_data'
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        self.CONTEXT_NAME = 'gui.hdf5'
        CONTEXT_PATH = os.path.join(v_drive_folder, 'context')

        #=== screen ===
        FULLSCREEN = True
        SCREEN_RESOLUTION = utils.cr([800, 600])
        COORDINATE_SYSTEM='ulcorner'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        #=== experiment specific ===
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [280.0, [0, 300]] #mm
        SCREEN_PIXEL_WIDTH = [0.56, [0, 0.99]] # mm, must be measured by hand (depends on how far the projector is from the screen)
        degrees = 10.0*1/300 # 300 um on the retina corresponds to 10 visual degrees.  
        SCREEN_UM_TO_PIXEL_SCALE = numpy.tan(numpy.pi/180*degrees)*SCREEN_DISTANCE_FROM_MOUSE_EYE[0]/SCREEN_PIXEL_WIDTH[0] #1 um on the retina is this many pixels on the screen        
        MAXIMUM_RECORDING_DURATION = [900, [0, 10000]] #100
        PLATFORM = 'mes'
        #=== Network ===
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = '172.27.27.221'
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = True
        self.COMMAND_RELAY_SERVER['ENABLE'] = True
        #=== hardware ===
        ENABLE_PARALLEL_PORT = True
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        FRAME_TRIGGER_PULSE_WIDTH = 1e-3
        #=== stage ===
        motor_serial_port = {
                                    'port' :  'COM1',
                                    'baudrate' : 19200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }
        STAGE = [{'SERIAL_PORT' : motor_serial_port,
                 'ENABLE': True,
                 'SPEED': 2000,
                 'ACCELERATION' : 1000,
                 'MOVE_TIMEOUT' : 45.0,
                 'UM_PER_USTEP' : (1.0/51.0)*numpy.ones(3, dtype = numpy.float)
                 }]
        #=== DAQ ===
        SYNC_CHANNEL_INDEX = 1
        DAQ_CONFIG = [
                    {
                    'ANALOG_CONFIG' : 'ai', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 3.0,
                    'SAMPLE_RATE' : 5000,
                    'AI_CHANNEL' : 'Dev1/ai0:2',
                    'MAX_VOLTAGE' : 10.0,
                    'MIN_VOLTAGE' : -10.0,
                    'DURATION_OF_AI_READ' : 2*MAXIMUM_RECORDING_DURATION[0],
                    'ENABLE' : True
                    },
                    {
                    'ANALOG_CONFIG' : 'ao', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 3.0,
                    'SAMPLE_RATE' : 1000,
                    'AO_CHANNEL' : 'Dev1/ao0',
                    'MAX_VOLTAGE' : 10.0,
                    'MIN_VOLTAGE' : 0.0,
                    'ENABLE' : True
                    }
                    ]
        #=== Others ===
        USER_EXPERIMENT_COMMANDS = {'stop': {'key': 's', 'domain': ['running experiment']}, 
                                    'next': {'key': 'n', 'domain': ['running experiment']},}

        MAX_REALIGNMENT_OFFSET = 500.0
        ACCEPTABLE_REALIGNMENT_OFFSET = 5.0
        REALIGNMENT_XY_THRESHOLD = 2.0
        REALIGNMENT_Z_THRESHOLD = 1.0
        #MES scanning config
        
        self.ROI = {}
        self.ROI['process'] = 'all'
        self.ROI['overwrite'] = True
        self.ROI['rawdata_filter']= {'width':13, 
            'spatial_width':1,
            'ncpus':16, 
            'thr':2.5,
            'separation_width':1, 
            'spatial_connectivity':1, 
            'transfermode': 'file'
                                     }
        
        self._create_parameters_from_locals(locals())        
        
class VS3DUS(RcMicroscopeSetup):
    pass

if __name__ == "__main__":
    pass
    
