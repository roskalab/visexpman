import visexpman
import os,  sys
#While psychopy is not completely eliminated, this import is necessary under windows systems
if os.name == 'nt':
    from OpenGL.GL import *
    from OpenGL.GLUT import *
import time
import visexpman
import generic.utils
import visual_stimulation.user_interface
import hardware_interface.udp_interface
import visual_stimulation.stimulation_control
import visual_stimulation.command_handler
import visual_stimulation.configuration
import visexpman.users as users


class UnsupportedCommandLineArguments(Exception):
    pass

class VisualStimulation(object):
    def __init__(self, user,  config_class):
        '''
        Find out configuration and load the appropriate config and experiment modules, classes

		At the initialization the followings has to be accomplised:
        - find config class and instantiate it 
        - instantiate user interface, udp, stimulation control and command handler
        - create experiment list containing all the experiment classes residing in user folder
        - instantiate pre experiment config and pre experiment
        - experiment has to be instantiated in stimulation control not here!!!!     

        '''
        self.state = 'init'
        #== Fetch reference to config class and experiment config class ==
        self.config=generic.utils.fetch_classes('visexpman.users.'+user, classname=config_class, required_ancestors=visexpman.engine.visual_stimulation.configuration.VisionExperimentConfig)[0][1]()
        self.config.user=user
        #Lists all folders and python modules residing in the user's folder
        # this way of discovering classes has the drawback that modules searched must not have syntax errors
        classname = self.config.EXPERIMENT_CONFIG #RZ: This might be unnecessary
        self.experiment_config_list = generic.utils.fetch_classes('visexpman.users.'+self.config.user,  required_ancestors=visexpman.engine.visual_stimulation.experiment.ExperimentConfig)
        if len(self.experiment_config_list) > 10: raise RuntimeError('Maximum 10 different experiment types are allowed')
        self.selected_experiment_config = [ex1[1] for ex1 in self.experiment_config_list if ex1[1].__name__ == self.config.EXPERIMENT_CONFIG][0](self.config) # select and instantiate stimulus as specified in machine config
        #create screen
        self.user_interface = visual_stimulation.user_interface.UserInterface(self.config, self)
        self.stimulation_control = visual_stimulation.stimulation_control.StimulationControl(self, self.config,  self.user_interface)
        self.command_handler =  visual_stimulation.command_handler.CommandHandler(self.config,  self.stimulation_control,  self.user_interface, self)
        self.tcpip_listener = hardware_interface.udp_interface.TcpipListener(args=(self.config, self))
        self.tcpip_listener.start()
        self.abort=False
        self.command_buffer = []
        self.selected_experiment_config.pre_runnable.run()
        self.state='idle'
       # self.stimulation_control.runStimulation() #ez itt miert van hiva?

    def run(self):
        '''
        Run application. Check for commands coming from either keyboard or network. Command is parsed and handled by command handler
        '''
        while self.abort==False:
            # run the Pre class of the currently selected experiment
            if self.state =='new_stimulus' and hasattr(self.selected_experiment_config, 'pre_runnable') and self.selected_experiment_config.pre_runnable is not None:
                self.state= 'idle'
                self.selected_experiment_config.pre_runnable.run()
            else:
                if len(self.command_buffer)>0:
                    result = self.command_handler.parse(self.command_buffer[0]) # parse 1 item at once, tcpip can add more during processing but this should be safe since we always use the first element here
                    del self.command_buffer[0]
                time.sleep(0.1)
        self.user_interface.close()
        print 'run ended'
    
def find_out_config():
    '''
    Finds out configuration from the calling arguments. The following options are supported:
    - No argument: SafestartConfig is loaded
    - Username and config class name is encoded into one argument in the following form:
        user<separator>configclass, where separator can be: . , / \ <space> 
    - username and config class are provided as separate arguments
    '''        
    separators = [' ',  '.',  ',',  '/',  '\\']
    if len(sys.argv) == 1:
        config_class = 'SafestartConfig'
        user = ''
    elif len(sys.argv) == 2:
        for separator in separators:
            if sys.argv[1].find(separator) != -1:
                user = sys.argv[1].split(separator)[0]
                config_class = sys.argv[1].split(separator)[1]
    elif len(sys.argv) == 3:
        config_class = sys.argv[1]
        user = sys.argv[2]
    else:
        raise UnsupportedCommandLineArguments
    return config_class,  user

if __name__ == "__main__":
    VisualStimulation(*find_out_config()).run()
