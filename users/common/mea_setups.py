import os
import os.path
import numpy
import tempfile
import serial
from visexpman.engine.generic import utils,fileop
from visexpman.engine.vision_experiment.configuration import HiMEAConfig

class MEAConfig(HiMEAConfig):
    def _set_user_parameters(self):
        FULLSCREEN = not True
        SCREEN_RESOLUTION = utils.cr([1024, 768])
        self.root_folder = fileop.select_folder_exists(['/mnt/rzws/experiment_data','r:\\experiment_data', '/tmp'])
        LOG_PATH = self.root_folder
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = self.root_folder
#        DATA_STORAGE_PATH = fileop.select_folder_exists([ '/mnt/rzws/dataslow', '/tmp', 'C:\\temp'])
        CONTEXT_PATH = self.root_folder
#        CAPTURE_PATH = fileop.generate_foldername(os.path.join(tempfile.gettempdir(),'capture'))
#        os.mkdir(CAPTURE_PATH)
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        #### experiment specific ####
        PARSE_PERIOD = [0.1, [0.0, 100.0]]
        ENABLE_FRAME_CAPTURE = not True
        COORDINATE_SYSTEM='center'
        self._create_parameters_from_locals(locals())
