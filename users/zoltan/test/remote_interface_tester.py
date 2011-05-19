import sys
import socket
import os.path
import time

import Configurations

conf = Configurations.RemoteTesterConfig(os.getcwd())

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
