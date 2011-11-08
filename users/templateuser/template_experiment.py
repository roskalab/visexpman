import visual_stimulation.experiment
import generic.configuration
import generic.utils

class TemplateExperimentConfig(visual_stimulation.experiment.ExperimentConfig):
    def _create_application_parameters(self):
        #place for experiment parameters
        #parameter with range: list[0] - value, list[1] - range
        #path parameter: parameter name contains '_PATH'
        #string list: list[1] - empty        
        PARAMETER = 'dummy'
        self._create_parameters_from_locals(locals())
        

class TemplateExperiment(visual_stimulation.experiment.Experiment):
    
    def run(self):
        #accessing an experiment parameter
        print self.experiment_config.PARAMETER
        #calls to stimulation library
        #self.st.stimulation_library_function()
        pass

class TemplatePreExperiment(visual_stimulation.experiment.PreExperiment):    
  def run(self):
    #calls to stimulation library
    pass
