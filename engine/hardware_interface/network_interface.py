import socket
#import threading
import Queue
import sys
import time
import unittest
import visexpman.engine.generic.configuration
import PyQt4.QtCore as QtCore
import os

#Try: multiple clients, client thread starts in a thread, command buffer mutual exclusion. check out thread/target parameter
#Network listener -> CommandServer

class NetworkListener(QtCore.QThread):
    ''' Waits for connections on the port specified
    '''
    def __init__(self, ip_address, command_queue, socket_type, port,  udp_buffer_size=65535):        #TODO reorganize the order of these parameters
        target = None
        name = None
        QtCore.QThread.__init__(self)
        self.command_queue = command_queue
        self.socket_type = socket_type
        #set up socket
        self.socket = socket.socket(socket.AF_INET, self.socket_type)
        # Bind the socket to the port
        server_address = (ip_address, port)
        self.udp_buffer_size = udp_buffer_size
        self.socket.bind(server_address)
        if 1 and self.socket_type ==  socket.SOCK_DGRAM: #why only for UDP?
            self.socket.settimeout(0.001)
        self.sleep_sec=0
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self):
        if self.socket_type ==  socket.SOCK_STREAM:
            self.socket.listen(1)
            #print('listening')
            while True: #this while loop is intended to revive listening after an error?
                if self.sleep_sec==0:
                    connection, client_address = self.socket.accept()
                    #print(str(self.sleep_sec))
                    try:
                        data = ''
                        while True and self.sleep_sec==0:
                            newdata = connection.recv(16)
                            data = data+newdata
                            if len(newdata)==0:
                                #print >>sys.stderr, 'received "%s"' % data
                                print data
                                self.command_queue.put(data)
                                break
                    except Exception as e:
                        print e
                    finally:
                        # Clean up the connection
                        connection.close()
                else:
                    self.sleep(self.sleep_sec)
                    self.sleep_sec=0
        elif self.socket_type ==  socket.SOCK_DGRAM:
            while True:
                if self.sleep_sec==0:
                    try:
                        udp_buffer, addr = self.socket.recvfrom(self.udp_buffer_size)
                        self.client_address = addr
    #                    print udp_buffer
                        self.command_queue.put(udp_buffer)
    #                 except socket.timeout:
    #                     pass
                    except:
                        pass
                else:
                    self.sleep(self.sleep_sec)
                    self.sleep_sec=0

                    
    def close(self):
#        if self.socket_type ==  socket.SOCK_STREAM:
#            self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()


class NetworkSender(QtCore.QThread):    
    '''
    '''
    def __init__(self, config, socket_type, port):
        target = None
        name = None
        QtCore.QThread.__init__(self)
        self.config = config
        self.port = port
        self.socket_type = socket_type

    def run(self):
        for i in range(self.config.MSG_LENGTH):
            if self.socket_type ==  socket.SOCK_STREAM:
                sock = socket.create_connection((self.config.SERVER_IP, self.port))
                sock.sendall(str(i))
            elif self.socket_type ==  socket.SOCK_DGRAM:
                sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
                sock.sendto( str(i), (self.config.SERVER_IP, self.config.UDP_PORT) )            
            time.sleep(0.1)

class NetworkInterfaceTestConfig(visexpman.engine.generic.configuration.Config):
    def _create_application_parameters(self):
        SERVER_IP = 'localhost'
        import random
        COMMAND_INTERFACE_PORT = [10000 + int(10000 * random.random()), [300,  65000]]
        
        ENABLE_UDP = True
        UDP_PORT = [10000 + int(10000 * random.random()),  [300,  65000]]
        UDP_BUFFER_SIZE = [65536,  [1,  100000000]]
        
        MSG_LENGTH = [14, [1, 100]]
        self._create_parameters_from_locals(locals())

class testRunner():
    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(False)

    def run(self):
        print 'test runner started'        
        config = NetworkInterfaceTestConfig()
        listener = NetworkListener(config.SERVER_IP, self.command_queue, socket.SOCK_STREAM, config.COMMAND_INTERFACE_PORT)
        sender1 = NetworkSender(config, socket.SOCK_STREAM, config.COMMAND_INTERFACE_PORT)
        sender2 = NetworkSender(config, socket.SOCK_STREAM, config.COMMAND_INTERFACE_PORT)
        listener.start()
        sender1.start()
        time.sleep(0.5)
        sender2.start()
        time.sleep(0.5)        
        self.response = ''
        while not self.command_queue.empty():
            self.response += self.command_queue.get()
        print self.response
        listener.close()

class testNetworkInterface(unittest.TestCase):
    def setUp(self):
        self.state = 'ready'
        self.config = NetworkInterfaceTestConfig()

    def test_01_single_sender(self):
        self.command_queue = Queue.Queue()        
        self.listener1 = NetworkListener(self.config.SERVER_IP, self.command_queue, socket.SOCK_STREAM, self.config.COMMAND_INTERFACE_PORT)
        sender = NetworkSender(self.config, socket.SOCK_STREAM, self.config.COMMAND_INTERFACE_PORT)
        self.listener1.start()
        sender.start()
        if os.name == 'nt':
            time.sleep(2.5)
        elif os.name == 'posix':
            time.sleep(1.5)
        response = ''
        while not self.command_queue.empty():
            response += self.command_queue.get()        
        expected_string = ''
        for i in range(self.config.MSG_LENGTH):
            expected_string += str(i)
        self.assertEqual((response),  (expected_string))
        self.listener1.close()
        self.listener1.terminate()
        self.listener1.wait()
        
    def test_02_multiple_tcpip_senders(self):
        self.command_queue = Queue.Queue()        
        self.listener2 = NetworkListener(self.config.SERVER_IP, self.command_queue, socket.SOCK_STREAM, self.config.COMMAND_INTERFACE_PORT + 0)
        sender1 = NetworkSender(self.config, socket.SOCK_STREAM, self.config.COMMAND_INTERFACE_PORT + 0)
        sender2 = NetworkSender(self.config, socket.SOCK_STREAM, self.config.COMMAND_INTERFACE_PORT + 0)
        self.listener2.start()
        sender1.start()
        if os.name == 'nt':
            time.sleep(2.5)
        elif os.name == 'posix':
            time.sleep(1.5)
        sender2.start()
        if os.name == 'nt':
            time.sleep(2.5)
        elif os.name == 'posix':
            time.sleep(1.5)
        response = ''
        while not self.command_queue.empty():
            response += self.command_queue.get()        
        expected_string = ''
        for i in range(self.config.MSG_LENGTH):
            expected_string += str(i)
        expected_string = expected_string + expected_string
        self.assertEqual((response),  (expected_string))
        self.listener2.close()
        self.listener2.terminate()
        self.listener2.wait()
        
#    def test_03_multiple_tcpip_listeners(self):
#        #This test case does not work because a previously used socket cannot be reused
#        response = ''
#        self.command_queue = Queue.Queue()        
#        self.listener3 = NetworkListener(self.config, self.command_queue, socket.SOCK_STREAM, self.config.COMMAND_INTERFACE_PORT + 1)
#        sender1 = NetworkSender(self.config, socket.SOCK_STREAM, self.config.COMMAND_INTERFACE_PORT + 1)
#        self.listener3.start()
#        sender1.start()
#        time.sleep(2.5)
#        self.listener3.close()        
#        self.listener4 = NetworkListener(self.config, self.command_queue, socket.SOCK_STREAM, self.config.COMMAND_INTERFACE_PORT + 1)
#        sender2 = NetworkSender(self.config, socket.SOCK_STREAM, self.config.COMMAND_INTERFACE_PORT + 1)
#        sender2.start()         
#        time.sleep(2.5)
#        while not self.command_queue.empty():
#            response += self.command_queue.get()
#        expected_string = ''
#        for i in range(self.config.MSG_LENGTH):
#            expected_string += str(i)
#        expected_string = expected_string + expected_string
#        self.assertEqual((response),  (expected_string))
#        self.listener4.close()
        
    def test_03_single_udp_senders(self):
        self.command_queue = Queue.Queue()
        config = NetworkInterfaceTestConfig()
        self.listener3 = NetworkListener(config.SERVER_IP, self.command_queue, socket.SOCK_DGRAM, config.UDP_PORT)
        sender1 = NetworkSender(config, socket.SOCK_DGRAM, config.UDP_PORT)        
        self.listener3.start()
        sender1.start()
        if os.name == 'nt':
            time.sleep(2.5)
        elif os.name == 'posix':
            time.sleep(1.5)        
        response = ''
        while not self.command_queue.empty():
            response += self.command_queue.get()
        expected_string = ''
        for i in range(self.config.MSG_LENGTH):
            expected_string += str(i)        
        self.listener3.close()
        self.listener3.terminate()
        self.listener3.wait()
        self.assertEqual((response),  (expected_string))        
    
    def test_04_multiple_udp_senders(self):
        self.command_queue = Queue.Queue()
        config = NetworkInterfaceTestConfig()
        self.listener4 = NetworkListener(config.SERVER_IP, self.command_queue, socket.SOCK_DGRAM, config.UDP_PORT)
        sender1 = NetworkSender(config, socket.SOCK_DGRAM, config.UDP_PORT)
        sender2 = NetworkSender(config, socket.SOCK_DGRAM, config.UDP_PORT)
        self.listener4.start()
        sender1.start()
        if os.name == 'nt':
            time.sleep(2.5)
        elif os.name == 'posix':
            time.sleep(1.5) #or 2.5
        sender2.start()
        if os.name == 'nt':
            time.sleep(2.5)
        elif os.name == 'posix':
            time.sleep(1.5) #or 3.5
        response = ''
        while not self.command_queue.empty():
            response += self.command_queue.get()
        expected_string = ''
        for i in range(self.config.MSG_LENGTH):
            expected_string += str(i)
        expected_string = expected_string + expected_string
        self.listener4.close()
        self.listener4.terminate()
        self.listener4.wait()
        self.assertEqual((response),  (expected_string))
        
if __name__ == "__main__":
    unittest.main()
#    testRunner().start()
    
