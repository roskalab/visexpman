import network_interface
import unittest
import time
import PyQt4.QtCore as QtCore
import visexpman.engine.generic.configuration
import socket
import Queue
import sys
#TODO: do not wait when mes is not connected
class MesInterface(object):
    '''
    Protocol:
        1. acquire_line_scan, parameter: mat file path on MES computer
        2. Response from MES computer: acquire_line_scan, started
        3. visual stimulation
        4. acquire_line_scan, OK is received when the two photon acquisition is finished
        5. acquire_line_scan, saveOK is received when saving data is complete
    '''
    def __init__(self, config, command_queue, response_queue, command_server, screen = None, log = None, ):
        self.config = config
        self.command_queue = command_queue
        self.response_queue = response_queue
        self.screen = screen
        self.log = log
        if self.config.VISEXPMAN_MES['ENABLE']:
            self.command_server = command_server
            
    def _watch_keyboard(self):
        #Keyboard commands
        if self.screen != None:
            return self.screen.experiment_user_interface_handler() #Here only commands with running experiment domain are considered           
                
                        
        
        
    def start_line_scan(self, mat_file_path):
        aborted = False
        if self.config.VISEXPMAN_MES['ENABLE']:
            self.command_queue.put('SOCacquire_line_scanEOC{0}EOP'.format(mat_file_path))
            #Wait for MES response        
            while True:
                try:
                    response = self.response_queue.get(False)
                except:
                    response = ''
                if response.find('SOCacquire_line_scanEOCstartedEOP') != -1:
                    if self.log != None:
                        self.log.info('line scan started')
                        self.command_server.enable_keep_alive_check = False
                    break
                user_command = self._watch_keyboard()
                if user_command != None:
                    if user_command.find('stop') != -1:
                        aborted = True
                        if self.log != None:
                            self.log.info('stopped')
                        break
                time.sleep(0.1)
        return aborted
                
    def wait_for_line_scan_complete(self):        
        aborted = False
        if self.config.VISEXPMAN_MES['ENABLE']:
            self.command_server.enable_keep_alive_check = False
           #wait for finishing two photon acquisition
            while True:
                try:
                    response = self.response_queue.get(False)
                except:
                    response = ''
                if response.find('SOCacquire_line_scanEOCOKEOP') != -1:
                    if self.log != None:
                        self.log.info('line scan complete')
                    break
                user_command = self._watch_keyboard()
                if user_command != None:
                    if user_command.find('stop') != -1:
                        aborted = True
                        if self.log != None:
                            self.log.info('stopped')
                        break                    
                time.sleep(0.1)
        return aborted
                
    def wait_for_data_save_complete(self):
        aborted = False
        if self.config.VISEXPMAN_MES['ENABLE']:
            #Wait for saving data to disk
            while True:
                try:
                    response = self.response_queue.get(False)
                except:
                    response = ''
                if response.find('SOCacquire_line_scanEOCsaveOKEOP') != -1:
                    if self.log != None:
                        self.log.info('line scan data saved')
                    break
                user_command = self._watch_keyboard()
                if user_command != None:
                    if user_command.find('stop') != -1:
                        aborted = True
                        if self.log != None:
                            self.log.info('stopped')
                        break                    
                time.sleep(0.1)
            self.command_server.enable_keep_alive_check = True
        return aborted
    
class MesEmulator(QtCore.QThread):
    def __init__(self, config, port):
        self.config = config
        self.port = port
        QtCore.QThread.__init__(self)

        self.commands  = [['', 0.5], 
                        ['SOCacquire_line_scanEOCstartedEOP', 0.5], 
                        ['SOCacquire_line_scanEOCOKEOP', 0.5], 
                        ['SOCacquire_line_scanEOCsaveOKEOP', 0.5], ]

    def run(self):
        self.sock = socket.create_connection(('localhost', self.port))
        self.sock.send('create_connection')
        self.sock.recv(256)
        time.sleep(0.1)
        for command in self.commands:
            if len(command[0]) > 0:
                try:
                    self.sock.send(command[0])
                except:
                    print 'Error'
                    pass
            time.sleep(command[1])
            
        self.sock.close()
            
class ExperimentThread(QtCore.QThread):
    def __init__(self, config, command_queue, response_queue, command_server):
        QtCore.QThread.__init__(self)
        self.config = config
        self.command_queue = command_queue
        self.response_queue = response_queue
        self.command_server = command_server
        self.done = False        
        
    def run(self):
        self.mes_if = MesInterface(self.config, self.command_queue, self.response_queue, self.command_server)
        self.mes_if.start_line_scan('dummy.mat')
        time.sleep(1.0)
        self.mes_if.wait_for_line_scan_complete()
        time.sleep(0.3)
        self.mes_if.wait_for_data_save_complete()
        self.done = True        
            
class NetworkInterfaceTestConfig(visexpman.engine.generic.configuration.Config):
    def _create_application_parameters(self):
        import random
        port = 10000 + int(10000*random.random())
        VISEXPMAN_MES = {'ENABLE' : True, 'IP': '',  'PORT' : port,  'RECEIVE_BUFFER' : 256}
        self._create_parameters_from_locals(locals())

            
class TestMesInterface(unittest.TestCase):
    def setUp(self):
       
        self.config = NetworkInterfaceTestConfig()
        self.command_queue = Queue.Queue()
        self.response_queue = Queue.Queue()
        self.command_server = network_interface.CommandServer(self.command_queue, self.response_queue, self.config.VISEXPMAN_MES['PORT'])
        self.mes = MesEmulator(self.config, self.config.VISEXPMAN_MES['PORT'])
        self.experiment = ExperimentThread(self.config, self.command_queue, self.response_queue, self.command_server)

    def test_01_interaction_with_mes_emulator(self):
        self.command_server.start()
        self.mes.start()
        self.experiment.start()
        time.sleep(3.0)
        self.assertEqual(self.experiment.done,  True)
        
    def tearDown(self):
        self.command_server.terminate()
        self.mes.terminate()        
        self.experiment.terminate()
        
    
if __name__ == "__main__":
    unittest.main()
