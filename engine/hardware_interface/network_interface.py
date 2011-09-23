import socket
import threading
import Queue
import sys
import time
import unittest
import visexpman.engine.generic.configuration

#Try: multiple clients, client thread starts in a thread, command buffer mutual exclusion. check out thread/target parameter
#Network listener -> CommandServer

class NetworkListener(threading.Thread):
    '''
    '''
    def __init__(self, config, caller):
        target = None
        name = None
        threading.Thread.__init__(self, target=target, name=name)
        self.config = config
        self.caller = caller
        self.setDaemon(True)

        #set up socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bind the socket to the port
        server_address = (self.config.SERVER_IP, self.config.COMMAND_INTERFACE_PORT)
        self.socket.bind(server_address)

    def run(self):
        self.socket.listen(1)        
        while True:
            #Connections are not accepted during experiment
            if self.caller.state == 'ready':
                connection, client_address = self.socket.accept()
                try:
                    data = ''
                    while True:
                        newdata = connection.recv(16)
                        data = data+newdata
                        if len(newdata)==0:
    #                        print >>sys.stderr, 'received "%s"' % data
                            self.caller.command_queue.put(data)
                            break
                except Exception as e:
                    print e
                finally:
                    # Clean up the connection
                    connection.close()

class NetworkSender(threading.Thread):
    '''
    '''
    def __init__(self, config, caller):
        target = None
        name = None
        threading.Thread.__init__(self, target=target, name=name)
        self.config = config
        self.caller = caller

    def run(self):        
        for i in range(3):
            sock = socket.create_connection((self.config.SERVER_IP,  self.config.COMMAND_INTERFACE_PORT))
            sock.sendall(str(i))
            time.sleep(0.1)

class NetworkInterfaceTestConfig(visexpman.engine.generic.configuration.Config):
    def _create_application_parameters(self):
        SERVER_IP = 'localhost'
        COMMAND_INTERFACE_PORT = [10001, [300,  65000]]
        self._create_parameters_from_locals(locals())

class testRunner():
    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(False)
        

    def run(self):
        print 'test runner started'        
        config = NetworkInterfaceTestConfig()
        listener = NetworkListener(config, self)
        sender1 = NetworkSender(config, self)
        sender2 = NetworkSender(config, self)
        listener.start()
        sender1.start()
        time.sleep(0.5)
        sender2.start()
        time.sleep(0.5)
        self.response = ''
        while not self.command_queue.empty():
            self.response += self.command_queue.get()
        print self.response

        
class testNetworkInterface(unittest.TestCase):
    def setUp(self):
        self.state = 'ready'
        
    def test_01_multiple_senders(self):
        self.command_queue = Queue.Queue()
        config = NetworkInterfaceTestConfig()
        listener = NetworkListener(config, self)
        sender1 = NetworkSender(config, self)
        sender2 = NetworkSender(config, self)
        listener.start()
        sender1.start()
        time.sleep(0.5)
        sender2.start()
        time.sleep(0.5)
        response = ''
        while not self.command_queue.empty():
            response += self.command_queue.get()        
        self.assertEqual((response),  ('012012'))
        
if __name__ == "__main__":
    unittest.main()
#    testRunner().start()
    
