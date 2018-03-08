import os
import os.path
import numpy
import tempfile
try:
    import serial
except:
    pass
from visexpman.engine.generic import utils,fileop
from visexpman.engine.vision_experiment.configuration import HiMEAConfig,MCMEAConfig

class MEAConfig(HiMEAConfig):
    def _set_user_parameters(self):
        FULLSCREEN = True
        SCREEN_RESOLUTION = utils.cr([1280, 800])
        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        BACKGROUND_COLOR=[0.0, 0.0, 0.0]
        LOG_PATH = fileop.select_folder_exists(['e:\\log', '/tmp', 'c:\\Data'])
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = fileop.select_folder_exists(['e:\\Data', '/tmp', 'c:\\Data\\log'])
        CONTEXT_PATH = LOG_PATH
        EXPERIMENT_FILE_FORMAT = 'mat'
        PLATFORM='standalone'
        COORDINATE_SYSTEM='center'
        DIGITAL_IO_PORT = 'COM4'
        FRAME_TIMING_PIN = 1#RTS pin (green)
        BLOCK_TIMING_PIN = 0#TX pin (orange)
        INSERT_FLIP_DELAY=True
        self._create_parameters_from_locals(locals())

class MEAConfigDebug(MEAConfig):
    def _set_user_parameters(self):
        MEAConfig._set_user_parameters(self)
        self.FULLSCREEN = False
