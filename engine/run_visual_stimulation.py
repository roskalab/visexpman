import sys
import os.path

#Importing opengl before any importing any psychopy module is necessary to ensure operation under windows and non-standalone mode
if os.name == 'nt':
    from OpenGL.GL import *
    from OpenGL.GLUT import *

import UserInterface
import UdpInterface
import CommandHandler
import StimulationControl
import Configurations
import Experiment

class Presentinator():
    '''
    Main class that runs the main loop of Presentinator
    '''
    def __init__(self):
        '''
        Initializes application: objects are created
        
        Command line argument configuration class name
        
        '''
        
        #set default configurations when no command line parameter is provided
        if len(sys.argv) > 1:
        	self.config_class = sys.argv[1]
        else:            
			self.config_class = 'SafestartConfig'

        #determine execution mode
        setattr(self,  'config',  getattr(Configurations, self.config_class)())

        if self.config.RUN_MODE != 'user interface':
            self.config.set('TEXT_ENABLE',  False)
        
        self.ui = UserInterface.UserInterface(self.config)
        self.udp = UdpInterface.UdpInterface(self.config)
        self.sc = StimulationControl.StimulationControl(self.config,  self.ui,  self.udp)
        self.ch =  CommandHandler.CommandHandler(self.config,  self.sc,  self.udp,   self.ui)        
        
        
    def run(self):
        '''
        Run application. Check for commands coming from either keyboard or network. Command is parsed and handled by command handler
        '''        
        if self.config.RUN_MODE == 'single experiment':
            if os.path.exists(self.config.SINGLE_EXPERIMENT):
                self.sc.setStimulationFile(self.config.SINGLE_EXPERIMENT)
                self.sc.runStimulation()
            else:
                try:
                    getattr(Experiment, self.config.SINGLE_EXPERIMENT)
                    class_exists = True
                except:
                    print 'invalid experiment class'
                    class_exists = False
                if class_exists:
                    self.sc.runStimulation(self.config.SINGLE_EXPERIMENT)
                
        elif self.config.RUN_MODE == 'user interface':
                while True:
                    #check command interfaces:
                    command_buffer = self.ui.user_interface_handler()            
                    udp_command =  self.udp.checkBuffer()
                    if udp_command != '':
                        self.udp.send(udp_command + ' OK') 
                    command_buffer = command_buffer + udp_command
                    #parse commands
                    res = self.ch.parse(self.sc.state,  command_buffer)            
                    if res != 'no command executed':
                        self.ui.user_interface_handler(res)                
                        if res == 'quit':
                            self.ui.close()
                            break
        else:
            print 'invalid run mode'
    
    
if __name__ == "__main__":    
    Presentinator().run()
    
