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
    expected_top_level_nodes = ['call_parameters']
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
        'sync_data', 'actual_fragment',  'current_fragment', 'experiment_source', 'experiment_log', 'software_environment', \
        'laser_intensity', 'prepost_scan_image', 'experiment_config', 'machine_config', 'animal_parameters']
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
    
def read_merge_rois(cells, cell_group, region_name, objective_position, objective_origin, z_range, merge_distance):
    '''
    Reads rois of selected group, performs filtering based on objective position and merge distance
    '''
    if not cells.has_key(region_name):
        return None, None
    roi_locations = []
    roi_locations_rcd = []
    rois = []
    for cell in cells[region_name].values():
        #Calculate minimal distance of current cell from all the already selected cells
        distances = [abs(utils.rc_distance(roi_location, cell['roi_center'], rc_distance_only = True)) for roi_location in roi_locations_rcd]
        if cell['depth'] > objective_position - 0.5 * z_range and cell['depth'] < objective_position + 0.5 * z_range\
        and cell['group'] == cell_group and cell['accepted']:
            if len(distances) == 0 or min(distances) > merge_distance:
                rois.append(cell)
                roi_locations.append(utils.nd(cell['roi_center'])[0])
                roi_locations_rcd.append(cell['roi_center'])
            else:
                #find indexes
                merge_to_index = ((numpy.array(distances)<merge_distance).tolist()).index(True)
                if not rois[merge_to_index].has_key('merged_rois'):
                    rois[merge_to_index]['merged_rois'] = []
                rois[merge_to_index]['merged_rois'].append(cell)
    if len(roi_locations) == 0:
        return None, None
    else:
        roi_locations = utils.rcd(numpy.array(roi_locations))
        roi_locations['depth'] = objective_position + objective_origin
        return roi_locations, rois
        
def add_auxiliary_rois(rois, roi_pattern_size, objective_position, objective_origin, aux_roi_distance = None, soma_size_ratio = None):
    '''
    aux_roi_distance: fixed distance from soma center
    soma_size_ratio: distance from soma center as fraction of longer radius of soma
    '''
    debug = False
    if debug:
        im = numpy.zeros((1000, 1000, 3),  dtype = numpy.uint8)
    expanded_rois = []
    for roi in rois:
        if debug:
            im[roi['soma_roi']['row'], roi['soma_roi']['col'], :] = 128
        #Center
        roi_center_in_pixels = utils.rc((roi['soma_roi']['row'].mean(), roi['soma_roi']['col'].mean()))        
        #Find two furthest point
        max_distance = 0
        for i in range(roi['soma_roi'].shape[0]):
            for j in range(i, roi['soma_roi'].shape[0]):
                distance = utils.rc_distance(roi['soma_roi'][i], roi['soma_roi'][j])
                if distance > max_distance:
                    max_distance = distance
                    furthest_points = [i, j]
        #"direction" of soma
        point1 = roi['soma_roi'][furthest_points[0]]
        point2 = roi['soma_roi'][furthest_points[1]]
        direction = numpy.arctan2(float(point1['row']-point2['row']), float(point1['col']-point2['col']))
        #Pick from the furthest points the one which distance from roi center is bigger
        if abs(utils.rc_distance(roi_center_in_pixels, point1)) > abs(utils.rc_distance(roi_center_in_pixels, point2)):
            point = point1
        else:
            point = point2
        #determine  point halfway between center and picked point
        if soma_size_ratio is not None:
            aux_roi_distance_pix = soma_size_ratio * utils.rc_distance(roi_center_in_pixels, point)
        else:
            aux_roi_distance_pix = aux_roi_distance / roi['scale']['row']
        roi_to_add = copy.deepcopy(roi)
        roi_to_add['auxiliary'] = False
        expanded_rois.append(roi_to_add)
        if roi_pattern_size == 3:
            angles = [0, numpy.pi/2]
        else:
            angles = numpy.linspace(0, numpy.pi*2, roi_pattern_size)[:-1]
        for angle in angles:
            aux_roi_pix = utils.rc((roi_center_in_pixels['row'] - aux_roi_distance_pix * numpy.sin(direction + angle),
                                     roi_center_in_pixels['col'] - aux_roi_distance_pix * numpy.cos(direction + angle)))
            aux_roi = utils.pixel2um(aux_roi_pix, roi['origin'], roi['scale'])
            roi_to_add = copy.deepcopy(roi)
            roi_to_add['auxiliary'] = True
            roi_to_add['roi_center'] = utils.rcd((aux_roi['row'][0], aux_roi['col'][0], roi['roi_center']['depth']))
            expanded_rois.append(roi_to_add)
            if debug:
                im[int(numpy.round(aux_roi_pix['row'], 0)), int(numpy.round(aux_roi_pix['col'], 0)), 1] = 255
        if debug:
            im[int(roi_center_in_pixels['row']), int(roi_center_in_pixels['col']), :] = 255
    if debug:
        import Image
#        im = im[100:, 100:, :]
        im = Image.fromarray(im)
        try:
            im.save('/mnt/datafast/debug/somaroi.png')
        except:
            im.save('v:\\debug\\somaroi.png')
        pass
    return rois_to_roi_locations(expanded_rois, objective_position, objective_origin), expanded_rois
        
def rois_to_roi_locations(rois, objective_position, objective_origin):
    roi_locations = []
    for roi in rois:
        roi_locations.append(utils.nd(roi['roi_center'])[0])
    roi_locations = utils.rcd(numpy.array(roi_locations))
    roi_locations['depth'] = objective_position + objective_origin
    return roi_locations
   
   
class TestExperimentData(unittest.TestCase):
#    @unittest.skip("")
    def test_01_read_merge_rois(self):
        path = '/mnt/databig/testdata/read_merge_rois/mouse_test_1-1-2012_1-1-2012_0_0.hdf5'
        cells = hdf5io.read_item(path, 'cells')
        roi_locations, rois = read_merge_rois(cells, 'g2', 'scanned_2vessels_0_0', -130, 0, 80, 4)
        roi_locations, rois = add_auxiliary_rois(rois, 9, -130, -100, aux_roi_distance = 5.0)
        pass
        
if __name__=='__main__':
    unittest.main()
        
    
    
    
    
