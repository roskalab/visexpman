import sys
import socket
import os.path
import time
sys.path.append('../../../engine')
import visual_stimulation.configuration
import generic.utils as utils


class RemoteTesterConfig(visual_stimulation.configuration.VisualStimulationConfig):
    
    def _set_user_specific_parameters(self):                
        ENABLE_PARALLEL_PORT =False
        FULLSCR = False
        SCREEN_RESOLUTION = utils.rc[600,  800]
        self._set_parameters_from_locals(locals())

#Call params:
# 1. 1. argument: string of commands
# 2. 1. argument "t"
#     2. argument: path of stimfile to be sent

conf = RemoteTesterConfig('../../..')

try:
    command = sys.argv[1]
except IndexError:
    command = ''
    
try:
    stimulus_file = sys.argv[2]
    f = open(stimulus_file, 'rt')
    stimulation_code = f.read(os.path.getsize(stimulus_file))
    print stimulation_code
    f.close()
except IndexError:
    stimulus_file = ''
    stimulation_code = ''
    
print command,  stimulus_file

if command == 't':
    command = command + stimulation_code


sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
sock.sendto( command, (conf.SERVER_UDP_IP, conf.UDP_PORT) )
data, addr = sock.recvfrom( conf.UDP_BUFFER_SIZE )
print data

if command == 'g':
    data, addr = sock.recvfrom( conf.UDP_BUFFER_SIZE )
    sock.settimeout(5.0)
    log_length = int(data)
    print log_length    
    f = open('log' + str(time.time()).replace('.', '') + '.txt',  'wt')
    while True:
        data = ''
        try:
            data, a = sock.recvfrom( log_length )
            #print data
            f.write(data)
        except socket.timeout:
            break
           
        
    f.close()
