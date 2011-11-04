#== For automated tests ==
import visexpman
from visexpman.engine.visual_stimulation.configuration import VisionExperimentConfig
from visexpman.engine.generic import utils
import visexpman.engine.visual_stimulation.experiment as experiment
import time
import numpy
import random
import os
import os.path
import serial
import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner

#== Very simple experiment ==
class VerySimpleExperimentTestConfig(VisionExperimentConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'VerySimpleExperimentConfig'        
        #paths
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        ARCHIVE_PATH = unit_test_runner.TEST_working_folder
        
        #screen
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])

        COORDINATE_SYSTEM='center'
        ARCHIVE_FORMAT = 'zip'
        self._create_parameters_from_locals(locals())

class VerySimpleExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'VerySimpleExperiment'
        self._create_parameters_from_locals(locals())

class VerySimpleExperiment(experiment.Experiment):
    def run(self):
        self.show_fullscreen(duration = 0.0, color = 1.0)
        
#== Hdf5 archiving ==

class Hdf5TestConfig(VisionExperimentConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'VerySimpleExperimentConfig'        
        #paths
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        ARCHIVE_PATH = unit_test_runner.TEST_working_folder
        
        #screen
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])

        COORDINATE_SYSTEM='center'
        ARCHIVE_FORMAT = 'hdf5'
        self._create_parameters_from_locals(locals())

#== Abortable experiment ==
class AbortableExperimentTestConfig(VisionExperimentConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'AbortableExperimentConfig'
        #paths
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        ARCHIVE_PATH = unit_test_runner.TEST_working_folder
        
        #screen
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])

        COORDINATE_SYSTEM='center'
        ARCHIVE_FORMAT = 'zip'
        self._create_parameters_from_locals(locals())

class AbortableExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'AbortableExperiment'
        self._create_parameters_from_locals(locals())

class AbortableExperiment(experiment.Experiment):
    def run(self):
        self.add_text('press \'a\'\n', color = (1.0,  0.0,  0.0), position = utils.cr((0.0,0.0)))
        self.show_fullscreen(duration = -1.0, color = 1.0)

#== User command experiment ==
class UserCommandExperimentTestConfig(VisionExperimentConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'UserCommandExperimentConfig'
        #paths
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        ARCHIVE_PATH = unit_test_runner.TEST_working_folder
        
        #screen
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])

        COORDINATE_SYSTEM='center'
        ARCHIVE_FORMAT = 'zip'
        
        USER_EXPERIMENT_COMMANDS = {'user_command': {'key': 'u', 'domain': ['running experiment']}, }
        
        self._create_parameters_from_locals(locals())

class UserCommandExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'UserCommandExperiment'
        self._create_parameters_from_locals(locals())

class UserCommandExperiment(experiment.Experiment):
    def run(self):
        self.add_text('press \'u\' then \'a\'\n', color = (1.0,  0.0,  0.0), position = utils.cr((0.0,0.0)))
        self.show_fullscreen(duration = -1.0, color = 1.0)
        if self.command_buffer.find('user_command') != -1:
            self.command_buffer.replace('user_command', '')
            self.log.info('%2.3f\tUser note'%self.elapsed_time)
            
#== External Hardware controlling experiment ==
class TestExternalHardwareExperimentTestConfig(VisionExperimentConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'VerySimpleExperimentConfig'
        #paths
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        ARCHIVE_PATH = unit_test_runner.TEST_working_folder       
        
        #screen
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])

        #Hardware configuration
        ENABLE_PARALLEL_PORT = True
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 2
        ENABLE_FILTERWHEEL = unit_test_runner.TEST_filterwheel_enable
        FILTERWHEEL_SERIAL_PORT = [[{
                                    'port' :  unit_test_runner.TEST_com_port,
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,
                                    }]]

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

        COORDINATE_SYSTEM='center'
        ARCHIVE_FORMAT = 'zip'
        self._create_parameters_from_locals(locals())

class TestExternalHardwareExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'TestExternalHardwareExperiment'
        self._create_parameters_from_locals(locals())

class TestExternalHardwareExperiment(experiment.Experiment):
    def run(self):
        self.show_fullscreen(duration = 0.0, color = 0.5)
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

#== Disabled hardware ==
class DisabledlHardwareExperimentTestConfig(VisionExperimentConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'TestExternalHardwareExperimentConfig'
        #paths
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        ARCHIVE_PATH = unit_test_runner.TEST_working_folder
        
        #screen
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])
        
        #Hardware configuration
        ENABLE_PARALLEL_PORT = False
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 2
        ENABLE_FILTERWHEEL = False
        
        DAQ_CONFIG = [[
                    {
#                     'ANALOG_CONFIG' : 'ao', #'ai', 'ao', 'aio', 'undefined'
#                     'DAQ_TIMEOUT' : 1.0,
#                     'AO_SAMPLE_RATE' : 100,
#                     'AO_CHANNEL' : unit_test_runner.TEST_daq_device + '/ao0:1',
#                     'AI_CHANNEL' : unit_test_runner.TEST_daq_device + '/ai9:0',
#                     'MAX_VOLTAGE' : 5.0,
#                     'MIN_VOLTAGE' : 0.0,
#                     'DURATION_OF_AI_READ' : 1.0,
                    'ENABLE' : False
                    }
                    ]]

        COORDINATE_SYSTEM='center'
        ARCHIVE_FORMAT = 'zip'
        self._create_parameters_from_locals(locals())
        
#== Test pre experiment ==
class PreExperimentTestConfig(VisionExperimentConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'PreExperimentConfig'
        #paths
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        ARCHIVE_PATH = unit_test_runner.TEST_working_folder     
        
        #screen
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])

        COORDINATE_SYSTEM='center'
        ARCHIVE_FORMAT = 'zip'
        self._create_parameters_from_locals(locals())

class PreExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'PreExperiment'
        self.pre_runnable = 'PrePreExperiment'
        self._create_parameters_from_locals(locals())

class PrePreExperiment(experiment.PreExperiment):
    def run(self):        
        self.show_fullscreen(duration = 0.0, color = 1.0, flip = False)
        self.caller.log.info('Pre experiment log')

class PreExperiment(experiment.Experiment):
    def run(self):
        self.show_fullscreen(duration = 0.0, color = 0.5)

#== Test visual stimulations ==

class VisualStimulationsTestConfig(VisionExperimentConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'VisualStimulationsExperimentConfig'
        #paths
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        ARCHIVE_PATH = unit_test_runner.TEST_working_folder
        CAPTURE_PATH = utils.generate_foldername(os.path.join(unit_test_runner.TEST_working_folder, 'capture'))
        os.mkdir(CAPTURE_PATH)
        
        #screen
        ENABLE_FRAME_CAPTURE = True
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])
        SCREEN_EXPECTED_FRAME_RATE = 20.0

        COORDINATE_SYSTEM='center'
        ARCHIVE_FORMAT = 'zip'
        self._create_parameters_from_locals(locals())
        
class VisualStimulationsUlCornerTestConfig(VisionExperimentConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'VisualStimulationsExperimentConfig'
        #paths
        LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        ARCHIVE_PATH = unit_test_runner.TEST_working_folder       
        CAPTURE_PATH = utils.generate_foldername(os.path.join(unit_test_runner.TEST_working_folder, 'capture'))
        os.mkdir(CAPTURE_PATH)
        
        #screen
        ENABLE_FRAME_CAPTURE = True
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])
        SCREEN_EXPECTED_FRAME_RATE = 20.0

        COORDINATE_SYSTEM='ulcorner'
        ARCHIVE_FORMAT = 'zip'
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
        self.show_fullscreen(flip = False)
        #== Test text on stimulus ==
        self.add_text('TEST', color = (1.0,  0.0,  0.0), position = utils.cr((100.0, 100.0)))
        self.change_text(0, text = 'TEST1')
        self.add_text('TEST2', color = 0.5, position = utils.cr((100.0, 200.0)))
        self.show_fullscreen(duration = 0.0, color = (1.0, 1.0, 1.0))
        self.disable_text(0)
        self.disable_text(1)        
        #== Test show_grating ==
        self.show_grating()
        self.show_grating(white_bar_width = 200)
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
        self.show_grating(duration =2.0/self.config.SCREEN_EXPECTED_FRAME_RATE, profile = 'sqr', orientation = 0, velocity = 800.0, white_bar_width = 40)
        #== Test show_dots ==        
        self.add_text('TEST', color = (0.0,  0.0,  1.0), position = utils.cr((200.0, 100.0)))
        ndots = 2
        dot_sizes = [100, 100]
        dot_positions = [utils.cr((0, 0)), utils.cr((100, 0))]
        self.show_dots(dot_sizes, dot_positions, ndots)
        self.disable_text()
        ndots = 3
        dot_sizes = [100, 100, 10]
        dot_positions = [utils.cr((0, 0)), utils.cr((100, 0)), utils.cr((100, 100))]
        self.show_dots(dot_sizes, dot_positions, ndots, color = (1.0,  1.0,  0.0))
        self.show_dots(dot_sizes, dot_positions, ndots, color = numpy.array([[[1.0,  1.0,  0.0], [1.0,  0.0,  0.0], [0.0,  0.0,  1.0]]]))        
        #Multiple frames
        ndots = 3
        dot_sizes = numpy.array([200, 200, 200, 20, 20, 20])
        dot_positions = numpy.array([utils.cr((0, 0)), utils.cr((200, 0)), utils.cr((200, 200)), utils.cr((0, 0)), utils.cr((200, 0)), utils.cr((100, 100))])
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

#TODO: test for usage of experiment config
