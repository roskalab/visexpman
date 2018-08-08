import os
import os.path
import numpy
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment.configuration import ElphysRetinalCaImagingConfig,UltrasoundConfig

class UltrasoundSetupConfig(UltrasoundConfig):
    def _set_user_parameters(self):
        self.BACKGROUND_COLOR=[0.0]*3
        FULLSCREEN = True
        self.root_folder = 'x:\\ultrasound'
        LOG_PATH = os.path.join(self.root_folder,'log')
        EXPERIMENT_DATA_PATH = os.path.join(self.root_folder,'experiment_data')
        CONTEXT_PATH = os.path.join(self.root_folder,'context')
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        ENABLE_FRAME_CAPTURE = False
        DIGITAL_IO_PORT='COM3'
        BLOCK_TIMING_PIN=0
        FRAME_TIMING_PIN=1
        stim_computer_ip = '192.168.2.4'
        behavioral_computer_ip = '192.168.2.3'
        self.CONNECTIONS['stim']['ip']['stim'] = stim_computer_ip
        self.CONNECTIONS['stim']['ip']['main_ui'] = stim_computer_ip
        self.CONNECTIONS['behavioral']['ip']['behavioral'] = behavioral_computer_ip
        self.CONNECTIONS['behavioral']['ip']['main_ui'] = behavioral_computer_ip
        self.SCREEN_RESOLUTION = utils.cr([1920, 1080])
        #self.SCREEN_RESOLUTION = utils.cr([1366, 768])
        #self.SCREEN_POSITION=utils.cr([0, 0])#utils.cr([-1920, 0])
        self.SCREEN_WIDTH=600#mm
        self.SCREEN_MOUSE_DISTANCE=180#mm
        self.SCREEN_UM_TO_PIXEL_SCALE = numpy.tan(numpy.radians(1.0/self.MOUSE_1_VISUAL_DEGREE_ON_RETINA))*self.SCREEN_MOUSE_DISTANCE/(self.SCREEN_WIDTH/float(self.SCREEN_RESOLUTION['col']))        
        self.GUI['SIZE'] = utils.cr((600,400))
        self.SYNC_RECORDER_CHANNELS='Dev2/ai0:4'#stim sync and block trigger, ultrasound frame sync, behavioral reward, video recorder sync
        self.SYNC_RECORDER_SAMPLE_RATE=5000
        self.SYNC_RECORDING_BUFFER_TIME=5.0
        
        #at 500nm
        self.GAMMA_CORRECTION = numpy.array([
                                    [0.0, 0.0067e-6],
                                    [0.1, 0.0112e-6],
                                    [0.2, 0.0207e-6],
                                    [0.3, 0.0331e-6],
                                    [0.4, 0.0488e-6],
                                    [0.5, 0.0678e-6],
                                    [0.6, 0.0928e-6],
                                    [0.7, 0.1222e-6],
                                    [0.8, 0.1577e-6],
                                    [0.9, 0.1963e-6],
                                    [1.0, 0.2403e-6]])
        
        self.ULTRASOUND_PROTOCOLS=['default']
        self.ENABLE_ULTRASOUND_TRIGGERING=False
        self._create_parameters_from_locals(locals())
        
class UltrasoundSetupConfigDebug(UltrasoundSetupConfig):
    def _set_user_parameters(self):
        UltrasoundSetupConfig._set_user_parameters(self)
        self.EXPERIMENT_FILE_FORMAT = 'hdf5'
        self.SCREEN_RESOLUTION = utils.cr([800,600])
        self.SCREEN_RESOLUTION = utils.cr([1366, 768])
        self.SCREEN_POSITION=utils.cr([0, 0])
        self.FULLSCREEN=False
        self.SCREEN_MODE = 'psychopy'
        self.PSYCHOPY_MONITOR_NAME='HDMI'
        if 0:
            stim_computer_ip = 'localhost'
            behavioral_computer_ip = 'localhost'
            self.CONNECTIONS['stim']['ip']['stim'] = stim_computer_ip
            self.CONNECTIONS['stim']['ip']['main_ui'] = stim_computer_ip
            self.CONNECTIONS['behavioral']['ip']['behavioral'] = behavioral_computer_ip
            self.CONNECTIONS['behavioral']['ip']['main_ui'] = behavioral_computer_ip
        
        
class UltrasoundSetupConfigDevOffline(UltrasoundSetupConfig):
    def _set_user_parameters(self):
        UltrasoundSetupConfig._set_user_parameters(self)
        self.SCREEN_RESOLUTION = utils.cr([800,600])
        self.SCREEN_POSITION=utils.cr([0, 0])
        self.FULLSCREEN=False
#        self.SCREEN_MODE = 'psychopy'
#        self.PSYCHOPY_MONITOR_NAME='testMonitor'
        stim_computer_ip = '127.0.0.1'
        behavioral_computer_ip = '127.0.0.1'
        self.CONNECTIONS['stim']['ip']['stim'] = stim_computer_ip
        self.CONNECTIONS['stim']['ip']['main_ui'] = stim_computer_ip
        self.CONNECTIONS['behavioral']['ip']['behavioral'] = behavioral_computer_ip
        self.CONNECTIONS['behavioral']['ip']['main_ui'] = behavioral_computer_ip
        self.DIGITAL_IO_PORT=False
        self.root_folder = 'c:\\ultrasound'
        self.LOG_PATH = os.path.join(self.root_folder,'log')
        self.EXPERIMENT_DATA_PATH = os.path.join(self.root_folder,'experiment_data')
        self.CONTEXT_PATH = os.path.join(self.root_folder,'context')

class SantiagoSetupMainConfig(ElphysRetinalCaImagingConfig):
    def _set_user_parameters(self):
        #### paths/data handling ####
        FULLSCREEN = not True
        self.root_folder = 'b:\\'
        BACKUP_PATH='x:\\santiago-setup'
        self.BACKUPTIME=3#3am
        self.BACKUP_NO_EXPERIMENT_TIMEOUT=60#minutes
        LOG_PATH = os.path.join(self.root_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = os.path.join(self.root_folder, 'processed')
        CONTEXT_PATH = self.root_folder
        self.DELETED_FILES_PATH = 'c:\\temp'
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        FREE_SPACE_ERROR_THRESHOLD = 30e9
        #### experiment specific ####
        PARSE_PERIOD = [0.1, [0.0, 100.0]]
        ENABLE_FRAME_CAPTURE = not True
        #### Network ####
        stim_computer_ip = '192.168.1.103'
        elphys_computer_ip = '172.27.26.48'
        imaging_computer_ip = '192.168.1.101'
        self.CONNECTIONS['stim']['ip']['stim'] = stim_computer_ip
        self.CONNECTIONS['stim']['ip']['main_ui'] = stim_computer_ip
        self.CONNECTIONS['ca_imaging']['ip']['ca_imaging'] = imaging_computer_ip #bind to specific network card
        self.CONNECTIONS['ca_imaging']['ip']['main_ui'] = imaging_computer_ip

        self.BASE_PORT = 10000
        SYNC_RECORDER_CHANNELS='Dev1/ai4:7'
        self.SYNC_RECORDER_SAMPLE_RATE=10000
        self.SYNC_RECORDING_BUFFER_TIME=5.0
        self.TIMG_SYNC_INDEX=1
        self.TSTIM_SYNC_INDEX=2
        COORDINATE_SYSTEM='center'
        ######################### Ca imaging specific ################################ 
        self.CA_IMAGING_START_DELAY = 10.0#NEW
        self.CA_IMAGING_START_TIMEOUT = 15.0
        PMTS = {'TOP': {'CHANNEL': 1,  'COLOR': 'GREEN', 'ENABLE': True}, 
                            'SIDE': {'CHANNEL' : 0,'COLOR': 'RED', 'ENABLE': False}}
        POSITION_TO_SCANNER_VOLTAGE = 0.013
        self.GUI['SIZE'] =  utils.cr((1280,1024))
#        self.GUI['SIZE'] =  utils.cr((1024,700))
#        if os.name == 'nt':
#            DAQ_CONFIG[0]['AI_TERMINAL'] = DAQmxConstants.DAQmx_Val_PseudoDiff


        DATAFILE_COMPRESSION_LEVEL = 5
        self.DEFAULT_ROI_SIZE_ON_GUI=5
        self.DIGITAL_IO_PORT = 'parallel port'
        self.BLOCK_TIMING_PIN = 0
        self.ENABLE_PARALLEL_PORT = True
        self._create_parameters_from_locals(locals())
        
class SantiagoAnalysisConfig(ElphysRetinalCaImagingConfig):
    def _set_user_parameters(self):
        self.root_folder = 'D:\\Desktop\\Chiara\\Acute Slice Recordings' if not os.path.exists('/tmp') else '/tmp'
        self.LOG_PATH = self.root_folder
        self.EXPERIMENT_LOG_PATH = self.LOG_PATH        
        self.EXPERIMENT_DATA_PATH = self.root_folder
        self.EXPERIMENT_DATA_PATH = 'y:\\santiago-setup\\test'
        self.CONTEXT_PATH = self.root_folder
        self.COORDINATE_SYSTEM='center'
        self.TIMG_SYNC_INDEX=1
        self.TSTIM_SYNC_INDEX=2
        ######################### Ca imaging specific ################################ 
        self.GUI['SIZE'] =  utils.cr((1280,800))
        self.DEFAULT_ROI_SIZE_ON_GUI=5
