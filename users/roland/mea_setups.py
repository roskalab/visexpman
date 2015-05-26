import os
import os.path
import numpy
import tempfile
import time
try:
    import serial
except:
    pass
from visexpman.engine.generic import utils,fileop
from visexpman.engine.vision_experiment.configuration import HiMEAConfig

class MEAConfig(HiMEAConfig):
    def _set_user_parameters(self):
        FULLSCREEN = not True
        SCREEN_RESOLUTION = utils.cr([600, 600])
        COLOR_MASK = numpy.array([1.0, 1.0, 1.0])
        PLATFORM = 'hi_mea'
        
        # Scale:
        self.ELECTRODE_PITCH=17.5
        self.RETINA_ROOM_SCALE = 1.0/1.75
        SCREEN_UM_TO_PIXEL_SCALE = self.RETINA_ROOM_SCALE
        
        # Folders & paths:
        self.root_folder = fileop.select_folder_exists(['/home/localadmin/tmp'])
        LOG_PATH = self.root_folder
        EXPERIMENT_LOG_PATH = LOG_PATH
        
        #
        DIGITAL_IO_PORT = 'parallel port'
        ENABLE_PARALLEL_PORT = True
        # For USB: DIGITAL_IO_PORT = 'COM5'
        
        EXPERIMENT_DATA_PATH = fileop.select_folder_exists(['/home/localadmin/tmp']) #'/links/rolandd/tmp/lightX_stim_logs/'+time.strftime('%y%m%d{0}data'.format(os.sep)), 
        CONTEXT_PATH = self.root_folder
        EXPERIMENT_FILE_FORMAT = 'mat'
#        CAPTURE_PATH = fileop.generate_foldername(os.path.join(tempfile.gettempdir(),'capture'))
#        os.mkdir(CAPTURE_PATH)
        
        RECORDING_MACHINE_PORT = "12.0.1.1:75000"
        
        #### experiment specific ####
        PARSE_PERIOD = [0.1, [0.0, 100.0]]
        ENABLE_FRAME_CAPTURE = not True
        COORDINATE_SYSTEM='center'
        FRAME_TRIGGER_PIN = 1
        BLOCK_TRIGGER_PIN = 0
        self.ENABLE_MEA_START_COMMAND = False # set True when stim software needs to start the recording
        self.INTENSITIES_425NM = numpy.array([0.96, 21, 37.3, 84.5, 127, 263.4, 419, 597, 815, 1080, 1282])
        self.INTENSITIES_550NM = numpy.array([15.6, 17, 20.8, 49, 87, 185, 288, 409, 564, 738, 888])
        self.GAMMA_CORRECTION = numpy.array([numpy.arange(0,1.1,0.1), self.INTENSITIES_425NM]).T
        self._create_parameters_from_locals(locals())

class MEAConfigDebug(MEAConfig):
    def _set_user_parameters(self):
        MEAConfig._set_user_parameters(self)
        self.FULLSCREEN = False
