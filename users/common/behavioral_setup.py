import os,numpy,sys
from visexpman.engine.vision_experiment.configuration import BehavioralConfig
from visexpman.engine.generic import fileop,utils

class BehavioralSetup(object):
        PLATFORM = 'behav'
        LOG_PATH = fileop.select_folder_exists(['c:\\Data\\log','q:\\log', '/tmp', 'd:\\Data', 'c:\\Data','c:\\Users\\rz\\tmp'])
        EXPERIMENT_DATA_PATH = fileop.select_folder_exists(['q:\\data', '/tmp', 'd:\\Data', 'c:\\Data','c:\\Users\\rz\\tmp'])
        CONTEXT_PATH = fileop.select_folder_exists(['q:\\context', '/tmp', 'd:\\Data', 'c:\\Data','c:\\Users\\rz\\tmp'])
        ENABLE_CAMERA=True
        CAMERA_ID=0
        CAMERA_FRAME_RATE=7
        CAMERA_FRAME_WIDTH=640/2
        CAMERA_FRAME_HEIGHT=480/2
        SCREEN_SIZE=[1366,700]
        SCREEN_OFFSET=[4,19]
        BOTTOM_WIDGET_HEIGHT=260
        PLOT_WIDGET_WIDTH=700
        MINIMUM_FREE_SPACE=20#GByte
        ARDUINO_SERIAL_PORT='COM5'
        PROTOCOL_ORDER=['HitMiss','HitMiss1secRewardDelay','Lick', 'HitMissRandomLaser', 'LickRandomLaser']
        AI_CHANNELS='Dev1/ai0:5'#water valve, lick signal, laser, lick detector output, debug (protocol state), photodiode
        AI_SAMPLE_RATE=5000
        BACKUPTIME=3#3am
        BACKUP_LOG_TIMEOUT=60#minutes
        BACKUP_PATH='x:\\behavioral'
        SESSION_TIMEOUT=120#Minutes
        
class BehavioralSetup2(BehavioralSetup):
    ARDUINO_SERIAL_PORT='COM4'
    SCREEN_OFFSET=[4,25]
    SCREEN_SIZE=[1280,950]
    PLOT_WIDGET_WIDTH=600
    BOTTOM_WIDGET_HEIGHT=400
    WATER_VALVE_DO_CHANNEL=1
    AIRPUFF_VALVE_DO_CHANNEL=2
    TREADMILL_READ_TIMEOUT=200e-3

class BehavioralSetup3(BehavioralSetup):
    SCREEN_OFFSET=[4,37]
    SCREEN_SIZE=[1920,950]
    PLOT_WIDGET_WIDTH=1200
    BOTTOM_WIDGET_HEIGHT=400
    ARDUINO_SERIAL_PORT='COM3'
    WATER_VALVE_DO_CHANNEL=2

class OfficeTest(BehavioralSetup):
    LASER_AO_CHANNEL='/Dev2/ao0'
    ENABLE_CAMERA=False
    ARDUINO_SERIAL_PORT='COM9'
    SCREEN_SIZE=[1280,1024]
    PLOT_WIDGET_WIDTH=600
    AI_CHANNELS='Dev2/ai0:4'
    BACKUP_PATH='x:\\behavioral\\test3'
    BACKUPTIME=3
    BACKUP_LOG_TIMEOUT=15#minutes
    #SESSION_TIMEOUT=10#Minutes

class Behavioral2Setup(BehavioralConfig):#Miao's setup
    def _set_user_parameters(self):
        self.root_folder = 'x:\\behavioral2'
        LOG_PATH = os.path.join(self.root_folder,'log')
        EXPERIMENT_DATA_PATH = os.path.join(self.root_folder,'experiment_data')
        CONTEXT_PATH = os.path.join(self.root_folder,'context')
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        ENABLE_FRAME_CAPTURE = False
        DIGITAL_IO_PORT='daq'
        BLOCK_TRIGGER_PIN=0
        FRAME_TIMING_PIN=1
        self.SCREEN_RESOLUTION = utils.cr([1920, 1080])
        self.SCREEN_WIDTH=600#mm
        self.SCREEN_MOUSE_DISTANCE=180#mm
        self.SCREEN_UM_TO_PIXEL_SCALE = numpy.tan(numpy.radians(1.0/self.MOUSE_1_VISUAL_DEGREE_ON_RETINA))*self.SCREEN_MOUSE_DISTANCE/(self.SCREEN_WIDTH/float(self.SCREEN_RESOLUTION['col']))        
        self.SYNC_RECORDER_CHANNELS='Dev1/ai0:1'#0 block trigger, 1: trigger from ephys
        self.SYNC_RECORDER_SAMPLE_RATE=5000#mes sync pulses are very short
        self.SYNC_RECORDING_BUFFER_TIME=5.0
        self.TIMG_SYNC_INDEX=1
        self.TSTIM_SYNC_INDEX=0
        self.DIGITAL_OUTPUT='daq'
        self.TIMING_CHANNELS='dev1/port0/line1'
        self.STIM_TRIGGER_CHANNEL='dev1/port0/line2'
        self.BLOCK_TRIGGER_PIN = 1
        self.FRAME_TIMING_PIN = 0
        self.SYNC_RECORD_OVERHEAD=10
        gammafn=os.path.join(CONTEXT_PATH, 'gamma.hdf5')
        if os.path.exists(gammafn):
            import copy
            self.GAMMA_CORRECTION = copy.deepcopy(hdf5io.read_item(gammafn, 'gamma_correction'))
        if '--nofullscreen' in sys.argv:
            self.FULLSCREEN=False
        self._create_parameters_from_locals(locals())
