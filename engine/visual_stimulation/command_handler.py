import socket
import os
import time
import re
import PyQt4.QtCore as QtCore
#import visexpman.engine.hardware_interface.udp_interface as network_interface
import stimulation_control as experiment_control
command_extract = re.compile('SOC(.+)EOC') # a command is a string starting with SOC and terminated with EOC (End Of Command)
parameter_extract = re.compile('EOC(.+)EOP') # an optional parameter string follows EOC terminated by EOP. In case of binary data EOC and EOP should be escaped.

class CommandHandler():
    '''
    Responsible for interpreting incoming commands and calling the necessary functions
    '''
    def __init__(self, config, caller):
        '''
        TBD
        '''        
        self.machine_config = config
        self.caller = caller
        self.config = config
        #Initialize slected experiment config index
        for i in range(len(self.caller.experiment_config_list)):
            if self.caller.experiment_config_list[i][1].__name__ == self.config.EXPERIMENT_CONFIG:
                self.selected_experiment_config_index = i
                
        #Experiment counter will be used to identify each experiment (logging,....)
        self.experiment_counter = 0
        
    def process_command_buffer(self):
        '''
        Parsing all the commands in the command buffer
        '''
        result = ''        
        while not self.caller.command_queue.empty():
            result += '\n' + str(self.parse(self.caller.command_queue.get(),  state = self.caller.state))
        self.caller.command_buffer = []
        self.caller.screen_and_keyboard.message += result

    def select_experiment(self, par):
        '''
        Selects experiment config based on keyboard command and instantiates the experiment config class
        '''
        self.selected_experiment_config_index = int(par)        
        return 'selected experiment: ' + str(par) + ' '

    def execute_experiment(self, par):        
        #Experiment control class is always (re)created so that the necessary hardware initializations could take place
        self.caller.experiment_control = experiment_control.ExperimentControl(self.config, self.caller)
        #Run experiment
        self.caller.experiment_control.run_experiment()
        #Clean up experiment
        self.caller.experiment_control.finish_experiment()        
        self.experiment_counter += 1
        return 'experiment executed'

    def bullseye(self, par):
        #TODO: stimulus fajlla (experiment class) kene alakitani         
        return 'bullseye'
        
    def hide_menu(self, par):
        self.caller.screen_and_keyboard.hide_menu = not self.caller.screen_and_keyboard.hide_menu
        if self.caller.screen_and_keyboard.hide_menu:
            return ''
        else:
            return 'menu is unhidden'
            
    def abort_experiment(self, par):
        return 'abort_experiment'
        
    def quit(self, par):
        self.caller.loop_state = 'end loop'        
        return 'quit'        

    def parse(self,  command_buffer,  state = 'unspecified'):
        '''
        Incoming string stream is parsed into commands depending on software state. When stimulation is running, incoming string is discarded
        '''        
        result  = None
        if len(command_buffer) > 6: #SOC + EOC + 1 character is at least present in a command            
            cmd = command_extract.findall(command_buffer)
            par = parameter_extract.findall(command_buffer) #par is not at the beginning of the buffer            
            if len(par)>0:
                par = par[0]            
            if hasattr(self, cmd[0]):
                result=getattr(self, cmd[0])(par) # call the selected function with the optional parameter
            else:
                #If no function belong to the command, just return it. During experiment, keyboard commands are passed to command buffer this way.
                result = cmd[0]
            self.caller.log.info('Command handler: ' + result)
        return result
        
class CommandSender(QtCore.QThread):
    def __init__(self, config, caller, commands):
        self.config = config
        self.caller = caller
        self.commands = commands
        QtCore.QThread.__init__(self)
        
    def send_command(self, command):
        self.caller.command_queue.put(command)
        
    def run(self):
        for command in self.commands:
            time.sleep(command[0])
            self.send_command(command[1])            

    def close(self):
        self.terminate()
        self.wait()

if __name__ == "__main__":
    pass
