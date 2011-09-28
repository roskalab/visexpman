from visexpman.engine.visual_stimulation.configuration import VisualStimulationConfig
from visexpman.engine.generic import utils
import visexpman.engine.visual_stimulation.experiment as experiment
import os
import tempfile

#== Defaults ==
class DefaultExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'DefaultExperiment'
        self.pre_runnable = 'DefaultPreExperiment'
        self._create_parameters_from_locals(locals())
        
class DefaultPreExperiment(experiment.PreExperiment):
    def run(self):
        pass
        
class DefaultExperiment(experiment.Experiment):
    def run(self):
        pass
        
class SafestartConfig(VisualStimulationConfig):    
    def _set_user_parameters(self):
        EXPERIMENT_CONFIG = 'DefaultExperimentConfig'
        COORDINATE_SYSTEM = 'center'        
        FILTERWHEEL_ENABLE = False        
        ENABLE_PARALLEL_PORT = False
        ENABLE_UDP = False
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.rc([600, 800])
        
        tmp_folder = os.path.dirname(tempfile.mktemp())
        LOG_PATH = tmp_folder
        EXPERIMENT_LOG_PATH = tmp_folder
        BASE_PATH= tmp_folder
        ARCHIVE_PATH = tmp_folder        
        CAPTURE_PATH = tmp_folder
        
        ARCHIVE_FORMAT = 'zip'
        self._create_parameters_from_locals(locals())
