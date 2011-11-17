import visexpman.engine.hardware_interface.network_interface as network_interface
import Queue
import visexpman.engine.generic.configuration as configuration
import sys
import time
import socket
import PyQt4.QtCore as QtCore

class NetworkTestConfig(configuration.Config):
    def _create_application_parameters(self):
        import random
        port = 10000 + int(10000*random.random())
        CLIENT = {'ENABLE' : True, 'IP': 'localhost',  'PORT' : port,  'RECEIVE_BUFFER' : 256}
        SERVER = {'ENABLE' : True, 'IP': '',  'PORT' : port,  'RECEIVE_BUFFER' : 256}
        self._create_parameters_from_locals(locals())
        
class NetworkCommandInterface(QtCore.QThread):
    def __init__(self, data_in, data_out, role, address, port, buffer_size = 256):
        QtCore.QThread.__init__(self)
        self.data_in = data_in #from the network
        self.data_out = data_out #to the network
        self.address = address
        self.port = port
        self.buffer_size = buffer_size
        self.role = role #server or client
        
    def run(self):
        end_loop = False
        if self.role == 'server':
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)            
            server_address = ('', self.port)
            self.socket.bind(server_address)
            self.socket.listen(1)
            while True:
                self.connection, client_address = self.socket.accept()
                self.connection.setblocking(0)
                self.data_out.put('connection_accepted')
                while True:
                    if self.data_out.empty():
                        try:
                            data_in = self.connection.revc(self.buffer_size)
                            self.data_in.put(data_in)
                            print 'Server data in: ' + data_in
                        except:
                            print sys.exc_info()
                            data_in = ''
                    else:
                        data_out = self.data_out.get()
                        self.connection.send(data_out)
                        print 'Server data out: ' + data_out
                        if data_out.find('SOCclose_connectionEOC') != -1:
                            end_loop = True
                    if end_loop:
                        break
                    time.sleep(0.05)
                if end_loop:
                    break
            print 'Server done'
        elif self.role == 'client':
            while True:              
                self.connection = socket.create_connection((self.address, self.port))
                self.connection.setblocking(0)
                self.data_out.put('SOCconnection_createdEOC')
                while True:
                    if self.data_out.empty():
                        try:
                            data_in = self.connection.revc(self.buffer_size)
                            self.data_in.put(response)
                            print 'Client data in: ' + data_in
                        except:
                            data_in = ''
                            print sys.exc_info()
                        if data_in.find('SOCclose_connectionEOC') != -1:
                            end_loop = True
                    else:
                        data_out = self.data_out.get()
                        self.connection.send(data_out)
                        print 'Client data out: ' + data_out
                        if data_out.find('terminate_client') != -1:
                            end_loop = True
                        
                    if end_loop:
                        break
                    time.sleep(0.05)
                if end_loop:
                    break

            print 'Client done'
                    
        !!!!! queue.get blocks
    

        
if __name__ == '__main__':    
        
    import random
    port = 10000+int(10000*random.random())
    client_data_in = Queue.Queue()
    client_data_out = Queue.Queue()
    server_data_in = Queue.Queue()
    server_data_out = Queue.Queue()
    server = NetworkCommandInterface(server_data_in, server_data_out, 'server', '', port)
    client = NetworkCommandInterface(client_data_in, client_data_out, 'client', 'localhost', port)
    server.start()
    client.start()
#     time.sleep(1.0)
#     server_data_out.put('SOCtest1EOC')
#     time.sleep(0.1)
#     client_data_out.put('SOCtest2EOC')
#     client_data_out.put('terminate_client')
    time.sleep(1.0)
    server_data_out.put('SOCclose_connectionEOC')
    time.sleep(2.0)



#     config = NetworkInterfaceTestConfig()
#     server_command_queue = Queue.Queue()
#     server_response_queue = Queue.Queue()
#     server = network_interface.CommandServer(server_command_queue, server_response_queue, config.SERVER['PORT'])
#     client_out_queue = Queue.Queue()
#     client_in_queue = Queue.Queue()
#     client = network_interface.CommandClient(client_out_queue, client_in_queue, config.CLIENT['IP'], config.CLIENT['PORT'])
#     
#     server.start()
#     client.start()
#     client_out_queue.put('from client1')
#     server_command_queue.put('from server1')
#     server_command_queue.put('from server2')
# #    server_command_queue.put('SOCtest4EOC')
#     time.sleep(1.0)
#     client_out_queue.put('from client2')
# #    server_command_queue.put('SOCclose_connectionEOC')    
#     time.sleep(2.0)
# 
#     print '-------------------'
#     print '----server_command_queue'
#     while not server_command_queue.empty():
#         print server_command_queue.get()
#         
#     print '----server_response_queue'
#     while not server_response_queue.empty():
#         print server_response_queue.get()
#         
#     print '----client_out_queue'
#     while not client_out_queue.empty():
#         print client_out_queue.get()
#         
#     print '----client_in_queue'
#     while not client_in_queue.empty():
#         print client_in_queue.get()
