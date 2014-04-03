import zmq
import time
import multiprocessing
import platform
import unittest
from visexpman.engine.generic import utils

class QueuedSocket(multiprocessing.Process):
    '''
    Constructed with ip address: client, otherwise server. Non blocking reading of socket. Data is put to queue. 
    Received data is also saved to a queue
    
    Protocol: dictionary object are sent through with the following functionalities
    function call: {'function': function name, 'args': list of arguments, 'kwargs': dictionary of keyword arguments}
    data: {'data': list of data elements}
    When string is sent, it is intended as a log/console/screen message
    
    For testing connection the QueuedSocket.ping method shall be used
    '''
    def __init__(self, socket_name, isserver, port, tosocket, fromsocket, ip = None, log = None):
        self.socket_name = socket_name
        self.port = port
        self.tosocket = tosocket
        self.fromsocket = fromsocket
        self.ip= ip
        self.log=log
        self.isserver=isserver
        self.command = multiprocessing.Queue()
        self.loop_wait = 0.1
        multiprocessing.Process.__init__(self)
        if hasattr(self.log, 'add_source'):
            self.log.add_source(self.socket_name)
            
    def send(self,obj):
        self.tosocket.put(obj)
        
    def recv(self):
        if not self.fromsocket.empty():
            return self.fromsocket.get()
            
    def ping(self,timeout=1.0):
        self.send('ping')
        t0 = time.time()
        while True:
            resp = self.recv()
            if resp == 'pong':
                return True
            if time.time()-t0>timeout:
                return False
            time.sleep(0.1)
        
    def terminate(self):
        self.command.put('terminate')
        if platform.system()=='Windows' or True:
            while True:
                state = not self.command.empty()
                if state:
                    break
                time.sleep(0.1)
            multiprocessing.Process.terminate(self)
#        else:
#            self.join()
        
    def _connect(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PAIR)
        if self.isserver:
            if self.ip is None:
                self.socket.bind("tcp://*:{0}" .format(self.port))
            else:
                self.socket.bind("tcp://{0}:{1}" .format(self.ip, self.port))
            if hasattr(self.log, 'info'):
                self.log.info('listening on {0}:{1}'.format(self.ip,self.port),self.socket_name)
        else:
            self.socket.connect("tcp://{0}:{1}".format(self.ip, self.port))
            if hasattr(self.log, 'info'):
                self.log.info('connected to {0}:{1}'.format(self.ip,self.port),self.socket_name)

    def run(self):
        try:
            self._connect()
        except:
            import traceback
            if hasattr(self.log, 'error'):
                self.log.error(traceback.format_exc(),self.socket_name)
            return#In this case perhaps it is better to end the process
        while True:
            try:
                if not self.tosocket.empty():
                    message = self.tosocket.get()
                    message_str = utils.object2str(message)
                    #This blocks the process if remote peer is not connected.
                    #Receiving messages is blocked too which resumes only when remote peer is available.
                    #If this does not happen, Process.terminate() terimates the process.
                    self.socket.send(message_str)
                    if hasattr(self.log, 'info'):
                        self.log.info('sent: ' + str(message),self.socket_name)
                try:
                    message = self.socket.recv(flags=zmq.NOBLOCK)
                    message = utils.str2object(message)
                    if hasattr(self.log, 'info'):
                        self.log.info('received: ' + str(message),self.socket_name)
                    if message == 'ping':
                        self.tosocket.put('pong')
                    else:
                        self.fromsocket.put(message)
                except zmq.ZMQError:
                    pass#Nothing has received
                if not self.command.empty() and self.command.get()=='terminate':
                    break
                time.sleep(self.loop_wait)
            except:
                import traceback
                if hasattr(self.log, 'info'):
                    self.log.error(traceback.format_exc(),self.socket_name)
        self.command.put('terminated')
        if hasattr(self.log, 'info'):
            self.log.info('process ended', self.socket_name)

def start_sockets(appname, config, log):
    '''
    Starts sockets depending on config.CONNECTIONS and appname.
    '''
    sockets = {}
    if appname == 'main_ui':
        for server_name in config.CONNECTIONS.keys():
            sockets[server_name] = QueuedSocket('{0}-{1} socket'.format(appname, server_name), 
                                                                                    False, 
                                                                                    config.CONNECTIONS[server_name]['port'],
                                                                                    multiprocessing.Queue(), 
                                                                                    multiprocessing.Queue(), 
                                                                                    ip= config.CONNECTIONS[server_name]['ip']['main_ui'],
                                                                                    log=log)
    else:
        sockets[appname] = QueuedSocket('{0}-{1} socket'.format(appname, 'main_ui'), 
                                                                                    True, 
                                                                                    config.CONNECTIONS[appname]['port'],
                                                                                    multiprocessing.Queue(), 
                                                                                    multiprocessing.Queue(), 
                                                                                    ip = config.CONNECTIONS[appname]['ip'][appname],
                                                                                    log=log)
    [s.start() for s in sockets.values()]
    return sockets

def stop_sockets(sockets):
    [s.terminate() for s in sockets.values()]

class TestQueuedSocket(unittest.TestCase):
    def setUp(self):
        import random
        self.port = random.randrange(20000,20100)
        
    def _wait4queues(self,queues):
        while True:
            time.sleep(0.1)
            if all([not q.empty() for q in queues]):
                break
        
    def test_01_simple_transfer(self):
        server = QueuedSocket('server', True, self.port, multiprocessing.Queue(), multiprocessing.Queue())
        client = QueuedSocket('client', False, self.port, multiprocessing.Queue(), multiprocessing.Queue(), ip='localhost')
        client.start()
        server.start()
        client.tosocket.put(['request'])
        server.tosocket.put(['response'])
        self._wait4queues([client.fromsocket,server.fromsocket])
        self.assertEqual(['request'],server.fromsocket.get(block=False))
        self.assertEqual(['response'],client.fromsocket.get(block=False))
        for s in [client,server]:
            s.terminate()
        
    def test_02_big_data_transfer(self):
        server = QueuedSocket('server', True, self.port, multiprocessing.Queue(), multiprocessing.Queue())
        client = QueuedSocket('client', False, self.port, multiprocessing.Queue(), multiprocessing.Queue(), ip='localhost')
        client.start()
        server.start()
        import numpy
        data = numpy.random.random(5000)
        client.tosocket.put(data)
        server.tosocket.put(data)
        self._wait4queues([client.fromsocket,server.fromsocket])
        self.assertEqual(data.sum(),server.fromsocket.get(block=False).sum())
        self.assertEqual(data.sum(),client.fromsocket.get(block=False).sum())
        for s in [client,server]:
            s.terminate()
        
    def test_03_multiple_servers(self):
        server_names = ['stim','analysis', 'ca_imaging']
        gui = {}
        servers = {}
        i = 0
        for c in server_names:
            gui[c] = QueuedSocket('gui-{0}'.format(c), False, self.port+i, multiprocessing.Queue(), multiprocessing.Queue(), ip='localhost')
            gui[c].start()
            servers[c] = QueuedSocket(c, True, self.port+i, multiprocessing.Queue(), multiprocessing.Queue())
            servers[c].start()
            i += 1
        gui['stim'].tosocket.put({'start_experiment':True})
        gui['analysis'].tosocket.put(range(10))
        servers['stim'].tosocket.put('Done')
        self._wait4queues([gui['stim'].fromsocket, servers['analysis'].fromsocket, servers['stim'].fromsocket])
        self.assertEqual('Done',gui['stim'].fromsocket.get())
        self.assertEqual(range(10), servers['analysis'].fromsocket.get())
        self.assertEqual({'start_experiment':True}, servers['stim'].fromsocket.get())
        for c in server_names:
            gui[c].terminate()
            servers[c].terminate()
        
    def test_04_socket_helpers(self):
        server = QueuedSocket('server', True, self.port, multiprocessing.Queue(), multiprocessing.Queue())
        client = QueuedSocket('client', False, self.port, multiprocessing.Queue(), multiprocessing.Queue(), ip='localhost')
        client.start()
        server.start()
        data1 = range(10)
        data2 = {'a':2}
        client.send(data1)
        server.send(data2)
        self._wait4queues([client.fromsocket,server.fromsocket])
        self.assertEqual(data1,server.recv())
        self.assertEqual(data2,client.recv())
        for s in [client,server]:
            s.terminate()
        
    def test_05_bind2ip(self):
        server = QueuedSocket('server', True, self.port, multiprocessing.Queue(), multiprocessing.Queue(), ip = utils.get_ip())
        client = QueuedSocket('client', False, self.port, multiprocessing.Queue(), multiprocessing.Queue(), ip= utils.get_ip())
        client.start()
        server.start()
        data1 = range(10)
        data2 = {'a':2}
        client.send(data1)
        server.send(data2)
        self._wait4queues([client.fromsocket,server.fromsocket])
        self.assertEqual(data1,server.recv())
        self.assertEqual(data2,client.recv())
        for s in [client,server]:
            s.terminate()
        
    def test_06_start_sockets_from_config(self):
        '''
        QueuedSockets are started from a machine config.
        '''
        from visexpman.users.test.test_configurations import GUITestConfig
        from visexpman.engine.generic import log
        from visexpman.engine.generic import fileop
        import os.path
        config = GUITestConfig()
        config.user = 'test'
        appnames = ['main_ui']
        appnames.extend(config.CONNECTIONS.keys())
        logfiles = []
        for appname in appnames:
            config.application_name = appname
            logger = log.Logger(filename=fileop.get_logfilename(config), logpath = config.LOG_PATH, remote_logpath = config.REMOTE_LOG_PATH)
            sockets = start_sockets(appname, config, log=logger)#Unit under test
            logger.start()
            time.sleep(4.0)
            stop_sockets(sockets)
            logger.terminate()
            logfiles.append(logger.filename)
        self.assertNotEqual(map(os.path.getsize, logfiles), len(logfiles) * [0])
        self.assertEqual([True for logfile in logfiles if 'error' in fileop.read_text_file(logfile).lower()],[])#Check if there is any error in logfiles
            
    def test_07_ping_connections(self):
        server = QueuedSocket('server', True, self.port, multiprocessing.Queue(), multiprocessing.Queue(), ip = utils.get_ip())
        client = QueuedSocket('client', False, self.port, multiprocessing.Queue(), multiprocessing.Queue(), ip= utils.get_ip())
        client.start()
        server.start()
        time.sleep(2)
        self.assertTrue(client.ping(5))
        self.assertTrue(server.ping(5))
        for s in [client,server]:
            s.terminate()
            
if __name__ == "__main__":
    unittest.main()
