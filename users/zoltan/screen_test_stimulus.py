import time
import os
import numpy
import shutil
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig
from visexpman.engine.generic import utils
from visexpman.engine import visexp_runner

class ScreenTestSetup(VisionExperimentConfig):
    def _set_user_parameters(self):
        EXPERIMENT_CONFIG = 'ScreenTestConfig'
        COORDINATE_SYSTEM='center'
        SCREEN_UM_TO_PIXEL_SCALE= 1.0
        PLATFORM = 'standalone'
        #=== paths/data handling ===
        if os.name == 'nt':
            root_folder = 'V:\\'
        else:
            root_folder = '/mnt/datafast/'
            
        drive_data_folder = os.path.join(root_folder, 'debug', 'data')
        LOG_PATH = os.path.join(root_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = drive_data_folder
        self.CONTEXT_NAME = 'gui_dev.hdf5'
        CONTEXT_PATH = os.path.join(root_folder, 'context')
        CAPTURE_PATH = os.path.join(root_folder,  'debug', 'c')
        if os.path.exists(CAPTURE_PATH):
            shutil.rmtree(CAPTURE_PATH)
        os.mkdir(CAPTURE_PATH)
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        
        #=== screen ===
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])
        ENABLE_FRAME_CAPTURE = not True
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        
        
        #=== Network ===
        ENABLE_UDP = False
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = False
        self.COMMAND_RELAY_SERVER['ENABLE'] = False
        #=== hardware ===
        ENABLE_PARALLEL_PORT = False
        
        #=== Others ===
        USER_EXPERIMENT_COMMANDS = {'stop': {'key': 's', 'domain': ['running experiment']}, 
                                    'next': {'key': 'n', 'domain': ['running experiment']},}

        self._create_parameters_from_locals(locals())      
        
class ScreenTestConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.REPEATS = 1
        self.SCREEN_STRIPE_RATIO = 15.0
        self.COLORS = []
        colors = numpy.arange(0.0,  0.4,  0.0125).tolist()
        self.COLORS.extend(colors)
        for i in range(3):
            for c in colors:
                black = [0.0,  0.0, 0.0]
                black[i] = c
                self.COLORS.append(black)
        self.runnable = 'ScreenTest'
        
class ScreenTest(experiment.Experiment):
    def run(self):
        for i in range(self.experiment_config.REPEATS):
            self.show_grating(duration = 10, 
                            orientation = 0, 
                            velocity = 0.5 * self.machine_config.SCREEN_RESOLUTION['col'], 
                            white_bar_width = self.machine_config.SCREEN_RESOLUTION['col'] / self.experiment_config.SCREEN_STRIPE_RATIO,
                            duty_cycle = self.experiment_config.SCREEN_STRIPE_RATIO)
        for color in self.experiment_config.COLORS:
            self.show_shape( shape = 'rect',  duration = 1.0,  color = color,  size = utils.rc_multiply_with_constant(self.machine_config.SCREEN_RESOLUTION, 0.4))
                            
                            
if __name__=='__main__':    
    v = visexp_runner.VisionExperimentRunner('zoltan',  'ScreenTestSetup',  autostart = True)
    v.run_experiment()
