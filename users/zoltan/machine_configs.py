import time
import numpy
import serial
import visexpman
import os.path
import os
import tempfile

from visexpman.engine.vision_experiment import configuration
from visexpman.engine.generic import configuration as config
from visexpman.engine.generic import utils
from visexpman.engine.generic import file
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.hardware_interface import daq_instrument
from visexpman.users.zoltan.test import unit_test_runner
from visexpman.users.daniel import grating

GEOMETRY_PRECISION = 3

class GraphicsTestConfig(config.Config):
    def _create_application_parameters(self):
        FPS_RANGE = (1.0,  200.0) 
        COLOR_RANGE = [[0.0, 0.0,  0.0],  [1.0, 1.0,  1.0]]
        
        SCREEN_RESOLUTION = utils.rc([768, 1024])        
        FULLSCREEN = False
        SCREEN_EXPECTED_FRAME_RATE = [60.0,  FPS_RANGE]
        SCREEN_MAX_FRAME_RATE = [60.0,  FPS_RANGE]        
        BACKGROUND_COLOR = [[0.0, 0.0,  0.0],  COLOR_RANGE]
        FRAME_WAIT_FACTOR = [1.0,  [0.0,  1.0]]
        FLIP_EXECUTION_TIME = [0*1e-3, [0.0, 1.0]]
        COORDINATE_SYSTEM = 'center' #ulcorner
#        COORDINATE_SYSTEM = 'ulcorner'
        CAPTURE_PATH = '/media/Common/visexpman_data'
        SIMULATION_DATA_PATH = '/media/Common/visexpman_data'
        self.N_CORES = 4
        ENABLE_FRAME_CAPTURE = False
        self._create_parameters_from_locals(locals())
        
    def _calculate_parameters(self):
        self.ORIGO, self.HORIZONTAL_AXIS_POSITIVE_DIRECTION, self.VERTICAL_AXIS_POSITIVE_DIRECTION= utils.coordinate_system(self.COORDINATE_SYSTEM, self.SCREEN_RESOLUTION)

class Stimulus2video(configuration.VisionExperimentConfig):
    '''
    Converting stimulus to video file
    '''
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'MovingGratingConfig'
        PLATFORM = 'standalone'
        #=== paths/data handling ===
        use_drive = 'tmp'
        if use_drive =='v':
            root_folder = 'V:\\'
        elif use_drive =='c':
            root_folder = 'c:\\visexp'
        elif use_drive == 'tmp':
            root_folder = tempfile.gettempdir()
        else:
            root_folder = '/home/zoltan/visexp/' 
        drive_data_folder = os.path.join(root_folder, 'experiment_data')
        LOG_PATH = os.path.join(drive_data_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = drive_data_folder
        VIDEO_PATH = drive_data_folder
        if use_drive == 'g':
            MES_DATA_FOLDER = 'g:\\User\\Zoltan\\data'
        elif use_drive =='v':
            MES_DATA_FOLDER = 'V:\\debug\\data'
        elif use_drive =='c':
            MES_DATA_FOLDER = 'c:\\visexp\\debug\\data'
        elif use_drive == 'tmp':
            MES_DATA_FOLDER = drive_data_folder
            VIDEO_PATH = 'c:\\visexp'
        self.CONTEXT_NAME = 'gui_dev.hdf5'
        CONTEXT_PATH = os.path.join(root_folder, 'context')
        CAPTURE_PATH = os.path.join(drive_data_folder, 'capture')
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        #Create folders that does not exists
        for folder in [drive_data_folder, LOG_PATH, EXPERIMENT_DATA_PATH, EXPERIMENT_LOG_PATH, MES_DATA_FOLDER, CONTEXT_PATH, CAPTURE_PATH]:
            file.mkdir_notexists(folder)
        
        #=== screen ===
        FULLSCREEN = not True
        SCREEN_RESOLUTION = utils.cr([800, 600])
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
        
        #=== Network ===
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = True
        #=== hardware ===
        ENABLE_PARALLEL_PORT = False
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        FRAME_TRIGGER_PULSE_WIDTH = 1e-3
        
        self._create_parameters_from_locals(locals())

class SwDebugConfig(configuration.VisionExperimentConfig):
    '''
    Converting stimulus to video file
    '''
    def _set_user_parameters(self):        
#        EXPERIMENT_CONFIG = 'MovingGratingConfig'
        PLATFORM = 'standalone'
        root_folder = '/mnt/datafast/debug'
        if not os.path.exists(root_folder):
            root_folder = '/mnt/rznb'
        drive_data_folder = os.path.join(root_folder, 'experiment_data')
        LOG_PATH = os.path.join(drive_data_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = drive_data_folder
        self.CONTEXT_NAME = 'gui_dev.hdf5'
        CONTEXT_PATH = os.path.join(root_folder, 'context')
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        #Create folders that does not exists
        for folder in [drive_data_folder, LOG_PATH, EXPERIMENT_DATA_PATH, EXPERIMENT_LOG_PATH, CONTEXT_PATH]:
            file.mkdir_notexists(folder)
        
        #=== screen ===
        FULLSCREEN = not True
        SCREEN_RESOLUTION = utils.cr([800, 600])
        COORDINATE_SYSTEM='center'
        ENABLE_FRAME_CAPTURE =  False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0        
        
        #=== Network ===
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = False
        #=== hardware ===
        ENABLE_PARALLEL_PORT = False
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        FRAME_TRIGGER_PULSE_WIDTH = 1e-3
        
        self._create_parameters_from_locals(locals())
