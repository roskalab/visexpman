import logging
import os
import visexpman
from visexpman.engine.generic.configuration import Config
from visexpman.engine.generic import utils
import stimulation_library

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
            self.runnable= utils.fetch_classes('visexpman.users.'+ self.machine_config.user, classname = self.runnable,  required_ancestors = visexpman.engine.visual_stimulation.experiment.Experiment)[0][1](self.machine_config, self.caller, self) # instantiates the code that will run the actual stimulation
            if hasattr(self, 'pre_runnable'):
                self.pre_runnable = utils.fetch_classes('visexpman.users.'+ self.machine_config.user, required_ancestors = visexpman.engine.visual_stimulation.experiment.PreExperiment)[0][1](self.machine_config, self.caller, self) # instantiates the code that will run the pre experiment code

    def run(self):
        if self.runnable == None:
            raise ValueError('Specified stimulus class is not instantiated.')
        else:
            self.runnable.run()
        self.runnable.cleanup()
        
    def post_experiment(self):
        self.runnable.post_experiment()
        
    def set_experiment_control_context(self):
        self.runnable.set_experiment_control_context()

class Experiment(stimulation_library.Stimulations):
    def __init__(self, machine_config, caller, experiment_config):
        self.experiment_config = experiment_config
        self.machine_config = machine_config
        self.caller = caller
        stimulation_library.Stimulations.__init__(self, self.machine_config, self.caller)
        self.caller.log.info('init experiment %s'%(utils.class_name(self)))
            
    def set_experiment_control_context(self):
        '''
        This function ensures that the hardware related calls are available from the experiment/run method
        '''
        self.devices = self.caller.experiment_control.devices
        self.parallel_port = self.devices.parallel_port        
        self.filterwheels = self.devices.filterwheels
        self.stage = self.devices.stage        
        self.mes_command = self.caller.mes_command_queue
        self.mes_response = self.caller.mes_response_queue
        self.mes_interface = self.caller.experiment_control.devices.mes_interface
        self.gui_command = self.caller.gui_command_queue
        self.gui_response = self.caller.gui_response_queue
        self.gui_connection = self.caller.gui_connection
        self.zip = self.caller.experiment_control.data_handler.archive
        if self.machine_config.ARCHIVE_FORMAT == 'hdf5':
            self.hdf5 = self.caller.experiment_control.data_handler.hdf5_handler
        if hasattr(self.devices, 'led_controller'): #This hasattr checking is unnecessary
            self.led_controller = self.devices.led_controller
        self.log = self.caller.experiment_control.log
        self.logfile_path = self.caller.experiment_control.logfile_path
        self.command_buffer = ''
        self.abort = False
        self.experiment_name = self.__class__.__name__

    def run(self):
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
    def printl(self, message):
        '''
        Helper function that can be called during experiment. The message is sent to:
        -standard output
        -gui
        -experiment log
        '''
        print message
        self.gui_command.put(str(message))
        if hasattr(self, 'log'):
            self.log.info(str(message))
        

class PreExperiment(Experiment):
    '''
    The run method of this experiment will be called prior the experiment to provide some initial stimulus while the experimental setup is being set up.
    '''
    pass
    #TODO: Overlay menu on pre experiment visual stimulus so that the text is blended to the graphical pattern
    #Preexperiment can be a static image, that is always drawn when the non-experiment screen is redrawn.
    #Alternatively while preexperiment runs, keyboard handler&command handler shall be called.
