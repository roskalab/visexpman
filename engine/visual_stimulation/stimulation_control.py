#TODO: Calibration/test experiments:
#1. Default visual stimulations/examples for safestart config
#2. Setup testing, check frame rate, visual pattern capabilities, etc
#3. Projector calibration
#4. Virtual reality screen morphing calibration

#TODO: frame rate error thresholding, logging etc
#TODO: rename to experiment_control

import sys
import time
import numpy

import logging
from visexpman.engine.generic import utils    
import visexpman
import unittest
import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner
import experiment
import stimulation_library
import visexpman.users as users

import visexpman.engine.hardware_interface.instrument as instrument
import visexpman.engine.hardware_interface.daq_instrument as daq_instrument
#import visexpA.engine.datahandlers.hdf5io as hdf5io
import os
import logging
import zipfile
import os.path
import shutil
import tempfile

#For unittest:
import visexpman.engine.generic.configuration as configuration
import serial

 
def experiment_file_name(experiment_config, folder, extension, name = ''):
    experiment_class_name = str(experiment_config.runnable.__class__).split('.users.')[-1].split('.')[-1]
    if name == '':
        name_ = ''
    else:
        name_ = name + '_'
    experiment_file_path = utils.generate_filename(os.path.join(folder, name_ + experiment_class_name + '_' + utils.date_string() + '.' + extension))
    return experiment_file_path
 
class ExperimentControl():
    '''
    Starts experiment, takes care of all the logging, data file handling, saving, aggregating, handles external devices.
    '''
    def __init__(self, config, caller):
        self.config = config
        self.caller = caller
        self.devices = Devices(config, caller)
        self.data_handler = DataHandler(config, caller)        

    def init_experiment_logging(self):        
        self.logfile_path = experiment_file_name(self.caller.selected_experiment_config, self.config.EXPERIMENT_LOG_PATH, 'txt', 'log')
        #Ensure that the name of the log object is unique
        self.log = logging.getLogger('experiment log' + str(self.caller.command_handler.experiment_counter) + str(time.time()))
        self.handler = logging.FileHandler(self.logfile_path)
        formatter = logging.Formatter('%(message)s')
        self.handler.setFormatter(formatter)
        self.log.addHandler(self.handler)
        self.log.setLevel(logging.INFO)
        
    def prepare_experiment_run(self):
        #(Re)instantiate selected experiment config
        self.caller.selected_experiment_config = self.caller.experiment_config_list[int(self.caller.command_handler.selected_experiment_config_index)][1](self.config, self.caller)
        #init experiment logging
        self.init_experiment_logging()
        #Set experiment control context in selected experiment configuration
        self.caller.selected_experiment_config.set_experiment_control_context()

    def run_experiment(self):
        if hasattr(self.caller, 'selected_experiment_config') and hasattr(self.caller.selected_experiment_config, 'run'):
            self.prepare_experiment_run()
            #Message to screen, log experiment start
            self.caller.screen_and_keyboard.message += '\nexperiment started'
            self.caller.log.info('Started experiment: ' + str(self.caller.selected_experiment_config.runnable.__class__))
            self.start_time = time.time()
            self.log.info('{0:2.3f}\tExperiment started at {1}'.format(time.time()-self.start_time, utils.datetime_string()))
            #Change visexprunner state
            self.caller.state = 'experiment running'
            #Set acquisition trigger pin to high
            self.devices.parallel_port.set_data_bit(self.config.ACQUISITION_TRIGGER_PIN, 1)
            #Run experiment
            self.caller.selected_experiment_config.run()
            #Clear acquisition trigger pin
            self.devices.parallel_port.set_data_bit(self.config.ACQUISITION_TRIGGER_PIN, 0)
            #Change visexprunner state to ready
            self.caller.state = 'ready'
            #Send message to screen, log experiment completition
            self.log.info('{0:2.3f}\tExperiment finished at {1}' .format(time.time()-self.start_time, utils.datetime_string()))
            self.caller.screen_and_keyboard.message += '\nexperiment ended'
            self.caller.log.info('Experiment complete')
        else:
            raise AttributeError('Stimulus config class does not have a run method?')
        
    def finish_experiment(self):
        self.handler.flush()
        self.devices.close()
        self.data_handler.archive_software_environment()
        
class Devices():
    '''
    This class encapsulates all the operations need to access (external) hardware: parallel port, shutter, filterwheel...
    '''
    def __init__(self, config, caller):
        self.config = config
        self.caller = caller
        self.parallel_port = instrument.ParallelPort(config, caller)
        self.filterwheels = []
        if hasattr(self.config, 'FILTERWHEEL_SERIAL_PORT'):
            self.number_of_filterwheels = len(config.FILTERWHEEL_SERIAL_PORT)
        else:
            #If filterwheels neither configured, nor enabled, two virtual ones are created, so that experiments calling filterwheel functions could be called
            self.number_of_filterwheels = 2
        for id in range(self.number_of_filterwheels):
            self.filterwheels.append(instrument.Filterwheel(config, caller, id =id))

        if hasattr(self.config, 'LED_CONTROLLER_INSTRUMENT_INDEX') and hasattr(self.config, 'DAQ_CONFIG'):
#             if self.config.DAQ_CONFIG[self.config.LED_CONTROLLER_INSTRUMENT_INDEX]['ENABLE'] and self.config.DAQ_CONFIG[self.config.LED_CONTROLLER_INSTRUMENT_INDEX]['ANALOG_CONFIG'] == 'ao':
                self.led_controller = daq_instrument.AnalogPulse(self.config, self.caller)

    def close(self):        
        self.parallel_port.release_instrument()
        if os.name == 'nt':
            for filterwheel in self.filterwheels:
                filterwheel.release_instrument()
        if hasattr(self, 'led_controller'):
            self.led_controller.release_instrument()
            
class DataHandler():
    '''
    Responsible for the following:
    1. Collect into zip file all the experiment related files: source code, experiment log, list of version of python modules
    2. Convert this zip file to hdf5 (check VisexpA)
    3. zipping is optional
    '''
    def __init__(self, config, caller):
        self.caller = caller
        self.config = config
        self.visexpman_module_paths  = self.caller.visexpman_module_paths
        self.module_versions = self.caller.module_versions        
        
    def archive_software_environment(self):
        '''
        Archives the called python modules within visexpman package and the versions of all the called packages
        '''
        #save module version data to file
        module_versions_file_path = os.path.join(os.path.dirname(tempfile.mktemp()),'module_versions.txt')
        f = open(module_versions_file_path, 'wt')
        f.write(self.module_versions)
        f.close()
        #If the archive format is hdf5, zip file is saved to a temporary folder
        if self.config.ARCHIVE_FORMAT == 'zip':
            zip_folder = self.config.ARCHIVE_PATH
            self.zip_file_path = experiment_file_name(self.caller.selected_experiment_config, zip_folder, 'zip')
        elif self.config.ARCHIVE_FORMAT == 'hdf5':
            self.zip_file_path = tempfile.mktemp()
#            self.hdf5_handler = hdf5io.Hdf5io(experiment_file_name(self.caller.selected_experiment_config, self.config.ARCHIVE_PATH, 'hdf5') , self.config, self.caller)
        else:
            raise RuntimeError('Archive format is not defined. Please check the configuration!')
        #Create zip file        
        archive = zipfile.ZipFile(self.zip_file_path, "w")
        archive.write(module_versions_file_path, module_versions_file_path.replace(os.path.dirname(module_versions_file_path), ''))
        for python_module in self.visexpman_module_paths:
            zip_path = python_module.split('visexpman')[-1]
            archive.write(python_module, zip_path)
        #include experiment log
        archive.write(self.caller.experiment_control.logfile_path, self.caller.experiment_control.logfile_path.replace(os.path.dirname(self.caller.experiment_control.logfile_path), ''))
        archive.close()
        f = open(self.zip_file_path, 'rb')
        archive_binary = f.read(os.path.getsize(self.zip_file_path))
        f.close()
        archive_binary_in_bytes = []
        for byte in list(archive_binary):
            archive_binary_in_bytes.append(ord(byte))
        archive_binary_in_bytes = numpy.array(archive_binary_in_bytes, dtype = numpy.uint8)
        #Restoring it to zip file: utils.numpy_array_to_file(archive_binary_in_bytes, '/media/Common/test.zip')

class TestConfig(configuration.Config):
    def _create_application_parameters(self):
        PIN_RANGE = [0, 7]
        #parallel port
        ENABLE_PARALLEL_PORT = True
        ACQUISITION_TRIGGER_PIN = [0,  PIN_RANGE]
        FRAME_TRIGGER_PIN = [2,  PIN_RANGE]
        FRAME_TRIGGER_PULSE_WIDTH = [1e-3,  [1e-4,  1e-1]]

        #filterwheel settings
        ENABLE_FILTERWHEEL = unit_test_runner.TEST_filterwheel_enable
        if os.name == 'nt':
            port = 'COM4'
        elif os.name == 'posix':
            port = '/dev/ttyUSB0'
        FILTERWHEEL_SERIAL_PORT = [[{
                                    'port' :  port,
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,
                                    }]]
        if os.name == 'nt':
            ARCHIVE_PATH = 'c:\\_del\\test'
        elif os.name == 'posix':
            ARCHIVE_PATH = '/media/Common/visexpman_data/test'
        ARCHIVE_PATH = os.path.join(ARCHIVE_PATH, 'test')
        if not os.path.exists(ARCHIVE_PATH):
            os.mkdir(ARCHIVE_PATH)
        
        ARCHIVE_FORMAT = 'zip'

        self._create_parameters_from_locals(locals())

class testDataHandler(unittest.TestCase):
    def setUp(self):
        module_info = utils.imported_modules()
        self.visexpman_module_paths  = module_info[1]
        self.module_versions = utils.module_versions(module_info[0])
        self.config = TestConfig()
        self.dh = DataHandler(self.config, self)

    def test_01_DataHandler_contructor(self):
        self.assertEqual((hasattr(self.dh, 'visexpman_module_paths'), hasattr(self.dh, 'module_versions')), (True, True))

    def tearDown(self):
        shutil.rmtree(self.config.ARCHIVE_PATH)

class testExternalHardware(unittest.TestCase):
    '''
    '''
    def setUp(self):
        self.state = 'ready'
        self.config = TestConfig()
        self.start_time = time.time()        
        
    #Testing constructor
    def test_01_creating_instruments(self):        
        e = Devices(self.config, self)
        self.assertEqual((hasattr(e, 'parallel_port'), hasattr(e, 'filterwheels')),  (True, True))
        e.close()

    def test_02_disabled_instruments(self):        
        self.config.ENABLE_PARALLEL_PORT = False
        self.config.ENABLE_FILTERWHEEL = False
        e = Devices(self.config, self)
        self.assertEqual((hasattr(e, 'parallel_port'), hasattr(e, 'filterwheels')),  (True, True))
        e.close()

    def test_03_toggle_parallel_port_pin(self):        
        self.d = Devices(self.config, self)
        self.d.parallel_port.set_data_bit(self.config.ACQUISITION_TRIGGER_PIN, 1)
        time.sleep(0.1)
        self.d.parallel_port.set_data_bit(self.config.ACQUISITION_TRIGGER_PIN, 0)
        self.assertEqual((hasattr(self.d, 'parallel_port'), hasattr(self.d, 'filterwheels'), self.d.parallel_port.iostate['data']),  (True, True, 0))
        self.d.close()
        

if __name__ == "__main__":
    unittest.main()
    
