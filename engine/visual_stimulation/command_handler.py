import os
import time
import generic.utils

class CommandHandler():
    '''
    Responsible for interpreting incoming commands and calling the necessary functions
    '''
    def __init__(self, config, stimulation_control,  udp_interface,  user_interface):
        '''
        Initializes command buffer
        '''
        self.config = config
        self.stimulation_control = stimulation_control
        self.udp_interface = udp_interface
        self.user_interface = user_interface
        self.command_buffer = ''        
        
    def parse(self,  state,  command_buffer):
        '''
        Incoming string stream is parsed into commands depending on software state. When stimulation is running, incoming string is discarded
        '''
        result = 'no command executed'
        if state == 'idle':
            self.command_buffer = self.command_buffer + command_buffer
            parsed_bytes = 0
            if len(self.command_buffer) > 0:
#                print self.command_buffer
                cmd = self.command_buffer[0].lower()
                #parsing commands
                filterwheel_command = False                
                if len(self.command_buffer) == 2:                
                    #filterwheel control
                    try:
                        filterwheel = int(self.command_buffer[0])
                        filter_position = int(self.command_buffer[1])
                        filterwheel_command = True
                    except ValueError:
                        filterwheel_command = False                       
                if filterwheel_command:
                    parsed_bytes = 2
                    if self.config.FILTERWHEEL_ENABLE:
                        self.stimulation_control.filterwheels[filterwheel - 1].set(filter_position)
                        #TODO: handle invalid filterwheel ID
                        result =  'filterwheel' + str(filterwheel) + str(filter_position)
                    
                elif cmd == self.config.CMD_START: #start stimulation
                    parsed_bytes = 1
                    result = 'start stimulus ' + self.stimulation_control.runStimulation()
                elif cmd == self.config.CMD_SET_BACKGROUND_COLOR:
                    try:
                        background_color = float(self.command_buffer[1:].replace(' ',  ''))
                    except ValueError:
                        background_color = 0
                    self.stimulation_control.setStimulationScript('self.st.clear_screen(color = ' + str(background_color) +')')
                    self.stimulation_control.runStimulation()
                    parsed_bytes = len(self.command_buffer)
                elif cmd == self.config.CMD_SEND_FILE: #transfer file and start it
                    bytes_to_parse = self.command_buffer[1:]
                    parsed_bytes = len(self.command_buffer[1:]) + 1 #THIS MAY BE TEMPORARY                    
                    self.stimulation_control.setStimulationScript(bytes_to_parse)
                    self.stimulation_control.runStimulation()
                    result = 'file transferred and loaded'
                elif cmd == self.config.CMD_BULLSEYE: #show bullseye
                    try:
                        bullseye_size = float(self.command_buffer[1:].replace(' ',  ''))
                    except ValueError:
                        bullseye_size = 0
                    parsed_bytes = len(self.command_buffer)
                    if self.user_interface.clear_stimulus and (bullseye_size > 0 or len(self.command_buffer) == 1):
                        self.user_interface.clear_stimulus = False
                        self.stimulation_control.setStimulationScript('self.st.show_image(self.config.BULLSEYE_PATH,  duration = 0.0,  position = (0, 0), size = (' + str(bullseye_size) + ',' + str(bullseye_size) +'))')
                        self.stimulation_control.runStimulation()
                    elif not self.user_interface.clear_stimulus and (bullseye_size == 0 or len(self.command_buffer) == 1):
                        self.user_interface.clear_stimulus = True                    
                    result =  'bullseye'
                elif cmd == self.config.CMD_START_TEST: #run stimulation library test
                    parsed_bytes = 1
                    bullseye_size = 0
                    self.stimulation_control.setStimulationScript('self.st.stimulation_library_test()')
                    self.stimulation_control.runStimulation()
                    result =  'test stimulus library'                    
                elif cmd == self.config.CMD_GET_LOG:                    
                    parsed_bytes = 1
                    log_to_send = self.stimulation_control.last_stimulus_log()
                    self.udp_interface.send(str(len(log_to_send)))
                    if log_to_send < self.config.UDP_BUFFER_SIZE:
                        self.udp_interface.send(log_to_send)
                    else:
                        log_to_send_size = len(log_to_send)
                        for i in range(int(log_to_send_size / (self.config.UDP_BUFFER_SIZE * 0.5) + 1)):
                            start_index = int(0.5 * i * self.config.UDP_BUFFER_SIZE)
                            end_index = int((i + 1) * self.config.UDP_BUFFER_SIZE * 0.5 - 1)                    
                            if end_index > log_to_send_size:
                                end_index = log_to_send_size - 1
                            self.udp_interface.send(log_to_send[start_index:end_index])
                            time.sleep(WAIT_BETWEEN_UDP_SENDS)                            
                    result =  'send log ' + log_to_send
                elif cmd == self.config.CMD_SET_MEASUREMENT_ID:
                    bytes_to_parse = self.command_buffer[1:]
                    parsed_bytes = len(self.command_buffer[1:]) + 1 #THIS MAY BE TEMPORARY
                    self.stimulation_control.setMesurementId(bytes_to_parse)
                    result = 'measurement ID set'
                elif cmd == self.config.CMD_QUIT: #quit
                    parsed_bytes = 1
                    result =  'quit' 
                elif cmd == self.config.CMD_SET_STIMULUS_FILE_START and self.command_buffer.find(self.config.CMD_SET_STIMULUS_FILE_END)  > 0:  # set stimulation file
                    stimulus_filename = self.command_buffer[self.command_buffer.find('<')+1 :self.command_buffer.find('>') ] 
                    file = self.config.STIMULATION_FOLDER_PATH + os.sep + stimulus_filename
                    self.stimulation_control.setStimulationFile(file)
                    parsed_bytes = len(stimulus_filename) + 2
                    result =  'load file ' + stimulus_filename
                elif ord(cmd) >= 48 and ord(cmd) <= 58:  #select stimulation from default stimulation folder
                    file_index = int(self.command_buffer[0])
                    files = generic.utils.filtered_file_list(self.config.STIMULATION_FOLDER_PATH,  ['stimulus',  'example'])
                    files.sort()
                    file = self.config.STIMULATION_FOLDER_PATH + os.sep + files[file_index]
                    self.stimulation_control.setStimulationFile(file)
                    parsed_bytes = 1
                    result =  'load stimulation '  + self.command_buffer[0] + ' ' + self.stimulation_control.stimulation_file                
                else:
                    parsed_bytes = 1
                #remove parsed byte(s) from buffer
                self.command_buffer = self.command_buffer[parsed_bytes:]                
#            result = self.command_buffer
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
