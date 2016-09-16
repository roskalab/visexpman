import socket
import time
import sys
ip = "172.27.25.220"
ip = 'localhost'
ip = '172.27.26.13'
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((ip, int(sys.argv[1])))
client_socket.send('dummy client started')
st = time.time()
while True:    
    data = client_socket.recv(128)        
    client_socket.send(data+'resp')
    if len(data)>0 and data.find('echoEOCalive') == -1:
        print data
    if data.find('SOCacquire_z_stackEOC') != -1:
        print 'sleep'
        time.sleep(1.0)
        print 'send response'
        client_socket.send(data)
    if data.find('SOCclose_connectionEOC') != -1:
        print 'exit1'
        break
    if len(sys.argv) >2:        
        if time.time()-st>float(sys.argv[2]):
            print 'exit2'
            break
            
client_socket.close()
