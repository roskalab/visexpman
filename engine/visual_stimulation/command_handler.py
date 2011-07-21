import os
import time
import re
command_extract = re.compile('SOC(.+)EOC') # a command is a string starting with SOC and terminated with EOC (End Of Command)
parameter_extract = re.compile('EOC(.+)EOP') # an optional parameter string follows EOD terminated by EOP. In case of binary data EOC and EOP should be escaped.

class CommandHandler():
    '''
    Responsible for interpreting incoming commands and calling the necessary functions
    '''
    def __init__(self, config, stimulation_control,   user_interface,  runner):
        '''
        Initializes command buffer
        '''
        self.machine_config = config
        self.stimulation_control = stimulation_control
        self.user_interface = user_interface
        self.runner = runner
     
    def filterwheel(self, par):
        filterwheel = int(self.command_buffer[0])
        filter_position = int(self.command_buffer[1])
        if self.machine_config.FILTERWHEEL_ENABLE:
            self.stimulation_control.filterwheels[filterwheel - 1].set(filter_position)
            #TODO: handle invalid filterwheel ID
            return  'filterwheel' + str(filterwheel) + str(filter_position)
            
    def start_stimulation(self, par):
        return 'start stimulus ' + str(self.stimulation_control.runStimulation())
        
    def set_background_color(self, par):
        try:
            background_color = float(self.command_buffer[1:].replace(' ',  ''))
        except ValueError:
            background_color = 0
        self.stimulation_control.setStimulationScript('self.st.clear_screen(color = ' + str(background_color) +')')
        self.stimulation_control.runStimulation()
    
    def send_file(self, par):
        bytes_to_parse = self.command_buffer[1:]
        parsed_bytes = len(self.command_buffer[1:]) + 1 #THIS MAY BE TEMPORARY                    
        self.stimulation_control.setStimulationScript(bytes_to_parse)
        self.stimulation_control.runStimulation()
        return 'file transferred and loaded'
        
    def bullseye(self, par):
        # stimulus fajlla kene alakitani
        try:
            bullseye_size = float(self.command_buffer[1:].replace(' ',  ''))
        except ValueError:
            bullseye_size = 0
        parsed_bytes = len(self.command_buffer)
        if self.user_interface.clear_stimulus and (bullseye_size > 0 or len(self.command_buffer) == 1):
            self.user_interface.clear_stimulus = False
            self.stimulation_control.setStimulationScript('self.st.show_image(self.machine_config.BULLSEYE_PATH,  duration = 0.0,  position = (0, 0), size = (' + str(bullseye_size) + ',' + str(bullseye_size) +'))')
            self.stimulation_control.runStimulation()
        elif not self.user_interface.clear_stimulus and (bullseye_size == 0 or len(self.command_buffer) == 1):
            self.user_interface.clear_stimulus = True                    
        return 'bullseye'
        
    def start_test(self, par):
        '''stimulation library test'''
        bullseye_size = 0
        self.stimulation_control.setStimulationScript('self.st.stimulation_library_test()')
        self.stimulation_control.runStimulation()
        return  'test stimulus library'   
        
    def get_log(self, par):
        log_to_send = self.stimulation_control.last_stimulus_log()
        self.udp_interface.send(str(len(log_to_send)))
        if log_to_send < self.machine_config.UDP_BUFFER_SIZE:
            self.udp_interface.send(log_to_send)
        else:
            log_to_send_size = len(log_to_send)
            for i in range(int(log_to_send_size / (self.machine_config.UDP_BUFFER_SIZE * 0.5) + 1)):
                start_index = int(0.5 * i * self.machine_config.UDP_BUFFER_SIZE)
                end_index = int((i + 1) * self.machine_config.UDP_BUFFER_SIZE * 0.5 - 1)                    
                if end_index > log_to_send_size:
                    end_index = log_to_send_size - 1
                self.udp_interface.send(log_to_send[start_index:end_index])
                time.sleep(WAIT_BETWEEN_UDP_SENDS)                            
        return  'send log ' + log_to_send
        
    def set_measurement_id(self, par):
        bytes_to_parse = self.command_buffer[1:]
        parsed_bytes = len(self.command_buffer[1:]) + 1 #THIS MAY BE TEMPORARY
        self.stimulation_control.setMesurementId(bytes_to_parse)
        result = 'measurement ID set'
        
    def quit(self, par):
        self.runner.abort = True
        return 'quit'
        
    
    def parse(self,  command_buffer,  state = 'unspecified'):
        '''
        Incoming string stream is parsed into commands depending on software state. When stimulation is running, incoming string is discarded
        '''
        if len(command_buffer) > 6: #SOC + EOC + 1 character is at least present in a command
            cmd = command_extract.findall(command_buffer)
            par = parameter_extract.findall(command_buffer) #par is not at the beginning of the buffer
            if len(par)>0:
                par = par[0]
            result=getattr(self, cmd[0])(par) # call the selected function with the optional parameter                
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
        print 'command executed' #this is only for development purposes, later this shall be removed
        import sys
        sys.exit()
        return result
    
def test():
    '''
    Test cases:
    - invalid state
    - invalid command
    - valid commands following each other
    - valid commands and dummy characters are mixed
    '''
    test_configurations = [
                                    {
                                    'name' : 'invalid state', 
                                    'expected results': ['no command executed'], 
                                    'iterations' : 1,
                                    'states': ['dummy'], 
                                    'commands' : ['s']
                                    }, 
                                    {
                                    'name' : 'invalid command', 
                                    'expected results': ['no command executed'], 
                                    'iterations' : 1,
                                    'states': ['idle'], 
                                    'commands' : [' ']
                                    }, 
                                    {
                                    'name' : 'multiple valid commands', 
                                    'expected results': ['start stimulus', 'load file stimulus.py', 'bullseye', 'no command executed'], 
                                    'iterations' : 4,
                                    'states': ['idle',  'idle',  'idle',  'stimulation'], 
                                    'commands' : ['s<stimulus.py>', 'bbs',  '',  '' ]
                                    }, 
                                    {
                                    'name' : 'multiple valid commands mixed with valid ones', 
                                    'expected results': ['start stimulus', 'no command executed', 'no command executed', 'load file stimulus.py', 'bullseye', 'no command executed',  'no command executed',  'start stimulus',  'quit', 'no command executed'], 
                                    'iterations' : 10,
                                    'states': ['idle',  'idle',  'idle',  'idle',  'idle',  'idle', 'idle',  'idle',  'idle',  'idle'], 
                                    'commands' : ['sd <stimulus.py>', 'b',  '86',  'sq',  '', '', 'g', '', '', '' ]
                                    },                                    
                                    ]
    for test_configuration in test_configurations:
        test_case(test_configuration)
    
def test_case(configuration):    
    ch =  CommandHandler()
    result = True
    for i in range(configuration['iterations']):         
        res = ch.parse(configuration['states'][i],  configuration['commands'][i])         
        if res != configuration['expected results'][i]:
            result = False
    print 'test case: ' + configuration['name'] + ': ' + str(result)
    return result
    
if __name__ == "__main__":
    test()
