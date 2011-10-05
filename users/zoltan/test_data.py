from visexpman.engine.visual_stimulation.configuration import VisionExperimentConfig
from visexpman.engine.generic import utils
import visexpman.engine.visual_stimulation.experiment as experiment
import time
import numpy
import serial
import visexpman
import os.path
import os
import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner

#== For software development test ==

class VRWT(VisionExperimentConfig):
    '''
    Visexp runner windows test config
    '''
    def _set_user_parameters(self):
        dataset = 0
        
        RUN_MODE = 'single experiment'
        
        #paths
        EXPERIMENT_CONFIG = 'TestExperimentConfig'
        LOG_PATH = unit_test_runner.TEST_working_folder      
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        ARCHIVE_PATH = unit_test_runner.TEST_working_folder
        CAPTURE_PATH = unit_test_runner.TEST_working_folder
        TEST_DATA_PATH = unit_test_runner.TEST_working_folder
        
        #hardware
        ENABLE_PARALLEL_PORT = True
        ENABLE_UDP = True
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 2
        ENABLE_FILTERWHEEL = True
        
        FILTERWHEEL_SERIAL_PORT = [[{
                                    'port' :  unit_test_runner.TEST_com_port,
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }]]        
                                    
        FILTERWHEEL_FILTERS = [[{
                                                'ND0': 1, 
                                                'ND10': 2, 
                                                'ND20': 3, 
                                                'ND30': 4, 
                                                'ND40': 5, 
                                                'ND50': 6, 
                                                }]]
        
        #screen
        FULLSCREEN = False        
        SCREEN_RESOLUTION = utils.cr([800, 600])        
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        GAMMA = 1.0        
        TEXT_ENABLE = True
        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        if dataset == 0:
            COORDINATE_SYSTEM='center'
        elif dataset == 1:
            COORDINATE_SYSTEM='ulcorner'
        
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [36.0, [0, 100]] #cm
        SCREEN_PIXEL_WIDTH = [0.0425, [0, 0.5]] # mm
        FRAME_WAIT_FACTOR = 0

        SEGMENT_DURATION = 2
        MAXIMUM_RECORDING_DURATION = [270, [0, 10000]] #seconds
        ACTION_BETWEEN_STIMULUS = 'off'
        
        ARCHIVE_FORMAT = 'zip'
#        ARCHIVE_FORMAT = 'hdf5'
        
        USER_EXPERIMENT_COMMANDS = {'dummy': {'key': 'd', 'domain': ['running experiment']}, }
        self._create_parameters_from_locals(locals())

class VisexpRunnerTestConfig(VisionExperimentConfig):
    def _set_user_parameters(self):
        dataset = 0
        
        RUN_MODE = 'single experiment'
        
        #paths
        EXPERIMENT_CONFIG = 'TestExperimentConfig'
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        BASE_PATH= unit_test_runner.TEST_working_folder
        ARCHIVE_PATH = unit_test_runner.TEST_working_folder
        CAPTURE_PATH = os.path.join(unit_test_runner.TEST_working_folder,'Capture')
        if not os.path.exists(CAPTURE_PATH):
            os.mkdir(CAPTURE_PATH)
        
        #hardware
        ENABLE_PARALLEL_PORT = True
        ENABLE_UDP = True
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 2
        ENABLE_FILTERWHEEL = True
        FILTERWHEEL_SERIAL_PORT = [[{
                                    'port' :  unit_test_runner.TEST_com_port,
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }]]
                                    
        FILTERWHEEL_FILTERS = [[{
                                                'ND0': 1, 
                                                'ND10': 2, 
                                                'ND20': 3, 
                                                'ND30': 4, 
                                                'ND40': 5, 
                                                'ND50': 6, 
                                                }]]

        
        #screen
        FULLSCREEN = False        
        SCREEN_RESOLUTION = utils.cr([800, 600])        
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        GAMMA = 1.0        
        TEXT_ENABLE = True
        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        if dataset == 0:
            COORDINATE_SYSTEM='center'
        elif dataset == 1:
            COORDINATE_SYSTEM='ulcorner'
        
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [36.0, [0, 100]] #cm
        SCREEN_PIXEL_WIDTH = [0.0425, [0, 0.5]] # mm
        FRAME_WAIT_FACTOR = 0

        SEGMENT_DURATION = 2
        MAXIMUM_RECORDING_DURATION = [270, [0, 10000]] #seconds
        ACTION_BETWEEN_STIMULUS = 'off'
        
        ARCHIVE_FORMAT = 'zip'
#        ARCHIVE_FORMAT = 'hdf5'
        
        USER_EXPERIMENT_COMMANDS = {'dummy': {'key': 'd', 'domain': ['running experiment']}, }
        self._create_parameters_from_locals(locals())

class TestExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'TestExp1'
        self.pre_runnable = 'TestPre'
        self._create_parameters_from_locals(locals())        

class TestPre(experiment.PreExperiment):
    def run(self):
        self.show_fullscreen(color = (0.28, 0.29, 0.3), flip = False)

class TestExp1(experiment.Experiment):
    def run(self):
        self.log.info('%2.3f\tMy log'%time.time())
        self.show_fullscreen(duration = 3.0,  color = 0.5)
        import random
        filter = int(5 * random.Random().random()) + 1
        time.sleep(0.2)
        self.filterwheels[0].set(filter)        
        self.filterwheels[0].set_filter('ND0')
        self.parallel_port.set_data_bit(0, 0)
        time.sleep(0.1)
        self.parallel_port.set_data_bit(0, 1)
        self.show_grating(duration =1.0, profile = 'sqr', orientation = 0, velocity =50.0, white_bar_width = 100, display_area =  utils.cr((0, 0)), pos = utils.cr((0, 0)), color_contrast = 1.0)
        if self.command_buffer.find('dummy') != -1:
            self.show_grating(duration =10.0, profile = 'sqr', orientation = 0, velocity =50.0, white_bar_width = 100, display_area =  utils.cr((0, 0)), pos = utils.cr((0, 0)), color_contrast = 1.0)

class TestExpShort(experiment.Experiment):
    def run(self):
        self.show_grating(duration =1.0, profile = 'sqr', orientation = 0, velocity =50.0, white_bar_width = 100, display_area =  utils.cr((0, 0)), pos = utils.cr((0, 0)), color_contrast = 1.0)
        
class DotsExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.NDOTS = 20
        self.NFRAMES = 1
        self.PATTERN_DURATION = 10.0
        self.RANDOM_DOTS = True
        self.runnable = 'MultipleDotTest'
        self.pre_runnable = 'TestPre'
        self._create_parameters_from_locals(locals())
        
class MultipleDotTest(experiment.Experiment):
    def run(self):
        self.add_text('tex\nt', color = (1.0,  0.0,  0.0), position = utils.cr((100.0, 100.0)))
        self.change_text(0, text = 'aa')
        self.add_text('tex\nt', color = (1.0,  0.0,  0.0), position = utils.cr((100.0, 200.0)))
        self.disable_text(1)
        import random
        self.config = self.experiment_config.machine_config
        random.seed(0)
        dot_sizes = []
        dot_positions = []
        for j in range(self.experiment_config.NFRAMES):
            dot_sizes_per_frame = []
            dot_positions_per_frame = []
            if isinstance(self.experiment_config.NDOTS,  list):
                dots = ndots[j]
            else:
                dots = self.experiment_config.NDOTS
            for i in range(dots):
                coords = (random.random(),  random.random())
                coords = utils.rc(coords)
                dot_positions.append([coords['col'] * self.config.SCREEN_RESOLUTION['col'] - self.config.SCREEN_RESOLUTION['col'] * 0.5, coords['row'] * self.config.SCREEN_RESOLUTION['row'] - 0.5 * self.config.SCREEN_RESOLUTION['row']])
                dot_sizes.append(10 + 100 * random.random())
        
        dot_positions = utils.cr(numpy.array(dot_positions).transpose())
        dot_sizes = numpy.array(dot_sizes)
        if isinstance(self.experiment_config.NDOTS, list):
            colors = utils.random_colors(max(self.experiment_config.NDOTS), self.experiment_config.NFRAMES,  greyscale = True,  inital_seed = 0)
        else:
            colors = utils.random_colors(self.experiment_config.NDOTS, self.experiment_config.NFRAMES,  greyscale = True,  inital_seed = 0)
        if self.experiment_config.NFRAMES == 1:
            colors = [colors]
        
        if self.experiment_config.RANDOM_DOTS:
            self.show_dots(dot_sizes, dot_positions, self.experiment_config.NDOTS, duration = self.experiment_config.PATTERN_DURATION,  color = numpy.array(colors))
        else:
            side = 240.0
            dot_sizes = numpy.array([50, 30, 30, 30, 30, 20])
            colors = numpy.array([[[1.0,0.0,0.0],[1.0,1.0,1.0],[0.0,1.0,0.0],[0.0,0.0,1.0],[0.0,1.0,1.0],[0.8,0.0,0.0]]])
            dot_positions = utils.cr(numpy.array([[0, side, side, -side, -side, 1.5 * side], [0, side, -side, -side, side, 1.5 * side]]))
            ndots = 6
            self.show_dots(dot_sizes, dot_positions, ndots, duration = 4.0,  color = colors)    
            
