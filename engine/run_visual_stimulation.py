import sys
import os
import os.path
import generic.utils
sys.path.append('..' ) 
import users
#import visual_stimulation




class UnsupportedCommandLineArguments(Exception):
    pass

class VisualStimulation(object):
    def __init__(self):
        #find out config class and user name from command line arguments
        self.find_out_config()
        #Lists all folders and python modules residing in the user's folder
        directories, python_modules = generic.utils.find_files_and_folders('..' + os.sep + 'users' + os.sep + self.user,  'py')
        #all directories are added to python path
        for directory in directories:
            sys.path.append(directory)            
        #find module where the configuration class resides
        config_module_name = generic.utils.find_class_in_module(python_modules, self.config_class)
        __import__('users.' + self.user + '.' + config_module_name)
        #instantiate configuration class
        setattr(self,  'config',  getattr(getattr(getattr(users,  self.user),  config_module_name), self.config_class)('..'))
        #HERE TO CONTINUE!!!!!!!!!!!!!: find out run mode, experiment, load experiment class        
    
    def find_out_config(self):
        '''
        Finds out configuration from the calling arguments. The following options are supported:
        - No argument: SafestartConfig is loaded
        - Username and config class name is encoded into one argument in the following form:
            user<separator>configclass, where separator can be: . , / \ <space> 
        - username and config class are provided as separate arguments
        '''        
        separators = [' ',  '.',  ',',  '/',  '\\']
        if len(sys.argv) == 1:
            self.config_class = 'SafestartConfig'
        elif len(sys.argv) == 2:
            for separator in separators:
                if sys.argv[1].find(separator) != -1:
                    self.user = sys.argv[1].split(separator)[0]
                    self.config_class = sys.argv[1].split(separator)[1]
        elif len(sys.argv) == 3:
            self.config_class = sys.argv[1]
            self.user = sys.argv[2]
        else:
            raise UnsupportedCommandLineArguments
        
    def run(self):
        pass

if __name__ == "__main__":    
    VisualStimulation().run()
#import sys
#import os.path
#import os
#
##Importing opengl before any importing any psychopy module is necessary to ensure operation under windows and non-standalone mode
#if os.name == 'nt':
#    from OpenGL.GL import *
#    from OpenGL.GLUT import *
#    
#if os.name == 'nt':
#    sys.path.append(os.path.dirname(sys.argv[0]) + '\generic' )
#else:
#    sys.path.append('../users/zoltan/test' ) 
#
#import visual_stimulation.user_interface
#import hardware_interface.udp_interface
#import visual_stimulation.command_handler
#import visual_stimulation.stimulation_control
#import visual_stimulation.configuration
#import visual_stimulation.experiment
#
#class Presentinator():
#    '''
#    Main class that runs the main loop of Presentinator
#    '''
#    def __init__(self):
#        '''
#        Initializes application: objects are created
#        
#        Command line argument configuration class name
#        
#        '''
#        
#        #set default configurations when no command line parameter is provided
#        if len(sys.argv) > 1:
#        	self.config_class = sys.argv[1]
#        else:            
#			self.config_class = 'SafestartConfig'
#
#        #determine execution mode
#        setattr(self,  'config',  getattr(configuration, self.config_class)())
#
#        if self.config.RUN_MODE != 'user interface':
#            self.config.set('TEXT_ENABLE',  False)
#        
#        self.ui = UserInterface.UserInterface(self.config)
#        self.udp = UdpInterface.UdpInterface(self.config)
#        self.sc = StimulationControl.StimulationControl(self.config,  self.ui,  self.udp)
#        self.ch =  CommandHandler.CommandHandler(self.config,  self.sc,  self.udp,   self.ui)        
#        
#        
#    def run(self):
#        '''
#        Run application. Check for commands coming from either keyboard or network. Command is parsed and handled by command handler
#        '''        
#        if self.config.RUN_MODE == 'single experiment':
#            if os.path.exists(self.config.SINGLE_EXPERIMENT):
#                self.sc.setStimulationFile(self.config.SINGLE_EXPERIMENT)
#                self.sc.runStimulation()
#            else:
#                try:
#                    getattr(Experiment, self.config.SINGLE_EXPERIMENT)
#                    class_exists = True
#                except:
#                    print 'invalid experiment class'
#                    class_exists = False
#                if class_exists:
#                    self.sc.runStimulation(self.config.SINGLE_EXPERIMENT)
#                
#        elif self.config.RUN_MODE == 'user interface':
#                while True:
#                    #check command interfaces:
#                    command_buffer = self.ui.user_interface_handler()            
#                    udp_command =  self.udp.checkBuffer()
#                    if udp_command != '':
#                        self.udp.send(udp_command + ' OK') 
#                    command_buffer = command_buffer + udp_command
#                    #parse commands
#                    res = self.ch.parse(self.sc.state,  command_buffer)            
#                    if res != 'no command executed':
#                        self.ui.user_interface_handler(res)                
#                        if res == 'quit':
#                            self.ui.close()
#                            break
#        else:
#            print 'invalid run mode'
    
    
#if __name__ == "__main__":    
#    Presentinator().run()
    
