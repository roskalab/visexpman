import os
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment.configuration import ElectroporationConfig

class ElectroporationSetup228Config(ElectroporationConfig):
    '''
    '''
    def _set_user_parameters(self):
        root_folder = 'o:\\'
        if not  os.path.exists(root_folder):
            import tempfile
            root_folder=tempfile.gettempdir()
        LOG_PATH = os.path.join(root_folder, 'log')
        if not os.path.exists(LOG_PATH):
            os.mkdir(LOG_PATH)
        DATA_PATH = root_folder
        CONTEXT_PATH=root_folder
        EXPERIMENT_DATA_PATH = root_folder
        EXPERIMENT_LOG_PATH = LOG_PATH
        
        #=== screen ===
        FULLSCREEN = True
        SCREEN_RESOLUTION = utils.cr([1280,768])
        COORDINATE_SYSTEM='center'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        IMAGE_DIRECTLY_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = 135.0#mm
        SCREEN_PIXEL_WIDTH = 0.38#50 pixels = 19 mm
        
        #=== hardware ===
        DIGITAL_IO_PORT='COM3'
        CAMERA_TRIGGER_PORT='COM4'
        self.CAMERA_TRIGGER_FRAME_RATE=23.256 #right now cant go above 12/13 hz
        self.CAMERA_TRIGGER_PIN=5
        self.CAMERA_PRE_STIM_WAIT=5.0
        self.CAMERA_POST_STIM_WAIT=5.0
        ACQUISITION_TRIGGER_PIN = 0
        BLOCK_TIMING_PIN = 0
        FRAME_TIMING_PIN = 1
        STIM_START_TRIGGER_PIN = 0
        WAIT4TRIGGER_ENABLED = True
        self._create_parameters_from_locals(locals())

class DebugEposConfig(ElectroporationSetup228Config):
    def _set_user_parameters(self):
        ElectroporationSetup228Config._set_user_parameters(self)
        self.FULLSCREEN = False
        self.WAIT4TRIGGER_ENABLED=False
        self.CAMERA_TRIGGER_FRAME_RATE=10.0
        
class DevelopEposLinuxConfig(ElectroporationSetup228Config):
    def _set_user_parameters(self):
        ElectroporationSetup228Config._set_user_parameters(self)
        self.FULLSCREEN = False
        self.WAIT4TRIGGER_ENABLED=False
        self.CAMERA_TRIGGER_FRAME_RATE=10
        self.DIGITAL_IO_PORT='/dev/ttyUSB0'
        self.CAMERA_TRIGGER_PORT='/dev/ttyACM0'
        self.INJECT_START_TRIGGER=True
        
class DevelopEposConfig(ElectroporationSetup228Config):
    def _set_user_parameters(self):
        ElectroporationSetup228Config._set_user_parameters(self)
        self.FULLSCREEN = False
        self.WAIT4TRIGGER_ENABLED=not False
        self.CAMERA_TRIGGER_FRAME_RATE=10
        self.SCREEN_RESOLUTION = utils.cr([1280/2,768/2])
        self.WAIT4TRIGGER_ENABLED=False
        

