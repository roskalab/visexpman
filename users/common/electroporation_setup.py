import os
import os.path
import numpy
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment.configuration import ElectroporationConfig

class ElectroporationSetup228Config(ElectroporationConfig):
    '''
    '''
    def _set_user_parameters(self):
        root_folder = 'o:\\'
        LOG_PATH = os.path.join(root_folder, 'log')
        if not os.path.exists(LOG_PATH):
            os.mkdir(LOG_PATH)
        DATA_PATH = root_folder
        EXPERIMENT_DATA_PATH = root_folder
        EXPERIMENT_LOG_PATH = LOG_PATH
        
        #=== screen ===
        FULLSCREEN = True
        SCREEN_RESOLUTION = utils.cr([1024,768])
        COORDINATE_SYSTEM='ulcorner'
        gamma_values= numpy.array([0.000707026,0.0007070262,0.001148917,0.003137428,0.007821476,0.017366328,0.026336721,
            0.036632788,0.045338047,0.059080866,0.079982324,0.101634998,0.130799823,0.165709236,
            0.205921343,0.250110473,0.302695537,0.365444101,0.432611578,0.507291206,0.599646487,
            0.702165267,0.807777287,0.926646045,1,1.0000000001,1.000000002])
        x_axis = numpy.arange(0,  255, 10)
        x_axis = x_axis.tolist()
        x_axis.append(255)
        GAMMA_CORRECTION = numpy.array([x_axis, gamma_values]).T
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0      
        IMAGE_DIRECTLY_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = 340.0#mm
        SCREEN_PIXEL_WIDTH = 0.46#50 pixels = 23 mm
        
        #=== hardware ===
        ENABLE_PARALLEL_PORT = (os.name == 'nt')
        ACQUISITION_TRIGGER_PIN = 0
        BLOCK_TRIGGER_PIN = 1
        FRAME_TRIGGER_PIN = 2
        EXPERIMENT_START_TRIGGER = 11
        self._create_parameters_from_locals(locals())

class DebugElectroporationSetup228Config(ElectroporationSetup228Config):
    def _set_user_parameters(self):
        ElectroporationSetup228Config._set_user_parameters(self)
#        SCREEN_UM_TO_PIXEL_SCALE = 1.0
#        IMAGE_DIRECTLY_PROJECTED_ON_RETINA = True
        USER_EXPERIMENT_COMMANDS = {'stop': {'key': 's', 'domain': ['running experiment']}, 
                                    'next': {'key': 'n', 'domain': ['running experiment']},}

#        FULLSCREEN = False
#        self.EXPERIMENT_START_TRIGGER_TIMEOUT = 1.0
        self._create_parameters_from_locals(locals())
