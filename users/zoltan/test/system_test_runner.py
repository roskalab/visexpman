import shutil
import threading
import Queue
import sys
import os.path
import subprocess
import time
import scipy.io

import visexpman
import visexpA
from visexpman.engine import visexp_gui
import hdf5io
from visexpman.engine.generic import utils
from visexpman.engine.generic import fileop
from visexpman.engine.hardware_interface import network_interface
from visexpman.engine.generic import command_parser
if 0:
    from visexpA.engine.datahandlers import matlabfile
    from visexpA.engine import jobhandler

class VisexpAppRunner(threading.Thread):
    def __init__(self, uiname):
        if uiname == 'visexp_runner':
            self.command = 'python {0} {1} {2}'.format(os.path.join(os.path.split(visexpman.__file__)[0], 'engine', 'visexp_runner.py'), sys.argv[1], sys.argv[2])
        elif uiname == 'jobhandler':
            self.command = 'python {0} {1} {2}'.format(os.path.join(os.path.split(visexpA.__file__)[0], 'engine', 'jobhandler.py'), sys.argv[1], sys.argv[2])
        threading.Thread.__init__(self)
        
    def run(self):
        if hasattr(self, 'command'):
            subprocess.call(self.command, shell = True)
    
class MESSimulator(threading.Thread):
    def __init__(self):
        self.config = utils.fetch_classes('visexpman.users.'+sys.argv[1], classname = sys.argv[2], required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig,direct = False)[0][1]()
        self.config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX']['MES_GUI'] = {'GUI' : {'IP': 'localhost', 'PORT': self.config.BASE_PORT}, 'MES' : {'IP': 'localhost', 'PORT': self.config.BASE_PORT + 1}}
        self.config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX']['MES_STIM'] = {'STIM' : {'IP': 'localhost', 'PORT': self.config.BASE_PORT+2}, 'MES' : {'IP': 'localhost', 'PORT': self.config.BASE_PORT + 3}}
        self.connections = {}
        self.queues = {}
        self.queues['gui'] = {}
        self.queues['gui']['out'] = Queue.Queue()
        self.queues['gui']['in'] = Queue.Queue()
        self.queues['stim'] = {}
        self.queues['stim']['out'] = Queue.Queue()
        self.queues['stim']['in'] = Queue.Queue()
        self.connections['gui'] = network_interface.start_client(self.config, 'MES', 'MES_GUI', self.queues['gui']['in'], self.queues['gui']['out'])
        self.connections['mes'] = network_interface.start_client(self.config, 'MES', 'MES_STIM', self.queues['stim']['in'], self.queues['stim']['out'])
        threading.Thread.__init__(self)
        self.command_parsers = {}
        self.init_mes_variables()
        for connection in ['stim', 'gui']:
            self.command_parsers[connection] = MESCommandParser(self.config, self.queues[connection]['in'], self.queues[connection]['out'], self.mes_variables)
            
    def init_mes_variables(self):
        self.mes_variables = {}
        self.mes_variables['laser_intensity'] = 0.0
        self.mes_variables['objective_postion'] = 0.0
        self.mes_variables['relative_objective_postion'] = 0.0
        self.mes_variables['objective_postion_origin'] = 0.0
        
    def run(self):
        while True:
            exit = False
            for cp in self.command_parsers.values():
                result = cp.parse()
                if result[0] == 'exit':
                    exit = True
            if exit:
                break
            time.sleep(0.05)
#        print self.mes_variables
        
class MESCommandParser(command_parser.CommandParser):
    def __init__(self, config, queue_in, queue_out, mes_variables):
        self.mes_variables = mes_variables
        self.config = config
        self.qin = queue_in
        self.qout = queue_out
        command_parser.CommandParser.__init__(self, [queue_in], queue_out)
        
    def _mes2linux_path(self, filename):
        return os.path.join(self.config.root_folder, filename.split(':')[1][1:].replace('\\', '/'))
        
    def echo(self, par):
        self.qout.put('SOCechoEOC' + str(par) + 'EOP')
        
    def read_laser_intensity(self):
        self.qout.put('SOCread_laser_intensityEOC{0}EOP'.format(self.mes_variables['laser_intensity']))

    def set_laser_intensity(self, filename):
        self.mes_variables['laser_intensity'] = scipy.io.loadmat(self._mes2linux_path(filename), mat_dtype=True)['DATA']['laser_intensity'][0][0][0][0]
        self.qout.put('SOCset_laser_intensityEOCcommandsentEOP')
        
    def setZ_relative(self, filename):
        new_value = scipy.io.loadmat(self._mes2linux_path(filename), mat_dtype=True)['DATA']['z_relative'][0][0][0][0]
        self.mes_variables['objective_postion'] += new_value - self.mes_variables['relative_objective_postion']
        self.mes_variables['relative_objective_postion'] = new_value
        self.qout.put('SOCsetZ_relativeEOCcommandsentEOP')
        
    def set_objective_origin(self, filename):
        new_value = scipy.io.loadmat(self._mes2linux_path(filename), mat_dtype=True)['DATA']['origin'][0][0][0][0]
        self.mes_variables['objective_postion_origin'] = new_value
        self.mes_variables['relative_objective_postion'] = self.mes_variables['objective_postion'] - self.mes_variables['objective_postion_origin']
        self.qout.put('SOCset_objective_originEOCcommandsentEOP')
        
    def acquire_line_scan_template(self, filename):
        reffilename = os.path.join(self.config.TESTDATA_PATH, 'mes_simulator', 'read_objective_position.mat')
        ref_data = scipy.io.loadmat(reffilename,mat_dtype=True)
        ref_data['DATA']['ZlevelArm'][0][0][0][0] = self.mes_variables['objective_postion']
        ref_data['DATA']['Zlevel'][0][0][0][0] = self.mes_variables['relative_objective_postion']
        ref_data['DATA']['ZlevelOrigin'][0][0][0][0] = self.mes_variables['objective_postion_origin']
        scipy.io.savemat(self._mes2linux_path(filename), ref_data, oned_as = 'row', long_field_names=True)
        self.qout.put('SOCacquire_line_scan_templateEOCsaveOKEOP')
        
    def acquire_line_scan(self, filename):
        #find out length of recording
        m = matlabfile.MatData(self._mes2linux_path(filename))
        duration = m.get_field(m.name2path('ts'))[0][0][0][0][-1]/1000.0
        self.qout.put('SOCacquire_line_scanEOCstartedEOP')
        time.sleep(duration)
        self.qout.put('SOCacquire_line_scanEOCOKEOP')
        #find a file in test data folder with the same duration
        for f in fileop.filtered_file_list(os.path.join(self.config.TESTDATA_PATH, 'mes_simulator'), ['fragment', 'mat'], fullpath = True,filter_condition = 'and'):
            m = matlabfile.MatData(f)
            tduration = m.get_field(m.name2path('ts'))[0][0][0][0][-1]
            if tduration == duration:
                break
        shutil.copyfile(f, self._mes2linux_path(filename))
        self.qout.put('SOCacquire_line_scanEOCsaveOKEOP')
        
    def acquire_xy_image(self, filename):
        self.qout.put('SOCacquire_xy_imageEOCstartedEOP')
        time.sleep(0.3)
        self.qout.put('SOCacquire_xy_imageEOCOKEOP')
        if not os.path.exists(self._mes2linux_path(filename)):
            shutil.copyfile(os.path.join(self.config.TESTDATA_PATH, 'mes_simulator',  'scan_region_1_parameters.mat'), self._mes2linux_path(filename))
        time.sleep(0.3)
        self.qout.put('SOCacquire_xy_imageEOCsaveOKEOP')

    def exit(self):
        self.qout.put('SOCclose_connectionEOCstop_clientEOP')
        return 'exit'
    
if __name__ == '__main__':
    var = []
    for uiname in ['visexp_runner', 'jobhandler']:
        var.append(VisexpAppRunner(uiname))
    for v in var:
        v.start()
    messim = MESSimulator()
    messim.start()
    visexp_gui.run_gui()
#    hdf5io.lockman.__del__()
