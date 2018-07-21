import os
import os.path
import serial
import numpy
import time
import sys
import shutil

from visexpman.engine.generic.parameter import Parameter
from visexpman.engine.vision_experiment.configuration import IntrinsicConfig, VisionExperimentConfig,RcCorticalCaImagingConfig
from visexpman.engine.generic import utils
from visexpman.engine.generic import fileop


class IntrinsicDevelopment(IntrinsicConfig):
    '''
    '''

    def _set_user_parameters(self):
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
                os.makedirs(p)
        DATA_PATH = self.root_folder
        EXPERIMENT_DATA_PATH = self.root_folder
        EXPERIMENT_LOG_PATH = LOG_PATH

        # === screen ===
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800,600]) #utils.cr([1680, 1050])  # utils.cr([1024,768])
        COORDINATE_SYSTEM = 'center'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        STIM_RECORDS_ANALOG_SIGNALS = False
        EXPERIMENT_FILE_FORMAT = 'hdf5'

        # === hardware ===
        ENABLE_PARALLEL_PORT = False
        CAMERA = {'simulator':False, 'output':'/home/hd/camtemp', 'exposure_gain': [10000, 30],
                       'width': 1376, 'height': 1038, 'framerate':5, 'binning':None}
        self._create_parameters_from_locals(locals())



    
if __name__ == "__main__":
    pass
