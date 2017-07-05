import os,sys
import os.path
import numpy,copy,hdf5io
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment.configuration import AoCorticalCaImagingConfig

class AOSetup(AoCorticalCaImagingConfig):
    def _set_user_parameters(self):
        AoCorticalCaImagingConfig._set_user_parameters(self)
        # Files
        self.EXPERIMENT_FILE_FORMAT = 'hdf5'
        self.LOG_PATH = 'v:\\log_ao'
        self.EXPERIMENT_DATA_PATH = 'v:\\experiment_data_ao'
        self.CONTEXT_PATH='v:\\context_ao'
        #Stimulus screen
        self.SCREEN_DISTANCE_FROM_MOUSE_EYE = 190.0
        self.SCREEN_RESOLUTION = utils.cr([1280, 720])
        self.SCREEN_PIXEL_WIDTH = 477.0/self.SCREEN_RESOLUTION ['col']
        self.SCREEN_EXPECTED_FRAME_RATE = 60.0
        self.SCREEN_MAX_FRAME_RATE = 60.0
        self.IMAGE_DIRECTLY_PROJECTED_ON_RETINA=False
        self.FULLSCREEN=True
        self.COORDINATE_SYSTEM='center'
        self.ENABLE_FRAME_CAPTURE = False
        self.GUI['SIZE'] =  utils.cr((1024,768)) 
        #Network
        stim_computer_ip = '172.27.26.46'
        self.CONNECTIONS['stim']['ip']['stim'] = stim_computer_ip
        self.CONNECTIONS['stim']['ip']['main_ui'] = stim_computer_ip
        #Command relay server is used for conencting to MES because no zmq is supported and mes works only in client mode
        self.COMMAND_RELAY_SERVER={}
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = stim_computer_ip
        self.COMMAND_RELAY_SERVER['TIMEOUT'] = 5
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = True
        self.COMMAND_RELAY_SERVER['ENABLE'] = True
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP_FROM_TABLE'] = True
        self.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'] = \
            {
            'STIM_MES'  : {'STIM' : {'IP': stim_computer_ip, 'LOCAL_IP': '', 'PORT': 10002}, 'MES' : {'IP': '', 'LOCAL_IP': '', 'PORT': 10003}}, 
            }
        self.COMMAND_RELAY_SERVER['SERVER_IP'] = {\
                     'GUI_MES': ['',''],
                     'STIM_MES': ['',''],
                     'GUI_STIM': ['', stim_computer_ip],
                     'GUI_ANALYSIS'  : ['', stim_computer_ip],
        }   
        #Sync signal
        self.SYNC_RECORDER_CHANNELS='Dev1/ai0:3' if 'cameron' not in sys.argv else 'Dev1/ai0:4' #0: ao, 1: frame sync, 2: block, 3: ao
        self.SYNC_RECORDER_SAMPLE_RATE=40000#mes sync pulses are very short
        self.SYNC_RECORDING_BUFFER_TIME=5.0
        self.TIMG_SYNC_INDEX=3
        self.TSTIM_SYNC_INDEX=2
        self.DIGITAL_IO_PORT='COM4'
        self.BLOCK_TRIGGER_PIN = 1
        self.FRAME_TRIGGER_PIN = 0
        self.MES_RECORD_OVERHEAD=5
        self.MES_RECORD_START_WAITTIME=5
        self.MES_TIMEOUT=5
        self.SYNC_RECORD_OVERHEAD=10
        gammafn=os.path.join(self.CONTEXT_PATH, 'gamma_ao_cortical_monitor.hdf5')
        if 0:#TMP TEST
            self.GAMMA_CORRECTION = copy.deepcopy(hdf5io.read_item(gammafn, 'gamma_correction'))
        if '--nofullscreen' in sys.argv:
            self.FULLSCREEN=False
        
        
class CameronAoSetup(AOSetup):
    def _set_user_parameters(self):
        AOSetup._set_user_parameters(self)
        SCREEN_UM_TO_PIXEL_SCALE=1.0
        IMAGE_DIRECTLY_PROJECTED_ON_RETINA=True
        SCREEN_RESOLUTION = utils.cr([1280, 800])
        COORDINATE_SYSTEM='center'
        TRIGGER_MES=True
        self.MES_RECORD_OVERHEAD=10#This is responsible for the recording overhead. Reduce if don't want to wait too long after recording
        self.MES_RECORD_OVERHEAD2=10#This is responsible for the recording overhead. Reduce if don't want to wait too long after recording
        self.SCREEN_EXPECTED_FRAME_RATE = 119.0
        self._create_parameters_from_locals(locals())
        
        
class CameronBpSetup(AoCorticalCaImagingConfig):
    def _set_user_parameters(self):
        AoCorticalCaImagingConfig._set_user_parameters(self)
        self.PLATFORM='standalone'
        self.KEYS['start stimulus'] = 'e'
        # Files
        self.EXPERIMENT_FILE_FORMAT = 'hdf5'
        self.LOG_PATH = 'd:\\log'
        self.EXPERIMENT_DATA_PATH = 'd:\\experiment_data'
        self.CONTEXT_PATH='d:\\context'
        #Stimulus screen
        self.SCREEN_RESOLUTION = utils.cr([1024, 768])
        self.SCREEN_MAX_FRAME_RATE = 60.0
        self.FULLSCREEN=not True
        self.COORDINATE_SYSTEM='center'
        self.ENABLE_FRAME_CAPTURE = False
        stim_computer_ip = '127.0.0.1'
        self.COMMAND_RELAY_SERVER={}
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = stim_computer_ip
        self.COMMAND_RELAY_SERVER['TIMEOUT'] = 5
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = True
        self.COMMAND_RELAY_SERVER['ENABLE'] = True
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP_FROM_TABLE'] = True
        self.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'] = \
            {
            'STIM_MES'  : {'STIM' : {'IP': stim_computer_ip, 'LOCAL_IP': '', 'PORT': 10002}, 'MES' : {'IP': '', 'LOCAL_IP': '', 'PORT': 10003}}, 
            }
        self.COMMAND_RELAY_SERVER['SERVER_IP'] = {\
                     'GUI_MES': ['',''],
                     'STIM_MES': ['',''],
                     'GUI_STIM': ['', stim_computer_ip],
                     'GUI_ANALYSIS'  : ['', stim_computer_ip],
        }   
        self.DIGITAL_IO_PORT='COM1'
        self.BLOCK_TRIGGER_PIN = 1
        self.FRAME_TRIGGER_PIN = 0
        
#        self.MES_RECORD_OVERHEAD=12
#        self.MES_RECORD_START_WAITTIME=6
#        self.SYNC_RECORD_OVERHEAD=5
        SCREEN_UM_TO_PIXEL_SCALE = 1
        #self.GAMMA_CORRECTION = copy.deepcopy(hdf5io.read_item(os.path.join(self.CONTEXT_PATH, 'gamma_ao_cortical_monitor.hdf5'), 'gamma_correction'))

class CameronDev(CameronAoSetup):
    def _set_user_parameters(self):
        CameronAoSetup._set_user_parameters(self)
        self.SCREEN_RESOLUTION = utils.cr([800,600])
        self.FULLSCREEN=False
        self.SCREEN_EXPECTED_FRAME_RATE = 59
        self.MES_RECORD_OVERHEAD=5
