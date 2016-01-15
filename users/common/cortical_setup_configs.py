import os
import os.path
import numpy
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment.configuration import ElphysRetinalCaImagingConfig,UltrasonicConfig

class UltrasonicSetupConfig(UltrasonicConfig):
    def _set_user_parameters(self):
        self.BACKGROUND_COLOR=[0.0]*3
        FULLSCREEN = False
        self.root_folder = 'd:\\Data'
        LOG_PATH = self.root_folder
        EXPERIMENT_DATA_PATH = self.root_folder
        CONTEXT_PATH = self.root_folder
        if 0:
            CAPTURE_PATH = fileop.generate_foldername(os.path.join(tempfile.gettempdir(),'capture'))
            os.mkdir(CAPTURE_PATH)
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        ENABLE_FRAME_CAPTURE = not True
        stim_computer_ip = '127.0.0.1'
        behavioral_computer_ip = '127.0.0.1'
        self.CONNECTIONS['stim']['ip']['stim'] = stim_computer_ip
        self.CONNECTIONS['stim']['ip']['main_ui'] = stim_computer_ip
        self.CONNECTIONS['behavioral']['ip']['analysis'] = behavioral_computer_ip
        self.CONNECTIONS['behavioral']['ip']['main_ui'] = behavioral_computer_ip
        self.SCREEN_RESOLUTION = utils.cr([1920, 1080])
        self.SCREEN_POSITION=utils.cr([-1920, 0])
        self.SCREEN_WIDTH=600#mm
        self.SCREEN_MOUSE_DISTANCE=180#mm
        self.SCREEN_UM_TO_PIXEL_SCALE = numpy.tan(numpy.radians(1.0/self.MOUSE_1_VISUAL_DEGREE_ON_RETINA))*self.SCREEN_MOUSE_DISTANCE/(self.SCREEN_WIDTH/float(self.SCREEN_RESOLUTION['col']))        
        self.GUI['SIZE'] =  utils.cr((600,400))
        self._create_parameters_from_locals(locals())
    

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
