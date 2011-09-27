import socket
import os
import time
import re
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
        
#    def filterwheel(self, par):
#        pass
##        filterwheel = int(self.command_buffer[0])
##        filter_position = int(self.command_buffer[1])
##        if self.machine_config.FILTERWHEEL_ENABLE:
##            self.stimulation_control.filterwheels[filterwheel - 1].set(filter_position)
##            #TODO: handle invalid filterwheel ID
##            return  'filterwheel' + str(filterwheel) + str(filter_position)
#            
#    
#        
#    def set_background_color(self, par):
#        try:
#            background_color = float(self.command_buffer[1:].replace(' ',  ''))
#        except ValueError:
#            background_color = 0
##        self.stimulation_control.setStimulationScript('self.st.clear_screen(color = ' + str(background_color) +')')
##        self.stimulation_control.run_stimulation()
#    
#    def send_file(self, par):
#        bytes_to_parse = self.command_buffer[1:]
#        parsed_bytes = len(self.command_buffer[1:]) + 1 #THIS MAY BE TEMPORARY                    
##        self.stimulation_control.setStimulationScript(bytes_to_parse)
##        self.stimulation_control.run_stimulation()
#        return 'file transferred and loaded'
#        
#    
#        
#    def start_test(self, par):
#        '''
#        stimulation library test
#        '''
#        bullseye_size = 0
##        self.stimulation_control.setStimulationScript('self.st.stimulation_library_test()')
##        self.stimulation_control.run_stimulation()
#        return  'test stimulus library'
#        
#    def get_log(self, par):
##        log_to_send = self.stimulation_control.last_stimulus_log()
#        log_to_send = ''
#        self.udp_interface.send(str(len(log_to_send)))
#        if log_to_send < self.machine_config.UDP_BUFFER_SIZE:
#            self.udp_interface.send(log_to_send)
#        else:
#            log_to_send_size = len(log_to_send)
#            for i in range(int(log_to_send_size / (self.machine_config.UDP_BUFFER_SIZE * 0.5) + 1)):
#                start_index = int(0.5 * i * self.machine_config.UDP_BUFFER_SIZE)
#                end_index = int((i + 1) * self.machine_config.UDP_BUFFER_SIZE * 0.5 - 1)                    
#                if end_index > log_to_send_size:
#                    end_index = log_to_send_size - 1
#                self.udp_interface.send(log_to_send[start_index:end_index])
#                time.sleep(WAIT_BETWEEN_UDP_SENDS)                            
#        return  'send log ' + log_to_send
#        
#    def set_measurement_id(self, par):
#        bytes_to_parse = self.command_buffer[1:]
#        parsed_bytes = len(self.command_buffer[1:]) + 1 #THIS MAY BE TEMPORARY
##        self.stimulation_control.setMesurementId(bytes_to_parse)
#        result = 'measurement ID set'
#        
#    
#        
#    done = False
#    
#    def capture_keypress(self):
#        '''Call this method when you want to process keys pressed on the keyboard'''
#        while not done:
#            for event in pygame.event.get():
#                if (event.type == KEYUP) or (event.type == KEYDOWN):
#                    return event

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
                result = cmd[0]
            self.caller.log.info('Command handler: ' + result)
#                elif cmd == self.machine_config.CMD_SET_STIMULUS_FILE_START and self.command_buffer.find(self.machine_config.CMD_SET_STIMULUS_FILE_END)  > 0:  # set stimulation file
#                    stimulus_filename = self.command_buffer[self.command_buffer.find('<')+1 :self.command_buffer.find('>') ] 
#                    file = self.machine_config.STIMULATION_FOLDER_PATH + os.sep + stimulus_filename
#                    self.stimulation_control.setStimulationFile(file)
#                    parsed_bytes = len(stimulus_filename) + 2
#                    result =  'load file ' + stimulus_filename
#                elif ord(cmd) >= 48 and ord(cmd) <= 58:  #select stimulation from default stimulation folder
#                    file_index = int(self.command_buffer[0])
#                    files = generic.utils.filtered_file_list(self.machine_config.STIMULATION_FOLDER_PATH,  ['stimulus',  'example'])
#                    files.sort()
#                    file = self.machine_config.STIMULATION_FOLDER_PATH + os.sep + files[file_index]
#                    self.stimulation_control.selected_experiment_config = file
#                    parsed_bytes = 1
#                    result =  'load stimulation '  + self.command_buffer[0] + ' ' + self.stimulation_control.stimulation_file                
#        print 'command executed' #this is only for development purposes, later this shall be removed
#        import sys
#        sys.exit()
        return result
    
#def test():
#    '''
#    Test cases:
#    - invalid state
#    - invalid command
#    - valid commands following each other
#    - valid commands and dummy characters are mixed
#    '''
#    test_configurations = [
#                                    {
#                                    'name' : 'invalid state', 
#                                    'expected results': ['no command executed'], 
#                                    'iterations' : 1,
#                                    'states': ['dummy'], 
#                                    'commands' : ['s']
#                                    }, 
#                                    {
#                                    'name' : 'invalid command', 
#                                    'expected results': ['no command executed'], 
#                                    'iterations' : 1,
#                                    'states': ['idle'], 
#                                    'commands' : [' ']
#                                    }, 
#                                    {
#                                    'name' : 'multiple valid commands', 
#                                    'expected results': ['start stimulus', 'load file stimulus.py', 'bullseye', 'no command executed'], 
#                                    'iterations' : 4,
#                                    'states': ['idle',  'idle',  'idle',  'stimulation'], 
#                                    'commands' : ['s<stimulus.py>', 'bbs',  '',  '' ]
#                                    }, 
#                                    {
#                                    'name' : 'multiple valid commands mixed with valid ones', 
#                                    'expected results': ['start stimulus', 'no command executed', 'no command executed', 'load file stimulus.py', 'bullseye', 'no command executed',  'no command executed',  'start stimulus',  'quit', 'no command executed'], 
#                                    'iterations' : 10,
#                                    'states': ['idle',  'idle',  'idle',  'idle',  'idle',  'idle', 'idle',  'idle',  'idle',  'idle'], 
#                                    'commands' : ['sd <stimulus.py>', 'b',  '86',  'sq',  '', '', 'g', '', '', '' ]
#                                    },                                    
#                                    ]
#    for test_configuration in test_configurations:
#        test_case(test_configuration)
#    
#def test_case(configuration):    
#    ch =  CommandHandler()
#    result = True
#    for i in range(configuration['iterations']):         
#        res = ch.parse(configuration['states'][i],  configuration['commands'][i])         
#        if res != configuration['expected results'][i]:
#            result = False
#    print 'test case: ' + configuration['name'] + ': ' + str(result)
#    return result
    
if __name__ == "__main__":
#    test()
    pass
