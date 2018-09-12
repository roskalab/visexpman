import os,sys
import numpy
import copy
import visexpA.engine.datahandlers.hdf5io as hdf5io
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment.configuration import ResonantConfig
        
class ResonantSetup(ResonantConfig):
    def _set_user_parameters(self):
        ResonantConfig._set_user_parameters(self)
        # Files
        self.EXPERIMENT_FILE_FORMAT = 'hdf5'
        root='x:\\resonant-setup'
        self.LOG_PATH = os.path.join(root,'log')
        self.EXPERIMENT_DATA_PATH = os.path.join(root,'processed')
        self.CONTEXT_PATH= os.path.join(root, 'context')
        #Stimulus screen
        self.SCREEN_DISTANCE_FROM_MOUSE_EYE = 145.0 # original at 300
        self.SCREEN_RESOLUTION = utils.cr([1280, 720])
        self.SCREEN_PIXEL_WIDTH = 540.0/self.SCREEN_RESOLUTION ['col'] # 		original at 477
        self.SCREEN_EXPECTED_FRAME_RATE = 60.0
        IMAGE_DIRECTLY_PROJECTED_ON_RETINA=False
        self.FULLSCREEN=not '--nofullscreen' in sys.argv
        self.COORDINATE_SYSTEM='center'
        self.ENABLE_FRAME_CAPTURE = False
        self.GUI['SIZE'] =  utils.cr((1024,768)) 
        #Network
        stim_computer_ip = '172.27.26.47'
        self.CONNECTIONS['stim']['ip']['stim'] = stim_computer_ip
        self.CONNECTIONS['stim']['ip']['main_ui'] = stim_computer_ip
        #Sync signal
        self.SYNC_RECORDER_CHANNELS='Dev1/ai0:6' #0: frame sync, 1: stim frame, 2: block, 3, 4, 5, 6: camera trigger from MESc computer
        self.SYNC_RECORDER_SAMPLE_RATE=5000#mes sync pulses are very short
        self.SYNC_RECORDING_BUFFER_TIME=5.0
        self.TIMG_SYNC_INDEX=0
        self.TSTIM_SYNC_INDEX=2
        self.DIGITAL_IO_PORT=['Dev1/port1/line0','Dev1/port1/line1']
        self.DIGITAL_IO_PORT_TYPE='daq'
        self.MES_START_TRIGGER_PIN = 0
        self.BLOCK_TIMING_PIN = 1
        self.FRAME_TIMING_PIN = 0
        self.IMAGING_START_DELAY=5
        self.SYNC_RECORD_OVERHEAD=10
        gammafn=os.path.join(self.CONTEXT_PATH, 'gamma_resonant_monitor.hdf5')
        if os.path.exists(gammafn):
            self.GAMMA_CORRECTION = copy.deepcopy(hdf5io.read_item(gammafn, 'gamma_correction'))
        self._create_parameters_from_locals(locals())
        
class GeorgResonantSetup(ResonantSetup):
    def _set_user_parameters(self):
        ResonantSetup._set_user_parameters(self)
        self.FULLSCREEN=True
        self.CAMERA_TRIGGER_ENABLE=True
        
        self.CAMERA_TRIGGER_FRAME_RATE=15
        self.CAMERA_PRE_STIM_WAIT=0.5
        self.CAMERA_POST_STIM_WAIT=0.5
        self.CAMERA_TIMING_ON_STIM=False
        self.CAMERA_TIMING_PIN=5
        self.CAMERA_IO_PORT_STIM='COM3'
        self.CAMERA_IO_PORT='COM10'

class ResonantDev(ResonantSetup):
    def _set_user_parameters(self):
        ResonantSetup._set_user_parameters(self)
#        self.LOG_PATH = 'c:\\zoli\\log'
#        self.EXPERIMENT_DATA_PATH = 'c:\\zoli\\experiment_data'
#        self.CONTEXT_PATH='c:\\zoli\\context'
#        stim_computer_ip = '172.27.27.187'
#        self.CONNECTIONS['stim']['ip']['stim'] = stim_computer_ip
#        self.CONNECTIONS['stim']['ip']['main_ui'] = stim_computer_ip
        self.FULLSCREEN=False
        self.CAMERA_TRIGGER_ENABLE=True
        self.CAMERA_IO_PORT_STIM='COM3'
        self.CAMERA_TRIGGER_FRAME_RATE=30
        self.CAMERA_PRE_STIM_WAIT=0.5
        self.CAMERA_POST_STIM_WAIT=0.5
        self.SCREEN_RESOLUTION = utils.cr([1280, 720])
        self.CAMERA_TIMING_PIN=5
        self.CAMERA_TIMING_ON_STIM=False
        self.CAMERA_IO_PORT='COM10'
