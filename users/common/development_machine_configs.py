import os
import os.path
import numpy
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig

class StimulusDevelopment(VisionExperimentConfig):
    '''
    '''
    def _set_user_parameters(self):
        PLATFORM = 'standalone'
        if os.name == 'nt':
            self.root_folder = 'c:\\data'
        elif os.path.exists('/mnt/rzws/dataslow/temp'):
            self.root_folder = '/mnt/rzws/dataslow/temp'
        else:
            self.root_folder = '/tmp'
        LOG_PATH = os.path.join(self.root_folder, 'log')
        CAPTURE_PATH = os.path.join(self.root_folder, 'capture')
        CONTEXT_PATH = self.root_folder
        for p in [CAPTURE_PATH, LOG_PATH]:
            if not os.path.exists(p):
                os.mkdir(p)
        DATA_PATH = self.root_folder
        EXPERIMENT_DATA_PATH = self.root_folder
        EXPERIMENT_LOG_PATH = LOG_PATH
        
        #=== screen ===
        FULLSCREEN = False
        COORDINATE_SYSTEM='center'
        ENABLE_FRAME_CAPTURE = False
#        SCREEN_EXPECTED_FRAME_RATE = 60.0
#        SCREEN_MAX_FRAME_RATE = 60.0
        STIM_RECORDS_ANALOG_SIGNALS = False
        EXPERIMENT_FILE_FORMAT = 'mat'
        
        #=== hardware ===
        ENABLE_PARALLEL_PORT = False
        
        
        SCREEN_RESOLUTION = utils.cr((1024, 768))#TMP febr 09
        SCREEN_UM_TO_PIXEL_SCALE = 0.5#1/2.47#TMP febr 09
        BACKGROUND_COLOR = 3*[0.0]#TMP febr 09
        
        self._create_parameters_from_locals(locals())
