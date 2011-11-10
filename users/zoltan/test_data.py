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
        ENABLE_PARALLEL_PORT = False
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
        
        #LED controller        
        DAQ_CONFIG = [[
                    {
                    'ANALOG_CONFIG' : 'ao', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 1.0,
                    'AO_SAMPLE_RATE' : 100,
                    'AO_CHANNEL' : unit_test_runner.TEST_daq_device + '/ao0:1',
                    'AI_CHANNEL' : unit_test_runner.TEST_daq_device + '/ai9:0',
                    'MAX_VOLTAGE' : 5.0,
                    'MIN_VOLTAGE' : 0.0,
                    'DURATION_OF_AI_READ' : 1.0,
                    'ENABLE' : True
                    }
                    ]]

        self._create_parameters_from_locals(locals())

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

        MES = {'ENABLE' : True, 'ip': '',  'port' : 20001,  'receive buffer' : 256}
        #screen
        FULLSCREEN = False        
        SCREEN_RESOLUTION = utils.cr([800, 600])        
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
            self.show_grating(duration =1.0, profile = 'sqr', orientation = orientation[i], velocity = 50.0, white_bar_width = 100)
        
    def cleanup(self):
        #Empty command buffer, this shall be done by experiment control
        time.sleep(0.1)
        while not self.mes_command.empty():
            print self.mes_command.get()

        

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

class ManipulationExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        
        MAX_LED_VOLTAGE = [10.0, [0.0, 20.0]]
        self.MID_GREY = 165.0/255.0
        self.stimulation_type = 'grating'#flicker, grating, spots        #PAR
        self.stimulation_length = 20.0 #s   #PAR
        self.pause_between_manipulation_and_control = 0.0*90.0 #s
        self.stimulation_protocol = 'control' #control, manipulation, both
        
        #flash parameters
        self.enable_flash = True    #PAR
        self.flash_width = 1e-3#seconds     #PAR
        self.flash_intensity = 1.0#PU       #PAR
        self.flash_color = 'blue'
        self.delay_after_flash = 5.0 #s min 5 sec       #PAR
        #general stimulus parameters
        self.spot_size = 50.0 #50-1000 um           #PAR
        self.background_color = self.MID_GREY       #PAR
        #spot stimulus parameters
        self.on_time = 2.0 #s
        self.off_time = 2.0 #s
        self.spot_contrast = 1.0 #      #PAR        
        #flickering stimulus parameters
        self.flicker_contrast = 1.0     #PAR
        self.flicker_mid_contrast = self.MID_GREY       #PAR
        self.flicker_frequency = 2.5 #Hz            #PAR
        self.flicker_background = True
        self.flicker_background_contrast_change = 1.0
        self.flicker_background_mid_contrast = self.MID_GREY
        self.flicker_background_frequency = 1.0/4.0 #Hz
        self.flicker_background_waveform = 'square' #steps, square
        #grating
        self.spatial_frequency = 0.01#cycle per degree 0.0012-0.155
        self.temporal_frequency = 1.0
        self.grating_contrast = 1.0
        self.grating_mid_contrast = self.MID_GREY
        self.grating_angle = 0.0 #degrees
        self.grating_size = utils.cr((0, 0))
        
        self.runnable = 'ManipulationExperiment'
        self._create_parameters_from_locals(locals())

class ManipulationExperiment(experiment.Experiment):
    def run(self):
        self.show_fullscreen(color =  self.experiment_config.background_color)
        if self.experiment_config.enable_flash:
            #generate pulses        
            offsets = [0]
            pulse_widths = [self.experiment_config.flash_width]
            amplitudes = [self.experiment_config.MAX_LED_VOLTAGE *  self.experiment_config.flash_intensity]
            duration = self.experiment_config.delay_after_flash + self.experiment_config.flash_width
            self.led_controller.set([[offsets, pulse_widths, amplitudes], [offsets, pulse_widths, amplitudes]], duration)
            self.led_controller.start()
            
        if self.experiment_config.stimulation_protocol == 'both':
            repetitions = 2
        else:
            repetitions = 1
        for i in range(repetitions):
            #Here starts the stimulus
            if self.experiment_config.stimulation_type == 'spots':
                number_of_periods = int(round(self.experiment_config.stimulation_length / float(self.experiment_config.on_time + self.experiment_config.off_time), 0))
                for period in range(number_of_periods):
                    self.show_shape(shape = 'o',  duration = self.experiment_config.on_time,  color = self.experiment_config.spot_contrast, 
                                        background_color = self.experiment_config.background_color,  size = self.experiment_config.spot_size)
                    self.show_fullscreen(duration = self.experiment_config.on_time, color =  self.experiment_config.background_color)
            elif self.experiment_config.stimulation_type == 'grating':
                screen_width = self.machine_config.SCREEN_RESOLUTION['col'] / self.machine_config.SCREEN_PIXEL_TO_UM_SCALE
                white_bar_width = screen_width/(2*self.experiment_config.spatial_frequency * 360.0)                 
                velocity = self.experiment_config.temporal_frequency * 2 * white_bar_width
                self.show_grating(duration = self.experiment_config.stimulation_length,  profile = 'sin',  white_bar_width = white_bar_width,   
                                  display_area = self.experiment_config.grating_size,  orientation = self.experiment_config.grating_angle,  
                                  velocity = velocity,  color_contrast = self.experiment_config.grating_contrast, color_offset = self.experiment_config.grating_mid_contrast)
            
            #End of stimulus
            if i == 0 and self.experiment_config.stimulation_protocol == 'both':
                time.sleep(self.experiment_config.pause_between_manipulation_and_control)
                
        if self.experiment_config.enable_flash:
            self.led_controller.release_instrument()
