import os
import copy
import numpy
import scipy.io
import cPickle as pickle
import unittest
import hashlib
import string

from visexpman.engine.generic import utils
from visexpman.engine import generic
from visexpA.engine.datahandlers import hdf5io
from visexpA.engine.dataprocessors import generic as gen


############### Preprocess measurement data ####################
def preprocess_stimulus_sync(sync_signal, stimulus_frame_info = None):
    #Find out high and low voltage levels
    histogram, bin_edges = numpy.histogram(sync_signal, bins = 20)
    if histogram.max() == histogram[0] or histogram.max() == histogram[-1]:
        low_voltage_level = 0.5 * (bin_edges[0] + bin_edges[1])
        high_voltage_level = 0.5 * (bin_edges[-1] + bin_edges[-2])
    else:
        print 'Sync signal is not binary'
        return stimulus_frame_info, 0
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

def check_fragment(path, config):
    messages = []
    result = True
    if config.EXPERIMENT_FILE_FORMAT == 'mat':
        expected_top_level_nodes = ['rising_edges_indexes', 'number_of_fragments', 'stimulus_frame_info', 'generated_data', \
            'experiment_log_dict', 'sync_data', 'actual_fragment', 'config', 'current_fragment', 'experiment_source', 'software_environment']
        mat_data = scipy.io.loadmat(path, mat_dtype = True)
        if numpy.array(map(mat_data.has_key,expected_top_level_nodes)).sum() != len(expected_top_level_nodes):
            messages.append('Top level node missing')
            result = False
        else:
            #TODO: Here comes the check of the subnodes and its contents
            pass
    elif config.EXPERIMENT_FILE_FORMAT == 'hdf5':
        data_node_name =  os.path.split(path)[-1].replace('.hdf5', '').split('_')
        if config.PLATFORM == 'mes':
            data_node_name = data_node_name[4:]
        else:
            data_node_name = data_node_name[1:]
        data_node_name = string.join(data_node_name).replace(' ', '_')
        expected_top_level_nodes = ['experiment_config', 'machine_config', 'experiment_config_pickled', 'machine_config_pickled', 'experiment_log', \
                                    'software_environment']
        if config.PLATFORM == 'mes':
            expected_top_level_nodes.append('position')
        expected_top_level_nodes.append(data_node_name)
        fragment_handle = hdf5io.Hdf5io(path)
        nodes = fragment_handle.findvar(expected_top_level_nodes)
        if None in nodes:
            result = False
            messages.append('Top level node missing: {0}'.format(expected_top_level_nodes[nodes.index(None)]))
        hdf5_data_dict = {}
        for i in range(len(nodes)):
            node = nodes[i]
            node_name = expected_top_level_nodes[i]
            if node_name == 'software_environment':
                #TODO: check the source code content
                if not hasattr(node, 'keys'):
                    result = False
                    messages.append('unexpected data type in software_environment')
                elif not (node.has_key('source_code') and node.has_key('module_version')):
                    result = False
                    messages.append('unexpected data in software_environment')
            elif node_name == 'position':
                pass#TODO: check it
            elif node_name == 'experiment_config' or node_name == 'machine_config':
                if not hasattr(node, 'keys'):
                    result = False
                    messages.append('unexpected data type in {0}'.format(node_name))
                elif not (node.has_key('OS') and node.has_key('PACKAGE_PATH')):
                    result = False
                    messages.append('unexpected data in {0}'.format(node_name))
            elif node_name == 'experiment_config_pickled' or node_name == 'machine_config_pickled':
                if not hasattr(node,  'dtype'):
                    result = False
                    messages.append('unexpected data type in {0}'.format(node_name))
            elif node_name == 'experiment_log_dict':
                if not hasattr(node,  'keys'):
                    result = False
                    messages.append('unexpected data type in {0}'.format(node_name))
            elif node_name == expected_top_level_nodes[-1]:
                expected_subnodes = ['rising_edges_indexes', 'number_of_fragments', 'stimulus_frame_info', 'generated_data', \
            'sync_data', 'actual_fragment',  'current_fragment', 'experiment_source']
                if not hasattr(node,  'has_key'):
                    result = False
                    messages.append('unexpected data type in {0}'.format(node_name))
                elif numpy.array(map(node.has_key, expected_subnodes)).sum() != len(expected_subnodes):
                    result = False
                    messages.append('unexpected number of datafields in {0}'.format(node_name))
        fragment_handle.close()        
    return result, messages
    
def merge_brain_regions(scan_regions, region_on_top = None):
    #gather images, scales and positions
    regions = []
    scales = []
    region_on_top_index = 0
    index = 0
    for k, v in scan_regions.items():
        region = {}
        region['image'] = v['brain_surface']['image']
        scale = v['brain_surface']['scale']['row'] #um/pixel
        region['scale'] = scale
        region['position'] = utils.cr((v['position']['y'], v['position']['x']))
        regions.append(region)
        scales.append(scale)
        if region_on_top == k:
            region_on_top_index = index
        index += 1
    #put preferred one to the last position
    pushed = regions[-1]
    regions[-1] = regions[region_on_top_index]
    regions[region_on_top_index] = pushed
    #convert images to same scale
    common_scale = min(scales)
    image_bounds = []
    for i in range(len(regions)):
        scale = regions[i]['scale'] / common_scale
        regions[i]['image'] = generic.rescale_numpy_array_image(regions[i]['image'], utils.rc((scale, scale)))
        regions[i]['position'] = utils.rc_multiply(regions[i]['position'], utils.rc((1/common_scale, 1/common_scale)))
        regions[i]['position'] = utils.rc((int(regions[i]['position']['row']), int(regions[i]['position']['col'])))
        image_extent = utils.cr(regions[i]['image'].shape)
        image_bounds.append([regions[i]['position']['row'] + image_extent['row'], regions[i]['position']['col'] + image_extent['col']])
        image_bounds.append([regions[i]['position']['row'], regions[i]['position']['col'] + image_extent['col']])
        image_bounds.append([regions[i]['position']['row'] + image_extent['row'], regions[i]['position']['col']])
        image_bounds.append([regions[i]['position']['row'], regions[i]['position']['col']])
    #find out image_size 
    image_bounds = numpy.array(image_bounds)
    row_min = image_bounds[:,0].min()
    row_max = image_bounds[:,0].max()
    col_min = image_bounds[:,1].min()
    col_max = image_bounds[:,1].max()
    image_size = (int(col_max - col_min), int(row_max - row_min))
    offset = (int(-col_min), int(-row_min))
    #create image
    image = numpy.zeros(image_size, dtype = numpy.uint8)
    for region in regions:
        image[region['position']['col'] + offset[0]:region['position']['col'] + offset[0] + region['image'].shape[0], \
              region['position']['row'] + offset[1]:region['position']['row'] + offset[1] + region['image'].shape[1]] = region['image'] 
    return image, common_scale

if __name__=='__main__':
    import Image
    im, c = merge_brain_regions(hdf5io.read_item('/home/zoltan/visexp/debug/data/mouse_chatdtr_14-9-2011_26-1-2012_0_0.hdf5', 'scan_regions'), 'master')
    im = Image.fromarray(im)
    im.save('/home/zoltan/visexp/debug/data/p.png')
    
    
    
    
    
