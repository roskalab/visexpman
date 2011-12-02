import socket
import Queue
import sys
import time
import unittest
import visexpman.engine.generic.configuration
import PyQt4.QtCore as QtCore
import os
import sys
import SocketServer

class SockServer(SocketServer.TCPServer):
    def __init__(self, address, queue_in, queue_out, name, debug_queue):        
        SocketServer.TCPServer.__init__(self, address, None)
        self.queue_in = queue_in
        self.queue_out = queue_out
        self.debug_queue = debug_queue
        self.state = True   
        self.connection_timeout = 1.0
        self.name = name
        
    def debug(self, message):
        if self.debug_queue != None:
            debug_message = self.name + ': ' + message
            self.debug_queue.put([time.time(), debug_message], True)
        
    def process_request(self, request, client_address):
        self.last_receive_timeout = time.time()
        request.settimeout(0.01)
        print client_address, self.name
        request.send('connected')
        while True:            
            # self.request is the TCP socket connected to the client
            if self.queue_out.empty():
                alive = False
                try:
                    data = request.recv(1024)
                except:
                    if sys.exc_info()[0].__name__ == 'timeout':
                        self.last_receive_timeout = time.time()
                    data = ''
                
                if len(data) > 0:                    
                    if 'close' in data or\
                       'close_connection' in data or\
                       'quit' in data or\
                       time.time() - self.last_receive_timeout > self.connection_timeout:
    #                    print data, time.time() - self.last_receive_timeout
                        break
                    else:
                        self.queue_in.put(data)
                        self.debug(data)
                    
                
            else:
                out = self.queue_out.get()
                try:
                    request.send(out)
                except:
                    self.queue_out.put(out)
                    print sys.exc_info()
                    break
            
        print 'closed'

class QueuedServer(QtCore.QThread):
    #TODO: Queued server and sock server could be subclassed 
    def __init__(self, queue_in, queue_out, port, name, debug_queue = None):
        QtCore.QThread.__init__(self)
        self.port = port
        self.queue_in = queue_in
        self.queue_out = queue_out
        self.debug_queue = debug_queue
        self.name = name
        self.server = SockServer(("", port), self.queue_in, self.queue_out, self.name, self.debug_queue)

    def run(self):
        self.server.serve_forever()

class CommandRelayServer(object):
    def __init__(self, config):
        self.config = config
        self.generate_queues()
        self.create_servers()
        self.start_servers()
        
    def generate_queues(self):
        '''
        Generates queues and put them in a dictionary :
        queues[connection_name][endpointA2endpointB], queues[connection_name][endpointB2endpointA]
        '''
        self.debug_queue = Queue.Queue()
        self.queues = {}
        for connection, connection_config in self.config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'].items():
            endpoints = connection_config.keys()
            self.queues[connection] = {}
            self.queues[connection][endpoints[0] + '2' + endpoints[1]] = Queue.Queue()
            self.queues[connection][endpoints[1] + '2' + endpoints[0]] = Queue.Queue()
        
            
    def create_servers(self):
        '''
        Generates server threads, two for each connection.
        Dictionary format:
            servers[connection][endpointA]
            servers[connection][endpointB]
        '''
        self.servers = {}
        for connection, connection_config in self.config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'].items():
            endpoints = connection_config.keys()
            self.servers[connection] = {}
            
            self.servers[connection][endpoints[0]] = QueuedServer(
                                                                            self.queues[connection][endpoints[1] + '2' + endpoints[0]], #in
                                                                            self.queues[connection][endpoints[0] + '2' + endpoints[1]], #out
                                                                            connection_config[endpoints[0]]['PORT'], 
                                                                            'connection: {0}, endpoint {1}, port {2}'.format(connection, endpoints[0], connection_config[endpoints[0]]['PORT']), 
                                                                            self.debug_queue
                                                                            )
                                                                            
            self.servers[connection][endpoints[1]] = QueuedServer(
                                                                            self.queues[connection][endpoints[0] + '2' + endpoints[1]], #in
                                                                            self.queues[connection][endpoints[1] + '2' + endpoints[0]], #out
                                                                            connection_config[endpoints[1]]['PORT'], 
                                                                            'connection: {0}, endpoint {1}, port {2}'.format(connection, endpoints[1], connection_config[endpoints[1]]['PORT']), 
                                                                            self.debug_queue
                                                                            )

    def start_servers(self):
        for connection_name, connection in self.servers.items():
            for endpoint, server in connection.items():
                server.start()
                
    def get_debug_info(self):
        debug_info = []
        while not self.debug_queue.empty():
            debug_info.append(self.debug_queue.get())
        return debug_info

class QueuedClient(QtCore.QThread):
    def __init__(self, queue_out, queue_in, server_address, port):
        QtCore.QThread.__init__(self)
        self.queue_in = queue_in
        self.queue_out = queue_out
        self.port = port
        self.server_address = server_address
        
    def run(self):   
        out = ''
        while True:
            try:
                self.connection = socket.create_connection((self.server_address, self.port))
                self.queue_in.put('connected to server')
                self.last_receive_timout = time.time()
                self.connection.settimeout(0.01)
#                 self.queue_out.put('SOCconnection_createdEOC')
                while True:
                    if not self.queue_out.empty():
                        out = self.queue_out.get()
                        if 'stop_client' in out:
                            break
                        else:
                            if 'close' in out:
                                break
                            try:                    
                                self.connection.send(out)
                            except:                                
                                self.queue_out.put(out)
                                break
                        
                    else:
                        try:
                            data = self.connection.recv(1024)
                        except:                    
                            if sys.exc_info()[0].__name__ == 'timeout':
                                self.last_receive_timout = time.time()
                            data = ''
                        if len(data) > 0:
                            self.queue_in.put(data)
                
                time.sleep(0.1)  
                self.connection.close()                
                self.queue_in.put('connection closed')
            except socket.error:
                #Server does not respond
                pass
            if 'stop_client' in out:
                break
        print 'quit'       

def start_client(config, client_name, connection_name, queue_in, queue_out):
    '''
    Returns a reference to the client thread.
    '''
    client = QueuedClient(queue_out, queue_in, 
                          config.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'], 
                          config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'][connection_name][client_name]['PORT'])
    client.start()
    return client









#===================================================================================================


#Try: multiple clients, client thread starts in a thread, command buffer mutual exclusion. check out thread/target parameter
#Network listener -> CommandServer
class CommandServer(QtCore.QThread):#TODO unit test
    def __init__(self, command_queue, response_queue, port, buffer_size = 256):
        QtCore.QThread.__init__(self)
        self.command_queue = command_queue
        self.response_queue = response_queue
        self.response = ''
        self.port = port
        self.buffer_size = buffer_size
        self.enable_keep_alive_check = True
        self.connection_state = False
        
    def run(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = ('', self.port)
        self.socket.bind(server_address)
        self.socket.listen(1)
        end_loop = False
        while True:
            self.connection, client_address = self.socket.accept()
            self.connection.settimeout(1.0)
            print 'connection accepted'
            self.response_queue.put('connection accepted')
            self.connection_state = True
#            response = self.connection.recv(self.config.MES['receive buffer'])
#            self.response_queue.put(response)
#            print response              
            start_time = time.time()
            timeout = 1000
            
            while True:
                if self.command_queue.empty():
                    #If client does not respond to the echo command, connection is closed
                    elapsed_time_ms = int(1000* (time.time() - start_time))
                    if elapsed_time_ms%timeout == 0 and elapsed_time_ms > 20 * timeout and self.enable_keep_alive_check:
                    	#other detection of periodicity                        
                    	timeout_saved = self.connection.gettimeout()
                        self.connection.settimeout(30.0)                        
                        try:
                            if self.send_command('SOCechoEOCaliveEOP').find('echo') == -1:
                                print 'client does not respond'
                                self.connection_state = False
#                                 break
                        except:
                            print sys.exc_info()[0]
                            break
                        self.connection.settimeout(timeout_saved)
                    else:
                        timeout_saved = self.connection.gettimeout()
                        self.connection.settimeout(0.1)
                        
                        try:
                            response = self.connection.recv(self.buffer_size)
                            if len(response) > 0:
                                print response
                                self.response_queue.put(response)
                        except socket.timeout:
                            pass
                        except socket.error:
                            print 'end of connection'
                            self.connection_state = False
                            break
                        self.connection.settimeout(timeout_saved)
                else:
                    command = self.command_queue.get()
                    try:
                        response = self.send_command(command)
                        print response
                    except:
                            print sys.exc_info()[0]
                            break
                    self.response_queue.put(response)
                    if command == 'SOCclose_connectionEOC':
                        end_loop = True
                        self.connection_state = False
                if end_loop:
                    break
                time.sleep(0.1)
#            time.sleep(0.5)
            self.connection_state = False
            self.connection.close()
            
            
#             if end_loop:
#                 break

    def send_command(self, command):
        self.connection.send(command)
        response = self.connection.recv(self.buffer_size)
        return response
        
class CommandClient(QtCore.QThread):
    def __init__(self, out_queue, in_queue, server_address, port, buffer_size = 256):
        QtCore.QThread.__init__(self)
        self.out_queue = out_queue
        self.in_queue = in_queue
        self.response = ''
        self.port = port
        self.server_address = server_address
        self.buffer_size = buffer_size
        self.enable_keep_alive_check = True
        
    def run(self):
        while True:
            self.response = ''
            self.connection = socket.create_connection((self.server_address, self.port))
            while True:
                self.out_queue.put('SOCconnection_createdEOC')
                if not self.out_queue.empty():
                    out = self.out_queue.get()
                    print 'C send: ' + out
                    self.connection.send(out)
                    self.receive_from_server()
                    self.response = self.connection.recv(self.buffer_size)
                    if len(self.response)>0:
                        self.in_queue.put(self.response)
                else:
                    self.receive_from_server()
                if len(self.response)>0:
                    print 'C ' + self.response
                if self.response.find('SOCclose_connectionEOC') != -1:
                    self.connection.send('SOCconnection_closedEOC')
                    break
            self.connection.close()
            if self.response.find('SOCclose_connectionEOC') != -1:
                break

    def receive_from_server(self):
        self.response = self.connection.recv(self.buffer_size)
        if len(self.response)>0:
            self.in_queue.put(self.response)
        
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
        if 1 and self.socket_type ==  socket.SOCK_DGRAM: #why only for UDP?#TODO check it
            self.socket.settimeout(0.001)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self):
        if self.socket_type ==  socket.SOCK_STREAM:
            self.socket.listen(1)
            
            while True: #this while loop is intended to revive listening after an error?
#                print('listening') 
                connection, client_address = self.socket.accept()
                #print(str(self.sleep_sec))
                try:
                    data = ''
                    while True:
#                            connection.sendall('command')#TMP
                        newdata = connection.recv(16)
                        data = data+newdata
                        if len(newdata)==0:
                            #print >>sys.stderr, 'received "%s"' % data                            
                            self.command_queue.put(data)
                            break
                except Exception as e:
                    print e
                finally:
                    # Clean up the connection
                    connection.close()

        elif self.socket_type ==  socket.SOCK_DGRAM:
            while True:
                try:
                    udp_buffer, addr = self.socket.recvfrom(self.udp_buffer_size)
                    self.client_address = addr
#                    print udp_buffer
                    self.command_queue.put(udp_buffer)
#                 except socket.timeout:
#                     pass
                except:
                    pass
                

                    
    def close(self):
#        if self.socket_type ==  socket.SOCK_STREAM:
#            self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()


class NetworkSender(QtCore.QThread):    
    '''
    '''
    def __init__(self, config, socket_type, port, message_length = 200):
        target = None
        name = None
        QtCore.QThread.__init__(self)
        self.config = config
        self.port = port
        self.socket_type = socket_type
        self.message_length = message_length

    def run(self):
        for i in range(self.message_length):
            if self.socket_type ==  socket.SOCK_STREAM:
                sock = socket.create_connection((self.config.SERVER_IP, self.port))
                sock.sendall(str(i))
            elif self.socket_type ==  socket.SOCK_DGRAM:
                sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
                sock.sendto( str(i), (self.config.SERVER_IP, self.config.UDP_PORT) )            
            time.sleep(0.1)
            
class NetworkSender1(QtCore.QThread):    
    '''
    '''
    def __init__(self, config, socket_type, port, message):
        target = None
        name = None
        QtCore.QThread.__init__(self)
        self.config = config
        self.port = port
        self.socket_type = socket_type
        self.message = message

    def run(self):        
        if self.socket_type ==  socket.SOCK_STREAM:
            sock = socket.create_connection((self.config.SERVER_IP, self.port))
            sock.sendall(self.message)
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
        sender1 = NetworkSender(config, socket.SOCK_STREAM, config.COMMAND_INTERFACE_PORT, self.config.MSG_LENGTH)
        sender2 = NetworkSender(config, socket.SOCK_STREAM, config.COMMAND_INTERFACE_PORT, self.config.MSG_LENGTH)
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

class TestNetworkInterface(unittest.TestCase):
    def setUp(self):
        self.state = 'ready'
        self.config = NetworkInterfaceTestConfig()

    def test_01_single_sender(self):
        self.command_queue = Queue.Queue()        
        self.listener1 = NetworkListener(self.config.SERVER_IP, self.command_queue, socket.SOCK_STREAM, self.config.COMMAND_INTERFACE_PORT)
        sender = NetworkSender(self.config, socket.SOCK_STREAM, self.config.COMMAND_INTERFACE_PORT, self.config.MSG_LENGTH)
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
        sender1 = NetworkSender(self.config, socket.SOCK_STREAM, self.config.COMMAND_INTERFACE_PORT + 0, self.config.MSG_LENGTH)
        sender2 = NetworkSender(self.config, socket.SOCK_STREAM, self.config.COMMAND_INTERFACE_PORT + 0, self.config.MSG_LENGTH)
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
        sender1 = NetworkSender(config, socket.SOCK_DGRAM, config.UDP_PORT, self.config.MSG_LENGTH)
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
        sender1 = NetworkSender(config, socket.SOCK_DGRAM, config.UDP_PORT, self.config.MSG_LENGTH)
        sender2 = NetworkSender(config, socket.SOCK_DGRAM, config.UDP_PORT, self.config.MSG_LENGTH)
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
    
