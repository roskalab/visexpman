import socket
import threading
import sys

class TcpipListener(threading.Thread):
    '''Listens to tcpip messages and parses them'''
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        threading.Thread.__init__(self, group=group, target=target, name=name,
                                  verbose=verbose)
        self.config = args[0]
        self.runner = args[1]
        self.setDaemon(True)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bind the socket to the port
        server_address = ('localhost', 10000)
        self.socket.bind(server_address)
        return
        
    def run(self):
        self.socket.listen(1)
        while True:
            connection, client_address = self.socket.accept()
            try:
                # Receive the data in small chunks
                data = ''
                while True:
                    newdata = connection.recv(16)
                    data = data+newdata
                    if len(newdata)==0:
                        print >>sys.stderr, 'received "%s"' % data
                        #while self.runner.state !='idle':
                          #  time.sleep(0.3) # do not put data into buffer while processing buffer contents, even if it is 
                        self.runner.command_buffer.append(data) # append to list is thread safe
                        break
            except Exception as e:
                print e
                pass
            finally:
                # Clean up the connection
                connection.close()
            
class UdpInterface():
    """
    Udp server instance. This class handles all the UDP related communications (including sending/receiving files)
    """
    def __init__(self,  config):
        self.config = config
        if self.config.UDP_ENABLE:
            self.server_socket = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
            self.server_socket.bind( (self.config.CLIENT_UDP_IP,self.config.UDP_PORT) )
            self.server_socket.settimeout(0.001)
        
    def checkBuffer(self):
        if self.config.UDP_ENABLE:
            try:
                self.udp_buffer, addr = self.server_socket.recvfrom(self.config.UDP_BUFFER_SIZE)
                self.client_address = addr
            except socket.timeout:
                self.udp_buffer = ''
            return self.udp_buffer
        else:
            return ''
        
    def send(self,  message):
        if self.config.UDP_ENABLE:
            self.server_socket.sendto( message, self.client_address)
        
    def isAbortReceived(self):
        '''
        Checks if abort request is received
        '''
        if self.config.UDP_ENABLE:
            if self.checkBuffer() == 'a':
                self.send('a' + ' OK') 
                return True
            else:
                return False
        
    def __del__(self):
        if self.config.UDP_ENABLE:
            self.server_socket.close()
        
if __name__ == "__main__":
    u = UdpInterface()
    while 1:        
        resp =  u.checkBuffer()
        if resp != '':
            print resp
            u.send('asdasdsads......')
            
            
        exit = 0
        for i in range(len(resp)):
            if resp[i] == 'q':
                exit = 1
        if exit == 1:
            break
