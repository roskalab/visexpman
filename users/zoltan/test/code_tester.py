import visexpman.engine.hardware_interface.network_interface as network_interface
import Queue
import visexpman.engine.generic.configuration as configuration
import sys
import time

class GuiConfig(configuration.Config):
    def _create_application_parameters(self):
        if len(sys.argv) > 1:
            port = int(sys.argv[1])
        else:
            port = 10000
            
        if len(sys.argv) > 2:
            self.working_path =  sys.argv[2]
        else:
            self.working_path = 'c:\\temp\\test'
        MES = {'ip': '',  'port' : port,  'receive buffer' : 256}
        VISEXPMAN = {'ip': '',  'port' : 10001}
        VISEXPA = {'ip': '',  'port' : 10002}        
        self._create_parameters_from_locals(locals())
        
if __name__ == '__main__':
    commands = ['test', 'SOCclose_connectionEOC']
    config = GuiConfig()    
    command_queue = Queue.Queue()
    response_queue = Queue.Queue()
    server = network_interface.MesServer(config, command_queue, response_queue)
    server.start()
    for cmd in commands:
        command_queue.put(cmd)
        time.sleep(1.0)
    
    
    time.sleep(20.0)
