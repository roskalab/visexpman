####### Configurations, experiment configurations and experiments for automated tests #######
import time
import numpy
import random
import os
import os.path
import serial

import visexpman
from visexpman.engine.vision_experiment import configuration
from visexpman.engine.generic import utils
from visexpman.engine.generic import file
from visexpman.engine.vision_experiment import experiment

from visexpman.users.zoltan.test import unit_test_runner

class StandaloneConfig(configuration.VisionExperimentConfig):
    def _set_user_parameters(self):
        PLATFORM = 'standalone'
        EXPERIMENT_CONFIG = 'StandaloneExperimentConfig'
        #paths
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_DATA_PATH = unit_test_runner.TEST_working_folder
        
        #screen
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])

        COORDINATE_SYSTEM='center'
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        
        #Disabled hardware
                #Hardware configuration
        ENABLE_PARALLEL_PORT = False
        ENABLE_FILTERWHEEL = False
        ENABLE_MES = False
        
        DAQ_CONFIG = [
                    {
                    'ENABLE' : False
                    }
                    ]
        
        USER_EXPERIMENT_COMMANDS = {'user_command': {'key': 'u', 'domain': ['running experiment']}, }
        
        self._create_parameters_from_locals(locals())

class StandaloneExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'StandaloneExperiment'
        self.pre_runnable = 'PrePreExperiment'
        DURATION = [10.0, [1.0, 100.0]]
        self._create_parameters_from_locals(locals())

class PrePreExperiment(experiment.PreExperiment):
    def run(self):
        self.show_fullscreen(duration = 0.0, color = [0.4, 0.2, 0.1], flip = False)
        self.application_log.info('Pre experiment log')

class StandaloneExperiment(experiment.Experiment):
    def run(self):
        self.add_text('press \'u\' then \'a\'\n', color = (1.0,  0.0,  0.0), position = utils.cr((0.0,0.0)))
        self.show_fullscreen(duration = -1.0, color = 1.0)
        if 'user_command' in self.command_buffer:
            self.command_buffer.replace('user_command', '')
            self.log.info('%2.3f\tUser note'%self.elapsed_time)
        self.abort = False
        self.change_text(0, text = 'Tests continue')
        self.show_fullscreen(duration = 0.0, color = 0.0)
        #Using external hardware
        self.parallel_port.set_data_bit(1, 1)
        self.parallel_port.set_data_bit(1, 0)
        filter = int(5 * random.Random().random()) + 1
        time.sleep(0.2)
        self.filterwheels[0].set(filter)
        #generate pulses        
        offsets = [0, 0.2, 0.5]
        pulse_widths = [0.1,  0.1,  0.1]
        amplitudes = [2.0, 2.0, 2.0]
        duration = 1.0
        self.led_controller.set([[offsets, pulse_widths, amplitudes], [offsets, pulse_widths, amplitudes]], duration)
        self.led_controller.start()
        self.led_controller.release_instrument()
        #Test frame rate
        duration = self.experiment_config.DURATION
        self.t0 = time.time()
        self.show_grating(duration = duration, velocity = 500.0, white_bar_width = 200)
        self.t1 = time.time()
        self.frame_rate = (self.t1 - self.t0) / duration * self.machine_config.SCREEN_EXPECTED_FRAME_RATE
        print self.frame_rate
        self.log.info('Frame rate: ' + str(self.frame_rate))

class TestMesPlatformConfig(configuration.VisionExperimentConfig):
    '''
    Windows development machine
    '''
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'MesPlatformExperimentC'
        PLATFORM = 'mes'
        #=== paths/data handling ===
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder        
        EXPERIMENT_DATA_PATH = unit_test_runner.TEST_working_folder
        MES_DATA_FOLDER = EXPERIMENT_DATA_PATH.replace('/home/zoltan/visexp', 'V:').replace('/', '\\')
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        #=== screen ===
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])
        COORDINATE_SYSTEM='ulcorner'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        #=== experiment specific ===
        SCREEN_UM_TO_PIXEL_SCALE = 0.3
        MAXIMUM_RECORDING_DURATION = [10, [0, 10000]] #100
        MES_TIMEOUT = 10.0
        #=== Network ===
        ENABLE_UDP = False
        self.BASE_PORT = 10000
        COMMAND_RELAY_SERVER  = {
        'RELAY_SERVER_IP' : 'localhost', 
        'ENABLE' : True, 
        'CLIENTS_ENABLE' : True, 
        'TIMEOUT':10.0, 
        'CONNECTION_MATRIX':
            {
            'STIM_MES'  : {'STIM' : {'IP': 'localhost', 'PORT': self.BASE_PORT+2}, 'MES' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 3}}, 
            'GUI_STIM'  : {'GUI' : {'IP': 'localhost', 'PORT': self.BASE_PORT+4}, 'STIM' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 5}}, 
            }
        }
        #=== hardware ===
        ENABLE_PARALLEL_PORT = (self.OS == 'win')
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        FRAME_TRIGGER_PULSE_WIDTH = 1e-3
        #=== stage ===
        motor_serial_port = {
                                    'port' :  'COM1',
                                    'baudrate' : 19200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                    
                                    }
        STAGE = [{'serial_port' : motor_serial_port,
                 'enable': (self.OS == 'win'),
                 'speed': 800,
                 'acceleration' : 200,
                 'move_timeout' : 45.0,
                 'um_per_ustep' : (1.0/51.0)*numpy.ones(3, dtype = numpy.float)
                 }]
        #=== DAQ ===
        SYNC_CHANNEL_INDEX = 1
        DAQ_CONFIG = [
                    {
                    'ANALOG_CONFIG' : 'ai',
                    'DAQ_TIMEOUT' : 3.0,
                    'SAMPLE_RATE' : 5000,
                    'AI_CHANNEL' : 'Dev1/ai0:2',
                    'MAX_VOLTAGE' : 10.0,
                    'MIN_VOLTAGE' : -10.0,
                    'DURATION_OF_AI_READ' : 2*MAXIMUM_RECORDING_DURATION[0],
                    'ENABLE' : (self.OS == 'win')
                    },
                    {
                    'ANALOG_CONFIG' : 'ao',
                    'DAQ_TIMEOUT' : 3.0,
                    'SAMPLE_RATE' : 1000,
                    'AO_CHANNEL' : 'Dev1/ao0',
                    'MAX_VOLTAGE' : 10.0,
                    'MIN_VOLTAGE' : 0.0,
                    'ENABLE' : (self.OS == 'win')
                    }
                    ]
        self._create_parameters_from_locals(locals())

class MesPlatformExperimentC(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'MesPlatformExperiment'
        self._create_parameters_from_locals(locals())

class MesPlatformExperiment(experiment.Experiment):
    def prepare(self):
        self.number_of_fragments = 2
        self.fragment_durations = [3.0] * self.number_of_fragments

    def run(self, fragment_id = 0):
        self.show_fullscreen(duration = self.fragment_durations[fragment_id], color = fragment_id * 0.2 + 0.2)

class TestElphysPlatformConfig(configuration.VisionExperimentConfig):
    '''
    Windows development machine
    '''
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'ElphysPlatformExperimentCDummy'
        PLATFORM = 'elphys'
        #=== paths/data handling ===
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder        
        EXPERIMENT_DATA_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_FILE_FORMAT = 'mat'
        #=== screen ===
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])
        COORDINATE_SYSTEM='center'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        #=== experiment specific ===
        SCREEN_UM_TO_PIXEL_SCALE = 0.3
        MAXIMUM_RECORDING_DURATION = [10, [0, 10000]] #100
        #=== Network ===
        ENABLE_UDP = False
        #=== hardware ===
        ENABLE_PARALLEL_PORT = (self.OS == 'win')
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        FRAME_TRIGGER_PULSE_WIDTH = 1e-3
        #=== DAQ ===
        SYNC_CHANNEL_INDEX = 1
        DAQ_CONFIG = [
                    {
                    'ANALOG_CONFIG' : 'ai',
                    'DAQ_TIMEOUT' : 3.0,
                    'SAMPLE_RATE' : 5000,
                    'AI_CHANNEL' : 'Dev1/ai0:2',
                    'MAX_VOLTAGE' : 10.0,
                    'MIN_VOLTAGE' : -10.0,
                    'DURATION_OF_AI_READ' : 2*MAXIMUM_RECORDING_DURATION[0],
                    'ENABLE' : (self.OS == 'win')
                    },
                    {
                    'ANALOG_CONFIG' : 'ao',
                    'DAQ_TIMEOUT' : 3.0,
                    'SAMPLE_RATE' : 1000,
                    'AO_CHANNEL' : 'Dev1/ao0',
                    'MAX_VOLTAGE' : 10.0,
                    'MIN_VOLTAGE' : 0.0,
                    'ENABLE' : (self.OS == 'win')
                    }
                    ]
        self._create_parameters_from_locals(locals())

class ElphysPlatformExperimentCDummy(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'ElphysPlatformExperimentDummy'
        self._create_parameters_from_locals(locals())

class ElphysPlatformExperimentDummy(experiment.Experiment):
    def prepare(self):
        pass

    def run(self, fragment_id = 0):
        pass

#== Test visual stimulations ==
class VisualStimulationsTestConfig(configuration.VisionExperimentConfig):
    def _set_user_parameters(self):
        PLATFORM = 'standalone'
        EXPERIMENT_CONFIG = 'VisualStimulationsExperimentConfig'
        #paths
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_DATA_PATH = unit_test_runner.TEST_working_folder
        CAPTURE_PATH = file.generate_foldername(os.path.join(unit_test_runner.TEST_working_folder, 'capture'))
        os.mkdir(CAPTURE_PATH)
        
        #screen
        ENABLE_FRAME_CAPTURE = True
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])
        SCREEN_EXPECTED_FRAME_RATE = 60.0

        COORDINATE_SYSTEM='center'
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        self._create_parameters_from_locals(locals())
        
class VisualStimulationsUlCornerTestConfig(configuration.VisionExperimentConfig):
    def _set_user_parameters(self):
        PLATFORM = 'standalone'
        EXPERIMENT_CONFIG = 'VisualStimulationsExperimentConfig'
        #paths
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_DATA_PATH = unit_test_runner.TEST_working_folder       
        CAPTURE_PATH = file.generate_foldername(os.path.join(unit_test_runner.TEST_working_folder, 'capture'))
        os.mkdir(CAPTURE_PATH)
        
        #screen
        ENABLE_FRAME_CAPTURE = True
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])
        SCREEN_EXPECTED_FRAME_RATE = 60.0

        COORDINATE_SYSTEM='ulcorner'
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        self._create_parameters_from_locals(locals())
        
class VisualStimulationsScaledTestConfig(configuration.VisionExperimentConfig):
    def _set_user_parameters(self):
        PLATFORM = 'standalone'
        EXPERIMENT_CONFIG = 'VisualStimulationsExperimentConfig'
        #paths
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_DATA_PATH = unit_test_runner.TEST_working_folder       
        CAPTURE_PATH = file.generate_foldername(os.path.join(unit_test_runner.TEST_working_folder, 'capture'))
        os.mkdir(CAPTURE_PATH)
        
        #screen
        ENABLE_FRAME_CAPTURE = True
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_UM_TO_PIXEL_SCALE = 2.0

        COORDINATE_SYSTEM='ulcorner'
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        self._create_parameters_from_locals(locals())

class VisualStimulationsExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'VisualStimulationsExperiment'        
        self._create_parameters_from_locals(locals())

class VisualStimulationsExperiment(experiment.Experiment):
    def run(self):
        #== Test show_fullscreen ==
        self.show_fullscreen(color = 1.0)
        self.show_fullscreen()
        self.show_fullscreen(duration = 0.0, color = 255)
        self.show_fullscreen(duration = 0.0, color = (1.0, 1.0, 1.0))
        self.show_fullscreen(flip = False) #0004
        #== Test text on stimulus ==
        self.add_text('TEST', color = (1.0,  0.0,  0.0), position = utils.cr((100.0, 100.0)))
        self.change_text(0, text = 'TEST1')
        self.add_text('TEST2', color = 0.5, position = utils.cr((100.0, 200.0)))
        self.show_fullscreen(duration = 0.0, color = (1.0, 1.0, 1.0)) #0005
        self.disable_text(0)
        self.disable_text(1)        
        #== Test show_grating ==
        self.show_grating()
        self.show_grating(white_bar_width = 200)  #0007
        self.show_grating(duration =0.0, profile = 'sqr', orientation = 0, velocity = 0.0, white_bar_width = 100, display_area =  utils.cr((0, 0)), pos = utils.cr((0, 0)), color_contrast = 1.0)
        self.show_grating(duration =0.0, profile = 'sqr', orientation = 45, velocity = 50.0, white_bar_width = 100, display_area =  utils.cr((0, 0)), pos = utils.cr((0, 0)), color_contrast = 1.0, duty_cycle = 2.0)
        self.show_grating(duration =0.0, profile = 'sqr', orientation = 90, velocity = 50.0, white_bar_width = 100, display_area =  utils.cr((0, 0)), pos = utils.cr((0, 0)), color_contrast = 1.0, color_offset = 0.5)
        self.show_grating(duration =0.0, profile = 'sqr', orientation = 90, velocity = 50.0, white_bar_width = 100, display_area =  utils.cr((0, 0)), pos = utils.cr((0, 0)), color_contrast = 0.5, color_offset = 0.25)
        self.show_grating(duration =0.0, profile = 'sqr', orientation = 90, velocity = 50.0, white_bar_width = 100, display_area =  utils.cr((0, 0)), pos = utils.cr((0, 0)), color_contrast = (1.0, 0.3, 0.0) , color_offset = (0.5, 0.85, 0.0))
        self.show_grating(duration =0.0, profile = 'sqr', orientation = 90, velocity = 0.0, white_bar_width = 10, display_area =  utils.cr((100, 100)), pos = utils.cr((0, 0)), color_contrast = [1.0, 1.0, 1.0] , color_offset = 0.5)
        self.show_grating(duration =0.0, profile = 'sin', orientation = 10, velocity = 0.0, white_bar_width = 20, display_area =  utils.cr((600, 600)), color_contrast = 0.5 , color_offset = 0.25)
        self.show_grating(duration =0.0, profile = 'sin', orientation = 10, velocity = 0.0, white_bar_width = 20, display_area =  utils.cr((0, 600)), color_contrast = 0.5 , color_offset = 0.25)
        self.show_grating(duration =0.0, profile = 'sin', orientation = -10, velocity = 0.0, white_bar_width = 20, display_area =  utils.cr((600, 0)), pos = utils.cr((0, 0)), color_contrast = 0.5 , color_offset = 0.25)
        self.show_grating(duration =0.0, profile = 'tri', orientation = 350, velocity = 0.0, white_bar_width = 20, display_area =  utils.cr((100, 100)), pos = utils.cr((100, 0)), color_contrast = 0.5 , color_offset = 0.25)
        self.add_text('TEST', color = (0.0,  1.0,  0.0), position = utils.cr((100.0, 100.0)))        
        self.show_grating(duration =0.0, profile = 'tri', orientation = 350, starting_phase = 90.0, velocity = 0.0, white_bar_width = 20, display_area =  utils.cr((100, 100)), pos = utils.cr((100, 0)), color_contrast = 0.5 , color_offset = 0.25)
        self.disable_text()
        self.set_background(0.5)
        self.show_grating(duration =0.0, profile = 'saw', orientation = 0, starting_phase = 0.0, velocity = 0.0, white_bar_width = 50, display_area =  utils.cr((200, 100)), pos = utils.cr((300, 250)), color_contrast = 1.0 , color_offset = 0.5)        
        self.set_background(self.config.BACKGROUND_COLOR)
        #Test speed        
        self.show_grating(duration =2.0/self.config.SCREEN_EXPECTED_FRAME_RATE, profile = 'sqr', orientation = 0, velocity = 2400.0, white_bar_width = 40)
        #== Test show_dots ==        
        self.add_text('TEST', color = (0.0,  0.0,  1.0), position = utils.cr((200.0, 100.0)))
        ndots = 2
        dot_sizes = [100, 100]
        dot_positions = utils.cr(((0, 0), (100, 0)))
        self.show_dots(dot_sizes, dot_positions, ndots)
        self.disable_text()
        ndots = 3
        dot_sizes = [100, 100, 10]
        dot_positions = utils.cr(((0, 100, 0), (0, 0, 100)))
        self.show_dots(dot_sizes, dot_positions, ndots, color = (1.0,  1.0,  0.0))
        self.show_dots(dot_sizes, dot_positions, ndots, color = numpy.array([[[1.0,  1.0,  0.0], [1.0,  0.0,  0.0], [0.0,  0.0,  1.0]]]))        
        #Multiple frames
        ndots = 3
        dot_sizes = numpy.array([200, 200, 200, 20, 20, 20])
        dot_positions = utils.cr(((0, 200, 200, 0, 200, 100), (0, 0, 200, 0, 0, 100)))
        color = numpy.array([[[1.0,  1.0,  0.0], [1.0,  0.0,  0.0], [0.0,  0.0,  1.0]], [[1.0,  1.0,  0.0], [1.0,  0.0,  0.0], [0.0,  0.0,  1.0]]])
        self.show_dots(dot_sizes, dot_positions, ndots, duration = 2.0/self.config.SCREEN_EXPECTED_FRAME_RATE, color = color)
        #Test show_shape
        self.show_shape(size = 200.0, pos = utils.cr((-50, 100)))
        self.show_shape(shape = 'circle', color = 200, duration = 2.0/self.machine_config.SCREEN_EXPECTED_FRAME_RATE, size = utils.cr((100.0, 200.0)))
        self.show_shape(shape = 'r', size = 100.0, background_color = (1.0, 0.0, 0.0))        
        self.show_shape(shape = 'a', size = 100.0, background_color = 120, ring_size = 10.0) 
        self.add_text('TEST', color = (0.0,  0.0,  1.0), position = utils.cr((200.0, 100.0)))
        self.show_shape(shape = 'r', size = utils.rc((100.0, 200)), color = [1.0, 0.0,0.0], orientation = 10)
        self.disable_text()
        self.show_shape(shape = 'a', size = utils.rc((100.0, 200)), ring_size = 10.0)        

#== Stage test experiment ==
class StageExperimentTestConfig(configuration.VisionExperimentConfig):
    def _set_user_parameters(self):
        MEASUREMENT_PLATFORM = 'elphys'
        EXPERIMENT_CONFIG = 'StageExperimentConfig'        
        #paths
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_DATA_PATH = unit_test_runner.TEST_working_folder
        
        #screen
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])
        
        motor_serial_port = {
                                    'port' :  unit_test_runner.TEST_stage_com_port,
                                    'baudrate' : 19200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }
                                    
        STAGE = [{'serial_port' : motor_serial_port,
                 'enable': True,
                 'speed': 1000000,
                 'acceleration' : 1000000,
                 'move_timeout' : 45.0,
                 'um_per_ustep' : numpy.ones(3, dtype = numpy.float)
                 }]

        COORDINATE_SYSTEM='center'
        EXPERIMENT_FILE_FORMAT = 'zip'
        self._create_parameters_from_locals(locals())

class StageExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'StageExperiment'
        self._create_parameters_from_locals(locals())
        
class StageExperiment(experiment.Experiment):
    def run(self):
        self.initial_position = self.stage.position
        movement_vector = numpy.array([10000.0,1000.0,10.0])
        self.result1 = self.stage.move(movement_vector)
        self.result2 = self.stage.move(-movement_vector)
