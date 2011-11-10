import socket
import time
import sys
ip = "172.27.25.220"
ip = 'localhost'
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((ip, int(sys.argv[1])))
client_socket.send('dummy client started')
while True:    
    data = client_socket.recv(128)        
    client_socket.send(data)
    if len(data)>0:
        print data
    if data.find('SOCclose_connectionEOC') != -1:
        print 'exit'
        break
client_socket.close()
