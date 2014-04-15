import os
import os.path
import numpy
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment.configuration import ElphysConfig

class SantiagoSetupConfig(ElphysConfig):
    '''
    '''
    def _set_user_parameters(self):
        root_folder = 'c:\\Data'
        LOG_PATH = os.path.join(root_folder, 'log')
        if not os.path.exists(LOG_PATH):
            os.mkdir(LOG_PATH)
        DATA_PATH = root_folder
        EXPERIMENT_DATA_PATH = root_folder
        EXPERIMENT_LOG_PATH = LOG_PATH
        
        #=== screen ===
        FULLSCREEN = True
        SCREEN_RESOLUTION = utils.cr([960,540])
        SCREEN_ROTATION=-90
        COORDINATE_SYSTEM='center'
        
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0      
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
        FULLSCREEN = not False

        self._create_parameters_from_locals(locals())
