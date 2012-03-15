import time
import os.path
import tempfile
import uuid
import hashlib
import scipy.io
import io
import StringIO
import zipfile
import numpy
import inspect
import cPickle as pickle
import traceback
import gc
import shutil

import experiment
import experiment_data
import visexpman.engine.generic.log as log
from visexpman.engine.generic import utils
from visexpman.engine.generic import file
from visexpman.engine.hardware_interface import mes_interface
from visexpman.engine.hardware_interface import instrument
from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.hardware_interface import stage_control

import visexpA.engine.datahandlers.hdf5io as hdf5io
import visexpA.engine.datahandlers.importers as importers

class ExperimentControl(object):
    
    def __init__(self, config, application_log):
        '''
        
        '''
        self.application_log = application_log
        self.config = config
        if not hasattr(self, 'number_of_fragments'):
            self.number_of_fragments = 1
        if not issubclass(self.__class__,experiment.PreExperiment): #In case of preexperiment, fragment durations is not expected
            if self.config.PLATFORM == 'mes' and not hasattr(self, 'fragment_durations'):
                raise RuntimeError('At MES platform self.fragment_durations variable is mandatory')
            if hasattr(self, 'fragment_durations'):
                if not hasattr(self.fragment_durations, 'index') and not hasattr(self.fragment_durations, 'shape'):
                    self.fragment_durations = [self.fragment_durations]
        if self.parameters.has_key('objective_positions'):
            self.objective_positions = map(float, self.parameters['objective_positions'].split('<comma>'))

    def run_experiment(self, context):
        message_to_screen = ''
        if hasattr(self, 'objective_positions'):
            for objective_position in self.objective_positions:
                context['objective_position'] = objective_position
                message_to_screen += self.run_single_experiment(context)
                if self.abort:
                    break
        else:
            message_to_screen = self.run_single_experiment(context)
        return message_to_screen
        
    def run_single_experiment(self, context):
        if context.has_key('stage_origin'):
            self.stage_origin = context['stage_origin']
        message_to_screen = ''
        if not self.connections['mes'].connected_to_remote_client() and self.config.PLATFORM == 'mes':
            message_to_screen = self.printl('No connection with MES')
            return message_to_screen
        message_to_screen += self._prepare_experiment(context)
        message = '{0}/{1} started at {2}' .format(self.experiment_name, self.experiment_config_name, utils.datetime_string())
        message_to_screen += self.printl(message,  application_log = True) + '\n'
        self.finished_fragment_index = 0
        for fragment_id in range(self.number_of_fragments):
            if utils.is_abort_experiment_in_queue(self.queues['gui']['in'], False):
                message_to_screen += self.printl('Experiment aborted',  application_log = True) + '\n'
                self.abort = True
                break
            elif utils.is_graceful_stop_in_queue(self.queues['gui']['in'], False):
                message_to_screen += self.printl('Graceful stop requested',  application_log = True) + '\n'
                break
            elif self._start_fragment(fragment_id):
                    if self.number_of_fragments == 1:
                        self.run()
                    else:
                        self.run(fragment_id)
                    if not self._finish_fragment(fragment_id):
                        self.abort = True
                        break #Do not record further fragments in case of error
            else:
                self.abort = True
                if self.analog_input.finish_daq_activity(abort = utils.is_abort_experiment_in_queue(self.queues['gui']['in'])):
                    self.printl('Analog acquisition finished')
                break
        self._finish_experiment()
        #Send message to screen, log experiment completition
        message_to_screen += self.printl('Experiment finished at {0}' .format(utils.datetime_string()),  application_log = True) + '\n'
        self.application_log.flush()
        return message_to_screen
        
    def _prepare_experiment(self, context):
        message_to_screen = ''
        self.frame_counter = 0
        self.stimulus_frame_info = []
        self.start_time = time.time()
        self.timestamp = str(int(self.start_time))
        self.filenames = {}
        self.initialize_experiment_log()
        self.initialize_devices()
        if self.config.PLATFORM == 'mes':
            if context.has_key('objective_position'):
                if not self.mes_interface.set_objective(context['objective_position'], self.config.MES_TIMEOUT):
                    self.abort = True
                    message_to_screen = 'objective not set'
            #read stage and objective
            self.stage_position = self.stage.read_position() - self.stage_origin
            result,  self.objective_position = self.mes_interface.read_objective_position(timeout = self.config.MES_TIMEOUT)
        self.prepare_files()
        return message_to_screen 
        
    def _finish_experiment(self):
        self.finish_data_fragments()
        self.printl('Closing devices')
        self.close_devices()
        utils.empty_queue(self.queues['gui']['out'])
        #Update logdata to files
        self.log.info('Experiment finished at {0}' .format(utils.datetime_string()))
        self.log.flush()
        

########## Fragment related ############

    def _start_fragment(self, fragment_id):
        self.printl('Start fragment {0}/{1}'. format(fragment_id+1,  self.number_of_fragments))
        self.stimulus_frame_info_pointer = 0
        self.frame_counter = 0
        self.stimulus_frame_info = []
        # Start ai recording
        self.analog_input = daq_instrument.AnalogIO(self.config, self.log, self.start_time)
        if self.analog_input.start_daq_activity():
            self.printl('Analog signal recording started')
        if self.config.PLATFORM == 'mes':
            mes_record_time = self.fragment_durations[fragment_id] + self.config.MES_RECORD_START_DELAY
            utils.empty_queue(self.queues['mes']['in'])
            #start two photon recording
            line_scan_start_success, line_scan_path = self.mes_interface.start_line_scan(scan_time = mes_record_time, 
                parameter_file = self.filenames['mes_fragments'][fragment_id], timeout = self.config.MES_TIMEOUT)
            if line_scan_start_success:
                time.sleep(1.0)
            else:
                self.printl('Line scan start ERROR')
            return line_scan_start_success
        elif self.config.PLATFORM == 'elphys':
            #Set acquisition trigger pin to high
            self.parallel_port.set_data_bit(self.config.ACQUISITION_TRIGGER_PIN, 1)
            return True
        elif self.config.PLATFORM == 'standalone':
            return True
        return False
        
    def _stop_data_acquisition(self, fragment_id):
        '''
        Stops data acquisition processes:
        -analog input sampling
        -waits for mes data acquisition complete
        '''
        #Stop external measurements
        if self.config.PLATFORM == 'elphys':
            #Clear acquisition trigger pin
            self.parallel_port.set_data_bit(self.config.ACQUISITION_TRIGGER_PIN, 0)
            data_acquisition_stop_success = True
        elif self.config.PLATFORM == 'mes':
            self.mes_timeout = 2.0 * self.fragment_durations[fragment_id]            
            if self.mes_timeout < self.config.MES_TIMEOUT:
                self.mes_timeout = self.config.MES_TIMEOUT
            if not utils.is_abort_experiment_in_queue(self.queues['gui']['in']):
                data_acquisition_stop_success =  self.mes_interface.wait_for_line_scan_complete(self.mes_timeout)
                if not data_acquisition_stop_success:
                    self.printl('Line scan complete ERROR')
            else:
                data_acquisition_stop_success =  False
        elif self.config.PLATFORM == 'standalone':
            data_acquisition_stop_success =  True
        #Stop acquiring analog signals
        if self.analog_input.finish_daq_activity(abort = utils.is_abort_experiment_in_queue(self.queues['gui']['in'])):
            self.printl('Analog acquisition finished')
        return data_acquisition_stop_success
        
    def _finish_fragment(self, fragment_id):
        result = True
        aborted = False
        if self._stop_data_acquisition(fragment_id):
            if self.config.PLATFORM == 'mes':
                if not utils.is_abort_experiment_in_queue(self.queues['gui']['in']):
                    self.printl('Wait for data save complete')
                    line_scan_data_save_success = self.mes_interface.wait_for_line_scan_save_complete(self.mes_timeout)
                    self.printl('Data save complete')
                    if not line_scan_data_save_success:
                        self.printl('Line scan data save error')
                else:
                    aborted = True
                    line_scan_data_save_success = False
                result = line_scan_data_save_success
            else:
                pass
            if not aborted:
                self.save_fragment_data(fragment_id)
        else:
            result = False
            self.printl('Data acquisition stopped with error')
        if not aborted:
            self.finished_fragment_index = fragment_id
        return result
    
     ############### Devices ##################
     
    def initialize_devices(self):
        '''
        All the devices are initialized here, that allow rerun like operations
        '''
        self.parallel_port = instrument.ParallelPort(self.config, self.log, self.start_time)
        self.filterwheels = []
        if hasattr(self.config, 'FILTERWHEEL_SERIAL_PORT'):
            self.number_of_filterwheels = len(self.config.FILTERWHEEL_SERIAL_PORT)
        else:
            #If filterwheels neither configured, nor enabled, two virtual ones are created, so that experiments calling filterwheel functions could be called
            self.number_of_filterwheels = 2
        for id in range(self.number_of_filterwheels):
            self.filterwheels.append(instrument.Filterwheel(self.config, self.log, self.start_time, id =id))
        self.led_controller = daq_instrument.AnalogPulse(self.config, self.log, self.start_time, id = 1)#TODO: config shall be analog pulse specific, if daq enabled, this is always called
        self.analog_input = None #This is instantiated at the beginning of each fragment
        self.stage = stage_control.AllegraStage(self.config, self.log, self.start_time)
        if self.config.PLATFORM == 'mes':
            self.mes_interface = mes_interface.MesInterface(self.config, self.queues, self.connections, log = self.log)
        
    def close_devices(self):
        self.parallel_port.release_instrument()
        if self.config.OS == 'win':
            for filterwheel in self.filterwheels:
                filterwheel.release_instrument()
        self.led_controller.release_instrument()
        self.stage.release_instrument()
        
    ############### File handling ##################
    def prepare_files(self):
        self._generate_filenames()
        self._create_files()
        self.stimulus_frame_info_pointer = 0
        
    def _generate_filenames(self):
        ''''
        Generates the necessary filenames for the experiment. The following files are generated during an experiment:
        experiment log file: 
        zipped:
            source code
            module versions
            experiment log
            
        Fragment file name formats:
        1) mes/hdf5: experiment_name_timestamp_fragment_id
        2) elphys/mat: experiment_name_fragment_id_index

        fragment file(s): measurement results, stimulus info, configs, zip
        '''
        self.filenames['fragments'] = []
        self.filenames['local_fragments'] = []#fragment files are first saved to a local, temporary file
        self.filenames['mes_fragments'] = []
        self.fragment_names = []
        for fragment_id in range(self.number_of_fragments):
            if self.config.EXPERIMENT_FILE_FORMAT == 'mat':
                fragment_name = 'fragment_{0}' .format(self.experiment_name)
            elif self.config.EXPERIMENT_FILE_FORMAT == 'hdf5':
                fragment_name = 'fragment_{0}_{1}_{2}' .format(self.experiment_name, self.timestamp, fragment_id)
            fragment_filename = os.path.join(self.config.EXPERIMENT_DATA_PATH, '{0}.{1}' .format(fragment_name, self.config.EXPERIMENT_FILE_FORMAT))
            if self.config.EXPERIMENT_FILE_FORMAT  == 'hdf5' and  self.config.PLATFORM == 'mes':
                if hasattr(self, 'objective_position'):
                    if self.parameters.has_key('region_name'):
                        fragment_filename = fragment_filename.replace('fragment_', 
                        'fragment_{0}_{1}_'.format(self.parameters['region_name'], self.objective_position))
                    elif hasattr(self, 'stage_position'):
                        fragment_filename = fragment_filename.replace('fragment_', 
                        'fragment_{0:.1f}_{1:.1f}_{2}_'.format(self.stage_position[0], self.stage_position[1], self.objective_position))
                self.filenames['mes_fragments'].append(fragment_filename.replace('hdf5', 'mat'))
            elif self.config.EXPERIMENT_FILE_FORMAT == 'mat' and self.config.PLATFORM == 'elphys':
                fragment_filename = file.generate_filename(fragment_filename, last_tag = str(fragment_id))
            local_fragment_file_name = os.path.join(tempfile.mkdtemp(), os.path.split(fragment_filename)[-1])
            self.filenames['local_fragments'].append(local_fragment_file_name)
            self.filenames['fragments'].append(fragment_filename )
            self.fragment_names.append(fragment_name.replace('fragment_', ''))

    def _create_files(self):
        self.fragment_files = []
        self.fragment_data = {}
        for fragment_file_name in self.filenames['local_fragments']:
            if self.config.EXPERIMENT_FILE_FORMAT  == 'hdf5':
                self.fragment_files.append(hdf5io.Hdf5io(fragment_file_name))
        if self.config.EXPERIMENT_FILE_FORMAT  == 'mat':
            pass

    def initialize_experiment_log(self):
        date = utils.date_string()
        self.filenames['experiment_log'] = \
            file.generate_filename(os.path.join(self.config.EXPERIMENT_LOG_PATH, 'log_{0}_{1}.txt' .format(self.experiment_name, date)))
        self.log = log.Log('experiment log' + uuid.uuid4().hex, self.filenames['experiment_log'], write_mode = 'user control', timestamp = 'elapsed_time')

    ########## Fragment data ############
    def _prepare_fragment_data(self, fragment_id):
        if hasattr(self.analog_input, 'ai_data'):
            analog_input_data = self.analog_input.ai_data
        else:
            analog_input_data = numpy.zeros((2, 2))
            self.printl('Analog input data is not available')
        stimulus_frame_info_with_data_series_index, rising_edges_indexes =\
                            experiment_data.preprocess_stimulus_sync(\
                            analog_input_data[:, self.config.SYNC_CHANNEL_INDEX], 
                            stimulus_frame_info = self.stimulus_frame_info[self.stimulus_frame_info_pointer:])
        if not hasattr(self, 'experiment_specific_data'):
                self.experiment_specific_data = 0
        if hasattr(self, 'source_code'):
            experiment_source = self.source_code
        else:
            experiment_source = utils.file_to_binary_array(inspect.getfile(self.__class__).replace('.pyc', '.py'))
        data_to_file = {
                                    'sync_data' : analog_input_data, 
                                    'current_fragment' : fragment_id, #deprecated
                                    'actual_fragment' : fragment_id,
                                    'rising_edges_indexes' : rising_edges_indexes, 
                                    'number_of_fragments' : self.number_of_fragments, 
                                    'generated_data' : self.experiment_specific_data, 
                                    'experiment_source' : experiment_source, 
                                    }
        if self.config.EXPERIMENT_FILE_FORMAT == 'hdf5':
            stimulus_frame_info = {}
            if stimulus_frame_info_with_data_series_index != 0:
                stimulus_frame_info = self.stimulus_frame_info
            if self.config.PLATFORM == 'mes':
                time.sleep(0.5+0.1 * 1e-6 * os.path.getsize(self.filenames['mes_fragments'][fragment_id])) #Wait till data write complete
                try:
                    #Maybe a local copy should be made:
                    tmp_mes_file = tempfile.mktemp()
                    shutil.copy(self.filenames['mes_fragments'][fragment_id], tmp_mes_file)
                    mes_data = utils.file_to_binary_array(tmp_mes_file)
                except:
                    self.printl(traceback.format_exc())
                    mes_data = numpy.zeros((2, 1), dtype = numpy.uint8)
                data_to_file['mes_data'] = mes_data
                data_to_file['mes_data_hash'] = hashlib.sha1(mes_data).hexdigest()
        elif self.config.EXPERIMENT_FILE_FORMAT == 'mat':
            stimulus_frame_info = stimulus_frame_info_with_data_series_index
        data_to_file['stimulus_frame_info'] = stimulus_frame_info
        self.stimulus_frame_info_pointer = len(self.stimulus_frame_info)
        return data_to_file
            
    def save_fragment_data(self, fragment_id):
        data_to_file = self._prepare_fragment_data(fragment_id)
        if self.config.EXPERIMENT_FILE_FORMAT == 'hdf5':
            experiment_data.save_config(self.fragment_files[fragment_id], self.config, self.experiment_config)
            #Save stage and objective position
            if self.config.PLATFORM == 'mes':
                experiment_data.save_position(self.fragment_files[fragment_id], self.stage_position, self.objective_position)
            setattr(self.fragment_files[fragment_id], self.fragment_names[fragment_id], data_to_file)
            self.fragment_files[fragment_id].save(self.fragment_names[fragment_id])
            if hasattr(self, 'fragment_durations'):
                time.sleep(1.0 + 0.05 * self.fragment_durations[fragment_id])#Wait till data is written to disk
            else:
                time.sleep(1.0)
        elif self.config.EXPERIMENT_FILE_FORMAT == 'mat':
            self.fragment_data[self.filenames['local_fragments'][fragment_id]] = data_to_file
        del data_to_file
        self.printl('Measurement data saved to: {0}'.format(self.filenames['fragments'][fragment_id]))

    def finish_data_fragments(self):
        #Experiment log, source code, module versions
        software_environment = self._pack_software_environment()
        experiment_log_dict = self.log.log_dict
        if self.config.EXPERIMENT_FILE_FORMAT == 'hdf5':
            for fragment_file in self.fragment_files[0:self.finished_fragment_index +1]:
                fragment_file.software_environment = software_environment
                fragment_file.experiment_log = numpy.fromstring(pickle.dumps(experiment_log_dict), numpy.uint8)
                fragment_file.save(['software_environment', 'experiment_log'])
                fragment_file.close()
            for fragment_file in self.fragment_files[self.finished_fragment_index :]:
                fragment_file.close()
        elif self.config.EXPERIMENT_FILE_FORMAT == 'mat':
            for fragment_path, data_to_mat in self.fragment_data.items():
                data_to_mat['software_environment'] = software_environment
                data_to_mat['experiment_log_dict'] = experiment_log_dict
                data_to_mat['config'] = experiment_data.save_config(None, self.config, self.experiment_config)
                scipy.io.savemat(fragment_path, data_to_mat, oned_as = 'row', long_field_names=True)
        #Check all the fragments
        self.printl('Check measurement data')
        self.fragment_check_result = True
        for fragment_file in self.filenames['local_fragments'][0:self.finished_fragment_index +1]:
            if os.path.exists(fragment_file):
                try:
                    result, self.fragment_error_messages = experiment_data.check_fragment(fragment_file, self.config)
                except:
                    result = False
                    self.fragment_error_messages = traceback.format_exc()
                if not result:
                    self.fragment_check_result = result
                    self.printl('Incorrect fragment file: ' + str(self.fragment_error_messages))
        for fid in range(len(self.filenames['local_fragments'][0:self.finished_fragment_index +1])):
            if os.path.exists(self.filenames['local_fragments'][fid]):
                shutil.copy(self.filenames['local_fragments'][fid], self.filenames['fragments'][fid])

    def _pack_software_environment(self):
        software_environment = {}
        module_names, visexpman_module_paths = utils.imported_modules()
        module_versions, software_environment['module_version'] = utils.module_versions(module_names)
        stream = io.BytesIO()
        stream = StringIO.StringIO()
        zipfile_handler = zipfile.ZipFile(stream, 'a')
        for module_path in visexpman_module_paths:
            if 'visexpA' in module_path:
                zip_path = '/visexpA' + module_path.split('visexpA')[-1]
            elif 'visexpman' in module_path:
                zip_path = '/visexpman' + module_path.split('visexpman')[-1]
            if os.path.exists(module_path):
                zipfile_handler.write(module_path, zip_path)
        software_environment['source_code'] = numpy.fromstring(stream.getvalue(), dtype = numpy.uint8)
        zipfile_handler.close()
        return software_environment

    ############### Helpers ##################
    def _get_elapsed_time(self):
        return time.time() - self.start_time

    def printl(self, message,  application_log = False, experiment_log = True):
        '''
        Helper function that can be called during experiment. The message is sent to:
        -standard output
        -gui
        -experiment log
        '''
        print message
        self.queues['gui']['out'].put(str(message))
        if application_log:
            self.application_log.info(message)
        if hasattr(self, 'log') and experiment_log:
            self.log.info(str(message))
        return message
