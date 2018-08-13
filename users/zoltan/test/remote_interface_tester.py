import sys
import socket
import os.path
import time
import visexpman.engine.generic.configuration
import visexpman.engine.generic.utils as utils

class RemoteTesterConfig(visexpman.engine.generic.configuration.Config):
    def _create_application_parameters(self):
        SERVER_IP = 'localhost'
        SERVER_IP = '172.27.26.8'
        COMMAND_INTERFACE_PORT = [10000, [300,  65000]]
        
        ENABLE_UDP = True
        UDP_PORT = [446,  [300,  65000]]
        UDP_BUFFER_SIZE = [65536,  [1,  100000000]]
        
        MSG_LENGTH = [14, [1, 100]]
        self._create_parameters_from_locals(locals())

#class RemoteTesterConfig(visual_stimulation.configuration.VisionExperimentConfig):
#    
#    def _set_user_specific_parameters(self):                
#        ENABLE_PARALLEL_PORT =False
#        FULLSCR = False
#        SCREEN_RESOLUTION = utils.rc[600,  800]
#        self._set_parameters_from_locals(locals())

#Call params:
# 1. 1. argument: string of commands
# 2. 1. argument "t"
#     2. argument: path of stimfile to be sent

conf = RemoteTesterConfig()

try:
    command = sys.argv[1]
except IndexError:
    command = ''
    
try:
    stimulus_file = sys.argv[2]
    f = open(stimulus_file, 'rt')
    stimulation_code = f.read(os.path.getsize(stimulus_file))
#    print stimulation_code
    f.close()
except IndexError:
    stimulus_file = ''
    stimulation_code = ''

#print command,  stimulus_file

if command == 'execute_experiment':
    command = 'SOC' + command + 'EOC' + stimulation_code + 'EOP'
else:
    command = command.split(',')
    if len(command) == 1:
        command = 'SOC' + command[0] + 'EOC'
    else:
        command = 'SOC' + command[0] + 'EOC' + command[1] + 'EOP'
print(command)
sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
sock.sendto( command, (conf.SERVER_IP, conf.UDP_PORT) )
#data, addr = sock.recvfrom( conf.UDP_BUFFER_SIZE )
#print data
#
#if command == 'g':
#    data, addr = sock.recvfrom( conf.UDP_BUFFER_SIZE )
#    sock.settimeout(5.0)
#    log_length = int(data)
#    print log_length    
#    f = open('log' + str(time.time()).replace('.', '') + '.txt',  'wt')
#    while True:
#        data = ''
#        try:
#            data, a = sock.recvfrom( log_length )
#            #print data
#            f.write(data)
#        except socket.timeout:
#            break
#           
#        
#    f.close()
