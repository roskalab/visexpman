import zmq
import time
import multiprocessing
from visexpman.engine.generic import utils
import unittest

class QueuedSocket(multiprocessing.Process):
    '''
    Constructed with ip address: client, otherwise server. Non blocking reading of socket. Data is put to queue. 
    Received data is also saved to a queue
    '''
    def __init__(self, socket_name, port, tosocket, fromsocket, ip = None, log = None):
        self.socket_name = socket_name
        self.port = port
        self.tosocket = tosocket
        self.fromsocket = fromsocket
        self.ip= ip
        self.command = multiprocessing.Queue()
        self.loop_wait = 0.1
        multiprocessing.Process.__init__(self)
        self.log=log
        if hasattr(self.log, 'add_source'):
            self.log.add_source(self.socket_name)
        
    def terminate(self):
        self.command.put('terminate')

    def run(self):
        context = zmq.Context()
        self.socket = context.socket(zmq.PAIR)
        if self.ip is None:
            self.socket.bind("tcp://*:{0}" .format(self.port))
        else:
            self.socket.connect("tcp://{0}:{1}".format(self.ip, self.port))
        while True:
            if not self.tosocket.empty():
                message = self.tosocket.get()
                message = utils.object2str(message)
                if hasattr(self.log, 'info'):
                    self.log.info('sent: ' + str(message))
                self.socket.send(message)
            try:
                message = self.socket.recv(flags=zmq.NOBLOCK)
                message = utils.str2object(message)
                if hasattr(self.log, 'info'):
                    self.log.info('received: ' + str(message))
                self.fromsocket.put(message)
            except zmq.ZMQError:
                pass#Nothing has received
            if not self.command.empty() and self.command.get()=='terminate':
                break
            time.sleep(self.loop_wait)
            
class TestQueuedSocket(unittest.TestCase):
    def setUp(self):
        import random
        self.port = random.randrange(10000,20000)
        
    def test_01_simple_transfer(self):
        server = QueuedSocket('server', self.port, multiprocessing.Queue(), multiprocessing.Queue())
        client = QueuedSocket('client', self.port, multiprocessing.Queue(), multiprocessing.Queue(), ip='localhost')
        client.start()
        server.start()
        client.tosocket.put(['request'])
        server.tosocket.put(['response'])
        time.sleep(1.0)
        for s in [client,server]:
            s.terminate()
        for s in [client,server]:
            s.join()
        self.assertEqual(['request'],server.fromsocket.get(block=False))
        self.assertEqual(['response'],client.fromsocket.get(block=False))
        
    def test_02_big_data_transfer(self):
        server = QueuedSocket('server', self.port, multiprocessing.Queue(), multiprocessing.Queue())
        client = QueuedSocket('client', self.port, multiprocessing.Queue(), multiprocessing.Queue(), ip='localhost')
        client.start()
        server.start()
        import numpy
        data = numpy.random.random(5000)
        client.tosocket.put(data)
        server.tosocket.put(data)
        time.sleep(1.0)
        for s in [client,server]:
            s.terminate()
        for s in [client,server]:
            s.join()
        self.assertEqual(data.sum(),server.fromsocket.get(block=False).sum())
        self.assertEqual(data.sum(),client.fromsocket.get(block=False).sum())
        
    def test_03_multiple_servers(self):
        server_names = ['stim','analysis', 'ca_imaging']
        gui = {}
        servers = {}
        i = 0
        for c in server_names:
            gui[c] = QueuedSocket('gui-{0}'.format(c), self.port+i, multiprocessing.Queue(), multiprocessing.Queue(), ip='localhost')
            gui[c].start()
            servers[c] = QueuedSocket(c, self.port+i, multiprocessing.Queue(), multiprocessing.Queue())
            servers[c].start()
            i += 1
        gui['stim'].tosocket.put({'start_experiment':True})
        gui['analysis'].tosocket.put(range(10))
        servers['stim'].tosocket.put('Done')
        time.sleep(3.0)
        for c in server_names:
            gui[c].terminate()
            servers[c].terminate()
        print gui['stim'].fromsocket.get()
        print servers['stim'].fromsocket.get()
        print servers['analysis'].fromsocket.get()
            
if __name__ == "__main__":
    unittest.main()
