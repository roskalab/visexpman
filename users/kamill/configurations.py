import numpy
import os
import serial
from visexpman.engine.generic.parameter import Parameter
from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig
import visexpman.engine.vision_experiment.experiment as experiment
import visexpman.engine.hardware_interface.daq_instrument as daq_instrument
import visexpman.engine.generic.utils as utils
import scipy.interpolate

class StimDev(VisionExperimentConfig):
    '''
    Stimulation development on notebook
    '''
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'MovingShapeParameters'
        PLATFORM = 'standalone'
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        #=== paths/data handling ===
        v_drive_data_folder = '/home/kabalint/visexp/data'
        LOG_PATH = os.path.join(v_drive_data_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH
        EXPERIMENT_DATA_PATH = v_drive_data_folder
        
#        CAPTURE_PATH = os.path.join(v_drive_data_folder, 'capture')
        
        #=== screen ===
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800,600])
#        SCREEN_RESOLUTION = utils.cr([1024, 768])
        COORDINATE_SYSTEM='center'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0        
        SCREEN_UM_TO_PIXEL_SCALE = 1.65
        
        #=== hardware ===
        ENABLE_PARALLEL_PORT =  False#(self.OS == 'Windows')
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        
        #=== network ===
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        ENABLE_UDP = False#(self.OS == 'Windows')
  
        #=== Filterwheel ===
        ENABLE_FILTERWHEEL = False
        #=== LED controller ===
        STIM_SYNC_CHANNEL_INDEX = 1
        #=== Others ===
        USER_EXPERIMENT_COMMANDS = {'stop': {'key': 's', 'domain': ['running experiment']}, }

        self._create_parameters_from_locals(locals())


if __name__ == "__main__":
    pass
    
