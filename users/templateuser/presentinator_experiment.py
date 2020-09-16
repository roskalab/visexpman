import visexpman
import visexpman.generic.utils as utils
import visexpman.visual_stimulation.experiment as experiment
import time
import shutil
import os

class PresentinatorExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.experiment_log_copy_path = ''
        self.color = 1.0
        self.duration = 1.0
        self.runnable = 'PresentinatorExperiment'
        self._create_parameters_from_locals(locals())

class PresentinatorExperiment(experiment.Experiment):
    def run(self):        
        self.show_fullscreen(duration = self.experiment_config.duration, color = self.experiment_config.color)               
        
    def cleanup(self):
        try:
            shutil.copyfile(self.logfile_path, self.experiment_config.experiment_log_copy_path)
        except:
            print 'not copied for some reason'
            
