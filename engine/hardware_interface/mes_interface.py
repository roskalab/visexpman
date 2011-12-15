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
import os.path
import visexpman.engine.generic.utils as utils
import re
import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner
#TODO: This module needs to be reworked: two group of functions: communication helpers and mat interfacing, mes intrerface class shall take care of both
#TODO: generate reference mat files without the unnecessary numpy.object parts

class MesData(object):
    '''
    This class is responsible for reading/writing data from /to mes files
    '''
    def __init__(self, config = None):        
        self.config = config
        
    def read_rc_scan(self, mes_file):
        pass
    

        
    def generate_scan_points_mat(self, points, mat_file):
        '''
        Points shall be a struct array of numpy.float64 with x, y and z fields.
        numpy.zeros((3,100), {'names': ('x', 'y', 'z'), 'formats': (numpy.float64, numpy.float64, numpy.float64)})
        '''
        if points.dtype != [('row', '<f8'), ('col', '<f8'), ('depth', '<f8')]:
            raise RuntimeError('Data format is incorrect')
        data_to_mes_mat = {}
        data_to_mes_mat['DATA'] = points
        scipy.io.savemat(mat_file, data_to_mes_mat, oned_as = 'column')       

        
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
        
def set_mes_mesaurement_save_flag(mat_file, flag):
    m = matlabfile.MatData(reference_path, target_path)
    m.rawmat['DATA'][0]['DELETEE'] = int(flag) #Not tested, this addressing might be wrong
    m.flush()   
        
def set_line_scan_time(scan_time, reference_path, target_path):
    '''
    scan_time: in ms
    reference_path: reference mat file that will be used as a template
    target_path: 
    '''
    m = matlabfile.MatData(reference_path, target_path)
    ts = m.get_field(m.name2path('ts'))[0][0][0][0]
    ts = numpy.array([ts[0],ts[1],ts[2],numpy.round(float(1000*scan_time), 0)], dtype = numpy.float64)
    m.set_field(m.name2path('ts'), ts, allow_dtype_change=True)
    
class MesInterface(object):
    '''
    Protocol:
        1. acquire_line_scan, parameter: mat file path on MES computer
        2. Response from MES computer: acquire_line_scan, started
        3. visual stimulation
        4. acquire_line_scan, OK is received when the two photon acquisition is finished
        5. acquire_line_scan, saveOK is received when saving data is complete
    '''
    #TODO: handle situations when interface is disabled
    def __init__(self, config, connection = None, keyboard_handler = None, log = None):        
        self.config = config
        self.connection = connection
        if hasattr(self.connection, 'queue_out'):
            self.command_queue = self.connection.queue_out
        else:
            self.command_queue = None
        if hasattr(self.connection, 'queue_in'):
            self.response_queue = self.connection.queue_in
        else:
            self.response_queue = None
        self.keyboard_handler = keyboard_handler
        self.log = log
        self.stop = False
        self.mes_file_handler = MesData()

    #================ Z stack ========================#
    def acquire_z_stack(self, timeout = -1, channel = 'pmtUGraw', test_mat_file = None):
        z_stack_path, z_stack_path_on_mes = self._generate_mes_file_paths('z_stack.mat')
        utils.empty_queue(self.response_queue)
        results = []
        #Acquire z stack
        if self.connection.connected_to_remote_client():
            self.command_queue.put('SOCacquire_z_stackEOC{0}EOP' .format(z_stack_path_on_mes))
            results.append(network_interface.wait_for_response(self.response_queue, 'SOCacquire_z_stackEOCstartedEOP', timeout = timeout))
            if results[-1]:
                results.append(network_interface.wait_for_response(self.response_queue, ['SOCacquire_z_stackEOCOKEOP', 'SOCacquire_z_stackEOCUSEOP'], timeout = -1))                 
                results.append(network_interface.wait_for_response(self.response_queue, 'SOCacquire_z_stackEOCsaveOKEOP', timeout = -1))                
            else:
                #Remove command from command queue
                if not self.command_queue.empty():
                    self.command_queue.get()
                return {}, results
            #Extract z stack from mat file
            if test_mat_file != None:
                z_stack_path = test_mat_file
            z_stack = {}
            if isinstance(z_stack_path, str):
                if os.path.exists(z_stack_path):            
                    z_stack = self.mes_file_handler.read_z_stack(z_stack_path, channel = channel)
            return z_stack, results
        else:
            return {}, results

    #======================  RC scan =======================#
    def rc_scan(self, trajectory, timeout = -1):
        results = []
        scanned_trajectory = {}
        #Send trajectory points to mes
        results.append(self.set_trajectory(trajectory, timeout = timeout))
        rc_scan_path, rc_scan_path_on_mes = self._generate_mes_file_paths('rc_scan.mat')
        utils.empty_queue(self.response_queue)
        if self.connection.connected_to_remote_client():
            self.command_queue.put('SOCrc_scanEOC{0}EOP' .format(rc_scan_path_on_mes))
            results.append(network_interface.wait_for_response(self.response_queue, 'SOCrc_scanEOCstartedEOP', error_response = 'error', timeout = timeout))    
            results.append(network_interface.wait_for_response(self.response_queue, ['SOCrc_scanEOCOKEOP', 'SOCrc_scanEOCUSEOP'], error_response = 'error', timeout = timeout))
            results.append(network_interface.wait_for_response(self.response_queue, 'SOCrc_scanEOCsaveOKEOP', error_response = 'error', timeout = tmeout))            
            command_signal = []
            if os.path.exists(rc_scan_path):
                #Extract data from file
                pass
        return scanned_trajectory, results

    def set_trajectory(self, points, timeout = -1):
        points_mat, points_mat_on_mes = self._generate_mes_file_paths('rc_points.mat')
        self.mes_file_handler.generate_scan_points_mat(points, points_mat)
        utils.empty_queue(self.response_queue)
        self.command_queue.put('SOCset_pointsEOC{0}EOP' .format(points_mat_on_mes))
        return network_interface.wait_for_response(self.response_queue, 'SOCset_pointsEOCpoints_setEOP', error_response = 'error', timeout = timeout)    
        
    def get_rc_range(self, timeout = -1):
        '''
        MES returns the range as follows: xmin, xmax, ymin, ymax, z range
        
        Not tested yet
        
        '''
        self.command_queue.put('SOCget_rangeEOCEOP')
        result = network_interface.wait_for_response(self.response_queue, 'SOCget_rangeEOC', timeout = timeout)[0]
        ranges =  re.findall('EOC(.+)EOP',result).split(',')
        mes_scan_range = {}
        if len(ranges) == 5:
            mes_scan_range['col'] = map(float, result[:2])
            mes_scan_range['row'] = map(float, result[2:4])
            mes_scan_range['depth'] = map(float, result[4])
        return mes_scan_range
        
    #======================  Line scan =======================#    
            
    
    def prepare_line_scan(self, scan_time, template_parameter_file = None):
        '''
        '''        
        result = False, None
        if template_parameter_file == None:
            #Get parameters from MES by requesting a short line scan
            query_parameters_result, modified_parameter_file = self.start_line_scan(timeout = 2.0)            
            if query_parameters_result:
                query_parameters_response_result = self.wait_for_line_scan_complete(10.0)                
                if query_parameters_response_result:                    
                    query_parameters_response_result = self.wait_for_line_scan_save_complete(10.0)                    
                    if query_parameters_response_result:
                        #prepare parameter file
                        set_line_scan_time(scan_time, modified_parameter_file, modified_parameter_file)
                        result = True, modified_parameter_file                    
        else:
            parameter_file = utils.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'line_scan_parameters.mat'))
            set_line_scan_time(scan_time, template_parameter_file, parameter_file)
            result = True, parameter_file
        return result
        
    def start_line_scan(self, timeout = -1, parameter_file = None):
        if parameter_file == None:
            #generate a mes parameter file name, that does not exits
            line_scan_path, line_scan_path_on_mes = self._generate_mes_file_paths('line_scan_parameters.mat')
        else:
            line_scan_path = parameter_file
            line_scan_path_on_mes = utils.convert_path_to_remote_machine_path(line_scan_path, self.config.MES_DATA_FOLDER,  remote_win_path = (self.config.OS != 'win'))
        #previously sent garbage is removed from queue
        utils.empty_queue(self.response_queue)        
        #Acquire line scan if MES is connected
        if self.connection.connected_to_remote_client():
            self.command_queue.put('SOCacquire_line_scanEOC{0}EOP' .format(line_scan_path_on_mes))
            result = network_interface.wait_for_response(self.response_queue, 'SOCacquire_line_scanEOCstartedEOP', timeout = timeout, keyboard_handler = self.keyboard_handler)
            if result:
                self._log_info('line scan started')
            else:
                self._log_info('line scan not started')
        else:
            self._log_info('mes not connected')
            result = False
        return result, line_scan_path
        
    def wait_for_line_scan_complete(self, timeout = -1):        
        return self._wait_for_mes_response(timeout, ['SOCacquire_line_scanEOCOKEOP', 'SOCacquire_line_scanEOCUSEOP'])
        
        
    def wait_for_line_scan_save_complete(self, timeout = -1):
        return self._wait_for_mes_response(timeout, 'SOCacquire_line_scanEOCsaveOKEOP')    
    
####################### Private functions ########################

    def _wait_for_mes_response(self, timeout, expected_responses):
        '''
        Waits till MES sends notification about the completition of a certain command.
        Waiting is aborted by the following events:
            -timeout
            -stop keyboard command, if keyboard_handler is present
        '''        
        result = network_interface.wait_for_response(self.response_queue, 
                                                     expected_responses, 
                                                     timeout = timeout, 
                                                     keyboard_handler = self.keyboard_handler)
        if result:
            self._log_info('MES responded with ' + str(expected_responses))
        else:
            self._log_info('No MES response')
        return result
        
    def _log_info(self, message):
        if self.log != None:
            self.log.info(message)
        
    def _generate_mes_file_paths(self, filename):
        path = utils.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, filename))
        path_on_mes = utils.convert_path_to_remote_machine_path(path, self.config.MES_DATA_FOLDER,  remote_win_path = True)
        return path, path_on_mes
######
def read_z_stack(mes_file_or_stream, channel = 'pmtUGraw'):
    '''
    Extract the following form a mes file containing a Z stack:
    -z stack data as a 3D array where the dimensions are: row, col, depth
    -mes system origin [um]
    -step size [um/pixel]
    -z stack size [um; row, col, depth]
    '''
    #TODO: reverse z stack over z axis
    #TODO data in row col depth format
    if not hasattr(mes_file_or_stream, 'raw_mat') and not hasattr(mes_file_or_stream, 'get_field'):
        data = matlabfile.MatData(mes_file_or_stream).get_field('DATA')
    else:
        data = mes_file_or_stream.get_field('DATA')
    n_frames = data[0].shape[0]
    n_average = int(data[0][0]['Average'][0][0][0])
    frames = []
    for i in range(n_frames-1, -1, -1):  # MES takes zstacks from the bottom, we treat zstacks starting from the cortex surface
        frame = matlab_image2numpy(data[0][i]['IMAGE'][0])
        channel_name = str(data[0][i]['Channel'][0][0])
        if channel_name == channel:
            frames.append(frame)
        
    z_stack_data = numpy.array(frames)#.transpose()
    depth_step = data[0][0]['D3Step'][0][0]#TODO: use getfield
    col_origin = data[0][0]['WidthOrigin'][0][0]
    row_origin = data[0][0]['HeightOrigin'][0][0]
    depth_origin = data[0][0]['D3Origin'][0][0]
    col_step = data[0][0]['WidthStep'][0][0]
    row_step = data[0][0]['HeightStep'][0][0]
    z_stack = {}
    z_stack['data'] = z_stack_data
    z_stack['origin'] = utils.rcd(numpy.array([row_origin, col_origin, depth_origin]))
    z_stack['scale'] = utils.rcd(numpy.array([row_step, col_step, depth_step]))
    z_stack['size'] = utils.rcd(utils.nd(z_stack['scale']) * (numpy.array(z_stack_data.shape)    -1))
    return z_stack
    
def matlab_image2numpy(data):
    ''' Converts a numpy array containing data as matlab image in the format: col,row, origin at bottom left
    to a numpy image in the native format: row,col, origin at top left'''
    return numpy.rollaxis(data, 1, 0)[::-1] 

#############3
class MesEmulator(QtCore.QThread):    
    def __init__(self, response_pattern, queue_in, queue_out):        
        '''
        response_pattern:
        -['delay:  ,
            'response':]
        '''
        QtCore.QThread.__init__(self)
        self.response_pattern  = response_pattern
        self.queue_in = queue_in
        self.queue_out = queue_out
        self.acquire_line_scan_received = False
        
    def run(self):        
        while True:            
            if not self.queue_in.empty():
                message = self.queue_in.get()                
                command = re.findall('SOC(.+)EOC', message)
                parameter = re.findall('EOC(.+)EOP', message)                
                if 'acquire_line_scan' in message:
                    self.acquire_line_scan_received = True
                    for response in self.response_pattern:
                        time.sleep(response['delay'])
                        self.queue_out.put(response['response'])
                elif 'echo' in command:
                    self.queue_out.put(message)
            time.sleep(0.1)        
        
                
            
class MESTestConfig(visexpman.engine.generic.configuration.Config):
    def _create_application_parameters(self):
        import random
        self.BASE_PORT = 10000 + 1* int(10000*random.random())
        COMMAND_RELAY_SERVER  = {
        'RELAY_SERVER_IP' : 'localhost', 
        'ENABLE' : True, 
        'TIMEOUT':10.0, 
        'CONNECTION_MATRIX':
            {
            'MES_USER'  : {'MES' : {'IP': 'localhost', 'PORT': self.BASE_PORT}, 'USER' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 1}},            
            }
        }
        EXPERIMENT_DATA_PATH = unit_test_runner.TEST_working_folder
        MES_DATA_FOLDER = unit_test_runner.TEST_working_folder
        self._create_parameters_from_locals(locals())

class TestMesInterfaceEmulated(unittest.TestCase):
    
    def tearDown(self):
        self.user_to_client.put('SOCclose_connectionEOCstop_clientEOP')
        if hasattr(self, 'mes_queue_out'):
            self.mes_to_client.put('SOCclose_connectionEOCstop_clientEOP')
        if hasattr(self, 'server'):
            self.server.shutdown_servers()     
        time.sleep(1.0)
        
    def setUp(self):
        self.config = MESTestConfig()       
        self.user_to_client = Queue.Queue()
        self.client_to_user = Queue.Queue()
        self.user_client = network_interface.start_client(self.config, 'USER', 'MES_USER', self.client_to_user, self.user_to_client)
        self.mes_interface = MesInterface(self.config, connection = self.user_client)        
        if not '_01_' in self._testMethodName:
            self.server = network_interface.CommandRelayServer(self.config)
            self.mes_to_client = Queue.Queue()
            self.client_to_mes = Queue.Queue()
            self.mes_client = network_interface.start_client(self.config, 'MES', 'MES_USER', self.client_to_mes, self.mes_to_client)
    
    def test_01_line_scan_mes_not_connected(self):   
        result = self.mes_interface.start_line_scan(2.0)
        self.assertEqual((result[0], os.path.exists(result[1])), (False, False))
        
    def test_02_line_scan_start_fails(self):
        '''
        Connection test should pass but mes will not respond with 'line scan started'
        '''
        response_pattern = []
        mes_emulator = MesEmulator(response_pattern, self.client_to_mes, self.mes_to_client)
        mes_emulator.start()
        result = self.mes_interface.start_line_scan(1.0)
        self.assertEqual((result[0], mes_emulator.acquire_line_scan_received), (False, True))

    def test_03_line_scan_started(self):
        '''
        Line scan started without error
        '''
        response_pattern = [{'delay':0.1, 'response':'SOCacquire_line_scanEOCstartedEOP'}]
        mes_emulator = MesEmulator(response_pattern, self.client_to_mes, self.mes_to_client)
        mes_emulator.start()
        result = self.mes_interface.start_line_scan(1.0)        
        self.assertEqual((result[0], mes_emulator.acquire_line_scan_received), (True, True))
        
    def test_04_line_scan_started_timeout(self):
        '''
        Line scan started but later than the timeout given in start_line_scan
        '''
        response_pattern = [{'delay':1.1, 'response':'SOCacquire_line_scanEOCstartedEOP'}]
        mes_emulator = MesEmulator(response_pattern, self.client_to_mes, self.mes_to_client)
        mes_emulator.start()
        result = self.mes_interface.start_line_scan(1.0)
        self.assertEqual((result[0], mes_emulator.acquire_line_scan_received), (False, True))
        
    def test_05_line_scan_and_data_save_completed(self):
        response_pattern = [{'delay':0.1, 'response':'SOCacquire_line_scanEOCstartedEOP'}, 
                            {'delay':0.1, 'response':'SOCacquire_line_scanEOCOKEOP'}, 
                            {'delay':0.1, 'response':'SOCacquire_line_scanEOCsaveOKEOP'}
                            ]
        mes_emulator = MesEmulator(response_pattern, self.client_to_mes, self.mes_to_client)
        mes_emulator.start()
        result_line_scan_started = self.mes_interface.start_line_scan(1.0)
        result_scan_ok = self.mes_interface.wait_for_line_scan_complete(1.0)
        result_save_ok = self.mes_interface.wait_for_line_scan_save_complete(1.0)
        self.assertEqual((result_line_scan_started[0], result_scan_ok, result_save_ok, mes_emulator.acquire_line_scan_received), 
                         (True, True, True, True))
                         
    def test_06_line_scan_save_ok_delayed(self):
        '''
        saveOK arrives later than timeout
        '''
        response_pattern = [{'delay':0.1, 'response':'SOCacquire_line_scanEOCstartedEOP'}, 
                            {'delay':0.1, 'response':'SOCacquire_line_scanEOCOKEOP'}, 
                            {'delay':3.1, 'response':'SOCacquire_line_scanEOCsaveOKEOP'}
                            ]
        mes_emulator = MesEmulator(response_pattern, self.client_to_mes, self.mes_to_client)
        mes_emulator.start()
        result_line_scan_started = self.mes_interface.start_line_scan(0.5)
        result_scan_ok = self.mes_interface.wait_for_line_scan_complete(0.5)
        result_save_ok = self.mes_interface.wait_for_line_scan_save_complete(0.5)
        time.sleep(3.0)
        mes_responses = utils.empty_queue(self.client_to_user)
        self.assertEqual((result_line_scan_started[0], result_scan_ok, result_save_ok, mes_emulator.acquire_line_scan_received, 
                          'SOCacquire_line_scanEOCsaveOKEOP' in mes_responses), 
                         (True, True, False, True, True))

class TestMesInterface(unittest.TestCase):
    
    def tearDown(self):
        pass
        
    def setUp(self):
        pass
        
    def test_all_functions(self):
        '''
        1. line scan with mes settings
        2. line scan with user scan time
        '''
        pass
    
        

        
            
        
        
    
if __name__ == "__main__":
    unittest.main()
#    mat_file = '/media/sf_M_DRIVE/Zoltan/visexpman/data/0_X-820381_Y-252527_Z+57516/acquire_z_stack_parameters_MovingDot_1321687013_0.mat'
#    print get_objective_position(mat_file)    
#    mat_file = '/media/sf_M_DRIVE/Zoltan/visexpman/data/test.mat'    
#    print get_objective_position(mat_file)
