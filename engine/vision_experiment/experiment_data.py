import os
import copy
import numpy
import scipy.io
import cPickle as pickle
import unittest
import hashlib
import string
import shutil
import tempfile

from visexpman.engine.generic import utils
from visexpman.engine import generic
from visexpA.engine.datahandlers import hdf5io
from visexpA.engine.dataprocessors import generic as gen

import unittest

############### Preprocess measurement data ####################
def preprocess_stimulus_sync(sync_signal, stimulus_frame_info = None,  sync_signal_min_amplitude = 1.5):
    #Find out high and low voltage levels
    histogram, bin_edges = numpy.histogram(sync_signal, bins = 20)
    if histogram.max() == histogram[0] or histogram.max() == histogram[-1]:
        pulses_detected = True
        low_voltage_level = 0.5 * (bin_edges[0] + bin_edges[1])
        high_voltage_level = 0.5 * (bin_edges[-1] + bin_edges[-2])
#        print high_voltage_level - low_voltage_level
        if high_voltage_level - low_voltage_level  < sync_signal_min_amplitude:
            pulses_detected = False
            return stimulus_frame_info, 0, pulses_detected
    else:
        pulses_detected = False
        return stimulus_frame_info, 0, pulses_detected
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
    return stimulus_frame_info_with_data_series_index, rising_edges_indexes, pulses_detected

#################### Saving/loading data to hdf5 ####################
def save_config(file_handle, machine_config, experiment_config = None):
    if hasattr(file_handle, 'save'):
        if 0:
            file_handle.machine_config = copy.deepcopy(machine_config.get_all_parameters()) #The deepcopy is necessary to avoid conflict between daqmx and hdf5io        
            file_handle.experiment_config = experiment_config.get_all_parameters()
        #pickle configs
        file_handle.machine_config = pickle_config(machine_config)
        file_handle.experiment_config = pickle_config(experiment_config)
        file_handle.save(['experiment_config', 'machine_config'])#, 'experiment_config_pickled', 'machine_config_pickled'])
    elif file_handle == None:
        config = {}
        config['machine_config'] = copy.deepcopy(machine_config.get_all_parameters())
        config['experiment_config'] = experiment_config.get_all_parameters()
        return config
        
def pickle_config(config):
    config_modified = copy.copy(config)
    if hasattr(config_modified, 'connections'):
        config_modified.connections = 0
    if hasattr(config_modified, 'application_log'):
        config_modified.application_log = 0
    if hasattr(config_modified, 'machine_config'):
        config_modified.machine_config = 0
    if hasattr(config_modified, 'runnable'):
        config_modified.runnable = config_modified.runnable.__class__.__name__
    if hasattr(config_modified, 'pre_runnable'):
        config_modified.pre_runnable = config_modified.pre_runnable.__class__.__name__
    if hasattr(config_modified, 'queues'):
        config_modified.queues = 0
    return numpy.fromstring(pickle.dumps(config_modified), numpy.uint8)
    
def save_position(hdf5, stagexyz, objective_z = None):
    '''
    z is the objective's position, since this is more frequently used than z_stage.
    '''
    hdf5.position = utils.pack_position(stagexyz, objective_z)
    hdf5.save('position')

def check_fragment(path, fragment_hdf5_handle = None):#TODO: Move to importers
    messages = []
    result = True
    data_node_name =  os.path.split(path)[-1].replace('.hdf5', '').split('_')
    data_node_name = data_node_name[-3:]
    data_node_name = string.join(data_node_name).replace(' ', '_')
    expected_top_level_nodes = ['experiment_config', 'machine_config', 'call_parameters']
    expected_top_level_nodes.append('position')
    expected_top_level_nodes.append(data_node_name)
    import time
#        time.sleep(10.0)#TMP, to be removed
    if fragment_hdf5_handle == None:
        fragment_handle = hdf5io.Hdf5io(path)
    else:
        fragment_handle = fragment_hdf5_handle
    nodes = fragment_handle.findvar(expected_top_level_nodes)
    if None in nodes:
        result = False
        messages.append('Top level node missing: {0}'.format(expected_top_level_nodes[nodes.index(None)]))
    hdf5_data_dict = {}
    for i in range(len(nodes)):
        node = nodes[i]
        node_name = expected_top_level_nodes[i]
        if node_name == 'software_environment':
            if not hasattr(node, 'keys'):
                result = False
                messages.append('unexpected data type in software_environment')
            elif not (node.has_key('source_code') and node.has_key('module_version')):
                result = False
                messages.append('unexpected data in software_environment')
        elif node_name == 'position':
            if not hasattr(node, 'dtype'):
                result = False
                messages.append('position data is in unexpected format')
        elif node_name == 'experiment_config' or node_name == 'machine_config':
            if not hasattr(node,  'dtype'):
                result = False
                messages.append('unexpected data type in {0}'.format(node_name))
        elif node_name == 'experiment_log_dict':
            if not hasattr(node,  'keys'):
                result = False
                messages.append('unexpected data type in {0}'.format(node_name))
        elif node_name == expected_top_level_nodes[-1]:
            expected_subnodes = ['rising_edges_indexes', 'number_of_fragments', 'stimulus_frame_info', 'generated_data', \
        'sync_data', 'actual_fragment',  'current_fragment', 'experiment_source', 'experiment_log', 'software_environment']#, 'laser_intensity']
            if not hasattr(node,  'has_key'):
                result = False
                messages.append('unexpected data type in {0}'.format(node_name))
            elif numpy.array(map(node.has_key, expected_subnodes)).sum() != len(expected_subnodes):
                result = False
                messages.append('unexpected number of datafields in {0}, {1}'.format(node_name,  map(node.has_key, expected_subnodes)))
            if 'MovingDot' in node_name and not node['generated_data'].has_key('shown_directions'):
                result = False
                messages.append('Shown directions are not saved {0}'.format(node['generated_data']))
    if fragment_hdf5_handle == None:
        fragment_handle.close()
    return result, messages
    
def read_rois(cells, cell_group, region_name, objective_position, z_range):
    rois = []
    for cell in cells[region_name].values():
        if cell['depth'] > objective_position - 0.5 * z_range and cell['depth'] < objective_position + 0.5 * z_range and cell['group'] ==cell_group:
            rois.append(utils.nd(cell['roi_center']))
    if len(rois) == 0:
        return None
    else:
        rois = utils.rcd(numpy.array(rois)[:, 0, :])
        return rois
            
def merge_cell_locations(cell_locations, merge_distance, xy_distance_only = False):
    if cell_locations != None:
        filtered_cell_locations = []
        for i in range(cell_locations.shape[0]):
            keep_cell = True
            for j in range(i+1, cell_locations.shape[0]):
                if abs(utils.rc_distance(cell_locations[i], cell_locations[j], rc_distance_only = xy_distance_only)) < merge_distance:
                    keep_cell = False
            if keep_cell:
                cell = cell_locations[i]
                filtered_cell_locations.append((cell['row'], cell['col'], cell['depth']))
        filtered_cell_locations = utils.rcd(numpy.array(filtered_cell_locations))
        return filtered_cell_locations

   
class TestExperimentData(unittest.TestCase):
    def test_01_read_merge_rois(self):
        cell_locations = read_rois('/mnt/rzws/debug/data/rois_test1_1-1-2012_1-1-2012_0_0.hdf5', 'r_0_0', objective_position = 0.0, z_range = 100.0, mouse_file = '/mnt/rzws/debug/data/mouse_test1_1-1-2012_1-1-2012_0_0.hdf5')
        cell_locations = merge_cell_locations(cell_locations, 10, True)
if __name__=='__main__':
    unittest.main()
        
    
    
    
    
