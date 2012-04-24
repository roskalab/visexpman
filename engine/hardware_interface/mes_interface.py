import network_interface
import unittest
import time
import socket
import Queue
import sys
import scipy.io
import numpy
import os.path
import re
import os
import os.path
import shutil

import PyQt4.QtCore as QtCore

import visexpman.engine.generic.configuration
from visexpA.engine.datahandlers import matlabfile
from visexpman.engine.generic import utils
from visexpman.engine.generic import file

from visexpman.users.zoltan.test import unit_test_runner
parameter_extract = re.compile('EOC(.+)EOP')


def generate_scan_points_mat(points, mat_file):
    '''
    Points shall be a struct array of numpy.float64 with x, y and z fields.
    numpy.zeros((3,100), {'names': ('x', 'y', 'z'), 'formats': (numpy.float64, numpy.float64, numpy.float64)})
    '''
#    if points.dtype != [('row', '<f8'), ('col', '<f8'), ('depth', '<f8')]:
#        raise RuntimeError('Data format is incorrect {0}'.format(points.dtype))
#TOD: check here that the data has rcd format and f8 datattype
    data_to_mes_mat = {}
    data_to_mes_mat['DATA'] = points
    scipy.io.savemat(mat_file, data_to_mes_mat, oned_as = 'column')       

def get_objective_position(mat_file, log = None):
    '''
    Reads relative Z position
    '''
    m = matlabfile.MatData(mat_file, log = log)
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
    
def read_objective_info(mat_file,  log=None):
    '''
    Returns absolute, relative objective position and z origin
    '''
    m = matlabfile.MatData(mat_file, log = log)
    data = m.get_field('DATA')
    data = {}
    data['rel'] = m.get_field('DATA.Zlevel') [0][0][0][0][0]
    data['abs'] = m.get_field('DATA.ZlevelArm') [0][0][0][0][0]
    data['origin'] = m.get_field('DATA.ZlevelOrigin')[0][0][0][0][0]
    return data

def set_mes_mesaurement_save_flag(mat_file, flag):
    m = matlabfile.MatData(reference_path, target_path)
    m.rawmat['DATA'][0]['DELETEE'] = int(flag) #Not tested, this addressing might be wrong
    m.flush()   

def set_line_scan_time(scan_time, reference_path, target_path, scan_mode = 'xy'):
    '''
    scan_time: in ms
    reference_path: reference mat file that will be used as a template
    target_path: 
    '''
    #TODO rename to set scan parameter file
    m = matlabfile.MatData(reference_path, target_path)
    ts = m.get_field(m.name2path('ts'))[0][0][0][0]
    ts = numpy.array([ts[0],ts[1],ts[2],numpy.round(float(1000*scan_time), 0)], dtype = numpy.float64)
    m.set_field(m.name2path('ts'), ts, allow_dtype_change=True)
    if scan_mode == 'xz':
        m.raw_mat['DATA'][0]['breakFFregion'] = 2.0
    elif scan_mode == 'xyz':
        m.raw_mat['DATA'][0]['info_Linfo'] = 0
    m.flush()

def get_line_scan_time(path):
    m = matlabfile.MatData(path)
    return m.get_field(m.name2path('ts'))[0][0][0][0][-1]


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
    #TODO: eliminate keyboard watching, waiting for timeouts can be terminated from network 
    def __init__(self, config, queues = None, connections = None, log = None):
        self.config = config
        self.queues = queues
        self.connection = connections['mes']
        self.log = log
        self.stop = False
        if self.queues.has_key('gui'):
            self.from_gui_queue = self.queues['gui']['in']
        else:
            self.from_gui_queue = None
        
    ################# Objective ###############
    def read_objective_position(self, timeout = -1):
        result, line_scan_path, line_scan_path_on_mes = self.get_line_scan_parameters(timeout = timeout)
        if result:
            objective_position = get_objective_position(line_scan_path)[0]
            os.remove(line_scan_path)
            return True, objective_position
        else:
            if os.path.exists(line_scan_path):
                os.remove(line_scan_path)
            return False,  None

    def set_objective(self, position, timeout = None):
        if timeout == None:
            timeout = self.config.MES_TIMEOUT
        parameter_path, parameter_path_on_mes = self._generate_mes_file_paths('set_objective.mat')
        #Generate parameter file
        data_to_mes_mat = {}
        data_to_mes_mat['DATA'] = {}
        data_to_mes_mat['DATA']['z_relative'] = numpy.array([position], dtype = numpy.float64)[0]
        scipy.io.savemat(parameter_path, data_to_mes_mat, oned_as = 'column') 
        result = False
        if self.connection.connected_to_remote_client():
            self.queues['mes']['out'].put('SOCsetZ_relativeEOC{0}EOP' .format(parameter_path_on_mes))
            if network_interface.wait_for_response( self.queues['mes']['in'], ['SOCsetZ_relativeEOCcommandsentEOP'], timeout = timeout):
                result = True
        if os.path.exists(parameter_path):#TODO: check why this is not working
            os.remove(parameter_path)
        return result
        
    def overwrite_relative_position(self, position_value, timeout = None):
        '''
        The value of the relative objective position is changed without moving the objective. The origin value is changed
        '''
        if timeout == None:
            timeout = self.config.MES_TIMEOUT
            
        #Get current objective info
        result, line_scan_path, line_scan_path_on_mes = self.get_line_scan_parameters(timeout = timeout)
        if not result:
            return False
        objective_info = read_objective_info(line_scan_path)
        new_origin = objective_info['origin'] + objective_info['rel'] - position_value
        parameter_path, parameter_path_on_mes = self._generate_mes_file_paths('set_objective_origin.mat')
        #Generate parameter file
        data_to_mes_mat = {}
        data_to_mes_mat['DATA'] = {}
        data_to_mes_mat['DATA']['origin'] = numpy.array([new_origin], dtype = numpy.float64)[0]
        scipy.io.savemat(parameter_path, data_to_mes_mat, oned_as = 'column') 
        result = False
        if self.connection.connected_to_remote_client():
            self.queues['mes']['out'].put('SOCset_objective_originEOC{0}EOP' .format(parameter_path_on_mes))
            if network_interface.wait_for_response( self.queues['mes']['in'], ['SOCset_objective_originEOCcommandsentEOP'], timeout = timeout):
                result = True
        if os.path.exists(parameter_path):
            os.remove(parameter_path)
        return result
        
        ################# Laser intensity ###############
    def set_laser_intensity(self, laser_intensity, timeout = None):
        if timeout == None:
            timeout = self.config.MES_TIMEOUT
        parameter_path, parameter_path_on_mes = self._generate_mes_file_paths('set_objective.mat')
        #Generate parameter file
        data_to_mes_mat = {}
        data_to_mes_mat['DATA'] = {}
        data_to_mes_mat['DATA']['laser_intensity'] = numpy.array([laser_intensity], dtype = numpy.float64)[0]
        scipy.io.savemat(parameter_path, data_to_mes_mat, oned_as = 'column') 
        result = False
        if self.connection.connected_to_remote_client():
            self.queues['mes']['out'].put('SOCset_laser_intensityEOC{0}EOP' .format(parameter_path_on_mes))
            if network_interface.wait_for_response( self.queues['mes']['in'], ['SOCset_laser_intensityEOCcommandsentEOP'], timeout = timeout):
                result = True
        if os.path.exists(parameter_path):
            os.remove(parameter_path)
        #Wait till laser reaches required intensity
        start_time = time.time()
        while True:
            result, adjusted_laser_intensity = self.read_laser_intensity(timeout = timeout)
            if time.time() - start_time > timeout:
                break
                result = False
            if result and abs(laser_intensity - adjusted_laser_intensity) < 0.1:
                result = True
                break
            time.sleep(1.0)
        return result, adjusted_laser_intensity
        
    def read_laser_intensity(self, timeout = None):
        result = False
        laser_intensity = 0
        if timeout == None:
            timeout = self.config.MES_TIMEOUT
        if self.connection.connected_to_remote_client():
            self.queues['mes']['out'].put('SOCread_laser_intensityEOCEOP')
            if utils.wait_data_appear_in_queue(self.queues['mes']['in'], timeout):
                while not self.queues['mes']['in'].empty():
                    response = self.queues['mes']['in'].get()
                    if 'read_laser_intensity' in response:
                        result = True
                        laser_intensity = parameter_extract.findall(response)
                        if len(laser_intensity) > 0:
                            laser_intensity = float(laser_intensity[0])
                        else:
                            result = False
        return result, laser_intensity

    ################# Single two photon frame###############
    def acquire_two_photon_image(self, timeout = -1, parameter_file = None):
        if parameter_file == None:
            #generate a mes parameter file name, that does not exits
            two_photon_image_path, two_photon_image_path_on_mes = self._generate_mes_file_paths('two_photon_image.mat')
        else:
            two_photon_image_path = parameter_file
            two_photon_image_path_on_mes = file.convert_path_to_remote_machine_path(two_photon_image_path, self.config.MES_DATA_FOLDER,  remote_win_path = (self.config.OS != 'win'))
        utils.empty_queue(self.queues['mes']['in'])
        result = False
        image = numpy.zeros((2, 2))
        if self.connection.connected_to_remote_client():
            self.queues['mes']['out'].put('SOCacquire_xy_imageEOC{0}EOP' .format(two_photon_image_path_on_mes))
            if network_interface.wait_for_response(self.queues['mes']['in'], ['SOCacquire_xy_imageEOCstartedEOP'], timeout = timeout):
                if network_interface.wait_for_response(self.queues['mes']['in'], ['SOCacquire_xy_imageEOCOKEOP'], timeout = timeout):
                    if network_interface.wait_for_response(self.queues['mes']['in'], ['SOCacquire_xy_imageEOCsaveOKEOP'], timeout = timeout):
                        if os.path.exists(two_photon_image_path):
                            time.sleep(0.2)
                            try:
                                image = matlabfile.read_two_photon_image(two_photon_image_path)
                                result = True
                            except AssertionError:
                                #Wait till file is available
                                time.sleep(1.0)
                                image = matlabfile.read_two_photon_image(two_photon_image_path)
                                result = True
#        import Image
#        im = numpy.cast['uint8'](image['pmtUGraw']/2)
#        im  = Image.fromarray(im)
#        im.save('v:\\debug\\data\\2p.png')
        return image, result

    ################# Z stack #########################
    def acquire_z_stack(self, timeout = -1, channel = 'pmtUGraw', test_mat_file = None):
        z_stack_path, z_stack_path_on_mes = self._generate_mes_file_paths('z_stack.mat')
        utils.empty_queue(self.queues['mes']['in'])
        results = []
        #Acquire z stack
        if self.connection.connected_to_remote_client():
            self.queues['mes']['out'].put('SOCacquire_z_stackEOC{0}EOP' .format(z_stack_path_on_mes))
            results.append(network_interface.wait_for_response(self.queues['mes']['in'], 'SOCacquire_z_stackEOCstartedEOP', timeout = timeout))
            if results[-1]:
                results.append(network_interface.wait_for_response(self.queues['mes']['in'], ['SOCacquire_z_stackEOCOKEOP'], timeout = 3*timeout))
            else:
                #Remove command from command queue
                if not self.queues['mes']['out'].empty():
                    self.queues['mes']['out'].get()
                return {}, results
            #Extract z stack from mat file
            if test_mat_file != None:
                z_stack_path = test_mat_file
            z_stack = {}
            if isinstance(z_stack_path, str):
                if os.path.exists(z_stack_path):            
                    z_stack = matlabfile.read_z_stack(z_stack_path, channel = channel)                    
            return z_stack, results
        else:
            return {}, results

    def start_z_stack(self, timeout = -1):
        z_stack_path, z_stack_path_on_mes = self._generate_mes_file_paths('z_stack.mat')
        utils.empty_queue(self.queues['mes']['in'])
        results = []
        #Acquire z stack
        if not self.connection.connected_to_remote_client():
            return z_stack_path, False
        self.queues['mes']['out'].put('SOCacquire_z_stackEOC{0}EOP' .format(z_stack_path_on_mes))
        result = network_interface.wait_for_response(self.queues['mes']['in'], 'SOCacquire_z_stackEOCstartedEOP', timeout = timeout)
        return z_stack_path, result
        
    #######################  RC scan #######################
    def create_XZline_from_points(self, cell_centers, z_range,  line_length):
        timeout = self.config.MES_TIMEOUT
        parameter_path, parameter_path_on_mes = self._generate_mes_file_paths('create_xz_line_params.mat')
        #Generate parameter file
        data_to_mes_mat = {}
        data_to_mes_mat['DATA'] = {}
        data_to_mes_mat['DATA']['points'] = cell_centers
        data_to_mes_mat['DATA']['params'] = {}
        data_to_mes_mat['DATA']['params']['LineLength'] = line_length
        data_to_mes_mat['DATA']['params']['zshift'] = 1.0
        data_to_mes_mat['DATA']['params']['Tpixnum'] = z_range/0.5
        data_to_mes_mat['DATA']['params']['Tpixwidth'] = 0.5
        scipy.io.savemat(parameter_path, data_to_mes_mat, oned_as = 'column') 
        self.queues['mes']['out'].put('SOCcreate_XZline_from_pointsEOC{0}EOP'.format(parameter_path_on_mes))
        result = network_interface.wait_for_response(self.queues['mes']['in'], 'SOCcreate_XZline_from_pointsEOCline_setEOP', timeout = timeout)
        return result
    
    def rc_scan(self, cell_centers):
        '''
        Performs roller coaster scanning.cell_centers tell the centers of the cells to be scanned. The trajectory of 
        scanning each cell will be a helix.
        '''
        timeout = self.config.MES_TIMEOUT
        result = False
        scanned_trajectory = {}
        #Send trajectory points to mes
        set_trajectory_success = self.set_points(cell_centers, timeout = timeout)
        print 'set_trajectory_success',  set_trajectory_success
        prepare_rc_scan_success = self.prepare_rc_scan(timeout = timeout)
        print 'prepare_rc_scan_success',  prepare_rc_scan_success
        rc_scan_path, rc_scan_path_on_mes = self._generate_mes_file_paths('rc_scan.mat')
        utils.empty_queue(self.queues['mes']['in'])
        if self.rc_runnability_test(cell_centers,  timeout = timeout) and self.connection.connected_to_remote_client():
            self.points_to_rc_line(timeout = timeout)
            self.queues['mes']['out'].put('SOCrc_scanEOC{0}EOP' .format(rc_scan_path_on_mes))
            rc_scan_started_success = network_interface.wait_for_response(self.queues['mes']['in'], 'SOCrc_scanEOCstartedEOP', timeout = timeout)
            if rc_scan_started_success:
                rc_scan_ready_success = network_interface.wait_for_response(self.queues['mes']['in'], 'SOCrc_scanEOCOKEOP', timeout = timeout)
                if rc_scan_ready_success:
                    rc_scan_save_success = network_interface.wait_for_response(self.queues['mes']['in'], 'SOCrc_scanEOCsaveOKEOP', timeout = timeout)#            
                    result = True
                    if os.path.exists(rc_scan_path):
                        scanned_trajectory = matlabfile.read_rc_scan(rc_scan_path)
        return scanned_trajectory, result
        
    def start_rc_scan(self, cell_centers, parameter_file = '', scan_time = None):
        timeout = self.config.MES_TIMEOUT
        if not self.set_points(cell_centers, timeout = timeout):
            self._log_info('Set points did not succeed')
            return False, ''
        if not self.prepare_rc_scan(timeout = timeout):
            self._log_info('Prepare rc scan did not succeed')
            return False, ''
        if not self.rc_runnability_test(cell_centers,  timeout = timeout):#TODO: check apptime and todelete parameters and omit unscannable points
            self._log_info('Runnability test did not succeed')
            return False, ''
        if parameter_file == '':
            rc_scan_path = file.generate_filename(os.path.join(self.config.MES_DATA_FOLDER, 'line_scan.mat'))
            rc_scan_path_on_mes =  file.convert_path_to_remote_machine_path(line_scan_path, self.config.MES_DATA_FOLDER,  remote_win_path = True)
            result = True
        elif os.path.exists(parameter_file):
            rc_scan_path = parameter_file
            rc_scan_path_on_mes = file.convert_path_to_remote_machine_path(line_scan_path, self.config.MES_DATA_FOLDER,  remote_win_path = True)
            result = True
        else:
            result, rc_scan_path, rc_scan_path_on_mes =  self.get_line_scan_parameters(parameter_file = parameter_file, timeout = timeout)
        if scan_time != None and result:
            set_line_scan_time(scan_time, rc_scan_path, rc_scan_path, scan_mode = 'xyz')
        else:
            self._log_info('Get parameter file did not succeed')
            return False, rc_scan_path
        if not self.points_to_rc_line(timeout = timeout):
            self._log_info('Points to RC line did not succeed')
            return False, rc_scan_path
        if not self.connection.connected_to_remote_client():
            self._log_info('MES not connected')
            return False, rc_scan_path
        self.queues['mes']['out'].put('SOCrc_scanEOC{0}EOP' .format(rc_scan_path_on_mes))
        if not network_interface.wait_for_response(self.queues['mes']['in'], 'SOCrc_scanEOCstartedEOP', timeout = timeout):
            self._log_info('RC scan start error')
            return False, rc_scan_path
        return True, rc_scan_path
        
    def wait_for_rc_scan_complete(self, timeout = -1):
        if timeout == -1:
            timeout = self.config.MES_TIMEOUT
        return self._wait_for_mes_response(timeout, ['SOCrc_scanEOCOKEOP'])

    def wait_for_rc_scan_save_complete(self, timeout = -1):
        if timeout == -1:
            timeout = self.config.MES_TIMEOUT
        return self._wait_for_mes_response(timeout, 'SOCrc_scanEOCsaveOKEOP')

    def set_points(self, points, timeout = -1):
        points_mat, points_mat_on_mes = self._generate_mes_file_paths('rc_points.mat')
        generate_scan_points_mat(points, points_mat)
        utils.empty_queue(self.queues['mes']['in'])
        self.queues['mes']['out'].put('SOCset_pointsEOC{0}EOP' .format(points_mat_on_mes))
        return network_interface.wait_for_response(self.queues['mes']['in'], 'SOCset_pointsEOCpoints_setEOP', timeout = timeout)

    def rc_runnability_test(self, points, timeout = -1):
        points_mat, points_mat_on_mes = self._generate_mes_file_paths('rc_points.mat')
        generate_scan_points_mat(points, points_mat)
        utils.empty_queue(self.queues['mes']['in'])
        self.queues['mes']['out'].put('SOCrunnability_testEOC{0}EOP' .format(points_mat_on_mes))
        return network_interface.wait_for_response(self.queues['mes']['in'], 'SOCrunnability_testEOCdoneEOP', timeout = timeout)

    def points_to_rc_line(self, timeout = -1):
        time.sleep(0.1)
        self.queues['mes']['out'].put('SOCpoints2RClineEOCEOP')
        result = network_interface.wait_for_response(self.queues['mes']['in'], 'SOCpoints2RClineEOCdoneEOP', timeout = timeout)
        time.sleep(0.1)
        return result

    def prepare_rc_scan(self, timeout = -1):
        self.queues['mes']['out'].put('SOCprepareRCscanEOCEOP')
        return network_interface.wait_for_response(self.queues['mes']['in'], 'SOCprepareRCscanEOCdoneEOP', timeout = timeout)


    def get_rc_range(self, timeout = -1):
        '''
        MES returns the range as follows: xmin, xmax, ymin, ymax, z range

        Not tested yet

        '''
        self.queues['mes']['out'].put('SOCget_rangeEOCEOP')
        result = network_interface.wait_for_response(self.queues['mes']['in'], 'SOCget_rangeEOC', timeout = timeout)[0]
        ranges =  re.findall('EOC(.+)EOP',result).split(',')
        mes_scan_range = {}
        if len(ranges) == 5:
            mes_scan_range['col'] = map(float, result[:2])
            mes_scan_range['row'] = map(float, result[2:4])
            mes_scan_range['depth'] = map(float, result[4])
        return mes_scan_range

    #######################  Line scan #######################
    def vertical_line_scan(self, parameter_file = '', scan_time = None): #TODO: generalize to line scan
        result, line_scan_path = self.start_line_scan(timeout = self.config.MES_TIMEOUT, parameter_file = parameter_file, scan_time = scan_time)
        if not result:
            return {}, False
        if scan_time != None:
            timeout = 1.5 * scan_time
        else:
            timeout = 2 * self.config.MES_TIMEOUT
        result = self.wait_for_line_scan_complete(timeout = timeout)
        if not result:
            return {}, False
        result = self.wait_for_line_scan_save_complete(timeout = timeout)
        if not result:
            return {}, False
        vertical_scan = matlabfile.read_vertical_scan(line_scan_path)
        return vertical_scan, True
        
    def get_line_scan_parameters(self, timeout = -1, parameter_file = None):
        if parameter_file == None:
            #generate a mes parameter file name, that does not exits
            line_scan_path, line_scan_path_on_mes = self._generate_mes_file_paths('line_scan_parameters.mat')
        else:
            line_scan_path = parameter_file
            line_scan_path_on_mes = file.convert_path_to_remote_machine_path(line_scan_path, self.config.MES_DATA_FOLDER,  remote_win_path = (self.config.OS != 'win'))
        utils.empty_queue(self.queues['mes']['in'])
        #Acquire line scan if MES is connected
        if self.connection.connected_to_remote_client():
            self.queues['mes']['out'].put('SOCacquire_line_scan_templateEOC{0}EOP' .format(line_scan_path_on_mes))
            result = network_interface.wait_for_response(self.queues['mes']['in'], 'SOCacquire_line_scan_templateEOCsaveOKEOP', timeout = timeout, 
                                                         from_gui_queue = self.from_gui_queue)
            if not result:
                self._log_info('acquiring line scan template was not successful')
        else:
            self._log_info('mes not connected')
            result = False
        time.sleep(1.5)#This delay is nccessary to ensure that the parameter file is completely written to the disk
        return result, line_scan_path, line_scan_path_on_mes
        
    def start_line_scan(self, timeout = -1, parameter_file = '', scan_time = None, scan_mode = 'xy'):
        '''
        parameter_file:
        valid, but nonexistent: generate lines scan parameter file
        existing: just use it as a parameter file
        not provided: use default mes settings, generate filename
        '''
        if parameter_file == '':
            line_scan_path = file.generate_filename(os.path.join(self.config.MES_DATA_FOLDER, 'line_scan.mat'))
            line_scan_path_on_mes =  file.convert_path_to_remote_machine_path(line_scan_path, self.config.MES_DATA_FOLDER,  remote_win_path = True)
            result = True
        elif os.path.exists(parameter_file):
            line_scan_path = parameter_file
            line_scan_path_on_mes = file.convert_path_to_remote_machine_path(line_scan_path, self.config.MES_DATA_FOLDER,  remote_win_path = True)
            result = True
        else:
            result, line_scan_path, line_scan_path_on_mes =  self.get_line_scan_parameters(parameter_file = parameter_file, timeout = timeout)

        if scan_time != None and result:
            set_line_scan_time(scan_time, line_scan_path, line_scan_path, scan_mode = scan_mode)
        if result:
            #previously sent garbage is removed from queue
            utils.empty_queue(self.queues['mes']['in'])        
            #Acquire line scan if MES is connected            
            if self.connection.connected_to_remote_client():
                self.queues['mes']['out'].put('SOCacquire_line_scanEOC{0}EOP' .format(line_scan_path_on_mes))
                result = network_interface.wait_for_response(self.queues['mes']['in'], 'SOCacquire_line_scanEOCstartedEOP', timeout = timeout, 
                                                             from_gui_queue = self.from_gui_queue)
                if result:
                    self._log_info('line scan started')
                else:
                    self._log_info('line scan not started')
            else:
                self._log_info('mes not connected')
                result = False
        return result, line_scan_path

    def wait_for_line_scan_complete(self, timeout = -1):
        if timeout == -1:
            timeout = self.config.MES_TIMEOUT
        return self._wait_for_mes_response(timeout, ['SOCacquire_line_scanEOCOKEOP'])

    def wait_for_line_scan_save_complete(self, timeout = -1):
        if timeout == -1:
            timeout = self.config.MES_TIMEOUT
        return self._wait_for_mes_response(timeout, 'SOCacquire_line_scanEOCsaveOKEOP')

####################### Private functions ########################
    def _wait_for_mes_response(self, timeout, expected_responses):
        '''
        Waits till MES sends notification about the completition of a certain command.
        Waiting is aborted by the following events:
            -timeout
            -stop keyboard command, if keyboard_handler is present
        '''
        result = network_interface.wait_for_response(self.queues['mes']['in'], 
                                                     expected_responses, 
                                                     timeout = timeout, 
                                                     from_gui_queue = self.from_gui_queue)
        if result:
            self._log_info('MES responded with ' + str(expected_responses))
        else:
            self._log_info('No MES response')
        return result

    def _log_info(self, message):
        if self.log != None:
            self.log.info(message)

    def _generate_mes_file_paths(self, filename):
        path = file.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, filename))
        path_on_mes = file.convert_path_to_remote_machine_path(path, self.config.MES_DATA_FOLDER,  remote_win_path = True)
        return path, path_on_mes

############# Unit tests ##########################
class MesEmulator(QtCore.QThread):    
    def __init__(self, response_pattern, queue_in, queue_out, start_message = 'acquire_line_scan_template'):        
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
        self.start_message = start_message

    def run(self):        
        while True:            
            if not self.queue_in.empty():
                message = self.queue_in.get()
                command = re.findall('SOC(.+)EOC', message)
                parameter = re.findall('EOC(.+)EOP', message)                
                if self.start_message in message:
                    self.acquire_line_scan_received = True
                    for response in self.response_pattern:
                        time.sleep(response['delay'])
                        self.queue_out.put(response['response'])
                elif 'echo' in command:
                    self.queue_out.put(message)
            time.sleep(0.05)



class MESTestConfig(visexpman.engine.generic.configuration.Config):
    def __init__(self, baseport = None, mes_data_to_new_folder = False):
        self.baseport = baseport
        self.mes_data_to_new_folder = mes_data_to_new_folder
        visexpman.engine.generic.configuration.Config.__init__(self)

    def _create_application_parameters(self):
        if self.baseport == None:
            import random
            self.BASE_PORT = 10000 + 1* int(10000*random.random())
        else:
            self.BASE_PORT = self.baseport
        COMMAND_RELAY_SERVER  = {
        'RELAY_SERVER_IP' : 'localhost', 
        'ENABLE' : True, 
        'CLIENTS_ENABLE' : True, 
        'TIMEOUT':10.0, 
        'CONNECTION_MATRIX':
            {
            'USER_MES'  : {'USER' : {'IP': 'localhost', 'PORT': self.BASE_PORT}, 'MES' : {'IP': 'localhost', 'PORT': self.BASE_PORT + 1}},            
            }
        }
        if self.mes_data_to_new_folder:
            EXPERIMENT_DATA_PATH = file.generate_foldername(os.path.join(unit_test_runner.TEST_working_folder, 'mes_test'))
            if not os.path.exists(EXPERIMENT_DATA_PATH):
                os.mkdir(EXPERIMENT_DATA_PATH)
        else:
            EXPERIMENT_DATA_PATH = unit_test_runner.TEST_working_folder

        MES_DATA_FOLDER = EXPERIMENT_DATA_PATH.replace('/home/zoltan/visexp', 'V:').replace('/', '\\')
        self.MES_TIMEOUT = 10.0
        LOG_PATH = unit_test_runner.TEST_working_folder
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
        self.parameter_path = os.path.join(unit_test_runner.TEST_working_folder, 'test.mat')
        self.config = MESTestConfig()       
        self.user_to_client = Queue.Queue()
        self.client_to_user = Queue.Queue()
        queues = {}
        queues['mes'] = {}
        queues['mes']['out'] = self.user_to_client
        queues['mes']['in'] = self.client_to_user
        queues['gui'] = {}
        queues['gui']['in'] = Queue.Queue()
        queues['gui']['out'] = Queue.Queue()
        self.user_client = network_interface.start_client(self.config, 'USER', 'USER_MES', self.client_to_user, self.user_to_client)
        self.mes_interface = MesInterface(self.config, queues = queues, connections = {'mes' : self.user_client})
        if not '_01_' in self._testMethodName:
            self.server = network_interface.CommandRelayServer(self.config)
            self.mes_to_client = Queue.Queue()
            self.client_to_mes = Queue.Queue()
            self.mes_client = network_interface.start_client(self.config, 'MES', 'USER_MES', self.client_to_mes, self.mes_to_client)

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
        result = self.mes_interface.start_line_scan(scan_time = 1.0, parameter_file = self.parameter_path, timeout = 2.0)
        self.assertEqual((result[0], mes_emulator.acquire_line_scan_received), (False, True))

    def test_03_line_scan_started(self):
        '''
        Line scan started without error
        '''
        response_pattern = [{'delay':0.1, 'response':'SOCacquire_line_scanEOCstartedEOP'}]
        mes_emulator = MesEmulator(response_pattern, self.client_to_mes, self.mes_to_client, 'acquire_line_scan')
        mes_emulator.start()
        result = self.mes_interface.start_line_scan(timeout = 2.0)
        self.assertEqual((result[0], mes_emulator.acquire_line_scan_received), (True, True))

    def test_04_line_scan_started_timeout(self):
        '''
        Line scan started but later than the timeout given in start_line_scan
        '''
        response_pattern = [{'delay':2.1, 'response':'SOCacquire_line_scanEOCstartedEOP'}]
        mes_emulator = MesEmulator(response_pattern, self.client_to_mes, self.mes_to_client, 'acquire_line_scan')
        mes_emulator.start()
        result = self.mes_interface.start_line_scan(timeout = 1.0)
        self.assertEqual((result[0], mes_emulator.acquire_line_scan_received), (False, True))

    def test_05_line_scan_and_data_save_completed(self):
        response_pattern = [{'delay':0.1, 'response':'SOCacquire_line_scanEOCstartedEOP'}, 
                            {'delay':0.1, 'response':'SOCacquire_line_scanEOCOKEOP'}, 
                            {'delay':0.1, 'response':'SOCacquire_line_scanEOCsaveOKEOP'}
                            ]
        mes_emulator = MesEmulator(response_pattern, self.client_to_mes, self.mes_to_client, 'acquire_line_scan')
        mes_emulator.start()
        result_line_scan_started = self.mes_interface.start_line_scan(timeout = 1.0)
        result_scan_ok = self.mes_interface.wait_for_line_scan_complete(1.0)
        result_save_ok = self.mes_interface.wait_for_line_scan_save_complete(1.0)
        self.assertEqual((result_line_scan_started[0], result_scan_ok, result_save_ok, mes_emulator.acquire_line_scan_received), 
                         (True, True, True, True))

    def test_06_line_scan_save_ok_delayed(self):
        '''
        saveOK arrives later than timeout
        '''
        response_pattern = [{'delay':0.1, 'response':'SOCechoEOCdumyEOP'},
                            {'delay':0.1, 'response':'SOCacquire_line_scanEOCstartedEOP'}, 
                            {'delay':0.1, 'response':'SOCacquire_line_scanEOCOKEOP'}, 
                            {'delay':3.1, 'response':'SOCacquire_line_scanEOCsaveOKEOP'}
                            ]
        mes_emulator = MesEmulator(response_pattern, self.client_to_mes, self.mes_to_client, 'acquire_line_scan')
        mes_emulator.start()
        result_line_scan_started = self.mes_interface.start_line_scan(timeout = 1.0)
        result_scan_ok = self.mes_interface.wait_for_line_scan_complete(0.5)
        result_save_ok = self.mes_interface.wait_for_line_scan_save_complete(0.5)
        time.sleep(4.0)
        mes_responses = utils.empty_queue(self.client_to_user)
        self.assertEqual((result_line_scan_started[0], result_scan_ok, result_save_ok, mes_emulator.acquire_line_scan_received, 
                          'SOCacquire_line_scanEOCsaveOKEOP' in mes_responses), 
                         (True, True, False, True, True))                        

class TestMesInterface(unittest.TestCase):

    def tearDown(self):
        self.user_to_client.put('SOCclose_connectionEOCstop_clientEOP')
        if hasattr(self, 'server'):
            self.server.shutdown_servers()
        time.sleep(0.5)

    def setUp(self):
        self.config = MESTestConfig(mes_data_to_new_folder = not True, baseport = 10000)
        self.user_to_client = Queue.Queue()
        self.client_to_user = Queue.Queue()
        queues = {}
        queues['mes'] = {}
        queues['mes']['out'] = self.user_to_client
        queues['mes']['in'] = self.client_to_user
        queues['gui'] = {}
        queues['gui']['in'] = Queue.Queue()
        queues['gui']['out'] = Queue.Queue()
        self.user_client = network_interface.start_client(self.config, 'USER', 'USER_MES', self.client_to_user, self.user_to_client)
        self.mes_interface = MesInterface(self.config, queues = queues, connections = {'mes' : self.user_client})
        self.server = network_interface.CommandRelayServer(self.config)


    def test_all_functions(self):
        '''
        1. line scan with mes settings
        2. line scan with user scan time
        '''

        scan_time_reference1 = 4.0
        scan_time_reference2 = 5.0
        raw_input('1. In MES software, server address shall be set to this machine\'s ip\n\
                2. Connect MES to gui\n\
                3. Press ENTER')

        line_scan_complete_success = False
        line_scan_data_save_success = False
        user_line_scan_file = file.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'user_line_scan.mat'))
        line_scan_start_success, line_scan_path = self.mes_interface.start_line_scan(parameter_file = user_line_scan_file, scan_time = scan_time_reference1, timeout = 2 * scan_time_reference1)
        if line_scan_start_success:
            line_scan_complete_success =  self.mes_interface.wait_for_line_scan_complete(2 * scan_time_reference1)
            if line_scan_complete_success:
                line_scan_data_save_success = self.mes_interface.wait_for_line_scan_save_complete(scan_time_reference1)
        self.assertEqual((line_scan_start_success, line_scan_complete_success, line_scan_data_save_success, get_line_scan_time(user_line_scan_file)) , (True, True, True, 1000 * scan_time_reference1))

    def _check_line_scan_result(self, expected_scan_time, line_scan_start_success = None, line_scan_path = None, user_line_scan_file = None, line_scan_complete_success = None, 
                                    line_scan_data_save_success = None):
        result = False
        if line_scan_start_success == None or line_scan_path == None or user_line_scan_file == None or line_scan_complete_success == None or line_scan_data_save_success == None:
            return result
        elif line_scan_start_success and line_scan_complete_success and line_scan_data_save_success:
            if 1000 * expected_scan_time == get_line_scan_time(user_line_scan_file) and 1000 * expected_scan_time == get_line_scan_time(line_scan_path):
                result = True
        return result

if __name__ == "__main__":
#    unittest.main()
    #TODO: put it to separate test: read_objective_info('/home/zoltan/visexp/data/test/line_scan_parameters_00000.mat')
    
    #TEST 0X
#    import shutil
#    path = file.generate_filename('/home/zoltan/visexp/unit_test_output/scanparams.mat')
#    shutil.copy('/home/zoltan/visexp/data/test/scanparams.mat', path)
#    set_line_scan_time(10.0, path,  path, scan_mode = 'xyz')
  #TEST )X+1
  from visexpA.engine.datahandlers import hdf5io
  points = hdf5io.read_item(os.path.join('/home/zoltan/visexp/context',  'cell_positions.hdf5'), 'cell_positions_fine')
  generate_scan_points_mat(points, '/home/zoltan/visexp/debug/data/crpoints.mat')
