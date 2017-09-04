import os
import os.path
import serial
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig

class BehavioralTester(VisionExperimentConfig):
    '''
    '''
    def _set_user_parameters(self):
        PLATFORM = 'smallapp'
        SMALLAPP = {'NAME': 'Behavioral tester',  'POLLER':'BehavioralTesterPoller'}
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
        GUI_REFRESH_PERIOD = 0.1
        if os.name == 'nt':
            comport = 'COM3'
        else:
            comport = '/dev/ttyUSB0'
        self.PHOTOINTERRUPTER_SERIAL_DIO_PORT = {'0': comport}
        self._create_parameters_from_locals(locals())
        
class IntrinsicSetup(VisionExperimentConfig):
    '''
    '''
    def _set_user_parameters(self):
        PLATFORM = 'standalone'
        if os.name == 'nt':
            root_folder = 'c:\\data'
        elif os.path.exists('/mnt/rzws/temp'):
            root_folder = '/mnt/rzws/temp'
        elif os.path.exists('/mnt/datafast/debug'):
            root_folder = '/mnt/datafast/debug'
        elif os.path.exists('/home/mouse'):
            root_folder = '/home/mouse'
        CONTEXT_PATH=root_folder
        LOG_PATH = os.path.join(root_folder, 'log')
        CAPTURE_PATH = os.path.join(root_folder, 'capture')
        for p in [CAPTURE_PATH, LOG_PATH]:
            if not os.path.exists(p):
                os.mkdir(p)
        DATA_PATH = root_folder
        EXPERIMENT_DATA_PATH = root_folder
        EXPERIMENT_LOG_PATH = LOG_PATH
#        TRIGGER_PATH = 'c:\\temp'#!!!!!!!!!!!!!!!!!!New feature
        
        #=== screen ===
        
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([1600,1200])
        COORDINATE_SYSTEM='center'
        INSERT_FLIP_DELAY = True
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
#        SCREEN_MAX_FRAME_RATE = 60.0
        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        STIM_RECORDS_ANALOG_SIGNALS = False
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        
        
        #=== hardware ===
        ENABLE_PARALLEL_PORT = False
        self._create_parameters_from_locals(locals())

class BehavioralSetup(IntrinsicSetup):
    def _set_user_parameters(self):
        IntrinsicSetup._set_user_parameters(self)
        self.FULLSCREEN = True
        self.SCREEN_SIZE = utils.cr([47.6,26.9])#cm
        self.SCREEN_RESOLUTION = utils.cr([1600/1,1200/1])
        self.SCREEN_RESOLUTION = utils.cr([1280,1024])
        self.SCREEN_RESOLUTION = utils.cr([1920,1080])
#        self.SCREEN_RESOLUTION = utils.cr([1024,768])
        
        self.SCREEN_UM_TO_PIXEL_SCALE = self.SCREEN_RESOLUTION['col']/self.SCREEN_SIZE['col']
#        self.SERIAL_DIO_PORT = '/dev/ttyUSB0'
        self.ACQUISITION_TRIGGER_PIN=1
        self.FRAME_TIMING_PIN=0

class GenVideoConf(BehavioralSetup):
    def _set_user_parameters(self):
        BehavioralSetup._set_user_parameters(self)
        self.ENABLE_FRAME_CAPTURE = True
        self.root_folder = '/mnt/rzws/temp'
        self.FULLSCREEN = False
