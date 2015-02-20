import os
import os.path
import numpy
import tempfile
try:
    import serial
except:
    pass
from visexpman.engine.generic import utils,fileop
from visexpman.engine.vision_experiment.configuration import HiMEAConfig

class MEAConfig(HiMEAConfig):
    def _set_user_parameters(self):
        FULLSCREEN = True
        SCREEN_RESOLUTION = utils.cr([1024, 768])
        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        COLOR_MASK = numpy.array([0.0, 1.0, 1.0])
        self.root_folder = fileop.select_folder_exists(['/mnt/rzws/experiment_data','r:\\experiment_data', '/tmp', 'c:\\temp'])
        LOG_PATH = self.root_folder
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = self.root_folder
        CONTEXT_PATH = self.root_folder
#        CAPTURE_PATH = fileop.generate_foldername(os.path.join(tempfile.gettempdir(),'capture'))
#        os.mkdir(CAPTURE_PATH)
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        #### experiment specific ####
        PARSE_PERIOD = [0.1, [0.0, 100.0]]
        ENABLE_FRAME_CAPTURE = not True
        COORDINATE_SYSTEM='center'
        DIGITAL_IO_PORT = 'COM4'
        FRAME_TRIGGER_PIN = 1
        BLOCK_TRIGGER_PIN = 0
        self._create_parameters_from_locals(locals())
