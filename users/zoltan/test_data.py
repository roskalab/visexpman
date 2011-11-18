from visexpman.engine.visual_stimulation.configuration import VisionExperimentConfig
from visexpman.engine.generic import utils
import visexpman.engine.visual_stimulation.experiment as experiment
import time
import numpy
import serial
import visexpman
import os.path
import os
import visexpman.engine.hardware_interface.daq_instrument as daq_instrument
import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner

#== For software development test ==

class LDC(VisionExperimentConfig):
    def _set_user_parameters(self):
        dataset = 0        
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
        ENABLE_UDP = False
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 2
        ENABLE_FILTERWHEEL = False
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
        FULLSCREEN = not False        
        SCREEN_RESOLUTION = utils.cr([800, 600])        
#        SCREEN_RESOLUTION = utils.cr([1680, 1050])        
#        SCREEN_RESOLUTION = utils.cr([1024, 768])        
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        GAMMA = 1.0
        ENABLE_TEXT = True
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
        
class MESExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'MESExperiment'
#        self.pre_runnable = 'TestPre'
        self._create_parameters_from_locals(locals())       

class MESExperiment(experiment.Experiment):
    def run(self):
        orientation = [0,45,90]
        for i in range(len(orientation)):
            self.mes_command.put('SOCacquire_line_scanEOCc:\\temp\\test\\line_scan_data{0}.matEOP'.format(i))
            self.show_grating(duration =1.0, profile = 'sqr', orientation = orientation[i], velocity = 500.0, white_bar_width = 100)
        

        

class TestExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'TestExp1'
#        self.pre_runnable = 'TestPre'
        self._create_parameters_from_locals(locals())
        
        
class TestPre(experiment.PreExperiment):
    def run(self):
        self.show_fullscreen(color = (0.28, 0.29, 0.3), flip = False)

class TestExp1(experiment.Experiment):
    def run(self):
        self.show_shape(shape = 'a', duration = 2.0,  size = 100.0, background_color = 120, ring_size = 10.0)
#        non_dot = False
#        #moving dots
#        
#        
#        dot_positions = utils.calculate_trajectory(utils.cr((-400.0, -300.0)), utils.cr((400.0, 300.0)), 10.1)        
#        n_frames = dot_positions.shape[0]
#        dot_sizes =numpy.ones(n_frames) * 50.0
#        ndots = 1
#        for i in range(3):
#            self.show_dots(dot_sizes, dot_positions, ndots, duration = 0.0)
#        
#        if non_dot:        
#            self.log.info('%2.3f\tMy log'%time.time())
#            self.show_fullscreen(duration = 3.0,  color = 0.5)
#            
#            #generate pulses        
#            offsets = [0, 0.2, 0.5]
#            pulse_widths = 0.1
#            amplitudes = 2.0
#            duration = 1.0
#            self.led_controller.set([[offsets, pulse_widths, amplitudes], [offsets, pulse_widths, amplitudes]], duration)
#            self.led_controller.start()
#            self.led_controller.release_instrument()
#            
#            import random
#            filter = int(5 * random.Random().random()) + 1
#            time.sleep(0.2)
#            self.filterwheels[0].set(filter)        
#            self.filterwheels[0].set_filter('ND0')
#            self.parallel_port.set_data_bit(0, 0)
#            time.sleep(0.1)
#            self.parallel_port.set_data_bit(0, 1)
#            
#            wait = 0.8
#            self.show_shape(size = 200.0, pos = utils.cr((-50, 100)))
#            time.sleep(wait)
#            self.show_shape(shape = 'circle', color = 200, duration = 2.0/self.machine_config.SCREEN_EXPECTED_FRAME_RATE, size = utils.cr((100.0, 200.0)))
#            time.sleep(wait)
#            self.show_shape(shape = 'r', size = 100.0, background_color = 100)
#            time.sleep(wait)
#            self.show_shape(shape = 'a', size = 100.0, background_color = 120, ring_size = 10.0)
#            time.sleep(wait)
#            self.show_shape(shape = 'a', size = utils.rc((100.0, 110)), ring_size = 10.0)
#            time.sleep(wait)
#            self.show_shape(shape = 'r', size = utils.rc((100.0, 110)), color = [1.0, 0.0,0.0], orientation = 45)
#            time.sleep(wait)
#            
#            self.show_grating(duration =1.0, profile = 'sqr', orientation = 0, velocity =50.0, white_bar_width = 100, display_area =  utils.cr((0, 0)), pos = utils.cr((0, 0)), color_contrast = 1.0)
#            if self.command_buffer.find('dummy') != -1:
#                self.show_grating(duration =10.0, profile = 'sqr', orientation = 0, velocity = 50.0, white_bar_width = 100, display_area =  utils.cr((0, 0)), pos = utils.cr((0, 0)), color_contrast = 1.0)

class TestExpShort(experiment.Experiment):
    def run(self):
        self.show_grating(duration =1.0, profile = 'sqr', orientation = 0, velocity = 50.0, white_bar_width = 100, display_area =  utils.cr((0, 0)), pos = utils.cr((0, 0)), color_contrast = 1.0)
