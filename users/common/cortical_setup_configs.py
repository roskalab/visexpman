import os
import os.path
import numpy
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment.configuration import ElphysRetinalCaImagingConfig

class SantiagoSetupConfig(ElphysRetinalCaImagingConfig):
    '''
    '''
    def _set_user_parameters(self):
        self.root_folder = 'c:\\Data'
        if not os.path.exists(self.root_folder):
            self.root_folder = '/tmp'
        LOG_PATH = os.path.join(self.root_folder, 'log')
        if not os.path.exists(LOG_PATH):
            os.mkdir(LOG_PATH)
        DATA_PATH = self.root_folder
        EXPERIMENT_DATA_PATH = self.root_folder
        EXPERIMENT_LOG_PATH = LOG_PATH
        
        #=== screen ===
        FULLSCREEN = True
        SCREEN_RESOLUTION = utils.cr([960,540])
        COORDINATE_SYSTEM='center'
        
        CONTEXT_PATH = self.root_folder
        CAPTURE_PATH=os.path.join(self.root_folder, 'capture')
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        IMAGE_DIRECTLY_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = 260.0#mm
        SCREEN_PIXEL_WIDTH = 0.5#mm 200 pixels = 100 mm
        
        #=== hardware ===
        ENABLE_PARALLEL_PORT = (os.name == 'nt')
        ACQUISITION_TRIGGER_PIN = 0
        BLOCK_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 1
        
        
        ENABLE_UDP = True
        self._create_parameters_from_locals(locals())

class DebugSantiagoSetupConfig(SantiagoSetupConfig):
    def _set_user_parameters(self):
        SantiagoSetupConfig._set_user_parameters(self)
#        SCREEN_UM_TO_PIXEL_SCALE = 1.0
#        SCREEN_RESOLUTION = utils.cr([960,540])
#        self.IMAGE_DIRECTLY_PROJECTED_ON_RETINA_p.v = True
        FULLSCREEN = False

        self._create_parameters_from_locals(locals())
