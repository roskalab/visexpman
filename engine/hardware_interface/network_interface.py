#OBSOLETE
import socket
import Queue
import sys
import time
import unittest
import visexpman.engine.generic.configuration
import PyQt4.QtCore as QtCore
import os
import numpy
try:
    import blosc
    import zmq
    import simplejson
except:
    pass
import os.path
import sys
import threading
import SocketServer
import random
from visexpman.engine.generic import utils
from visexpman.engine.generic import log
from visexpman.engine.generic import fileop
import traceback
try:
    from visexpman.users.test import unittest_aggregator
except:
    pass
from visexpman.engine.generic.introspect import list_type
import multiprocessing
try:
    import psutil
except:
    pass
from multiprocessing import Process, Manager,  Event
DISPLAY_MESSAGE = False

def zmq_device(in_port, out_port, monitor_port, in_type='PULL', out_type='PUSH',  in_prefix=b'in', out_prefix=b'out'):
    from zmq import devices
    device = devices.ProcessMonitoredQueue(getattr(zmq, in_type), getattr(zmq, out_type), zmq.PUB,
                                        in_prefix, out_prefix)
    device.connect_in("tcp://127.0.0.1:%i"%in_port)
    if in_type=='SUB':
        device.setsockopt_in(zmq.SUBSCRIBE, '')
    device.setsockopt_in(zmq.LINGER, 1000)
    device.bind_out("tcp://127.0.0.1:%i"%out_port)
    device.setsockopt_out(zmq.LINGER, 1000)
    device.bind_mon("tcp://127.0.0.1:%i"%monitor_port)
    device.setsockopt_mon(zmq.LINGER, 1000)
    device.start()
    time.sleep(.2)
    return device

def ZeroMQPuller( port, queue=None, type='PULL', serializer='json', maxiter=float('Inf'), threaded=False,debug=False): #type can be zmq.SUB too
    if threaded is True:
        base = threading.Thread
    else:
        base = multiprocessing.Process
    class ZeroMQPullerClass(base):
        '''Pulls zmq messages from a server and puts it in a python queue'''
        def __init__(self, port, queue=None, type='PULL', serializer='json', maxiter=float('Inf'), threaded=False,debug=False): #type can be zmq.SUB too
            self.serializer= serializer
            self.queue = queue
            self.port=port
            self.serializer=serializer
            self.threaded = threaded
            if queue is None:
                if not threaded:
                    self.manager= multiprocessing.Manager()
                    self.queue=self.manager.list()
                else:
                    self.queue=[] # list is thread safe for reading only!
            self.type=type
            if threaded:
                threading.Thread.__init__(self)
                self.exit = threading.Event()
            else:
                multiprocessing.Process.__init__(self)
                self.exit = multiprocessing.Event()
                self.parentpid = os.getpid() #init is executed in the parent process
            self.maxiter= maxiter
            self.debug=debug
            
        def run(self):
            try:
                self.pid1 = os.getpid()
                self.context = zmq.Context(1)
                self.client = self.context.socket(getattr(zmq, self.type))
                if self.type=='SUB':
                    self.client.setsockopt(zmq.SUBSCRIBE, '')
                self.client.setsockopt(zmq.LINGER, 150)
                self.client.connect('tcp://localhost:{0}'.format(self.port))
                self.poll = zmq.Poller()
                self.poll.register(self.client, zmq.POLLIN)
                while not self.exit.is_set():
                    if not self.threaded:
                        # make sure this process terminates when parent is no longer alive
                        p = psutil.Process(os.getpid())
                        if p.parent.pid != self.parentpid:
                            self.close()
                            return
                    socks = dict(self.poll.poll(1000)) #timeout in each second allows stopping process via the close method
                    if socks.get(self.client) == zmq.POLLIN:
                        try:
                            if self.serializer == 'json':
                                msg = self.client.recv_json()
                            else:
                                msg = self.client.recv()
                            if self.debug and self.threaded:
                                print 'Poller received message:{0}'.format(msg)
                            if msg=='TERMINATE': # exit process via network 
                                self.client.close()
                                self.context.term()
                                if hasattr(self.queue, 'put'):
                                    self.queue.put(msg)
                                elif hasattr(self.queue, 'append'):
                                    self.queue.append(msg) #propagate TERMINATE command in case receiver also handles it
                                return
                        except Exception as e:
                            msg = str(e)
                        if hasattr(self.queue, 'put'):
                            self.queue.put(msg)
                        elif hasattr(self.queue, 'append'):
                            self.queue.append(msg)
            except Exception as e:
                msg=str(e)
                if hasattr(self.queue, 'put'):
                    self.queue.put(msg)
                elif hasattr(self.queue, 'append'):
                    self.queue.append(msg)
            self.client.close()
            self.context.term()
            
            
        def close(self): #exit process if spawned on the same machine
            print "Shutdown initiated"
            self.debug=1
            self.exit.set()
        
        def kill(self):
            import signal
            try:
                os.kill(self.pid1, signal.SIGTERM)
            except:
                pass
    
    return ZeroMQPullerClass(port, queue, type, serializer, maxiter, threaded,debug)

class ZeroMQPusher(object):
    def __init__(self, port=None, type='PUSH', serializer='json'): #can be zmq.PUB too
        self.serializer=serializer
        self.context = zmq.Context(1)
        self.type=type
        self.socket = self.context.socket(getattr(zmq, self.type))
        self.socket.setsockopt(zmq.LINGER, 100)
        if port is None:
            self.port = self.socket.bind_to_random_port('tcp://*')
        else:
            self.port = port
            self.socket.bind('tcp://*:{0}'.format(port))
    
    def send(self, data, block=True):
        if block==False:
            if not hasattr(self, 'poller'):
                self.poll = zmq.Poller()
                self.poll.register(self.socket, zmq.POLLOUT)
            socks = dict(self.poll.poll(150)) #timeout in each second allows stopping process via the close method
            if len(socks)==0:
                return False
            if socks.get(self.socket) == zmq.POLLOUT:
                pass
            else:
                raise RuntimeError('poll returned another socket, this is not possible')
        if self.serializer=='json':
            self.socket.send_json(data)
        else:
            self.socket.send(data)
        return True
    
    def close(self):
        self.socket.close()
        self.context.term()

class CallableViaZeroMQ(threading.Thread, multiprocessing.Process):
    '''Interface to call a method via ZeroMQ socket'''
    def __init__(self, port, thread=1):
        '''We allow methods be called directly by another thread but you must ensure data is protected by locks. In those cases locks block concurrent access but allow fine grained concurrency
        between direct method calls and calls via ZMQ'''
        self.port = port
        if thread:
            threading.Thread.__init__(self)
        else:
            multiprocessing.Process.__init__(self)
        
    def run(self):
        if self.port is None:
            print 'callable via zmq did not get a port number'
            return
        self.context=zmq.Context(1)
        self.server = self.context.socket(zmq.REP)
        self.server.bind('tcp://*:'+str(self.port))
        while 1:
            request  = self.server.recv_json()
            if request[0] == 'TERMINATE':
                self.server.send('TERMINATED')
                self.server.close()
                self.context.term()
                return 'TERMINATED'
            try:
                target = getattr(self, request[0])
                if hasattr(target, '__call__'):
                    value = target(*request[1], **request[2])
                else:
                    value = target
                if value is None:
                    self.server.send('NONE')
                    continue
                if isinstance(value, (basestring, int, bool,  float,  complex)) or list_type(value)=='arrayized':
                    cargo=simplejson.dumps(value)
                else:
                    if not hasattr(value, 'shape'):
                        value = numpy.array(['arrayized', type(value),  value])
                    cargo=blosc.pack_array(value)
                self.server.send(cargo) 
            except Exception as e:
                print e
                self.server.send('ERROR:'+ str(e))
                
class CallViaZeroMQ(object):
    def __init__(self, server_endpoint=None, request_timeout=2500, request_retries=3):
        self.context = zmq.Context(1)
        self.server_endpoint = server_endpoint
        self.request_timeout = request_timeout
        self.request_retries = request_retries
        
    def connect(self):
        print "I: Connecting to server"
        self.client = self.context.socket(zmq.REQ)
        self.client.connect(self.server_endpoint)
        self.poll = zmq.Poller()
        self.poll.register(self.client, zmq.POLLIN)
        
    def call(self,  method_name, *args,  **kwargs):
        self.connect()
        retries_left = self.request_retries
        request = [method_name, args, kwargs]
        while retries_left:
            print "I: Sending request"
            print request
            self.client.send_json(request)
            expect_reply = True
            while expect_reply:
                socks = dict(self.poll.poll(self.request_timeout))
                if socks.get(self.client) == zmq.POLLIN:
                    reply = self.client.recv()
                    if not reply:
                        break
                    print "I: Server replied "
                    if reply=='TERMINATED' or reply=='NONE': 
                        return
                    if 'ERROR' in reply: return reply
                    try:
                        return simplejson.loads(reply)
                    except:
                        data = blosc.unpack_array(reply)
                        if data[0]=='arrayized':
                            data = data.tolist()[1:]
                            if type(data)!=data[1] and data[1] not in [list, tuple, dict]:
                                data=data[1]
                        return data
                else:
                    print "W: No response from server, retrying"
                    # Socket is confused. Close and remove it.
                    self.client.setsockopt(zmq.LINGER, 0)
                    self.client.close()
                    self.poll.unregister(self.client)
                    retries_left -= 1
                    if retries_left == 0:
                        print "E: Server seems to be offline, abandoning"
                        break
                    print "I: Reconnecting and resending request"
                    self.connect()
                    self.client.send_json(request)

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
        self.start_time = time.time()
        
    def shutdown_request(self):
        self.shutdown_requested = True
        
    def printl(self, message):        
        debug_message = self.name + ': ' + str(message)
        if DISPLAY_MESSAGE:
            print time.time()-self.start_time, debug_message
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
                                    try:
                                        request.send(self.alive_message)
                                    except:
                                        self.printl(traceback.format_exc())
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
                            if 'close_connection' in data or\
                               'quit' in data:                               
                                self.printl('connection close requested')
                                connection_close_request = True
                            elif 'SOCkeepaliveEOCoffEOP' in data:
                                self.printl('Keepalive check off')
                                self.keepalive = False
                                self.queue_in.put(data.replace('SOCkeepaliveEOCoffEOP', ''))
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
    def __init__(self, server_ip, queue_in, queue_out, port, name, log_queue, timeout):
        QtCore.QThread.__init__(self)
        self.port = port
        self.queue_in = queue_in
        self.queue_out = queue_out
        self.log_queue = log_queue
        self.name = name
        self.timeout = timeout
        self.server = SockServer((server_ip, port), self.queue_in, self.queue_out, self.name, self.log_queue, self.timeout)

    def run(self):
        self.server.serve_forever()
        
    def shutdown(self):
        self.server.shutdown_request()
        self.server.shutdown()

class CommandRelayServer(object):
    def __init__(self, config):
        self.config = config        
        if self.config.COMMAND_RELAY_SERVER['ENABLE']:
            self._generate_queues()
#            self.log = log.LoggerThread(self.command_queue, self.log_queue, 'server log', fileop.generate_filename(os.path.join(self.config.LOG_PATH, 'server_log.txt')), timestamp = 'no', local_saving = True) 
#            self.log.start()
            self._create_servers()
            self._start_servers()
        
    def _generate_queues(self):
        '''
        Generates queues and put them in a dictionary :
        queues[connection_name][endpointA2endpointB], queues[connection_name][endpointB2endpointA]
        '''
        self.log_queue = Queue.Queue()        
        self.command_queue = Queue.Queue()        
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
            if self.config.COMMAND_RELAY_SERVER['RELAY_SERVER_IP_FROM_TABLE']:
                server_ip = self.config.COMMAND_RELAY_SERVER['SERVER_IP'][connection]
            else:
                server_ip = ['','']
            self.servers[connection][endpoints[0]] = QueuedServer(
                                                                            server_ip[0], 
                                                                            self.queues[connection][endpoints[1] + '2' + endpoints[0]], #in
                                                                            self.queues[connection][endpoints[0] + '2' + endpoints[1]], #out
                                                                            connection_config[endpoints[0]]['PORT'], 
                                                                            '{0}/{1}/{2}'.format(connection, endpoints[0], connection_config[endpoints[0]]['PORT']), 
                                                                            self.log_queue, 
                                                                            self.config.COMMAND_RELAY_SERVER['TIMEOUT'], 
                                                                            )
                                                                            
            self.servers[connection][endpoints[1]] = QueuedServer(
                                                                            server_ip[1], 
                                                                            self.queues[connection][endpoints[0] + '2' + endpoints[1]], #in
                                                                            self.queues[connection][endpoints[1] + '2' + endpoints[0]], #out
                                                                            connection_config[endpoints[1]]['PORT'], 
                                                                            '{0}/{1}/{2}'.format(connection, endpoints[1], connection_config[endpoints[1]]['PORT']), 
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
            self.command_queue.put('TERMINATE')
            #self.log.join()
                
    def get_debug_info(self, time_format = True):
        debug_info = []
        if self.config.COMMAND_RELAY_SERVER['ENABLE']:
            while not self.log_queue.empty():
                packet = self.log_queue.get()
                if time_format:
                    packet = [utils.timestamp2hms(packet[0]), packet[1]]
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
    def __init__(self, queue_out, queue_in, server_address, port, timeout, endpoint_name, local_address = ''):
        '''
        queue_in: data coming from network connection
        queue_out: data to be sent via network
        '''
        QtCore.QThread.__init__(self)
        self.queue_in = queue_in
        self.queue_out = queue_out
        self.port = port
        self.server_address = server_address
        self.local_address = local_address
        self.no_message_timeout = timeout
        self.alive_message = 'SOCechoEOCaliveEOP'
        self.endpoint_name = endpoint_name
        self.log_queue = Queue.Queue()        
        
    def printl(self, message):
        debug_message = str(message)
        if DISPLAY_MESSAGE:
            print time.time()-self.start_time, debug_message
        self.log_queue.put([time.time(), debug_message], True)
        
    def run(self):   
        self.setPriority(QtCore.QThread.HighPriority)
        shutdown_request = False
        out = ''
        keepalive = True
        while True:
            connection_close_request = False
            try:
                if self.local_address != '':
                     self.connection = socket.create_connection((self.server_address, self.port), source_address = (self.local_address, 0))
                else:
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
                                    if 'EOPSOC' in data:
                                        commands = data.split('EOPSOC')
#                                         print commands
                                        for i in range(len(commands)):
                                            if i == 0:
                                                commands[i] += 'EOP'
                                            elif i == len(commands)-1:
                                                commands[i] = 'SOC' + commands[i]
                                            else:
                                                commands[i] = 'SOC' + commands[i] + 'EOP'
                                            self.queue_in.put(commands[i])
                                    else:
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
            except:
                self.printl(traceback.format_exc())
            time.sleep(0.1)
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
        import random
        echo_message = 'SOCechoEOC{0}_{1}EOP'.format(self.endpoint_name, int(random.random()*10e5))
        self.queue_out.put(echo_message)
        t = utils.Timeout(timeout)
        return t.wait_timeout(break_wait_function = self._is_echo_arrived)        

def start_client(config, client_name, connection_name, queue_in, queue_out):
    '''
    Returns a reference to the client thread.
    '''
    if config.COMMAND_RELAY_SERVER['RELAY_SERVER_IP_FROM_TABLE']:
        server_address = config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'][connection_name][client_name]['IP']
        local_address = config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'][connection_name][client_name]['LOCAL_IP']
    else:
        server_address = config.COMMAND_RELAY_SERVER['RELAY_SERVER_IP']
        local_address = ''
    if config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'].has_key(connection_name):
        client = QueuedClient(queue_out, queue_in, 
                              server_address,
                              config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'][connection_name][client_name]['PORT'], 
                              config.COMMAND_RELAY_SERVER['TIMEOUT'], 
                              client_name,
                          local_address = local_address)
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
        LOG_PATH = unittest_aggregator.TEST_working_folder
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
#                    print addr, udp_buffer
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


class TestZMQInterface(unittest.TestCase):
    def setUp(self):
        pass
    def test_zmq_interface(self):
        port = 5555
        class TestClass(CallableViaZeroMQ):
            def __init__(self):
                CallableViaZeroMQ.__init__(self,port)
            def dosomething(self, firstarg,  kw1=0,  kw2={'1':'one'}):
                return ['good', firstarg, kw1, kw2]
            def returnarray(self):
                return numpy.array([1, 2, 3])
        
        myserver = TestClass()
        myserver.start()
        myclient = CallViaZeroMQ('tcp://localhost:{0}'.format(port))
        response = myclient.call('dosomething', 13)
        ana = myclient.call('returnarray')
        myclient.call('TERMINATE')
        self.assertEqual(response, ['good', 13, 0, {'1': 'one'}])
        self.assertTrue(numpy.all(ana==numpy.array([1, 2, 3])))
        pass
        
    def test_push_without_listeners(self):
        pusher = ZeroMQPusher()
        print pusher.port
        returncode = pusher.send(1, False)
        pusher.close()
        self.assertTrue(returncode==0)
        
    def test_push_pull(self):
        port =5556
        from multiprocessing import Manager, Process
        puller = ZeroMQPuller(port)
        puller.start()
        pusher = ZeroMQPusher(port)
        time.sleep(0.6)
        pusher.send(1, False)
        time.sleep(0.2)
        pusher.send(2)
        pusher.send('TERMINATE')
        puller.join()
        puller.close()
       # puller.kill()
        result=list(puller.queue)
        pusher.close()
        self.assertEqual(result, [1, 2])
        
    def test_pub_sub(self):
        port = 5557
        puller1 = ZeroMQPuller(port,type='SUB')
        puller1.start()
        puller2 = ZeroMQPuller(port, type='SUB')
        puller2.start()
        pusher = ZeroMQPusher(port, type='PUB')
        time.sleep(0.2) #do not know why this is needed
        pusher.send(1)
        pusher.send(2)
        pusher.send('TERMINATE')
        puller1.join()
        puller2.join()
        result=list(puller1.queue)+list(puller2.queue)
        pusher.close()
        print 'pubsubtest:'+str(result)
        self.assertEqual(sum(list(result)),  2*sum([1, 2]))
        
    def test_push_pull_queue(self):
        for tsend, trec in [('PUSH', 'PULL'), ('PUB', 'SUB')]:
            server2forwarder_port = 5554
            forwarder2client_port = 5559
            monitor_port = 5558
            serializer = 'json'
            
            def pusher_process(port, type):
                pusher1 = ZeroMQPusher(port, type=type, serializer=serializer)
                time.sleep(2.2) # let puller start too
                pusher1.send(str(os.getpid())+' content 1')
                pusher1.send(str(os.getpid())+' content 2')
                time.sleep(0.2)
                pusher1.send('TERMINATE')
            broker=zmq_device(server2forwarder_port, forwarder2client_port, monitor_port, in_type=trec, out_type=tsend)
            monitor = ZeroMQPuller(monitor_port, type='SUB', serializer= '')
            monitor.start()
           # puller2 = ZeroMQPuller(5556, receiver, type='pushpull')
            #puller2.start()
            for pp1 in [0]:
                pusher1=threading.Thread(target=pusher_process, args=(server2forwarder_port,tsend ))
               # pusher1.daemon=True
            pusher1.start()
            puller1 = ZeroMQPuller(forwarder2client_port, type=trec, serializer=serializer)
            puller1.run() # no thread/process start in order to be able to debug
            puller1.close()
            if puller1.is_alive():
                puller1.join()
            if hasattr(broker.launcher, 'pid'):
                broker.launcher.terminate()
            result =list(puller1.queue)
            print list(monitor.queue)
            del pusher1
            del puller1
            monitor.close()
            del monitor
        self.assertTrue('content 1' in result[0] and 'content 2' in result[1] and len(result)==2)
        
if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestZMQInterface)
    unittest.TextTestRunner().run(suite)
    print 'all done'
    
