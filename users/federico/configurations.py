import os
import os.path
import serial
import numpy
import time

from visexpman.engine.generic.parameter import Parameter
from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig, AoCorticalCaImagingConfig
from visexpman.engine.generic import utils
from visexpman.engine.generic import file

class ProtocolDevelopment(VisionExperimentConfig):
    '''
    Windows development machine
    '''
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'TestConfig'

        root_folder = 'd:\\data'
        if not os.path.exists(root_folder):
            root_folder = '/mnt/datafast/debug'
        drive_data_folder = root_folder
        LOG_PATH = drive_data_folder
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = drive_data_folder
        self.CONTEXT_NAME = 'gui_dev.hdf5'
        CONTEXT_PATH = os.path.join(root_folder)
        EXPERIMENT_FILE_FORMAT = 'mat'
        #Create folders that does not exists
        for folder in [LOG_PATH, EXPERIMENT_DATA_PATH, EXPERIMENT_LOG_PATH, CONTEXT_PATH]:
            file.mkdir_notexists(folder)
        
        #=== screen ===
        FULLSCREEN = not False
        SCREEN_RESOLUTION = utils.cr([1280, 800])
        COORDINATE_SYSTEM='ulcorner'
        ENABLE_FRAME_CAPTURE =  False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0        
        
        #=== experiment specific ===
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [280.0, [0, 300]] #mm
        SCREEN_PIXEL_WIDTH = [0.56, [0, 0.99]] # mm, must be measured by hand (depends on how far the projector is from the screen)
        degrees = 10.0*1/300 # 300 um on the retina corresponds to 10 visual degrees.  
        SCREEN_UM_TO_PIXEL_SCALE = numpy.tan(numpy.pi/180*degrees)*SCREEN_DISTANCE_FROM_MOUSE_EYE[0]/SCREEN_PIXEL_WIDTH[0] #1 um on the retina is this many pixels on the screen        
        MAXIMUM_RECORDING_DURATION = [1000, [0, 10000]] #100
        MES_TIMEOUT = 10.0
        PLATFORM = 'standalone'
#        PLATFORM = 'mes'
        
        #=== Network ===
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = False
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
        STIM_SYNC_CHANNEL_INDEX = 1
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
        
class AoMicroscopeSetup(AoCorticalCaImagingConfig):
    '''
    Visual stimulation machine of 3D microscope setup
    '''
    def _set_user_parameters(self, check_path = True):
        GUI_REFRESH_PERIOD = 5.0
        ENABLE_MESEXTRACTOR = True
        ENABLE_CELL_DETECTION = True
        
        MES_TIMEOUT = 20.0
        CELL_MERGE_DISTANCE = 3.0
        ROI_PATTERN_SIZE = 4
        ROI_PATTERN_RADIUS = 3
        #MES scanning config
        XZ_SCAN_CONFIG = {'LINE_LENGTH':15.0, 'Z_PIXEL_SIZE' : 33.0, 'Z_RESOLUTION':3.03, 'Z_RANGE':80.0}
        ENABLE_ZIGZAG_CORRECTION = True
        #=== paths/data handling ===
        if os.name == 'nt':            
            v_drive_folder = 'V:\\'
        else:            
            v_drive_folder = '/mnt/datafast'
        v_drive_data_folder = os.path.join(v_drive_folder,  'experiment_data_ao')
        LOG_PATH = os.path.join(v_drive_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = v_drive_data_folder
        MES_DATA_FOLDER = 'V:\\experiment_data_ao'
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        self.CONTEXT_NAME = 'gui_ao.hdf5'
        CONTEXT_PATH = os.path.join(v_drive_folder, 'context')
        if os.name != 'nt':
            DATABIG_PATH = '/mnt/databig/data'
            self.TAPE_PATH = '/mnt/tape/hillier/invivocortex/TwoPhoton'

        #=== screen ===
        FULLSCREEN = True
        SCREEN_RESOLUTION = utils.cr([1280, 800])
        COORDINATE_SYSTEM='ulcorner'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        #=== experiment specific ===
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [390.0, [0, 500]] #mm
        SCREEN_PIXEL_WIDTH = [0.35, [0, 0.99]] # mm, must be measured by hand (depends on how far the projector is from the screen)
        degrees = 10.0*1/300 # 300 um on the retina corresponds to 10 visual degrees.  
        SCREEN_UM_TO_PIXEL_SCALE = numpy.tan(numpy.pi/180*degrees)*SCREEN_DISTANCE_FROM_MOUSE_EYE[0]/SCREEN_PIXEL_WIDTH[0] #1 um on the retina is this many pixels on the screen
        #=== Network ===
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = '172.27.27.236'
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = True
        self.COMMAND_RELAY_SERVER['ENABLE'] = True
        #=== hardware ===
        ENABLE_PARALLEL_PORT = False
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        FRAME_TRIGGER_PULSE_WIDTH = 1e-3
        #=== stage ===
#        motor_serial_port = {
#                                    'port' :  'COM1',
#                                    'baudrate' : 19200,
#                                    'parity' : serial.PARITY_NONE,
#                                    'stopbits' : serial.STOPBITS_ONE,
#                                    'bytesize' : serial.EIGHTBITS,                                    
#                                    }
#                                    
#        goniometer_serial_port = {
#                                    'port' :  'COM5',
#                                    'baudrate' : 9600,
#                                    'parity' : serial.PARITY_NONE,
#                                    'stopbits' : serial.STOPBITS_ONE,
#                                    'bytesize' : serial.EIGHTBITS,
#                                    }
#        degree_factor = 0.9/(8*252)
#        degree_factor = 0.00045*4 #According to manufacturer
#        STAGE = [{'SERIAL_PORT' : motor_serial_port,
#                 'ENABLE': True,
#                 'SPEED': 2000,
#                 'ACCELERATION' : 1000,
#                 'MOVE_TIMEOUT' : 45.0,
#                 'UM_PER_USTEP' : (0.75/51.0)*numpy.ones(3, dtype = numpy.float)
#                 }, 
#                 {'SERIAL_PORT' : goniometer_serial_port,
#                 'ENABLE':True,
#                 'SPEED': 1000000,
#                 'ACCELERATION' : 1000000,
#                 'MOVE_TIMEOUT' : 15.0,
#                 'DEGREE_PER_USTEP' : degree_factor * numpy.ones(2, dtype = numpy.float)}]
#        #=== DAQ ===
#        STIM_SYNC_CHANNEL_INDEX = 1
#        MES_SYNC_CHANNEL_INDEX = 0
#        DAQ_CONFIG = [
#                    {
#                    'ANALOG_CONFIG' : 'ai', #'ai', 'ao', 'aio', 'undefined'
#                    'DAQ_TIMEOUT' : 3.0,
#                    'SAMPLE_RATE' : 5000,
#                    'AI_CHANNEL' : 'Dev1/ai0:3',#stim frames, ca frames, led control, intrinsic frame start/stop
#                    'MAX_VOLTAGE' : 10.0,
#                    'MIN_VOLTAGE' : -10.0,
#                    'DURATION_OF_AI_READ' : 2*self.MAXIMUM_RECORDING_DURATION,
#                    'ENABLE' : True
#                    },
#                    {
#                    'ANALOG_CONFIG' : 'ao', #'ai', 'ao', 'aio', 'undefined'
#                    'DAQ_TIMEOUT' : 3.0,
#                    'SAMPLE_RATE' : 1000,
#                    'AO_CHANNEL' : 'Dev1/ao0',
#                    'MAX_VOLTAGE' : 10.0,
#                    'MIN_VOLTAGE' : 0.0,
#                    'ENABLE' : True
#                    }
#                    ]
        #=== Others ===
        USER_EXPERIMENT_COMMANDS = {'stop': {'key': 's', 'domain': ['running experiment']}, 
                                    'next': {'key': 'n', 'domain': ['running experiment']},}
        
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
        GREEN_LABELING = ['','scaav 2/1 hsyn gcamp3', 'aav 2/1 ef1a gcamp5', 'scaav 2/1 gcamp3 only']
        
        #Intrinsic imaging:
        self.CAMERA_MAX_FRAME_RATE=8
        self._create_parameters_from_locals(locals(), check_path = check_path)
        
if __name__ == "__main__":
    pass
