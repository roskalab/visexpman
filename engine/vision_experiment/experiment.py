import sys
import logging
import os
import visexpman
from visexpman.engine.generic.configuration import Config
from visexpman.engine.generic import utils
import stimulation_library
import inspect
import visexpA.engine.datahandlers.hdf5io as hdf5io
from visexpman.engine.generic import introspect
from visexpman.engine.vision_experiment import configuration

class ExperimentConfig(Config):
    def __init__(self, machine_config, queues, connections, application_log, experiment_class = None, source_code = None):
        self.machine_config = machine_config
        self.queues = queues
        self.connections = connections
        self.application_log = application_log
        Config.__init__(self, machine_config)
        if machine_config != None:
            self.create_runnable(experiment_class, source_code) # needs to be called so that runnable is instantiated and other checks are done        

    def create_runnable(self, experiment_class, source_code):
        if self.runnable == None:
            raise ValueError('You must specify the class which will run the experiment')
        else:
            if experiment_class == None and source_code == None:
                self.runnable = utils.fetch_classes('visexpman.users.'+ self.machine_config.user, classname = self.runnable,  required_ancestors = visexpman.engine.vision_experiment.experiment.Experiment)[0][1]\
                    (self.machine_config, self, self.queues, self.connections, self.application_log) # instantiates the code that will run the actual stimulation
            else:
                self.runnable = experiment_class(self.machine_config, self, self.queues, self.connections, self.application_log, source_code)
            if hasattr(self, 'pre_runnable'):
                for pre_experiment_class in  utils.fetch_classes('visexpman.users.'+ self.machine_config.user, required_ancestors = visexpman.engine.vision_experiment.experiment.PreExperiment):
                    if pre_experiment_class[1].__name__ == self.pre_runnable:
                        self.pre_runnable = pre_experiment_class[1](self.machine_config, self, self.queues, self.connections, self.application_log) # instantiates the code that will run the pre experiment code
                        break

    def run(self, fragment_id = 0):
        if self.runnable == None:
            raise ValueError('Specified stimulus class is not instantiated.')
        else:
            function_args = inspect.getargspec(self.runnable.run)
            if 'fragment_id' in function_args.args:
                self.runnable.run(fragment_id = fragment_id)
            else:
                self.runnable.run()
        self.runnable.cleanup()
        
    def post_experiment(self):
        self.runnable.post_experiment()
        
    def pre_first_fragment(self):
        self.runnable.pre_first_fragment()
        
    def set_experiment_control_context(self):
        self.runnable.set_experiment_control_context()

class Experiment(stimulation_library.Stimulations):
    '''
    The usage of experiment fragments assumes the existence of number_of_fragments variable
    The floowing variable is saved to the output file: self.experiment_specific_data
    '''
    def __init__(self, machine_config, experiment_config, queues, connections, application_log, source_code = None):
        self.experiment_config = experiment_config
        self.machine_config = machine_config
        self.queues = queues
        self.connections = connections
        if source_code != None:
            self.source_code = source_code
        self.experiment_name = self.__class__.__name__.split('_')[0]
        self.experiment_config_name = self.experiment_config.__class__.__name__
        self.prepare()
        stimulation_library.Stimulations.__init__(self, self.machine_config, application_log)

    def prepare(self):
        '''
        Compulsory outputs for fragmented mes experiments:
            self.number_of_fragments
            self.fragment_durations - list of fragment stim times in sec
            
        '''
        pass
        
    def pre_first_fragment(self):
        '''
        Called before run if experiment is fragmented
        '''

    def run(self, fragment_id = 0):
        '''
        fragment_id: experiment can be split up to measurement fragments.
        '''    
        pass

    def cleanup(self):
        '''
        Operations to execute right after running the experiment. Saving user specific files, closing instruments  that are not handled within Device class, user specific file operations
        '''
        pass
        
    def post_experiment(self):
        '''
        Instructions can be put here that are intended to execute after the whole experiment procedure, when all the logfiles are flushed
        '''
        pass
        
    ################# helpers ############################
#     def printl(self, message):
#         '''
#         Helper function that can be called during experiment. The message is sent to:
#         -standard output
#         -gui
#         -experiment log
#         '''
#         print message
#         self.to_gui.put(str(message))
#         if hasattr(self, 'log'):
#             self.log.info(str(message))
        

class PreExperiment(Experiment):
    '''
    The run method of this experiment will be called prior the experiment to provide some initial stimulus while the experimental setup is being set up.
    '''
    pass
    #TODO: Overlay menu on pre experiment visual stimulus so that the text is blended to the graphical pattern
    #Preexperiment can be a static image, that is always drawn when the non-experiment screen is redrawn.
    #Alternatively while preexperiment runs, keyboard handler&command handler shall be called.


######################### Restore experiment config from measurement data #########################

class MachineConfig(configuration.VisionExperimentConfig):
    def __init__(self, machine_config_dict, default_user = None):
        self.machine_config_dict = machine_config_dict
        self.default_user = default_user
        configuration.VisionExperimentConfig.__init__(self)
        
    def _set_user_parameters(self):
        copy_parameters = ['COORDINATE_SYSTEM']
        for k, v in self.machine_config_dict.items():
            if k in copy_parameters:
                setattr(self, k, v)
        if not hasattr(self, 'user'):
            self.user = self.default_user
        self._create_parameters_from_locals(locals())
        pass
        
def restore_experiment_config(experiment_config_name, fragment_hdf5_handler = None,  experiment_source = None,  machine_config_dict = None, user = None):
    if fragment_hdf5_handler != None and experiment_source == None and machine_config_dict == None:
        experiment_source = fragment_hdf5_handler.findvar('experiment_source').tostring()
        machine_config_dict = fragment_hdf5_handler.findvar('machine_config')
    machine_config = MachineConfig(machine_config_dict, default_user = user)
    introspect.import_code(experiment_source,'experiment_module',add_to_sys_modules=1)
    experiment_module = __import__('experiment_module')
    experiment_config = getattr(experiment_module, experiment_config_name)(machine_config = machine_config, caller = None)
    return experiment_config
    a = experiment_module.MovingDot(machine_config, None, experiment_config)
        
