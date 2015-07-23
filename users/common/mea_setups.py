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
        SCREEN_RESOLUTION = utils.cr([800, 600])
        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        COLOR_MASK = numpy.array([0.0, 1.0, 1.0])
        self.ELECTRODE_PITCH=17.5
        self.SCALE_10X = 300.0/(22*self.ELECTRODE_PITCH)
        self.SCALE_5X = 300.0/(42*self.ELECTRODE_PITCH)
        SCREEN_UM_TO_PIXEL_SCALE = self.SCALE_5X
        self.root_folder = fileop.select_folder_exists(['/mnt/rzws/experiment_data','r:\\experiment_data', '/tmp', 'c:\\temp'])
        LOG_PATH = self.root_folder
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = fileop.select_folder_exists(['v:\\', 'c:\\temp'])
        CONTEXT_PATH = self.root_folder
#        CAPTURE_PATH = fileop.generate_foldername(os.path.join(tempfile.gettempdir(),'capture'))
#        os.mkdir(CAPTURE_PATH)
        EXPERIMENT_FILE_FORMAT = 'mat'
        #### experiment specific ####
        PARSE_PERIOD = [0.1, [0.0, 100.0]]
        ENABLE_FRAME_CAPTURE = not True
        COORDINATE_SYSTEM='center'
        DIGITAL_IO_PORT = 'COM5'
        FRAME_TRIGGER_PIN = 1
        BLOCK_TRIGGER_PIN = 0
        self.ENABLE_MEA_START_COMMAND=False
        self.INTENSITIES_425NM = numpy.array([0.96, 21, 37.3, 84.5, 127, 263.4, 419, 597, 815, 1080, 1282])
        self.INTENSITIES_550NM = numpy.array([15.6, 17, 20.8, 49, 87, 185, 288, 409, 564, 738, 888])
        self.GAMMA_CORRECTION = numpy.array([numpy.arange(0,1.1,0.1), self.INTENSITIES_425NM]).T
        self._create_parameters_from_locals(locals())

class MEAConfigDebug(MEAConfig):
    def _set_user_parameters(self):
        MEAConfig._set_user_parameters(self)
        self.FULLSCREEN = False