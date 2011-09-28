#== For automated tests ==
from visexpman.engine.visual_stimulation.configuration import VisualStimulationConfig
from visexpman.engine.generic import utils
import visexpman.engine.visual_stimulation.experiment as experiment
import time
import numpy

#== Very simple experiment ==
class VerySimpleExperimentTestConfig(VisualStimulationConfig):
    def _set_user_parameters(self):
        #paths
        EXPERIMENT_CONFIG = 'VerySimpleExperimentConfig'
        LOG_PATH = '/media/Common/visexpman_data/test'
        EXPERIMENT_LOG_PATH = '/media/Common/visexpman_data/test'
        ARCHIVE_PATH = '/media/Common/visexpman_data/test'
        
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
        #paths
        EXPERIMENT_CONFIG = 'AbortableExperimentConfig'
        LOG_PATH = '/media/Common/visexpman_data/test'
        EXPERIMENT_LOG_PATH = '/media/Common/visexpman_data/test'
        ARCHIVE_PATH = '/media/Common/visexpman_data/test'
        
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
        #paths
        EXPERIMENT_CONFIG = 'UserCommandExperimentConfig'
        LOG_PATH = '/media/Common/visexpman_data/test'
        EXPERIMENT_LOG_PATH = '/media/Common/visexpman_data/test'
        ARCHIVE_PATH = '/media/Common/visexpman_data/test'
        
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
