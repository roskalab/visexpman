from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
import time
import numpy
            
class TemplateExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        #Define parameters here
        self.runnable = 'TemplateExperiment'
        self.pre_runnable = 'TemplatePreExperiment'
        self._create_parameters_from_locals(locals())

class TemplateExperiment(experiment.Experiment):
    def run(self):
        #Implement here your experiment
        pass
        
class TemplatePreExperiment(experiment.PreExperiment):    
  def run(self):
    #Call to stimulation_library without flipping
    pass
