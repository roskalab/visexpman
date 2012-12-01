import socket
import Queue
import sys
import time
import unittest
import visexpman.engine.generic.configuration
import PyQt4.QtCore as QtCore
import os
import os.path
import sys
import SocketServer
import random
from visexpman.engine.generic import utils
from visexpman.engine.generic import log
from visexpman.engine.generic import file
import traceback
import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner

DISPLAY_MESSAGE = False

class SockServer(SocketServer.TCPServer):
    def __init__(self, address, queue_in, queue_out, name, log_queue, timeout):
        SocketServer.TCPServer.__init__(self, address, None)
        self.allow_reuse_address = True
        self.queue_in = queue_in
        self.queue_out = queue_out
        self.log_queue = log_queue
        self.connected = False
        self.connection_timeout = timeout
        self.name = name
        self.alive_message = 'SOCechoEOCaliveEOP'
        self.shutdown_requested = False        
        self.keepalive = True#Client can request to stop keep alive check until the next message
        
    def shutdown_request(self):
        self.shutdown_requested = True
        
    def printl(self, message):        
        debug_message = self.name + ': ' + str(message)
        if DISPLAY_MESSAGE:
            print debug_message
        if self.log_queue != None:
            self.log_queue.put([time.time(), debug_message], True)
        
    def process_request(self, request, client_address):
        try:
            if not self.shutdown_requested:
                self.last_receive_time = time.time()
                self.last_alive_message = time.time()
                request.settimeout(0.01)
                self.printl('Client: ' + str(client_address))
                request.send('connected')
                self.connected = True
                connection_close_request = False
                while True:
                    # self.request is the TCP socket connected to the client
                    now = time.time()
                    if self.shutdown_requested:
                        connection_close_request = True
                    if self.queue_out.empty():
                        #Check if connection is alive
                        if now - self.last_alive_message > 0.2 * self.connection_timeout:
                            try:
                                if self.keepalive:
                                    request.send(self.alive_message)
                                    self.last_alive_message = now
                            except:
                                self.printl(traceback.format_exc())
                                #If sending alive message is unsuccessful, connection terminated
                                connection_close_request = True
                        #Receive data
                        try:
                            data = request.recv(1024)
                            self.last_receive_time = now
                            if len(data)>0:
                                if not self.keepalive:
                                    self.printl('Keepalive check on')
                                if not 'echo' in data:
                                    self.keepalive = True
                        except:           
                            data = ''
                        data = data.replace(self.alive_message,'')
                        if len(data) > 0: #Non empty messages are processed                        
                            if not self.alive_message in data: #Save message to debug queue except for keep alive messages
                                self.printl(data)
                            if 'close' in data or\
                               'close_connection' in data or\
                               'quit' in data:                               
                                self.printl('connection close requested')
                                connection_close_request = True
                            elif 'keepalive' in data and 'off' in data:
                                self.printl('Keepalive check off')
                                self.keepalive = False
                            else:
                                self.queue_in.put(data)
                        if now - self.last_receive_time > self.connection_timeout and self.keepalive:
                            connection_close_request = True
                            self.printl('Connection timeout')
                    else:
                        if not connection_close_request:
                            out = self.queue_out.get()
                            try:
                                request.send(out)
                            except:
                                self.queue_out.put(out)
                                self.printl(traceback.format_exc())
                                connection_close_request = True
                    if connection_close_request:
                        break
                self.printl('closed')
                self.connected = False
                time.sleep(0.5 + 1.5 * random.random())
        except:
            self.printl(traceback.format_exc())

class QueuedServer(QtCore.QThread):
    def __init__(self, queue_in, queue_out, port, name, log_queue, timeout):
        QtCore.QThread.__init__(self)
        self.port = port
        self.queue_in = queue_in
        self.queue_out = queue_out
        self.log_queue = log_queue
        self.name = name
        self.timeout = timeout
        self.server = SockServer(("", port), self.queue_in, self.queue_out, self.name, self.log_queue, self.timeout)

    def run(self):
        self.server.serve_forever()
        
    def shutdown(self):
        self.server.shutdown_request()
        self.server.shutdown()

class CommandRelayServer(object):
    def __init__(self, config):
        self.config = config        
        if self.config.COMMAND_RELAY_SERVER['ENABLE']:
            self.log = log.Log('server log', file.generate_filename(os.path.join(self.config.LOG_PATH, 'server_log.txt')), timestamp = 'no', local_saving = True) 
            self._generate_queues()
            self._create_servers()
            self._start_servers()
        
    def _generate_queues(self):
        '''
        Generates queues and put them in a dictionary :
        queues[connection_name][endpointA2endpointB], queues[connection_name][endpointB2endpointA]
        '''
        self.log_queue = Queue.Queue()        
        self.queues = {}
        for connection, connection_config in self.config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'].items():
            endpoints = connection_config.keys()            
            self.queues[connection] = {}
            self.queues[connection][endpoints[0] + '2' + endpoints[1]] = Queue.Queue()
            self.queues[connection][endpoints[1] + '2' + endpoints[0]] = Queue.Queue()
        
            
    def _create_servers(self):
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
                                                                            self.log_queue, 
                                                                            self.config.COMMAND_RELAY_SERVER['TIMEOUT'], 
                                                                            )
                                                                            
            self.servers[connection][endpoints[1]] = QueuedServer(
                                                                            self.queues[connection][endpoints[0] + '2' + endpoints[1]], #in
                                                                            self.queues[connection][endpoints[1] + '2' + endpoints[0]], #out
                                                                            connection_config[endpoints[1]]['PORT'], 
                                                                            'connection: {0}, endpoint {1}, port {2}'.format(connection, endpoints[1], connection_config[endpoints[1]]['PORT']), 
                                                                            self.log_queue, 
                                                                            self.config.COMMAND_RELAY_SERVER['TIMEOUT'], 
                                                                            )

    def _start_servers(self):
        for connection_name, connection in self.servers.items():
            for endpoint, server in connection.items():
                server.start()
                
    def shutdown_servers(self):
        if self.config.COMMAND_RELAY_SERVER['ENABLE']:
            for connection_name, connection in self.servers.items():
                for endpoint, server in connection.items():
                    server.shutdown()
            #Wait till all threads stop
            for connection_name, connection in self.servers.items():
                for endpoint, server in connection.items():
                    server.wait()
            self.log.queue(self.log_queue)
        if hasattr(self, 'log'):
            self.log.copy()
                
    def get_debug_info(self, time_format = True):
        debug_info = []
        if self.config.COMMAND_RELAY_SERVER['ENABLE']:
            while not self.log_queue.empty():
                packet = self.log_queue.get()
                if time_format:
                    packet = [utils.time_stamp_to_hms(packet[0]), packet[1]]
                try:
                    self.log.info(packet)
                except:
                    print 'network: log error'
                debug_info.append(packet)
        return debug_info
        
    def get_connection_status(self, connection_id = None, endpoint_name = None, ):
        connection_status = {}
        for connection_name, connection in self.servers.items():
            for endpoint, server in connection.items():
                connection_status[connection_name + '/' + endpoint]  = server.server.connected
        if connection_id != None and endpoint_name != None:
            connection_status = self.servers[connection_id][endpoint_name].server.connected
        return connection_status        
    

class QueuedClient(QtCore.QThread):
    def __init__(self, queue_out, queue_in, server_address, port, timeout, endpoint_name):
        '''
        queue_in: data coming from network connection
        queue_out: data to be sent via network
        '''
        QtCore.QThread.__init__(self)
        self.queue_in = queue_in
        self.queue_out = queue_out
        self.port = port
        self.server_address = server_address
        self.no_message_timeout = timeout
        self.alive_message = 'SOCechoEOCaliveEOP'
        self.endpoint_name = endpoint_name
        self.log_queue = Queue.Queue()        
        
    def printl(self, message):
        debug_message = str(message)
        if DISPLAY_MESSAGE:
            print debug_message        
        self.log_queue.put([time.time(), debug_message], True)
        
    def run(self):   
        self.setPriority(QtCore.QThread.HighPriority)
        shutdown_request = False
        out = ''
        keepalive = True
        while True:
            connection_close_request = False
            try:
                self.connection = socket.create_connection((self.server_address, self.port))
                self.printl(self.connection.getpeername())
                self.queue_in.put('connected to server')
                self.last_receive_timout = time.time()
                self.last_message_time = time.time()
                self.connection.settimeout(0.01)
                time.sleep(0.5)
                try:
                    data = self.connection.recv(1024)
                except:
                    data = ''
                    connection_close_request = True
                    self.printl(traceback.format_exc())
                if 'connected' in data:
                    while True:                    
                        if not self.queue_out.empty():
                            out = self.queue_out.get()
                            if 'stop_client' in out:
                                self.connection.send('close_connection')
                                connection_close_request = True
                                shutdown_request = True
                            else:
                                if 'close_connection' in out:
                                    connection_close_request = True
                                try:
                                    if 'queue_put_problem_dummy_message' not in out:
                                        self.connection.send(out)
                                except:
                                    self.printl(traceback.format_exc())
                                    self.queue_out.put(out)
                                    connection_close_request = True
                                if 'keepalive' in out and 'off' in out:
                                    keepalive = False
                                if 'keepalive' in out and 'on' in out:
                                    keepalive = True
                        else:
                            try:
                                data = self.connection.recv(1024)
                            except:
                                if sys.exc_info()[0].__name__ == 'timeout':
                                    self.last_receive_timout = time.time()
                                data = ''
                            if len(data) > 0:                            
                                if self.alive_message in data and keepalive:
                                   #Send back keep alive message
                                    data = data.replace(self.alive_message,'')
                                    try:
                                        self.connection.send(self.alive_message)
                                    except:
                                        pass
                                elif 'close_connection' in data:
                                    self.printl('Close requested')
                                    connection_close_request = True                                
                                if len(data)>0:                                    
                                    self.queue_in.put(data)
                                    self.printl(data)
                                self.last_message_time = time.time()
                            if time.time() - self.last_message_time > self.no_message_timeout:
                                self.printl('Connection timeout')
                                connection_close_request = True
                        if connection_close_request:
                            break
                        time.sleep(0.05)
                else:
                    time.sleep(self.no_message_timeout)
                time.sleep(0.1)
                self.connection.close()
                time.sleep(1.0 + 1.5 * random.random())
                self.printl('connection closed')                
                self.queue_in.put('connection closed')
            except socket.error:
                self.printl('socket error: ' + traceback.format_exc())                
            except:
                self.printl(traceback.format_exc())
                
            if shutdown_request:
                self.printl('stop client')
                break
            time.sleep(0.5)        
        self.printl('quit')

    def _is_echo_arrived(self):
        result = False
        data_back_to_queue = []
        while not self.queue_in.empty():
            response = self.queue_in.get()
            if 'SOCechoEOC' in response:
                result = True
            else:
                #Save non-echo messages
                data_back_to_queue.append(response)
        #Put non-echo messages back to queue so that other methods could process them
        map(self.queue_in.put, data_back_to_queue)
        return result
            
    def connected_to_remote_client(self, timeout = 1.5):
        '''connected_to_remote_client
        Sends an echo message to the remote client and waits for the response. If it does not arrive within the timout provided, it is assumed that the remote client is not connected
        '''
        #TODO: testcase is missing for this function
        echo_message = 'SOCechoEOC{0}EOP'.format(self.endpoint_name)
        self.queue_out.put(echo_message)
        t = utils.Timeout(timeout)
        return t.wait_timeout(break_wait_function = self._is_echo_arrived)        

def start_client(config, client_name, connection_name, queue_in, queue_out):
    '''
    Returns a reference to the client thread.
    '''
    client = QueuedClient(queue_out, queue_in, 
                          config.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'], 
                          config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'][connection_name][client_name]['PORT'], 
                          config.COMMAND_RELAY_SERVER['TIMEOUT'], 
                          client_name)
    if config.COMMAND_RELAY_SERVER['CLIENTS_ENABLE']:
        client.start()
    return client

#============= Helpers ====================#

def check_response(queue, expected_responses, keyboard_handler, from_gui_queue):    
    result = False
    data_back_to_queue = []
    while not queue.empty():
        response = queue.get()
        if any(expected_response in response for expected_response in expected_responses):
            result = True
        else:
            #Save non-echo messages
            data_back_to_queue.append(response)    
    #Put non-echo messages back to queue so that other methods could process them
    map(queue.put, data_back_to_queue)
    if hasattr(keyboard_handler, 'experiment_user_interface_handler'):
        key_pressed = keyboard_handler.experiment_user_interface_handler()
        if isinstance(key_pressed, str):
            if 'stop' in key_pressed:
                result = True
    if utils.is_abort_experiment_in_queue(from_gui_queue):
        result = True
    return result

def wait_for_response(queue, expected_responses, timeout = -1, keyboard_handler = None, from_gui_queue = None):
    '''
    Wait for response from a remote peer by checking the response queue.
    expected_responses: can be either a list of string or a string. If any of these patterns are detected, the response is assumed to arrive
    error_response: if this string is in the response, returns with error
    timeout: -1: waits forever, otherwise interpreted in seconds
    '''
    if not isinstance(expected_responses, list):  
        expected_responses = [expected_responses]
    t = utils.Timeout(timeout)
    return t.wait_timeout(check_response, queue, expected_responses, keyboard_handler, from_gui_queue)

####################################### Unit tests #################################################xx

class QueuedServerTestConfig(visexpman.engine.generic.configuration.Config):
    def _create_application_parameters(self):
        
        import random
        self.BASE_PORT = 10000 + 1* int(10000*random.random())
        COMMAND_RELAY_SERVER  = {
        'RELAY_SERVER_IP' : 'localhost', 
        'ENABLE' : True, 
        'CLIENTS_ENABLE' : True, 
        'TIMEOUT':10.0, 
        'CONNECTION_MATRIX':
            {
            '4_5'  : {'4' : {'IP': 'localhost', 'PORT': self.BASE_PORT}, '5' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 1}},
            '6_7'  : {'6' : {'IP': 'localhost', 'PORT': self.BASE_PORT+2}, '7' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 3}},
            }
        }
        LOG_PATH = unit_test_runner.TEST_working_folder
        self._create_parameters_from_locals(locals())

class TestQueuedServer(unittest.TestCase):
    def setUp(self):
        self.config = QueuedServerTestConfig()        
        self.server = CommandRelayServer(self.config)
        self.client_queues = []
        self.clients = []
        for i in range(4):
            self.client_queues.append({'in': Queue.Queue(), 'out': Queue.Queue()})
            connection_name = (i / 2) * 2+4
            connection_name  = '{0}_{1}'.format(connection_name, connection_name+1)
            self.clients.append(start_client(self.config, str(i+4), connection_name, self.client_queues[-1]['in'], self.client_queues[-1]['out']) )
    #TODO: check for connection status
    def test_01_check_connected_commands(self):
        time.sleep(0.5)        
        self.server.shutdown_servers()
        result = True
        for queues in self.client_queues:
            while not queues['in'].empty():
                msg =  queues['in'].get()
                if not msg == 'connected to server' and not msg == 'client connected' and not msg == 'client disconnected':
                    result = False      
        self.assertEqual(result, True)
                
    def test_02_send_data_between_endpoints(self):
        
        for queues in self.client_queues:
            queues['out'].put('close_connection')
        time.sleep(5.0)
        counter = 0
        for queues in self.client_queues:
            queues['out'].put(str(counter))
            counter += 1
        time.sleep(0.5)
        self.server.shutdown_servers()        
        messages = []
        connection_close_occured = True
        for queues in self.client_queues:
            connection_closed = False
            while not queues['in'].empty():
                data_from_client = queues['in'].get()
                if not 'connected to server' in data_from_client and not 'connection closed' in data_from_client:
                    messages.append(int(data_from_client))        
                if 'connection closed' in data_from_client:
                    connection_closed = True
            if not connection_closed:
                connection_close_occured = False
        if len(messages) != 4:
            result = False            
        else:
            result = utils.arrays_equal([1, 0, 3, 2], messages)
        self.assertEqual((result, connection_close_occured), (True, True))       

    def tearDown(self):
        pass

#########################################################################################################xx
#===== Network listener ========#
       
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
    
