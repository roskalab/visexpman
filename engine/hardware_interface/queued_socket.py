import zmq
import time
import multiprocessing
import platform
import traceback
import unittest
import sys
from visexpman.engine.generic import utils,log,introspect

class QueuedSocketHelpers(object):
    '''
    Provides send, receive and ping methods depending only on queues
    '''
    def __init__(self,socket_queues):
        self.socket_queues=socket_queues
        
    def _get_queue(self, connection):
        if connection == None:
            if self.socket_queues.has_key('fromsocket'):
                queue = self.socket_queues['fromsocket']
            elif len(self.socket_queues.keys())==1:
                queue = self.socket_queues.values()[0]['fromsocket']
            else:
                raise RuntimeError('Unknown socket queue format {0}'.format(self.socket_queues))
        else:
            queue = self.socket_queues[connection]['fromsocket']
        return queue
        
    def recv(self, connection=None, put_message_back=False):
        queue = self._get_queue(connection)
        try:
            if not queue.empty():
                m=queue.get()
                if put_message_back:
                    queue.put(m)
                return m
        except IOError:
            pass

    def send(self, msg, connection=None):
        if connection == None:
            queue = self.socket_queues['tosocket']
        else:
            queue = self.socket_queues[connection]['tosocket']
        queue.put(msg)
            
    def ping(self,timeout=1.0, connection=None):
        self.send('ping',connection)
        t0 = time.time()
        queue = self._get_queue(connection)
        while True:
            resp = self.recv(connection)
            if resp == 'pong':
                return True
            else:
                queue.put(resp)
            if time.time()-t0>timeout:
                return False
            time.sleep(0.1)

class QueuedSocket(multiprocessing.Process, QueuedSocketHelpers):
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
        QueuedSocketHelpers.__init__(self, {'tosocket': tosocket, 'fromsocket': fromsocket})
        self.socket_name = socket_name
        self.port = port
        self.ip= ip
        self.log=log
        self.isserver=isserver
        self.command = multiprocessing.Queue()
        self.loop_wait = 0.1
        multiprocessing.Process.__init__(self)
        if hasattr(self.log, 'add_source'):
            self.log.add_source(self.socket_name)

    def terminate(self):
        self.command.put('terminate')
        if platform.system()=='Windows' or True:
            while True:
                state = not self.command.empty()
                if state:
                    break
                time.sleep(0.1)
            self.join()
        
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
                if not self.socket_queues['tosocket'].empty():
                    message = self.socket_queues['tosocket'].get()
                    if message == 'sync':
                        message = {'sync': {'t1': time.time()}}
                    message_str = utils.object2str(message)
                    #This blocks the process if remote peer is not connected.
                    #Receiving messages is blocked too which resumes only when remote peer is available.
                    #If this does not happen, Process.terminate() terminates the process.
                    self.socket.send(message_str)
                    if hasattr(self.log, 'info'):
                        self.log.info('sent: ' + log.log2str(message),self.socket_name)
                try:
                    message = self.socket.recv(flags=zmq.NOBLOCK)
                    message = utils.str2object(message)
                    if hasattr(message,'has_key') and message.has_key('sync'):
                        if message['sync'].has_key('t2'):
                            message['sync']['t1'] = time.time()
                            self.socket_queues['fromsocket'].put(message)
                        else:
                            message['sync']['t2']=time.time()
                            self.socket_queues['tosocket'].put(message)
                    elif message == 'ping':
                        self.socket_queues['tosocket'].put('pong')
                    else:
                        self.socket_queues['fromsocket'].put(message)
                    if hasattr(self.log, 'info'):
                        self.log.info('received: ' + log.log2str(message),self.socket_name)
                except zmq.ZMQError:
                    pass#Nothing has received
#                    import traceback
#                    m=traceback.format_exc()
#                    if ' temporarily unavailable' in m:
#                        m = 'tmp unav'
#                    if 'anal' not in self.socket_name:
#                        self.log.info('error: ' + m,self.socket_name)
                if not self.command.empty() and self.command.get() =='terminate':
                    break
                time.sleep(self.loop_wait)
            except:
                import traceback
                if hasattr(self.log, 'error'):
                    self.log.error(traceback.format_exc(),self.socket_name)
        self.command.put('terminated')
        if hasattr(self.log, 'info'):
            self.log.info('process ended', self.socket_name)

def start_sockets(uiname, config, log, enable_sockets):
    '''
    Starts sockets depending on config.CONNECTIONS and uiname.
    '''
    sockets = {}
    if uiname == 'main_ui':
        for server_name in config.CONNECTIONS.keys():
            sockets[server_name] = QueuedSocket('{0}-{1} socket'.format(uiname, server_name), 
                                                                                    False, #client started
                                                                                    config.CONNECTIONS[server_name]['port'],
                                                                                    multiprocessing.Queue(), 
                                                                                    multiprocessing.Queue(), 
                                                                                    ip= config.CONNECTIONS[server_name]['ip'][server_name],
                                                                                    log=log)
    else:
        sockets[uiname] = QueuedSocket('{0}-{1} socket'.format(uiname, 'main_ui'), 
                                                                                    True, #server started
                                                                                    config.CONNECTIONS[uiname]['port'],
                                                                                    multiprocessing.Queue(), 
                                                                                    multiprocessing.Queue(), 
                                                                                    ip = config.CONNECTIONS[uiname]['ip'][uiname],
                                                                                    log=log)
    if not ((introspect.is_test_running() and platform.system()=='Windows') and '--testmode' in sys.argv) and enable_sockets:
        [s.start() for s in sockets.values()]#Not run when unittests of gui are executed on windows platform
    return sockets
    
def get_queues(sockets):
    queues = {}
    for k,v in sockets.items():
        queues[k] = {}
        queues[k]['fromsocket'] = v.socket_queues['fromsocket']
        queues[k]['tosocket'] = v.socket_queues['tosocket']
    return queues
    
    
def stop_sockets(sockets):
    [s.terminate() for s in sockets.values() if s.is_alive()]

class TestQueuedSocket(unittest.TestCase):
    def setUp(self):
        import random
        self.port = random.randrange(20000,20100)
        
    def _wait4queues(self,queues):
        t0=time.time()
        while True:
            time.sleep(0.1)
            if isinstance(queues, dict):
                q = queues.values()
            else:
                q = queues
            if all([not qi.empty() for qi in q]) or time.time()-t0>30:
                break
                
    def test_01_simple_transfer(self):
        from visexpman.users.test.test_configurations import GUITestConfig
        from visexpman.engine.generic import log
        from visexpman.engine.generic import fileop
        import os.path
        config = GUITestConfig()
        config.user = 'test'
        config.user_interface_name = 'main_ui'
        server = QueuedSocket('server', True, self.port, multiprocessing.Queue(), multiprocessing.Queue())
        client = QueuedSocket('client', False, self.port, multiprocessing.Queue(), multiprocessing.Queue(), ip='localhost')
        client.start()
        server.start()
        client.send(['request'])
        server.send(['response'])
        self._wait4queues(client.socket_queues)
        self.assertEqual(['request'],server.recv())
        self.assertEqual(['response'],client.recv())
        for s in [client,server]:
            s.terminate()
        
    def test_02_big_data_transfer(self):
        server = QueuedSocket('server', True, self.port, multiprocessing.Queue(), multiprocessing.Queue())
        client = QueuedSocket('client', False, self.port, multiprocessing.Queue(), multiprocessing.Queue(), ip='localhost')
        client.start()
        server.start()
        import numpy
        data = numpy.random.random(5000)
        client.send(data)
        server.send(data)
        self._wait4queues(client.socket_queues)
        self.assertEqual(data.sum(),server.recv().sum())
        self.assertEqual(data.sum(),client.recv().sum())
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
        gui['stim'].send({'start_experiment':True})
        gui['analysis'].send(range(10))
        servers['stim'].send('Done')
        self._wait4queues([gui['stim'].socket_queues['fromsocket'], servers['analysis'].socket_queues['fromsocket'], servers['stim'].socket_queues['fromsocket']])
        self.assertEqual('Done',gui['stim'].recv())
        self.assertEqual(range(10), servers['analysis'].recv())
        self.assertEqual({'start_experiment':True}, servers['stim'].recv())
        for c in server_names:
            gui[c].terminate()
            servers[c].terminate()
    
    def test_04_bind2ip(self):
        server = QueuedSocket('server', True, self.port, multiprocessing.Queue(), multiprocessing.Queue(), ip = utils.get_ip())
        client = QueuedSocket('client', False, self.port, multiprocessing.Queue(), multiprocessing.Queue(), ip= utils.get_ip())
        client.start()
        server.start()
        data1 = range(10)
        data2 = {'a':2}
        client.send(data1)
        server.send(data2)
        self._wait4queues(client.socket_queues)
        self.assertEqual(data1,server.recv())
        self.assertEqual(data2,client.recv())
        for s in [client,server]:
            s.terminate()
        
    def test_05_start_sockets_from_config(self):
        '''
        QueuedSockets are started from a machine config.
        '''
        from visexpman.users.test.test_configurations import GUITestConfig
        from visexpman.engine.generic import log
        from visexpman.engine.generic import fileop
        import os.path
        config = GUITestConfig()
        config.user = 'test'
        uinames = ['main_ui']
        uinames.extend(config.CONNECTIONS.keys())
        logfiles = []
        for uiname in uinames:
            config.user_interface_name = uiname
            logger = log.Logger(filename=log.get_logfilename(config), remote_logpath = config.REMOTE_LOG_PATH)
            sockets = start_sockets(uiname, config, log=logger, enable_sockets = True)#Unit under test
            logger.start()
            time.sleep(4.0)
            stop_sockets(sockets)
            logger.terminate()
            logfiles.append(logger.filename)
        self.assertNotEqual(map(os.path.getsize, logfiles), len(logfiles) * [0])
        self.assertEqual([True for logfile in logfiles if 'error' in fileop.read_text_file(logfile).lower()],[])#Check if there is any error in logfiles
    
    def test_06_ping_connections(self):
        server = QueuedSocket('server', True, self.port, multiprocessing.Queue(), multiprocessing.Queue(), ip = utils.get_ip())
        client = QueuedSocket('client', False, self.port, multiprocessing.Queue(), multiprocessing.Queue(), ip= utils.get_ip())
        client.start()
        server.start()
        time.sleep(2)
        self.assertTrue(client.ping(10))
        self.assertTrue(server.ping(10))
        for s in [client,server]:
            s.terminate()
            
if __name__ == "__main__":
    unittest.main()
