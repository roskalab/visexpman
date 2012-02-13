0#TODO: Calibration/test experiments:
#1. Default visual stimulations/examples for safestart config
#2. Setup testing, check frame rate, visual pattern capabilities, etc
#3. Projector calibration
#4. Virtual reality screen morphing calibration

#TODO: frame rate error thresholding, logging etc
#TODO: rename to experiment_control

import sys
import time
import numpy
import inspect
import re

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
import visexpman.engine.hardware_interface.motor_control as motor_control
import visexpman.engine.hardware_interface.mes_interface as mes_interface
import visexpA.engine.datahandlers.hdf5io as hdf5io
import visexpA.engine.datahandlers.importers as importers
from visexpA.users.zoltan import data_rescue
import scipy.io#????
from visexpman.engine.visual_stimulation import experiment_data
import gc
import os
import logging
import zipfile
import os.path
import shutil
import tempfile
import copy
import hashlib

#For unittest:
import visexpman.engine.generic.configuration as configuration
import serial
import visexpman.engine.generic.log as log
experiment_name_extract = re.compile('class (.+)(experiment.Experiment)')
 


class ExperimentControl():
    '''
    Starts experiment, takes care of all the logging, data file handling, saving, aggregating, handles external devices.
    '''
    def __init__(self, config, screen_and_keyboard, connections, experiment_source = ''):
        self.config = config
        self.screen_and_keyboard = screen_and_keyboard
        self.connections = connections
        self.from_gui_queue = self.connections['gui'].queue_in
        self.devices = Devices(config, self, screen_and_keyboard, connections)
        self.data_handler = DataHandler(config, caller)
        self.start_time = 0
        self.frame_counter = 0
        self.stimulus_frame_info = []
        self.stimulus_frame_info_pointer = 0
        #saving experiment source to a temporary file in the user's folder
        self.experiment_source = experiment_source
        self.experiment_source_path = os.path.join(self.config.PACKAGE_PATH, 'users', self.config.user, 'presentinator_experiment' + str(self.caller.command_handler.experiment_counter) + '.py')
        self.experiment_source_module = os.path.split(self.experiment_source_path)[-1].replace('.py', '')
        if len(self.experiment_source)>0 and self.config.ENABLE_UDP:
            #To avoid name confilct between experiment configs and experiments in the user's folder, these classes are renamed in the network loaded experiment module
            now = int(time.time())
            self.experiment_source = self.experiment_source.replace('(experiment.ExperimentConfig)', '{0}(experiment.ExperimentConfig)'.format(now))
            experiment_name =experiment_name_extract.findall(self.experiment_source)[0]
            self.experiment_source = self.experiment_source.replace(experiment_name, experiment_name+str(now))
            f = open(self.experiment_source_path, 'wt')
            f.write(self.experiment_source)
            f.close()
            #Find out name of experiment config sent over udp
            original_class_list = utils.class_list_in_string(self.caller.experiment_config_list)
            #Instantiate this experiment
            self.caller.experiment_config_list = utils.fetch_classes('visexpman.users.' + self.config.user,  required_ancestors = visexpman.engine.visual_stimulation.experiment.ExperimentConfig)
            #compare lists and find out index of newly sent experiment config
            new_class_list = utils.class_list_in_string(self.caller.experiment_config_list)
            for i in range(len(new_class_list)):
                if not utils.is_in_list(original_class_list, new_class_list[i]):
                    self.caller.command_handler.selected_experiment_config_index = i
                    break
            
            reload(sys.modules['visexpman.users.' + self.config.user + '.' + self.experiment_source_module])

    def init_experiment_logging(self):
        #Ensure that the name of the log object is unique
        self.logfile_path = experiment_file_name(self.caller.selected_experiment_config, self.config.EXPERIMENT_LOG_PATH, 'txt', 'log') 
        self.log = log.Log('experiment log' + str(self.caller.command_handler.experiment_counter) + str(time.time()),
                                                                                                                   self.logfile_path, write_mode = 'user control', timestamp = 'elapsed_time')
        self.devices.mes_interface.log = self.log #Probably this is not the nicest solution

    def prepare_experiment_run(self):
        '''
        Run context of the experiment is prepared
        '''
        self.frame_counter = 0
        self.stimulus_frame_info = []
        self.stimulus_frame_info_pointer = 0
        #(Re)instantiate selected experiment config        
        self.caller.selected_experiment_config = self.caller.experiment_config_list[int(self.caller.command_handler.selected_experiment_config_index)][1]\
            (self.config, self.screen_and_keyboard, self, self.connections)
        #init experiment logging
        self.init_experiment_logging()
        #Create archive files so that user can save data during the experiment
        self.archive = experiment_data.prepare_archive(self.config, self.caller.selected_experiment_config)
        self.data_handler.prepare_archive()
        #Set experiment control context in selected experiment configuration
        self.caller.selected_experiment_config.set_experiment_control_context()
        self.selected_experiment = self.caller.selected_experiment_config.runnable
        self.selected_experiment_config = self.caller.selected_experiment_config
        self.experiment_result_files = []
        
    def start_fragment(self, fragment_id):
        '''
        
        '''
        if not hasattr(self.caller.selected_experiment_config.runnable, 'fragment_durations') and self.config.MEASUREMENT_PLATFORM == 'mes':
                return True
        #Generate file name
        self.fragment_name = '{0}_{1}_{2}'.format(self.selected_experiment.experiment_name, int(self.start_time), fragment_id)
        self.printl('Fragment {0}/{1}, name: {2}'.format(fragment_id + 1, self.number_of_fragments, self.fragment_name))
        self.fragment_mat_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, ('fragment_{0}.mat'.format(self.fragment_name)))
        self.fragment_hdf5_path = self.fragment_mat_path.replace('.mat', '.hdf5')
        if self.config.MEASUREMENT_PLATFORM == 'mes':
            #Create mes parameter file            
            mes_recording_time = self.selected_experiment.fragment_durations[fragment_id]            
#            mes_interface.set_line_scan_time(mes_recording_time + 3.0, self.parameter_file, self.fragment_mat_path)
            ######################## Start mesurement ###############################
            self.frame_counter = 0 #shall be reset if fragmented experiment is run, because sync signal recording is restarted at each fragment
            #Start recording analog signals
            self.devices.ai = daq_instrument.AnalogIO(self.config, self.caller)
            self.devices.ai.start_daq_activity()
            self.printl('ai recording started')
            #empty queue
            while not self.caller.mes_response_queue.empty():
                self.caller.mes_response_queue.get()
            #start two photon recording
            line_scan_start_success, line_scan_path = self.devices.mes_interface.start_line_scan(scan_time = mes_recording_time + 3.0, 
                                                                                                 parameter_file = self.fragment_mat_path, 
                                                                                                 timeout = 10.0)
            if line_scan_start_success:
                time.sleep(1.0)
            else:
                self.printl('line scan start ERROR')
            return line_scan_start_success           
        elif self.config.MEASUREMENT_PLATFORM == 'elphys':
            #Start recording analog signals            
            self.devices.ai = daq_instrument.AnalogIO(self.config, self.caller)
            self.devices.ai.start_daq_activity()
            self.printl('ai recording started')
            #Set acquisition trigger pin to high
            self.devices.parallel_port.set_data_bit(self.config.ACQUISITION_TRIGGER_PIN, 1)
            return True
        elif self.config.MEASUREMENT_PLATFORM == 'standalone':
            return True
            
    def finish_fragment(self, fragment_id):
        gc.collect()
        if self.config.MEASUREMENT_PLATFORM == 'mes':
            if not hasattr(self.caller.selected_experiment_config.runnable, 'fragment_durations'):
                return
            timeout = self.selected_experiment.fragment_durations[fragment_id]            
            if timeout < 10.0:
                timeout = 10.0
            if not utils.is_abort_experiment_in_queue(self.from_gui_queue):
                line_scan_complete_success =  self.devices.mes_interface.wait_for_line_scan_complete(timeout)
            else:
                line_scan_complete_success =  False
            ######################## Finish fragment ###############################
            if line_scan_complete_success:
                #Stop acquiring analog signals
                self.devices.ai.finish_daq_activity(abort = utils.is_abort_experiment_in_queue(self.from_gui_queue))                
                self.printl('ai recording finished, waiting for data save complete')
                if not utils.is_abort_experiment_in_queue(self.from_gui_queue):
                    line_scan_data_save_success = self.devices.mes_interface.wait_for_line_scan_save_complete(timeout)
                else:
                    line_scan_data_save_success = False
                ######################## Save data ###############################
                if line_scan_data_save_success and not utils.is_abort_experiment_in_queue(self.from_gui_queue):
                    self.printl('Saving measurement data to hdf5')
                    #Save
                    fragment_hdf5 = hdf5io.Hdf5io(self.fragment_hdf5_path)
                    self.experiment_result_files.append(self.fragment_hdf5_path)
                    if not hasattr(self.devices.ai, 'ai_data'):
                        self.devices.ai.ai_data = numpy.zeros((2, 2))
                    mes_data = utils.file_to_binary_array(self.fragment_mat_path)
                    stimulus_frame_info_with_data_series_index, rising_edges_indexes =\
                                experiment_data.preprocess_stimulus_sync(self.devices.ai.ai_data[:, self.config.SYNC_CHANNEL_INDEX], stimulus_frame_info = self.stimulus_frame_info[self.stimulus_frame_info_pointer:])
                    stimulus_frame_info = {}
                    if stimulus_frame_info_with_data_series_index != None:
                        for i in range(0, len(stimulus_frame_info_with_data_series_index)):
                            stimulus_frame_info['index_'+str(i)] = self.stimulus_frame_info[i]
                    data_to_hdf5 = {
                                    'sync_data' : self.devices.ai.ai_data,
                                    'mes_data': mes_data, 
                                    'mes_data_hash' : hashlib.sha1(mes_data).hexdigest(),
                                    'current_fragment' : fragment_id, #deprecated
                                    'actual_fragment' : fragment_id,
                                    'stimulus_frame_info' : stimulus_frame_info,                                    
                                    'rising_edges_indexes' : rising_edges_indexes
                                    }
                    self.stimulus_frame_info_pointer = len(self.stimulus_frame_info)
                    if hasattr(self.selected_experiment, 'number_of_fragments'):
                        data_to_hdf5['number_of_fragments'] = self.selected_experiment.number_of_fragments
                    data_to_hdf5['generated_data'] = self.selected_experiment.fragment_data
                    #Saving source code of experiment
                    experiment_source_file_path = inspect.getfile(self.selected_experiment.__class__).replace('.pyc', '.py')
                    data_to_hdf5['experiment_source'] = utils.file_to_binary_array(experiment_source_file_path)
                    experiment_data.save_config(fragment_hdf5, self.config, self.selected_experiment_config)
                    time.sleep(2.0) #Wait for file ready DO WE ACTUALLY NEED THIS DELAY????
                    #read stage and objective position
                    if fragment_id == 0:
                        self.stage_position = self.devices.stage.read_position() - self.caller.stage_origin
                        self.objective_position = mes_interface.get_objective_position(self.fragment_mat_path, log = self.log)[0]
                    experiment_data.save_position(fragment_hdf5, self.stage_position, self.objective_position)                    
                    setattr(fragment_hdf5, self.fragment_name, data_to_hdf5)
                    fragment_hdf5.save(self.fragment_name)
                    #Here the saved data will be checked and preprocessed
                    self.printl('Prepare data for analysis')
                    mes_extractor = importers.MESExtractor(fragment_hdf5)
                    data_class, stimulus_class, mes_name = mes_extractor.parse()
                    fragment_hdf5.close()
                    #Rename fragment hdf5 so that coorinates are included
                    original_fragment_path = self.fragment_hdf5_path
                    self.fragment_hdf5_path = self.fragment_hdf5_path.replace('fragment_',  'fragment_{0:.1f}_{1:.1f}_{2}_'.format(self.stage_position[0], self.stage_position[1], self.objective_position))
                    shutil.move(original_fragment_path, self.fragment_hdf5_path)
                    result, messages = data_rescue.check_fragment(self.fragment_hdf5_path, ['data_class','stimulus_class','sync_signal','stimpar' ])
                    if not result:
                        self.printl('incorrect fragment file: ' + str(messages))                    
                    self.printl('measurement data saved to hdf5: {0}'.format(self.fragment_hdf5_path))
                else:
                    self.printl('line scan data save ERROR')
            else:
                self.printl('line scan complete ERROR')
            self.devices.ai.release_instrument()
        
        elif self.config.MEASUREMENT_PLATFORM == 'elphys':
            #Clear acquisition trigger pin
            self.devices.parallel_port.set_data_bit(self.config.ACQUISITION_TRIGGER_PIN, 0)
            #Stop acquiring analog signals
            if hasattr(self.devices, 'ai'):
                self.devices.ai.finish_daq_activity()
            self.printl('ai recording finished, waiting for data save complete')
            if hasattr(self.devices, 'ai'):
                if hasattr(self.devices.ai, 'ai_data'):
                    self.data_handler.ai_data = self.devices.ai.ai_data
                else:
                    self.data_handler.ai_data = numpy.zeros(2)
                self.devices.ai.release_instrument()
        elif self.config.MEASUREMENT_PLATFORM == 'standalone':
            return True
    
    def run_experiment(self):
        if hasattr(self.caller, 'selected_experiment_config') and hasattr(self.caller.selected_experiment_config, 'run'):
            self.abort = False
            self.prepare_experiment_run()
            #Message to screen, log experiment start
            self.caller.screen_and_keyboard.message += '\nexperiment started'
            self.caller.log.info('Started experiment: ' + utils.class_name(self.caller.selected_experiment_config.runnable))
            self.start_time = time.time()
            self.log.info('Experiment started at {0}'.format(utils.datetime_string()))
            #Change visexprunner state
            self.caller.state = 'experiment running'
            self.fragmented_experiment = hasattr(self.caller.selected_experiment_config.runnable, 'number_of_fragments') and\
                    hasattr(self.caller.selected_experiment_config.runnable, 'fragment_durations')
            if self.fragmented_experiment:
                self.number_of_fragments = len(self.caller.selected_experiment_config.runnable.fragment_durations)
            else:
                self.number_of_fragments = 1
            self.caller.selected_experiment_config.pre_first_fragment()
            for fragment_id in range(self.number_of_fragments):
                if utils.is_abort_experiment_in_queue(self.from_gui_queue, False):
                    self.printl('experiment aborted',  software_log = True)
                    self.abort = True
                    break
                elif self.start_fragment(fragment_id):
                    #Run stimulation
                    self.caller.selected_experiment_config.run(fragment_id)
                    self.finish_fragment(fragment_id)
            if utils.is_abort_experiment_in_queue(self.from_gui_queue, False):
                    self.printl('experiment aborted',  software_log = True)
                    self.abort = True
            #Change visexprunner state to ready
            self.caller.state = 'ready'
            #Send message to screen, log experiment completition
            self.log.info('Experiment finished at {0}' .format(utils.datetime_string()))
            self.caller.screen_and_keyboard.message += '\nexperiment ended'
            self.caller.log.info('Experiment complete')
        else:
            raise AttributeError('Does stimulus config class have run method?')
        
    def finish_experiment(self):
        self.log.flush()
        self.caller.log.flush()
        self.devices.close()
        self.data_handler.archive_software_environment(experiment_config = self.caller.selected_experiment_config, experiment_log = self.logfile_path,  stimulus_frame_info = self.stimulus_frame_info)
        self.frame_counter = 0
        self.stimulus_frame_info = []
        self.stimulus_frame_info_pointer = 0
        #remove temporary experiment file
        if len(self.experiment_source)>0 and self.config.ENABLE_UDP:
            os.remove(self.experiment_source_path)
            os.remove(self.experiment_source_path+'c')            
        if hasattr(self.caller, 'mes_command_queue'):
            while not self.caller.mes_command_queue.empty():
                print self.caller.mes_command_queue.get()
        #Rename hdf5 file to user provided name (experiment.experiment_hdf5_path) !!!! THIS IS SPECIFIC FOR HDF5
        if hasattr(self.data_handler,  'hdf5_handler'):
            experiment_data_file = self.data_handler.hdf5_handler.filename
        if hasattr(self.caller.selected_experiment_config.runnable, 'experiment_hdf5_path'):
            try:
                shutil.move(self.data_handler.hdf5_handler.filename, self.caller.selected_experiment_config.runnable.experiment_hdf5_path)
                experiment_data_file = self.caller.selected_experiment_config.runnable.experiment_hdf5_path
            except:
                print self.data_handler.hdf5_handler.filename, self.caller.selected_experiment_config.runnable.experiment_hdf5_path
                self.printl('NOT renamed for some reason')
            self.experiment_result_files.append(experiment_data_file)
        self.printl('Experiment complete')
        
    def check_experiment_data(self):
        print self.experiment_result_files
        if self.config.MEASUREMENT_PLATFORM == 'mes' :
            for experiment_result_file in self.experiment_result_files:
                if 'fragment' in experiment_result_file:
                    pass
#                    try:
#                        fragment_data = importers.MESExtractor(experiment_result_file)
#                        res = fragment_data.parse()
#                    except:
#                        import traceback
#                        traceback_info = traceback.format_exc()            
#                        self.caller.log.info(traceback_info)
#                        print traceback_info
        elif self.config.MEASUREMENT_PLATFORM == 'elphys':
            pass
        elif self.config.MEASUREMENT_PLATFORM == 'standalone':
            pass
        
    def printl(self, message,  software_log = False, experiment_log = True):
        '''
        Helper function that can be called during experiment. The message is sent to:
        -standard output
        -gui
        -experiment log
        '''
        print message
        self.caller.to_gui_queue.put(str(message))
        if software_log:
            self.caller.log.info(message)
        if hasattr(self, 'log') and experiment_log:
            self.log.info(str(message))
        
class Devices():
    '''
    This class encapsulates all the operations need to access (external) hardware: parallel port, shutter, filterwheel...
    '''
    def __init__(self, config, experiment_control, screen_and_keyboard, connections):
        self.config = config
        self.parallel_port = instrument.ParallelPort(config, experiment_control)
        self.filterwheels = []
        if hasattr(self.config, 'FILTERWHEEL_SERIAL_PORT'):
            self.number_of_filterwheels = len(config.FILTERWHEEL_SERIAL_PORT)
        else:
            #If filterwheels neither configured, nor enabled, two virtual ones are created, so that experiments calling filterwheel functions could be called
            self.number_of_filterwheels = 2
        for id in range(self.number_of_filterwheels):
            self.filterwheels.append(instrument.Filterwheel(config, experiment_control, id =id))
        self.led_controller = daq_instrument.AnalogPulse(self.config, experiment_control, id = 1)#TODO: config shall be analog pulse specific, if daq enabled, this is always called
        self.ai = None        
        self.stage = motor_control.AllegraStage(self.config, experiment_control)
        self.mes_interface = mes_interface.MesInterface(self.config, connections, screen_and_keyboard, log = experiment_control.log)

    def close(self):
        self.parallel_port.release_instrument()
        if os.name == 'nt':
            for filterwheel in self.filterwheels:
                filterwheel.release_instrument()
        if hasattr(self, 'led_controller'):
            if hasattr(self.led_controller,  'release_instrument'):
                self.led_controller.release_instrument()
        if hasattr(self, 'stage'):
            self.stage.release_instrument()
            
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
        port = unit_test_runner.TEST_com_port
        FILTERWHEEL_SERIAL_PORT = [{
                                    'port' :  port,
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,
                                    }]
        
        EXPERIMENT_DATA_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_DATA_PATH = os.path.join(EXPERIMENT_DATA_PATH, 'test')
        if not os.path.exists(EXPERIMENT_DATA_PATH):
            os.mkdir(EXPERIMENT_DATA_PATH)
        VISEXPMAN_MES = {'ENABLE' : False,'IP': '',  'PORT' : 10003,  'RECEIVE_BUFFER' : 256}
        ARCHIVE_FORMAT = 'zip'

        self._create_parameters_from_locals(locals())

class testExternalHardware(unittest.TestCase):
    '''
    '''
    def setUp(self):
        import Queue
        self.state = 'ready'
        self.mes_command_queue = Queue.Queue()
        self.mes_response_queue = Queue.Queue()
        self.from_gui_queue = Queue.Queue()
        self.mes_connection = None
        self.screen_and_keyboard = None
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
    
