import visexpA.engine.datahandlers.hdf5io as hdf5io
from visexpman.engine.generic import utils
import copy
import numpy
import scipy.io

############### Preprocess measurement data ####################
def preprocess_stimulus_sync(sync_signal, stimulus_frame_info = None):
    #Find out high and low voltage levels
    histogram, bin_edges = numpy.histogram(sync_signal, bins = 20)
    if histogram.max() == histogram[0] or histogram.max() == histogram[-1]:
        low_voltage_level = 0.5 * (bin_edges[0] + bin_edges[1])
        high_voltage_level = 0.5 * (bin_edges[-1] + bin_edges[-2])
    else:
#        raise RuntimeError('Sync signal is not binary')
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
        file_handle.save('machine_config')
        file_handle.experiment_config = experiment_config.get_all_parameters()
        file_handle.save('experiment_config')
    elif file_handle == None:
        config = {}
        config['machine_config'] = copy.deepcopy(machine_config.get_all_parameters())
        config['experiment_config'] = experiment_config.get_all_parameters()
        return config
        
    
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

