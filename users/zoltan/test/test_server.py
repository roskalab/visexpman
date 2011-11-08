import time
import socket
import sys
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import visexpman.engine.generic.utils as utils
import visexpman.engine.generic.configuration as configuration
import visexpman.engine.hardware_interface.network_interface as network_interface
import Queue
import visexpman.engine.visexpman_gui

class ServerConfig(configuration.Config):
    def _create_application_parameters(self):
        MES = {'ip': '',  'port' : int(sys.argv[2]),  'receive buffer' : 256}
        VISEXPMAN = {'ip': '',  'port' : 10001}
        VISEXPA = {'ip': '',  'port' : 10002}
        
        self._create_parameters_from_locals(locals())

if __name__ == '__main__':
    command_queue = Queue.Queue()
    response_queue = Queue.Queue()
    for i in range(5):
        command_queue.put('SOCacquire_camera_imageEOC/path/path/file.mEOP')
    command_queue.put('SOCdummyEOCEOP')
    command_queue.put('SOCclose_connectionEOCEOP')
    config = ServerConfig()
    server = network_interface.MesServer(config, command_queue, response_queue)
    server.start()
    time.sleep(int(sys.argv[1]))
    
    while not response_queue.empty():
        print response_queue.get()
