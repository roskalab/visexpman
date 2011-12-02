import visexpman.engine.generic.configuration as configuration
import visexpman.engine.hardware_interface.network_interface as network_interface
import time
import Queue

class CommandRelayTestConfig(configuration.Config):
    def _create_application_parameters(self):
        import random
        self.BASE_PORT = 10000 +0* int(10000*random.random())
        COMMAND_RELAY_SERVER  = {
        'RELAY_SERVER_IP' : 'localhost', 
        'CONNECTION_MATRIX':
            {
            'GUI_MES'  : {'GUI' : {'IP': 'localhost', 'PORT': self.BASE_PORT}, 'MES' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 1}}, 
            'STIM_MES'  : {'STIM' : {'IP': 'localhost', 'PORT': self.BASE_PORT+2}, 'MES' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 3}}, 
            'GUI_STIM'  : {'GUI' : {'IP': 'localhost', 'PORT': self.BASE_PORT+4}, 'STIM' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 5}}, 
            'GUI_ANAL'  : {'GUI' : {'IP': 'localhost', 'PORT': self.BASE_PORT+6}, 'ANAL' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 7}}, 
            'STIM_ANAL'  : {'STIM' : {'IP': 'localhost', 'PORT': self.BASE_PORT+8}, 'ANAL' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 9}}, 
            }
        
        }
        self._create_parameters_from_locals(locals())

if __name__ == "__main__":  
    queue_in = Queue.Queue()
    queue_out = Queue.Queue()
    config = CommandRelayTestConfig()
    cr = network_interface.CommandRelayServer(config)    
    a = network_interface.start_client(config, 'GUI', 'GUI_MES', queue_in, queue_out)
    
    time.sleep(30.0)
    while not cr.debug_queue.empty():
        print cr.debug_queue.get()
    
