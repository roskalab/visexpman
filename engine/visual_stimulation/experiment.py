import visexpman
from visexpman.engine.generic.configuration import Config
from visexpman.engine.generic import utils
import visexpman.engine.visual_stimulation.stimulation_library as stimulation_library

class ExperimentConfig(Config):
    def __init__(self, machine_config, caller):
        self.caller = caller
        self.machine_config = machine_config
        Config.__init__(self, machine_config)
        self.create_runnable() # needs to be called so that runnable is instantiated and other checks are done

    def create_runnable(self):
        if self.runnable == None:
            raise ValueError('You must specify the class which will run the experiment')
        else: 
            self.runnable= utils.fetch_classes('visexpman.users.'+self.machine_config.user, classname = self.runnable,  classtype = visexpman.engine.visual_stimulation.experiment.Experiment)[0][1](self.machine_config, self.caller, self) # instantiates the code that will run the actual stimulation
            self.pre_runnable = utils.fetch_classes('visexpman.users.'+self.machine_config.user, classtype = visexpman.engine.visual_stimulation.experiment.PreExperiment)[0][1](self.machine_config, self.caller, self) # instantiates the code that will run the actual stimulation
    def run(self):  #RZ: Why is the experiment started by the experiment config class?
        if self.runnable == None:
            raise ValueError('Specified stimulus class is not instantiated.')
        else:
            self.runnable.run()

class Experiment(stimulation_library.Stimulations):
#class Experiment():
    def __init__(self, machine_config, caller, experiment_config):
        self.experiment_config = experiment_config
        self.machine_config = machine_config
        self.caller = caller
        stimulation_library.Stimulations.__init__(self, self.machine_config, self.caller)

    def run(self):
        pass

    def cleanup(self):
        pass

class PreExperiment(Experiment):
    '''
    The run method of this experiment will be called prior the experiment to provide some initial stimulus while the experimental setup is being set up.
    '''
    pass
    #TODO: Overlay menu on pre experiment visual stimulus so that the text is blended to the graphical pattern
    #Preexperiment can be a static image, that is always drawn when the non-experiment screen is redrawn.
    #Alternatively while preexperiment runs, keyboard handler&command handler shall be called.

#class MultipleStimulus(Experiment):
#    
#    def run(self):
#        self.stimulus_set = []
#        i = 0
#        for stim in self.config.STIMULUS_LIST:
#            self.st._display_test_message(stim)            
#            self.stimulus_set.append(getattr(sys.modules[__name__],  stim)(self.st))
#            self.stimulus_set[i].run()            
#            
#            i = i + 1
#            
#    def cleanup(self):
#        for single_stimulus in self.stimulus_set:
#            single_stimulus.cleanup()
#        print 'DONE'
