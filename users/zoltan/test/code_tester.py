#import time
#import socket
#import sys
#import PyQt4.Qt as Qt
#import PyQt4.QtGui as QtGui
#import PyQt4.QtCore as QtCore
#import visexpman.engine.generic.utils as utils
#import visexpman.engine.generic.configuration as configuration
#import visexpman.engine.hardware_interface.network_interface as network_interface
#import Queue
#import visexpman.engine.visexpman_gui
#
#class Server(QtCore.QThread):
#    def __init__(self, config, name, queue):
#        self.config = config
#        QtCore.QThread.__init__(self)
#        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#        server_address = ('', self.config.MES['port'])
#        self.socket.bind(server_address)
#        self.sleep_sec=0
#        
#    def run(self):
#        self.socket.listen(1)
#        
#        while True: #this while loop is intended to revive listening after an error?
#            print('listening')
#            if self.sleep_sec==0:
#                connection, client_address = self.socket.accept()
#                #print(str(self.sleep_sec))
#                try:
#                    data = ''
#                    while True and self.sleep_sec==0:
##                        connection.sendall('command')#TMP
#                        newdata = connection.recv(16)
#                        data = data+newdata
#                        if len(newdata)==0:
#                            #print >>sys.stderr, 'received "%s"' % data
#                            print data
#                            break
#                except Exception as e:
#                    print e
#                finally:
#                    # Clean up the connection
#                    connection.close()
#                    
#if __name__ == '__main__':
#    queue = Queue.Queue()
#    config = visexpman.engine.visexpman_gui.GuiConfig()
#    server = Server(config, '', queue)
#    server.start()
##    time.sleep(1.0)
##    sock = socket.create_connection((config.MES['ip'], config.MES['port']))
##    sock.sendall('hello')
#    time.sleep(int(sys.argv[1]))
#'172.27.30.76'
#    server = network_interface.NetworkListener('localhost', queue, socket.SOCK_STREAM, 10001)
#    server.start()
##    time.sleep(0.3)
##    sender = network_interface.NetworkSender1(config, socket.SOCK_STREAM, config.MES['port'],  'hello')
##    sender.start()      
##    time.sleep(1.0)
##    sender1 = network_interface.NetworkSender1(config, socket.SOCK_STREAM, config.MES['port'],  'hello')
##    sender1.start()      
#    time.sleep(int(sys.argv[1]))
# TCP server example
import socket
import time
import sys
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(("", int(sys.argv[1])))
#server_socket.settimeout(1.0)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.listen(1)
st = time.time()
c = 0
client_socket, address = server_socket.accept()
print 'connection accepted'
repeats = 5
data = client_socket.recv(128)
print data
for i in range(repeats):
    time.sleep(1.0)
    command = 'SOCacquire_camera_imageEOC/path/path/file.mEOP'.format(i)
    if i == repeats-1:
        command = 'SOCclose_connectionEOCEOP'.format(i)
    for i in range(len(command)):
        client_socket.send(command[i])
        time.sleep(10e-3)
    print 'sent out ' + command
    time.sleep(0.2)
    data = client_socket.recv(128)    
    print time.time()-st,  data
    if  time.time()-st> 100.0:
        break
data = client_socket.recv(128)    
print data
time.sleep(1.5)
client_socket.close()

    
