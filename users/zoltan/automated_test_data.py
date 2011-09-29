#== For automated tests ==
import visexpman
from visexpman.engine.visual_stimulation.configuration import VisualStimulationConfig
from visexpman.engine.generic import utils
import visexpman.engine.visual_stimulation.experiment as experiment
import time
import numpy
import random
import os
import os.path

#== Very simple experiment ==
class VerySimpleExperimentTestConfig(VisualStimulationConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'VerySimpleExperimentConfig'        
        #paths
        if os.name == 'nt':
            path = 'c:\\_del'
        elif os.name == 'posix':
            path = '/media/Common/visexpman_data'
        LOG_PATH = path
        EXPERIMENT_LOG_PATH = os.path.join(path,'test')
        ARCHIVE_PATH = os.path.join(path,'test')
        
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

#== Abortable experiment ==
class AbortableExperimentTestConfig(VisualStimulationConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'AbortableExperimentConfig'
        #paths
        if os.name == 'nt':
            path = 'c:\\_del'
        elif os.name == 'posix':
            path = '/media/Common/visexpman_data'
        LOG_PATH = path
        EXPERIMENT_LOG_PATH = os.path.join(path,'test')
        ARCHIVE_PATH = os.path.join(path,'test')
        
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
class UserCommandExperimentTestConfig(VisualStimulationConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'UserCommandExperimentConfig'
        #paths
        if os.name == 'nt':
            path = 'c:\\_del'
        elif os.name == 'posix':
            path = '/media/Common/visexpman_data'
        LOG_PATH = path
        EXPERIMENT_LOG_PATH = os.path.join(path,'test')
        ARCHIVE_PATH = os.path.join(path,'test')
        
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
            self.log.info('%2.3f\tUser note'%time.time())
            
#== External Hardware controlling experiment ==
class TestExternalHardwareExperimentTestConfig(VisualStimulationConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'VerySimpleExperimentConfig'
        #paths
        if os.name == 'nt':
            path = 'c:\\_del'
        elif os.name == 'posix':
            path = '/media/Common/visexpman_data'
        LOG_PATH = path
        EXPERIMENT_LOG_PATH = os.path.join(path,'test')
        ARCHIVE_PATH = os.path.join(path,'test')        
        
        #screen
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])
        
        #Hardware configuration
        ENABLE_PARALLEL_PORT = visexpman.test_parallel_port
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 2
        FILTERWHEEL_ENABLE = True

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
        
#== Disabled hardware ==
class DisabledlHardwareExperimentTestConfig(VisualStimulationConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'TestExternalHardwareExperimentConfig'
        #paths
        if os.name == 'nt':
            path = 'c:\\_del'
        elif os.name == 'posix':
            path = '/media/Common/visexpman_data'
        LOG_PATH = path
        EXPERIMENT_LOG_PATH = os.path.join(path,'test')
        ARCHIVE_PATH = os.path.join(path,'test')        
        
        #screen
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])
        
        #Hardware configuration
        ENABLE_PARALLEL_PORT = False
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 2
        FILTERWHEEL_ENABLE = False

        COORDINATE_SYSTEM='center'
        ARCHIVE_FORMAT = 'zip'
        self._create_parameters_from_locals(locals())
        
#== Test pre experiment ==
class PreExperimentTestConfig(VisualStimulationConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'PreExperimentConfig'
        #paths
        if os.name == 'nt':
            path = 'c:\\_del'
        elif os.name == 'posix':
            path = '/media/Common/visexpman_data'
        LOG_PATH = path
        EXPERIMENT_LOG_PATH = os.path.join(path,'test')
        ARCHIVE_PATH = os.path.join(path,'test')        
        
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

class VisualStimulationsTestConfig(VisualStimulationConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'VisualStimulationsExperimentConfig'
        #paths
        if os.name == 'nt':
            path = 'c:\\_del'
        elif os.name == 'posix':
            path = '/media/Common/visexpman_data'
        LOG_PATH = path
        EXPERIMENT_LOG_PATH = os.path.join(path,'test')
        ARCHIVE_PATH = os.path.join(path,'test')        
        CAPTURE_PATH = os.path.join(path,'capture_' + str(int(time.time())))
        os.mkdir(CAPTURE_PATH)
        
        #screen
        ENABLE_FRAME_CAPTURE = True
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])
        SCREEN_EXPECTED_FRAME_RATE = 20.0

        COORDINATE_SYSTEM='center'
        ARCHIVE_FORMAT = 'zip'
        self._create_parameters_from_locals(locals())
        
class VisualStimulationsUlCornerTestConfig(VisualStimulationConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'VisualStimulationsExperimentConfig'
        #paths
        if os.name == 'nt':
            path = 'c:\\_del'
        elif os.name == 'posix':
            path = '/media/Common/visexpman_data'
        LOG_PATH = path
        EXPERIMENT_LOG_PATH = os.path.join(path,'test')
        ARCHIVE_PATH = os.path.join(path,'test')        
        CAPTURE_PATH = os.path.join(path,'capture_' + str(int(time.time())))
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
