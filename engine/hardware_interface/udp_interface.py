import socket

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
