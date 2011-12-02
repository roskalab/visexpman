import network_interface
import unittest
import time
import PyQt4.QtCore as QtCore
import visexpman.engine.generic.configuration
import socket
import Queue
import sys
import scipy.io
import visexpA.engine.datahandlers.matlabfile as matlabfile
import numpy
import Image

def get_objective_position(mat_file):    
    m = matlabfile.MatData(mat_file)
    data = m.get_field('DATA')
    n_frames = data[0].shape[0]
    if n_frames <= 2: #For some reason sometimes two data units reside in the mat file
        data = m.get_field('DATA.Zlevel.0')[0].flatten()
    else:
        data = []
        data_set = m.get_field('DATA.Zlevel') 
        for i in range(n_frames):
            data.append(data_set[0][i][0][0][0])
        data = numpy.array(data)
    return data

def image_from_mes_mat(mat_file, image_file = None, z_stack = False):
    if z_stack:
        data = matlabfile.MatData(mat_file).get_field('DATA')
        n_frames = data[0].shape[0]
        frames = []
        for i in range(n_frames):
            frame = data[0][i]['IMAGE'][0]
            frames.append(frame)
        image = numpy.array(frames)
    else:
        image = matlabfile.MatData(mat_file).get_field('DATA.0.IMAGE')[0]

    image_f32 = numpy.cast['float32'](image)
    image = image_f32 / 2.0**7
    image = numpy.cast['uint8'](image)
    
    if not z_stack:
        im = Image.fromarray(image)
        if image_file != None:
            im.save(image_file)
    return image_f32
    
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
        self.command_server = command_server
        self.stop = False


    def set_scan_time(self, scan_time, reference_path, target_path):        

        m = matlabfile.MatData(reference_path, target_path)
        ts = m.get_field(m.name2path('ts'))[0][0][0][0]
        ts = numpy.array([ts[0],ts[1],ts[2],float(1000*scan_time)], dtype = numpy.float64)
        m.set_field(m.name2path('ts'), ts, allow_dtype_change=True)
            
    def _watch_keyboard(self):
        #Keyboard commands
        if self.screen != None:
            return self.screen.experiment_user_interface_handler() #Here only commands with running experiment domain are considered
        
        #TODO: handle US parameter from mes: user abort
    def start_line_scan(self, mat_file_path):
        aborted = False
        self.stop = False
        if self.command_server.connection_state:
            self.command_queue.put('SOCacquire_line_scanEOC{0}EOP'.format(mat_file_path))
            #Wait for MES response        
            while True:
                try:
                    response = self.response_queue.get(False)
                except:
                    response = ''
                if 'SOCacquire_line_scanEOCstartedEOP' in response:
                    if self.log != None:
                        self.log.info('line scan started')
                        self.command_server.enable_keep_alive_check = False
                    break
                elif 'SOCacquire_line_scanEOCerror_starting_measurementEOP' in response:
                    aborted = True
                    if self.log != None:
                        self.log.info('error starting measurement')
                        self.stop = True
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
        if self.command_server.connection_state:
            self.command_server.enable_keep_alive_check = False
           #wait for finishing two photon acquisition
            while True:
                if self.stop:
                    break
                try:
                    response = self.response_queue.get(False)
                except:
                    response = ''
                if 'SOCacquire_line_scanEOCOKEOP' in response or 'SOCacquire_line_scanEOCUSEOP' in response:
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
        if self.command_server.connection_state:
            #Wait for saving data to disk
            while True:
                if self.stop:
                    break
                try:
                    response = self.response_queue.get(False)
                except:
                    response = ''
                if 'SOCacquire_line_scanEOCsaveOKEOP' in response:
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
                        ['SOCacquire_line_scanEOCstartedEOP', 0.35], 
                        ['SOCacquire_line_scanEOCOKEOP', 0.35], 
                        ['SOCacquire_line_scanEOCsaveOKEOP', 0.35], ]

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
        time.sleep(0.1)
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
       #TODO: this test has to be reworked because of the network thing
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
#    unittest.main()
    mat_file = '/media/sf_M_DRIVE/Zoltan/visexpman/data/0_X-820381_Y-252527_Z+57516/acquire_z_stack_parameters_MovingDot_1321687013_0.mat'
    print get_objective_position(mat_file)    
    mat_file = '/media/sf_M_DRIVE/Zoltan/visexpman/data/test.mat'    
    print get_objective_position(mat_file)
