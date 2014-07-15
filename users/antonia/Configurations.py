import numpy
import os
import serial
from visexpman.engine.generic.parameter import Parameter
from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig, ElphysRetinalCaImagingConfig
import visexpman.engine.vision_experiment.experiment as experiment
import visexpman.engine.hardware_interface.daq_instrument as daq_instrument
from visexpman.engine.generic import utils
import scipy.interpolate

class SPC(VisionExperimentConfig):
    '''
    Configuration for serial port pulse generator
    '''
    def _set_user_parameters(self):
        PLATFORM = 'smallapp'
        SMALLAPP = {'NAME': 'Serial port pulse generator', }
        GUI_SIZE = utils.rc((400, 300))
        GUI_REFRESH_PERIOD = 1.0
        ##### Flowmeter parameters #######
        
        if os.name == 'nt':
            SERIAL_DIO_PORT = 'COM1'
        else:
            SERIAL_DIO_PORT  = '/dev/ttyS0'
        self.MAX_PULSE_WIDTH = 3.0 #in seconds
        self.MIN_PULSE_WIDTH = 20.0e-3 #in seconds
        self.PULSE_OVERHEAD = 10.0e-3 #in seconds
        self._create_parameters_from_locals(locals())
        
class AEPHVS(ElphysRetinalCaImagingConfig):
    '''
    Antona's Electrophisology visual stimulation
    '''
    def _set_user_parameters(self, check_path = True):
        #=== paths/data handling ===
        if os.name == 'nt':
            v_drive_data_folder = 'c:\\Data'
        else:
            v_drive_data_folder = '/home/zoltan/visexp/debug/data'
        LOG_PATH = 'C:\\Data\\log'
        EXPERIMENT_LOG_PATH = LOG_PATH
        EXPERIMENT_DATA_PATH = v_drive_data_folder
        
        #=== screen ===
        FULLSCREEN = True
        SCREEN_RESOLUTION = utils.cr([800,600])
        SCREEN_RESOLUTION = utils.cr([1024, 768])
        COORDINATE_SYSTEM='center'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0        
        SCREEN_UM_TO_PIXEL_SCALE = 0.6
        BACKGROUND_COLOR = [0.5,0.5,0.5]
        
        #=== hardware ===
        ENABLE_PARALLEL_PORT = True
        ACQUISITION_TRIGGER_PIN = 2
        BLOCK_TRIGGER_PIN = 1
        FRAME_TRIGGER_PIN = 0
        
        #=== network ===
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        ENABLE_UDP = True
  
        #=== Filterwheel ===
        
        ENABLE_FILTERWHEEL = False
        
        #=== EphysData and stimulus Framerate recorder and LED controller ===
        STIM_SYNC_CHANNEL_INDEX = 1
        STIM_RECORDS_ANALOG_SIGNALS = True
        DAQ_CONFIG = [
                      {
                    'ANALOG_CONFIG' : 'ai', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 3.0,
                    'SAMPLE_RATE' : 10000,
                    'AI_CHANNEL' : 'Dev2/ai1:2',
                    'MAX_VOLTAGE' : 10.0,
                    'MIN_VOLTAGE' : -10.0,
                    'DURATION_OF_AI_READ' : 900.0,
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
                    
        self.GAMMA_CORRECTION = numpy.array([
                                             [0, 15.6], 
                                             [20, 54],
                                             [40, 175], 
                                             [60, 500],
                                             [70, 725], 
                                             [80, 996],
                                             [90, 1300], 
                                             [100, 1630],
                                             [110, 2000],
                                             [120, 2400], 
                                             [130, 2850], 
                                             [140, 3250], 
                                             [150, 3810], 
                                             [160, 4460],
                                             [165, 4820], 
                                             [170, 5130],  
                                             [180, 5890], 
                                             [190, 6630], 
                                             [200, 7430],
                                             [210, 8300], 
                                             [220, 9000], 
                                             [230, 9500],
                                             [255, 9500], 
                                             ])
        #=== Others ===
        USER_EXPERIMENT_COMMANDS = {'stop': {'key': 's', 'domain': ['running experiment']}, }
        self._create_parameters_from_locals(locals(), check_path = check_path)
        
class MEASetup(AEPHVS):
    '''
    Hidens mea setup
    '''
    def _set_user_parameters(self):
        AEPHVS._set_user_parameters(self, check_path=False)
        FULLSCREEN = True#TMP
        SCREEN_RESOLUTION = utils.cr((1024, 768))
        SCREEN_RESOLUTION = utils.cr((800, 600))
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        SCREEN_UM_TO_PIXEL_SCALE = 1.28/1.6276
        ENABLE_UDP = False
        BACKGROUND_COLOR = [0.5,0.5,0.5]
        INSERT_FLIP_DELAY = True
        PLATFORM = 'standalone'
        root_folder = 'c:\\Data'
        LOG_PATH = 'c:\\Data\\log'
        DATA_PATH = root_folder
        EXPERIMENT_DATA_PATH = root_folder
        EXPERIMENT_LOG_PATH = LOG_PATH
        ENABLE_PARALLEL_PORT = True
        ACQUISITION_TRIGGER_PIN = 1
        FRAME_TRIGGER_PIN = 0
        self.DAQ_CONFIG[0]['ENABLE'] = False
        self.DAQ_CONFIG[1]['ENABLE'] = False
        COLOR_MASK = numpy.array([0.0,  1.0,  1.0])
        import copy
        TEXT_COLOR = copy.deepcopy(BACKGROUND_COLOR)
        TEXT_COLOR[1] += 0.2
        gamma_corr_filename = 'c:\\visexp\\data\\gamma.hdf5'
        if os.path.exists(gamma_corr_filename):
            from visexpA.engine.datahandlers import hdf5io
            import copy
            self.GAMMA_CORRECTION = copy.deepcopy(hdf5io.read_item(gamma_corr_filename, 'gamma_correction',filelocking=False))
        else:
            del self.GAMMA_CORRECTION#Gamma calibration has to be done
        self._create_parameters_from_locals(locals())
        
class Debug(AEPHVS):
    '''
    Antona's Electrophisology visual stimulation
    '''
    def _set_user_parameters(self):
        AEPHVS._set_user_parameters(self, check_path=False)
#        FULLSCREEN = not True
        COORDINATE_SYSTEM='center'
        ENABLE_FRAME_CAPTURE = False
        self._create_parameters_from_locals(locals())

class ChiBlocktrigger(AEPHVS):
    '''
    Antona's Electrophisology visual stimulation
    '''
    def _set_user_parameters(self):
        AEPHVS._set_user_parameters(self, check_path=False)
        ACQUISITION_TRIGGER_PIN = 2
        BLOCK_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 1
        self._create_parameters_from_locals(locals())

        
if __name__ == "__main__":    
    c = LaserProjectorConfig()
    c.print_parameters() 
