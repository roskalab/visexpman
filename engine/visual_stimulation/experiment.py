from visexpman.engine.generic.configuration import Config
class ExperimentConfig(Config):
    pass

class Experiment():
    
    def __init__(self,  stimulus_library,  experiment_config):
        self.st = stimulus_library
        self.config = stimulus_library.config        
        self.experiment_config = experiment_config()
        
    def run(self):
        pass
        
    def cleanup(self):
        pass

class PreExperiment(Experiment):
    '''
    The run method of this experiment will be called prior the experiment to provide some initial stimulus while the experimental setup is being set up
    '''
    pass
    
class MultipleStimulus(Experiment):
    
    def run(self):
        self.stimulus_set = []
        i = 0
        for stim in self.config.STIMULUS_LIST:
            self.st._display_test_message(stim)            
            self.stimulus_set.append(getattr(sys.modules[__name__],  stim)(self.st))
            self.stimulus_set[i].run()            
            
            i = i + 1
            
    def cleanup(self):
        for single_stimulus in self.stimulus_set:
            single_stimulus.cleanup()
        print 'DONE'
