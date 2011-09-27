#TODO: Calibration/test experiments:
#1. Default visual stimulations/examples for safestart config
#2. Setup testing, check frame rate, visual pattern capabilities, etc
#3. Projector calibration
#4. Virtual reality screen morphing calibration

#TODO: frame rate error thresholding, logging etc
#TODO: rename to experiment_control

import sys
import zipfile as zip
import os
import os.path
import time
import numpy

from OpenGL.GL import *
from OpenGL.GLU import *
import logging
from visexpman.engine.generic import utils    
import visexpman
import unittest

#import modules for stimulus files:
#from random import *
#from numpy import *

import experiment
import stimulation_library
import visexpman.users as users

import visexpman.engine.hardware_interface. instrument as instrument
#import visexpA.engine.datahandlers.hdf5io as hdf5io
import os
import logging
import zipfile
import os.path
import shutil

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
        self.log = logging.getLogger('experiment log' + str(self.caller.command_handler.experiment_counter))
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
        self.prepare_experiment_run()
        #Message to screen, log experiment start
        self.caller.screen_and_keyboard.message += '\nexperiment started'
        self.caller.log.info('Started experiment: ' + str(self.caller.selected_experiment_config.runnable.__class__))
        self.log.info('%2.3f\tExperiment started at %s' %(time.time(), utils.datetime_string()))
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
        self.log.info('Experiment finished at ' + utils.datetime_string())
        self.caller.screen_and_keyboard.message += '\nexperiment ended'
        self.caller.log.info('Experiment complete')
        
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
        for id in range(len(config.FILTERWHEEL_SERIAL_PORT)):
            self.filterwheels.append(instrument.Filterwheel(config, caller, id =id))

    def close(self):        
        self.parallel_port.release_instrument()        
        self.filterwheels = []
        for filterwheel in self.filterwheels:
            filterwheel.release_instrument()
            
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
        module_versions_file_path = os.path.join(self.config.TMP_PATH,'module_versions.txt')
        f = open(module_versions_file_path, 'wt')
        f.write(self.module_versions)
        f.close()
        #If the archive format is hdf5, zip file is saved to a temporary folder
        if self.config.ARCHIVE_FORMAT == 'zip':
            zip_folder = self.config.ARCHIVE_PATH
        elif self.config.ARCHIVE_FORMAT == 'hdf5':            
            zip_folder = self.config.TMP_PATH
#            self.hdf5_handler = hdf5io.Hdf5io(experiment_file_name(self.caller.selected_experiment_config, self.config.ARCHIVE_PATH, 'hdf5') , self.config, self.caller)
        else:
            raise RuntimeError('Archive format is not defined. Please check the configuration!')
        #Create zip file
        zip_file_path = experiment_file_name(self.caller.selected_experiment_config, zip_folder, 'zip')        
        archive = zipfile.ZipFile(zip_file_path, "w")
        archive.write(module_versions_file_path, module_versions_file_path.replace(os.path.dirname(module_versions_file_path), ''))
        for python_module in self.visexpman_module_paths:
            zip_path = python_module.split('visexpman')[-1]
            archive.write(python_module, zip_path)
        #include experiment log
        archive.write(self.caller.experiment_control.logfile_path, self.caller.experiment_control.logfile_path.replace(os.path.dirname(self.caller.experiment_control.logfile_path), ''))
        archive.close()
        f = open(zip_file_path, 'rb')
        archive_binary = f.read(os.path.getsize(zip_file_path))
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
        FILTERWHEEL_ENABLE = True
        FILTERWHEEL_SERIAL_PORT = [[{
                                    'port' :  '/dev/ttyUSB0',
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,
                                    }]]

        ARCHIVE_PATH = '/media/Common/visexpman_data/test'
        TMP_PATH = '/media/Common/visexpman_data/tmp'
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

#This tests requires a more complex test environment
#    def test_02_archive_software_environment(self):
#        self.dh.archive_software_environment()
#        module_versions_path = os.path.join(self.config.TMP_PATH,'module_versions_000.txt')
#        zip_path = os.path.join(self.config.TMP_PATH,'archive_000.zip')
#        self.assertEqual((os.path.exists(module_versions_path), os.path.exists(zip_path)), (True, True))

    def tearDown(self):
        shutil.rmtree(self.config.TMP_PATH)
        os.mkdir(self.config.TMP_PATH)
        shutil.rmtree(self.config.ARCHIVE_PATH)
        os.mkdir(self.config.ARCHIVE_PATH)

class testExternalHardware(unittest.TestCase):
    '''
    '''
    def setUp(self):
        self.state = 'ready'
        self.config = TestConfig()
        
    #Testing constructor
    def test_01_creating_instruments(self):        
        e = Devices(self.config, self)
        self.assertEqual((hasattr(e, 'parallel_port'), hasattr(e, 'filterwheels')),  (True, True))
        e.close()

    def test_02_disabled_instruments(self):        
        self.config.ENABLE_PARALLEL_PORT = False
        self.config.FILTERWHEEL_ENABLE = False
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

class StimulationControl():
    '''
    StimulationControl handles stimulation sequences, generating TTL triggers and log stimulation events with timestamps
    '''
    def __init__(self, visual_stimulation_runner, config, user_interface):
        
        self.visual_stimulation_runner = visual_stimulation_runner
        self.config = config
        self.stimulation_file = ''
        self.user_interface = user_interface
        #self.udp_interface = udp_interface
        if self.config.ENABLE_PARALLEL_PORT:
            import parallel
            try:
                self.parallel = parallel.Parallel()
            except WindowsError:
                self.parallel = None
                self.config.set('ENABLE_PARALLEL_PORT',  False)
        else:
            self.parallel = None
        self.st = stimulation_library.Stimulations(config,  user_interface,  self,  self.parallel)
        self.state = 'idle'
        
        self.screen = user_interface.screen
        
        self.stimulation_script = ''
        self.measurement_id = 'not defined'
        
        #calculate wait time for frame rate control
        self.wait_time = 1.0/self.config.SCREEN_EXPECTED_FRAME_RATE

        #initialize event logging
        self.logfile_path = self.config.LOG_PATH + os.sep + 'log' + str(time.time()).replace('.', '') + '.txt'

        #self.logfile = psychopy.log.LogFile(self.logfile_path,  level = psychopy.log.DATA,  filemode = 'w')
        self.log = logging.getLogger('vision experiment log')
        handler = logging.FileHandler(self.logfile_path)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)
        self.log.setLevel(logging.INFO)
            
        self.log_file_index = 0                
            
        #self._disable_frame_interval_watch()
        
        #intitialize filterwheels
        if self.config.FILTERWHEEL_ENABLE:
            self.filterwheels = []
            for i in range(len(self.config.FILTERWHEEL_SERIAL_PORT)):
                self.filterwheels.append(generic.Instrument.Filterwheel(self.config,  id = i))
            
    def is_next_pressed(self):
        return self.user_interface.is_next_pressed()
        
    def _enable_frame_interval_watch(self):        
        self.screen.setRecordFrameIntervals(True)        

    def _disable_frame_interval_watch(self):        
        self.screen.setRecordFrameIntervals(False)             

    def handle_pygame_events(self):
        '''Programmer can call this method from his run method to check for user input'''
        if pygame.event.peek() is False: return # no events do not waste more time
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                    key_pressed = pygame.key.name(event.key)
            if key_pressed == 'q':
                break
    def zip_py_files(self, zip_path,  base_path, log):
        '''
        Saves Presentinator source files, stimulation file(s) and log file into a zip file
        '''
        zfile = zip.ZipFile(zip_path, "w")
        for root, subFolders, files in os.walk(base_path):
            for file in files:
                filename = os.path.join(root,file)
                if filename.find('.py') != -1 and filename.find('.pyc') == -1:
                    filepath_in_zip = filename.replace(base_path,'')
                    zfile.write(filename, filepath_in_zip, zip.ZIP_DEFLATED)
        
        #save log file to temporary file
        log_filename = 'log.txt'
        f = open(log_filename ,  'wt')
        f.write(log)
        f.close()
        zfile.write(log_filename , 'log/' + log_filename, zip.ZIP_DEFLATED)
        zfile.close()
        os.remove(log_filename)
        
    def last_stimulus_log(self):
        return utils.read_text_file(self.logfile_path)[self.log_file_index:]
    
    def log_data(self, log_message):
        f = open(self.logfile_path,  'at')
        string_to_file = "%2.3f"% (time.time() - self.start_time)
        string_to_file += '\t' + log_message + '\n'
        f.write(string_to_file)
        f.close()
    
    def run_stimulation(self):
        '''
        Runs stimulation and takes care of triggering and frame interval watching
        '''
        if hasattr(self.visual_stimulation_runner, 'selected_experiment_config') and hasattr(self.visual_stimulation_runner.selected_experiment_config, 'run'):
            #save log file index which is the current size of log file
            #self.log_file_index = len(utils.read_text_file(self.logfile_path))
            self.visual_stimulation_runner.state = 'stimulation'
            
            #psychopy.log.data('Measurement ID: ' + self.measurement_id)

            #self._enable_frame_interval_watch()
            if self.config.ENABLE_PARALLEL_PORT:
                self.parallel.setData(self.config.ACQUISITION_TRIGGER_ON)
                
            self.st.delayed_frame_counter = 0
            self.stimulation_start_time = time.time()
            if hasattr(self.visual_stimulation_runner.selected_experiment_config, 'pre_runnable') and self.visual_stimulation_runner.selected_experiment_config.pre_runnable is not None:
                self.visual_stimulation_runner.selected_experiment_config.pre_runnable.run()
            self.visual_stimulation_runner.selected_experiment_config.run(self.st)
            #psychopy.log.data(log_string)            
                
            if self.config.ENABLE_PARALLEL_PORT:
                self.parallel.setData(self.config.ACQUISITION_TRIGGER_OFF)
                       
            #self._disable_frame_interval_watch()
            self.st.set_background(self.config.BACKGROUND_COLOR)
            
            #log number of delayed frames
            self.log.info('Number of delayed frames: %d'%(self.st.delayed_frame_counter))            
            print self.st.delayed_frame_counter #TODO: normalize to number of frames and duration
            
            #save stimulus, source and log files into zip            
            log = self.last_stimulus_log()
            
            if len(self.config.ARCHIVE_PATH)  == 0:
                zip_path = self.config.ARCHIVE_PATH + str(time.time()).replace('.', '') + '.zip'
            else:
                zip_path = self.config.ARCHIVE_PATH + os.sep + str(time.time()).replace('.', '') + '.zip'
                
            #if user log file path defined save log data using that path. This is for maintain compatibility with labview presentinator
            for local in locals():
                if local == 'user_log_file_path':
                    if os.path.exists(os.path.dirname(user_log_file_path)):                
                        f = open(user_log_file_path ,  'wt')
                        f.write(log)
                        f.close()

            #save all the python source files in the visexpman module
            self.zip_py_files(zip_path, os.path.dirname(visexpman.__file__), log)
            self.visual_stimulation_runner.state = 'idle'
        else:
            raise AttributeError('Stimulus config class does not have a run method?')

if __name__ == "__main__":
    unittest.main()
    
