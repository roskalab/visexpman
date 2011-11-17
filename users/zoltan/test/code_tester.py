import visexpman.engine.hardware_interface.network_interface as network_interface
import Queue
import visexpman.engine.generic.configuration as configuration
import sys
import time

class NetworkInterfaceTestConfig(configuration.Config):
    def _create_application_parameters(self):
        import random
        port = 10000 + int(10000*random.random())
        CLIENT = {'ENABLE' : True, 'IP': 'localhost',  'PORT' : port,  'RECEIVE_BUFFER' : 256}
        SERVER = {'ENABLE' : True, 'IP': '',  'PORT' : port,  'RECEIVE_BUFFER' : 256}
        self._create_parameters_from_locals(locals())

        
if __name__ == '__main__':
    config = NetworkInterfaceTestConfig()
    server_command_queue = Queue.Queue()
    server_response_queue = Queue.Queue()
    server = network_interface.CommandServer(server_command_queue, server_response_queue, config.SERVER['PORT'])
    client_out_queue = Queue.Queue()
    client_in_queue = Queue.Queue()
    client = network_interface.CommandClient(client_out_queue, client_in_queue, config.CLIENT['IP'], config.CLIENT['PORT'])
    
    server.start()
    client.start()
    client_out_queue.put('from client1')
    server_command_queue.put('from server1')
    server_command_queue.put('from server2')
#    server_command_queue.put('SOCtest4EOC')
    time.sleep(1.0)
    client_out_queue.put('from client2')
#    server_command_queue.put('SOCclose_connectionEOC')    
    time.sleep(2.0)

    print '-------------------'
    print '----server_command_queue'
    while not server_command_queue.empty():
        print server_command_queue.get()
        
    print '----server_response_queue'
    while not server_response_queue.empty():
        print server_response_queue.get()
        
    print '----client_out_queue'
    while not client_out_queue.empty():
        print client_out_queue.get()
        
    print '----client_in_queue'
    while not client_in_queue.empty():
        print client_in_queue.get()
