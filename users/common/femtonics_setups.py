import os
import os.path
import numpy
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment.configuration import AoCorticalCaImagingConfig

class AOSetup(AoCorticalCaImagingConfig):
    def _set_user_parameters(self):
        AoCorticalCaImagingConfig._set_user_parameters(self)
        self.EXPERIMENT_FILE_FORMAT = 'hdf5'
        self.LOG_PATH = 'v:\\log'
        self.EXPERIMENT_DATA_PATH = 'v:\\experiment_data_ao'
        self.CONTEXT_PATH='v:\\context'
        self.SCREEN_DISTANCE_FROM_MOUSE_EYE = 250.0
        self.SCREEN_PIXEL_WIDTH = 0.375
        self.SCREEN_EXPECTED_FRAME_RATE = 60.0
        self.SCREEN_RESOLUTION = utils.cr([1280, 800])
        self.SCREEN_MAX_FRAME_RATE = 60.0
        self.COORDINATE_SYSTEM='center'
        self.ENABLE_FRAME_CAPTURE = False
        self.GUI['SIZE'] =  utils.cr((1024,768)) 
        stim_computer_ip = '172.27.26.69'
        behavioral_computer_ip = '192.168.2.3'
        self.CONNECTIONS['stim']['ip']['stim'] = stim_computer_ip
        self.CONNECTIONS['stim']['ip']['main_ui'] = stim_computer_ip
        
        
