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
 
def experiment_file_name(experiment_config, folder, extension, name = ''):
    experiment_class_name = str(experiment_config.runnable.__class__).split('.users.')[-1].split('.')[-1].replace('\'', '').replace('>','')
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
    def __init__(self, config, caller, experiment_source = ''):
        self.config = config
        self.caller = caller
        self.from_gui_queue = self.caller.from_gui_queue
        self.devices = Devices(config, caller)
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
            self.experiment_source = self.experiment_source.replace('(experiment.ExperimentConfig)', '{0}(experiment.ExperimentConfig)'.format(int(time.time()))) #avoid name conflict
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
        self.caller.selected_experiment_config = self.caller.experiment_config_list[int(self.caller.command_handler.selected_experiment_config_index)][1](self.config, self.caller)
        #init experiment logging
        self.init_experiment_logging()
        #Create archive files so that user can save data during the experiment
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
                    stage_position = self.devices.stage.read_position() - self.caller.stage_origin
                    objective_position = mes_interface.get_objective_position(self.fragment_mat_path, log = self.log)[0]
                    experiment_data.save_position(fragment_hdf5, stage_position, objective_position)                    
                    setattr(fragment_hdf5, self.fragment_name, data_to_hdf5)
                    fragment_hdf5.save(self.fragment_name)
                    #Here the saved data will be checked and preprocessed
                    self.printl('Prepare data for analysis')
                    mes_extractor = importers.MESExtractor(fragment_hdf5)
                    data_class, stimulus_class, mes_name = mes_extractor.parse()
                    fragment_hdf5.close()
                    #Rename fragment hdf5 so that coorinates are included
                    original_fragment_path = self.fragment_hdf5_path
                    self.fragment_hdf5_path = self.fragment_hdf5_path.replace('fragment_',  'fragment_{0:.1f}_{1:.1f}_{2}_'.format(stage_position[0], stage_position[1], objective_position))
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
            
    def set_mes_t4_back(self):
        result = True
        if self.config.MEASUREMENT_PLATFORM == 'mes' and hasattr(self.caller.selected_experiment_config.runnable, 'fragment_durations'):
            #Set back line scan time to initial 2 sec
            result = False
            self.printl('set back line scan time to 2s')
            time.sleep(0.5)
            mes_interface.set_line_scan_time(2.0, self.parameter_file, self.parameter_file)
            line_scan_start_success, line_scan_path = self.devices.mes_interface.start_line_scan(timeout = 5.0, parameter_file = self.parameter_file)
            if not line_scan_start_success:
                self.printl('setting line scan time to 2 s was NOT successful')
            else:
                line_scan_complete_success =  self.devices.mes_interface.wait_for_line_scan_complete(5.0)
                if line_scan_complete_success:
                    line_scan_save_complete_success =  self.devices.mes_interface.wait_for_line_scan_save_complete(5.0)
                    if line_scan_save_complete_success:
                        result = True
                        os.remove(self.parameter_file) #Parameter file is not used any more
            if not result:
                self.printl('Set t4 back to 2000 ms manually')
        return result
    
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
        self.led_controller = daq_instrument.AnalogPulse(self.config, self.caller, id = 1)#TODO: config shall be analog pulse specific, if daq enabled, this is always called
        self.ai = None        
        self.stage = motor_control.AllegraStage(self.config, self.caller)
        self.mes_interface = mes_interface.MesInterface(self.config, self.caller.mes_connection, self.caller.screen_and_keyboard, self.caller.from_gui_queue)

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
            
class DataHandler(object):
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
        
    def prepare_archive(self):
        #If the archive format is hdf5, zip file is saved to a temporary folder
        if self.config.ARCHIVE_FORMAT == 'zip':
            zip_folder = self.config.EXPERIMENT_DATA_PATH
            self.zip_file_path = experiment_file_name(self.caller.selected_experiment_config, zip_folder, 'zip')
        elif self.config.ARCHIVE_FORMAT == 'hdf5':
            self.zip_file_path = tempfile.mktemp()
            self.hdf5_path = experiment_file_name(self.caller.selected_experiment_config, self.config.EXPERIMENT_DATA_PATH, 'hdf5')
            self.hdf5_handler = hdf5io.Hdf5io(self.hdf5_path , config = self.config, caller = self.caller)
        elif self.config.ARCHIVE_FORMAT == 'mat':
            self.zip_file_path = tempfile.mktemp()
            self.mat_path = experiment_file_name(self.caller.selected_experiment_config, self.config.EXPERIMENT_DATA_PATH, 'mat')
        else:
            raise RuntimeError('Unknown archive format, check configuration!')
        #Create zip file
        self.archive = zipfile.ZipFile(self.zip_file_path, "w")
        
    def archive_software_environment(self, experiment_config = None, stimulus_frame_info = None, experiment_log = ''):
        '''
        Archives the called python modules within visexpman package and the versions of all the called packages
        '''
        #save module version data to file
        module_versions_file_path = os.path.join(os.path.dirname(tempfile.mktemp()),'module_versions.txt')
        f = open(module_versions_file_path, 'wt')
        f.write(self.module_versions)
        f.close()
        if self.config.ARCHIVE_FORMAT == 'zip':
            self.archive.write(module_versions_file_path, module_versions_file_path.replace(os.path.dirname(module_versions_file_path), ''))
        #Save source files
        if len(self.caller.experiment_control.experiment_source)>0 and self.config.ENABLE_UDP and not utils.is_in_list(self.visexpman_module_paths, self.caller.experiment_control.experiment_source_path):
            self.visexpman_module_paths.append(self.caller.experiment_control.experiment_source_path)
        for python_module in self.visexpman_module_paths:
            if 'visexpA' in python_module:
                zip_path = '/visexpA' + python_module.split('visexpA')[-1]
            elif 'visexpman' in python_module:
                zip_path = '/visexpman' + python_module.split('visexpman')[-1]
            if os.path.exists(python_module):
                self.archive.write(python_module, zip_path)
        #include experiment log
        if self.config.ARCHIVE_FORMAT == 'zip':
            self.archive.write(self.caller.experiment_control.logfile_path, self.caller.experiment_control.logfile_path.replace(os.path.dirname(self.caller.experiment_control.logfile_path), ''))
        self.archive.close()
        self.archive_binary_in_bytes = utils.file_to_binary_array(self.zip_file_path)
        self.archive_binary_in_bytes = numpy.array(self.archive_binary_in_bytes, dtype = numpy.uint8)
        if self.config.ARCHIVE_FORMAT == 'hdf5':
            self.hdf5_handler.source_code = self.archive_binary_in_bytes
            self.hdf5_handler.save('source_code')
            self.hdf5_handler.module_versions = self.module_versions
            self.hdf5_handler.save('module_versions')
            self.hdf5_handler.experiment_log = utils.file_to_binary_array(experiment_log)
            self.hdf5_handler.save('experiment_log')
            experiment_data.save_config(self.hdf5_handler, self.config, self.caller.selected_experiment_config)
            self.hdf5_handler.close()
        elif self.config.ARCHIVE_FORMAT == 'mat':
            stimulus_frame_info_with_data_series_index, rising_edges_indexes =\
                    experiment_data.preprocess_stimulus_sync(self.ai_data[:, self.config.SYNC_CHANNEL_INDEX], stimulus_frame_info = stimulus_frame_info)
            mat_to_save = {}
            mat_to_save['ai'] = self.ai_data
            mat_to_save['source_code'] = self.archive_binary_in_bytes
            mat_to_save['module_versions'] = self.module_versions            
            mat_to_save['experiment_log'] = utils.read_text_file(experiment_log)
            mat_to_save['config'] = experiment_data.save_config(None, self.config, experiment_config)
            mat_to_save['rising_edges_indexes'] = rising_edges_indexes
            mat_to_save['stimulus_frame_info'] = stimulus_frame_info_with_data_series_index
            scipy.io.savemat(self.mat_path, mat_to_save, oned_as = 'row', long_field_names=True)
            
        #Restoring it to zip file: utils.numpy_array_to_file(archive_binary_in_bytes, '/media/Common/test.zip')

    def experiment_log_to_string(self, log):
        '''
        --(Transforms experiment log to the following format:)--
        --([[float(timestamp), str(log)]])--
        '''
        log_string = ''
        for log_record in log:  
            log_string += log_record + '\n'
        return log_string

        

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
        shutil.rmtree(self.config.EXPERIMENT_DATA_PATH)

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
    
