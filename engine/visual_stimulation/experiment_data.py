import visexpA.engine.datahandlers.hdf5io as hdf5io
from visexpman.engine.generic import utils
import copy
import numpy
import scipy.io
import cPickle as pickle
import unittest

def experiment_file_name(experiment_config, folder, extension, name = ''):
    experiment_class_name = str(experiment_config.runnable.__class__).split('.users.')[-1].split('.')[-1].replace('\'', '').replace('>','')
    if name == '':
        name_ = ''
    else:
        name_ = name + '_'
    experiment_file_path = utils.generate_filename(os.path.join(folder, name_ + experiment_class_name + '_' + utils.date_string() + '.' + extension))
    return experiment_file_path
    
def prepare_archive(config, selected_experiment_config):
    '''
    Prepares source code zip file and experiment data file if hdf5io is the archive format
    '''
    #If the archive format is hdf5, zip file is saved to a temporary folder
    #TODO: why cant we do it at the end????
    if self.config.ARCHIVE_FORMAT == 'zip':
        zip_folder = config.EXPERIMENT_DATA_PATH
        zip_file_path = experiment_file_name(selected_experiment_config, zip_folder, 'zip')
        data_file = None
    elif self.config.ARCHIVE_FORMAT == 'hdf5':
        zip_file_path = tempfile.mktemp()
        hdf5_path = experiment_file_name(selected_experiment_config, config.EXPERIMENT_DATA_PATH, 'hdf5')
        data_file = hdf5io.Hdf5io(hdf5_path)
    elif self.config.ARCHIVE_FORMAT == 'mat':
        zip_file_path = tempfile.mktemp()
        data_file = experiment_file_name(selected_experiment_config, config.EXPERIMENT_DATA_PATH, 'mat')
    else:
        raise RuntimeError('Unknown archive format, check configuration!')
    #Create zip file
    archive = zipfile.ZipFile(zip_file_path, "w")
    return archive, data_file
        
def archive_software_environment(self, machine_config, experiment_config, archive, experiment_source, experiment_source_path, experiment_logfile_path, data_file, ai_data = None, stimulus_frame_info = None, experiment_log = ''):
    '''
    Archives the called python modules within visexpman package and the versions of all the called packages
    '''
    #save module version data to file
    module_versions_file_path = os.path.join(os.path.dirname(tempfile.mktemp()),'module_versions.txt')
    f = open(module_versions_file_path, 'wt')
    f.write(self.module_versions)
    f.close()
    if machine_config.ARCHIVE_FORMAT == 'zip':
        archive.write(module_versions_file_path, module_versions_file_path.replace(os.path.dirname(module_versions_file_path), ''))
    #Save source files
    if len(experiment_source)>0 and machine_config.ENABLE_UDP and not utils.is_in_list(self.visexpman_module_paths, experiment_source_path):
        self.visexpman_module_paths.append(experiment_source_path)
    for python_module in self.visexpman_module_paths:
        if 'visexpA' in python_module:
            zip_path = '/visexpA' + python_module.split('visexpA')[-1]
        elif 'visexpman' in python_module:
            zip_path = '/visexpman' + python_module.split('visexpman')[-1]
        if os.path.exists(python_module):
            archive.write(python_module, zip_path)
    #include experiment log
    if machine_config.ARCHIVE_FORMAT == 'zip':
        archive.write(experiment_logfile_path, experiment_logfile_path.replace(os.path.dirname(experiment_logfile_path), '')) #os.path.split
        archive.close()
    archive_binary_in_bytes = utils.file_to_binary_array(archive.filename)
    archive_binary_in_bytes = numpy.array(archive_binary_in_bytes, dtype = numpy.uint8)
    if machine_config.ARCHIVE_FORMAT == 'hdf5':
        data_file.source_code = self.archive_binary_in_bytes
        data_file.save('source_code')
        data_file.module_versions = self.module_versions
        data_file.save('module_versions')
        data_file.experiment_log = utils.file_to_binary_array(experiment_logfile_path)
        data_file.save('experiment_log')
        experiment_data.save_config(data_file, machine_config, self.caller.selected_experiment_config)
        data_file.close()
    elif machine_config.ARCHIVE_FORMAT == 'mat':
        stimulus_frame_info_with_data_series_index, rising_edges_indexes =\
                experiment_data.preprocess_stimulus_sync(ai_data[:, self.config.SYNC_CHANNEL_INDEX], stimulus_frame_info = stimulus_frame_info)
        mat_to_save = {}
        mat_to_save['ai'] = ai_data
        mat_to_save['source_code'] = archive_binary_in_bytes
        mat_to_save['module_versions'] = self.module_versions            
        mat_to_save['experiment_log'] = utils.read_text_file(experiment_logfile_path)
        mat_to_save['config'] = experiment_data.save_config(None, machine_config, experiment_config)
        mat_to_save['rising_edges_indexes'] = rising_edges_indexes
        mat_to_save['stimulus_frame_info'] = stimulus_frame_info_with_data_series_index
        scipy.io.savemat(data_file, mat_to_save, oned_as = 'row', long_field_names=True)
            
        #Restoring it to zip file: utils.numpy_array_to_file(archive_binary_in_bytes, '/media/Common/test.zip')

############### Preprocess measurement data ####################
def preprocess_stimulus_sync(sync_signal, stimulus_frame_info = None):
    #Find out high and low voltage levels
    histogram, bin_edges = numpy.histogram(sync_signal, bins = 20)
    if histogram.max() == histogram[0] or histogram.max() == histogram[-1]:
        low_voltage_level = 0.5 * (bin_edges[0] + bin_edges[1])
        high_voltage_level = 0.5 * (bin_edges[-1] + bin_edges[-2])
    else:
        print 'Sync signal is not binary'
        return None, None
    threshold = 0.5 * (low_voltage_level + high_voltage_level)
    #detect sync signal rising edges
    binary_sync = numpy.where(sync_signal < threshold, 0, 1)
    rising_edges = numpy.where(numpy.diff(binary_sync) > 0, 1, 0)
    rising_edges_indexes = numpy.nonzero(rising_edges)[0] + 1
    stimulus_frame_info_with_data_series_index = []
    if stimulus_frame_info != None:
        for stimulus_item in stimulus_frame_info:
            info = stimulus_item
            try:
                info['data_series_index'] = rising_edges_indexes[info['counter']]
            except IndexError:
                #less pulses detected
                info['data_series_index'] = -1
                print 'less trigger pulses were detected'
            stimulus_frame_info_with_data_series_index.append(info)
    return stimulus_frame_info_with_data_series_index, rising_edges_indexes

#################### Saving/loading data to hdf5 ####################
def save_config(file_handle, machine_config, experiment_config = None):
    if hasattr(file_handle, 'save'):
        file_handle.machine_config = copy.deepcopy(machine_config.get_all_parameters()) #The deepcopy is necessary to avoid conflict between daqmx and hdf5io        
        file_handle.experiment_config = experiment_config.get_all_parameters()
        #pickle configs
        file_handle.machine_config_pickled = pickle_config(machine_config)
        file_handle.experiment_config_pickled = pickle_config(experiment_config)
        file_handle.save(['experiment_config', 'machine_config', 'experiment_config_pickled', 'machine_config_pickled'])
    elif file_handle == None:
        config = {}
        config['machine_config'] = copy.deepcopy(machine_config.get_all_parameters())
        config['experiment_config'] = experiment_config.get_all_parameters()
        return config
        
def pickle_config(config):
    config_modified = copy.copy(config)
    if hasattr(config_modified, 'caller'):
        config_modified.caller = None
    if hasattr(config_modified, 'machine_config'):
        config_modified.machine_config = None
    if hasattr(config_modified, 'runnable'):
        config_modified.runnable = config_modified.runnable.__class__.__name__
    if hasattr(config_modified, 'pre_runnable'):
        config_modified.pre_runnable = config_modified.pre_runnable.__class__.__name__
    return utils.string_to_binary_array(pickle.dumps(config_modified))
    
def save_position(hdf5, stagexyz, objective_z = None):
    '''
    z is the objective's position, since this is more frequently used than z_stage.
    '''
    hdf5.position = utils.pack_position(stagexyz, objective_z)
    hdf5.save('position')
    
def read_master_position(path):
        hdf5_handler = hdf5io.Hdf5io(path)
        master_position = {}
        if hdf5_handler.findvar('master_position') != None:
            master_position = hdf5_handler.master_position
        hdf5_handler.close()
        return master_position

#def map_from_regions    
    
    
class TestDataHandler(unittest.TestCase):
    def setUp(self):
        module_info = utils.imported_modules()
        self.visexpman_module_paths  = module_info[1]
        self.module_versions = utils.module_versions(module_info[0])
        from visexpman.users.zoltan import automated_test_data
        self.config = automated_test_data.VerySimpleExperimentTestConfig()
        self.dh = DataHandler(self.config, self)

    def test_01_DataHandler_contructor(self):
        pass

    def tearDown(self):
        pass
