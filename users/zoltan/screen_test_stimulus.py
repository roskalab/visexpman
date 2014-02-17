import time
import os
import numpy
import shutil
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig
from visexpman.engine.generic import utils
from visexpman.engine.generic import fileop
from visexpman.engine import visexp_runner

class ScreenTestSetup(VisionExperimentConfig):
    def _set_user_parameters(self):
        EXPERIMENT_CONFIG = 'ScreenTestConfig'
        COORDINATE_SYSTEM='ulcorner'
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
        CAPTURE_PATH = os.path.join(root_folder,  'debug', 'screentest')
        if os.path.exists(CAPTURE_PATH):
            shutil.rmtree(CAPTURE_PATH)
        os.mkdir(CAPTURE_PATH)
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        
        #=== screen ===
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([1920, 1080])
        ENABLE_FRAME_CAPTURE = True
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
        self.COLOR_SCALE_DURATION = 5.0
        self.REPEATS = 4
        self.SCREEN_STRIPE_RATIO = 15.0
        self.ORIENTATIONS = [0,  180,  1]
        self.SPEEDS = [self.machine_config.SCREEN_RESOLUTION['col'],  0.5 * self.machine_config.SCREEN_RESOLUTION['col']]
        self.COLORS = []
        colors = numpy.arange(0.0,  1.0,  1.0/64).tolist()
        self.N_COLS = len(colors)
        self.COLORS.extend(colors)
        for i in range(3):
            for c in colors:
                black = [0.0,  0.0, 0.0]
                black[i] = c
                self.COLORS.append(black)
            for c in colors:
                black = [c, c, c]
                black[i] = 0.0
                self.COLORS.append(black)
        self.runnable = 'ScreenTest'
        
class ScreenTest(experiment.Experiment):
    def run(self):
        for spd in self.experiment_config.SPEEDS:
            for i in range(self.experiment_config.REPEATS):
                for ori in self.experiment_config.ORIENTATIONS:
                    self.show_grating(duration = float(self.machine_config.SCREEN_RESOLUTION['col']/spd), 
                                orientation = ori, 
                                velocity = spd, 
                                white_bar_width = self.machine_config.SCREEN_RESOLUTION['col'] / self.experiment_config.SCREEN_STRIPE_RATIO,
                                duty_cycle = self.experiment_config.SCREEN_STRIPE_RATIO)

    def generate_color_scale(self):
        color_index = 0
        nrows = len(self.experiment_config.COLORS)/self.experiment_config.N_COLS
        rectsize = utils.rc((self.machine_config.SCREEN_RESOLUTION['row']/float(nrows), self.machine_config.SCREEN_RESOLUTION['col']/float(self.experiment_config.N_COLS)))
        image = numpy.zeros((self.machine_config.SCREEN_RESOLUTION['row'], self.machine_config.SCREEN_RESOLUTION['col'],  3),  dtype = numpy.uint8)
        for row in range(nrows):
            for col in range(self.experiment_config.N_COLS):
                image[row*rectsize['row']:(row+1)*rectsize['row'],col*rectsize['col']:(col+1)*rectsize['col'],:]  = numpy.cast['uint8'](255*numpy.array(self.experiment_config.COLORS[color_index]))
                color_index+=1
        try:
            import Image
        except ImportError:
            from PIL import Image
        #Find out file index
        captured_files = fileop.listdir_fullpath(self.machine_config.CAPTURE_PATH)
        captured_files.sort()
        start_index = int(os.path.split(captured_files[-1])[-1].split('.')[0].split('_')[1]) + 1
        for i in range(start_index,  int(start_index + self.experiment_config.COLOR_SCALE_DURATION * self.machine_config.SCREEN_EXPECTED_FRAME_RATE)):
            impath = os.path.join(self.machine_config.CAPTURE_PATH,  'captured_{0:5}.bmp'.format(i)).replace(' ',  '0')
            Image.fromarray(image,).save(impath)

if __name__=='__main__':    
    v = visexp_runner.VisionExperimentRunner('zoltan',  'ScreenTestSetup',  autostart = True)
    v.run_experiment()
    v.experiment_config.runnable.generate_color_scale()
    v.experiment_config.runnable.export2video('/mnt/datafast/debug/screentest.mp4')
    
    
