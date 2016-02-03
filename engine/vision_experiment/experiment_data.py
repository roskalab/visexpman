import os
import os.path
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
from visexpman.engine.generic import file
from visexpman.engine import generic
from visexpA.engine.datahandlers import hdf5io
from visexpA.engine.dataprocessors import generic as gen

import unittest

############### Preprocess measurement data ####################
def preprocess_stimulus_sync(sync_signal, stimulus_frame_info = None,  sync_signal_min_amplitude = 1.5):
    #Find out high and low voltage levels
    histogram, bin_edges = numpy.histogram(sync_signal, bins = 20)
    if histogram.max() == histogram[0] or histogram.max() == histogram[-1] or histogram.max() == histogram[1] or histogram.max() == histogram[-2]:
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
                if info.has_key('counter'):
                    info['data_series_index'] = rising_edges_indexes[info['counter']]
            except IndexError:
                #less pulses detected
                info['data_series_index'] = -1
                print 'less trigger pulses were detected'
            stimulus_frame_info_with_data_series_index.append(info)
    return stimulus_frame_info_with_data_series_index, rising_edges_indexes, pulses_detected

#################### Saving/loading data to hdf5 ####################
def load_config(numpy_array):
    return utils.array2object(numpy_array)
    
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
    if hasattr(config_modified, 'GAMMA_CORRECTION'):
        config_modified.GAMMA_CORRECTION = 0
    return utils.object2array(config_modified)
    
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
    scan_mode = file.parse_fragment_filename(os.path.split(path)[1])['scan_mode']
    if fragment_hdf5_handle == None:
        fragment_handle = hdf5io.Hdf5io(path,filelocking=False)
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
        'laser_intensity', 'experiment_config', 'machine_config', 'anesthesia_history']
            #load animal parameters
            vname = fragment_handle.find_variable_in_h5f('animal_parameters', regexp=True, path = 'root.' + node_name)
            if len(vname) == 1:
                animal_parameters = fragment_handle.findvar(vname[0], path = 'root.'+node_name)
                expected_subnodes.append(vname[0])
            if scan_mode == 'xy' and\
                ((utils.safe_has_key(animal_parameters, 'red_labeling') and animal_parameters['red_labeling'] == 'no') \
                or not animal_parameters.has_key('red_labeling')):
                #prepost_scan_image is not expected when scan mode is xy and red labeling is set to no or no red labeling key in animal parameters
                pass
            else:
                expected_subnodes.append('prepost_scan_image')
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
        from PIL import Image
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
   
def images2mip(rawdata, timeseries_dimension = 0):
    return rawdata.max(axis=timeseries_dimension)

def detect_cells(rawdata, scale, cell_size):
    from scipy.ndimage.filters import gaussian_filter,maximum_filter
    from scipy.ndimage.morphology import generate_binary_structure, binary_erosion
    from scipy.ndimage.measurements import label
    import skimage
    from skimage import filter
    minimal_cell_size = 0.25 #
    maximal_cell_size = 1.1 #
    sigma = 0.1 #cell size scaled
    mip=images2mip(rawdata,2)[:,:,0]
    cell_size_pixel = cell_size*scale
    minimal_cell_area_pixels = (cell_size_pixel*minimal_cell_size*0.5)**2*numpy.pi
    maximal_cell_area_pixels = (cell_size_pixel*maximal_cell_size*0.5)**2*numpy.pi
    gaussian_filtered = gaussian_filter(mip, cell_size_pixel*sigma)
    th=filter.threshold_otsu(gaussian_filtered)
    gaussian_filtered[gaussian_filtered<th] = 0
    neighborhood = generate_binary_structure(gaussian_filtered.ndim,gaussian_filtered.ndim)
    local_max = maximum_filter(gaussian_filtered, footprint=neighborhood)==gaussian_filtered
    background_mask = (gaussian_filtered==0)
    eroded_background_mask = binary_erosion(background_mask, structure=neighborhood, border_value=1)
    centers = numpy.array(numpy.nonzero(local_max - eroded_background_mask)).T
    print 'Found {0} maximums'.format(centers.shape[0])
    cell_rois = []
    if centers.shape[0]>200 and mip.max()<200:
        print 'the recording is probably just noise'
        return mip, cell_rois
    for center in centers:
        distances = list(numpy.sqrt(((centers-center)**2).sum(axis=1)))
        distances.sort()
        if distances[1]<cell_size_pixel:#Use a smaller bounding box if the closest roi is closer than nominal cell size
            roi_size_factor = 1
        else:
            roi_size_factor = 1
        roi_size = int(numpy.round((roi_size_factor*cell_size_pixel)))
        offset = numpy.round(numpy.array([center[0]-0.5*roi_size, center[1]-0.5*roi_size]))
        offset = numpy.where(offset<0, 0, offset)
        for i in range(offset.shape[0]):
            if offset[i]>mip.shape[i]:
                offset[i] = mip.shape[i]-1
        offset=numpy.cast['int'](offset)
        roi = mip[offset[0]:offset[0]+roi_size, offset[1]:offset[1]+roi_size]
        center_pixel_value = roi[roi.shape[0]/2-1:roi.shape[0]/2+1,roi.shape[1]/2-1:roi.shape[1]/2+1].mean()
        bright_pixels_saturated = numpy.where(roi>center_pixel_value,center_pixel_value, roi)
        roi_th = filter.threshold_otsu(bright_pixels_saturated)
        roi_binary = numpy.where(bright_pixels_saturated>roi_th,1,0)
        labeled, nlabels = label(roi_binary)
        center_pixels = labeled[labeled.shape[0]/2-1:labeled.shape[0]/2+1,labeled.shape[1]/2-1:labeled.shape[1]/2+1]
        center_label = center_pixels.mean()
        if center_pixels.std() == 0 and center_label>0:#all pixels are labeled with the same value
            one_labeled = numpy.cast['uint8'](numpy.where(labeled==center_label,1,0))
            roi_coordinates = numpy.array(numpy.nonzero(one_labeled))
            #Exclude roi if roi edges are touched
            if numpy.where(numpy.logical_or(roi_coordinates==0, roi_coordinates==roi_size-1))[0].shape[0]>0.5*roi_size:
                continue
            #calculate perimeter and diameter. Accept as cell if it is close to circle
            inner_pixel_coordinates = numpy.array(numpy.where(scipy.ndimage.filters.convolve(one_labeled, numpy.ones((3,3)))==9))
            perimeter = roi_coordinates.shape[1] - inner_pixel_coordinates[0].shape[0]
            area = roi_coordinates.shape[1]
            #Diameter: get two furthest points
            import itertools
            #Checking the distance between all pixels. Optimal would be to do it for perimeter pixels
            diameter = max([numpy.sqrt(((roi_coordinates[:,ci[0]]-roi_coordinates[:,ci[1]])**2).sum()) for ci in [i for i in itertools.combinations(range(roi_coordinates.shape[1]), 2)]])
            #perimeter/diameter shall be around pi
            peri_diam_ratio = perimeter/diameter
            if (peri_diam_ratio<1.5*numpy.pi) and \
                            (area > minimal_cell_area_pixels and area < maximal_cell_area_pixels):
                #Transform these coordinates back to mip coordinates
                cell_rois.append(numpy.cast['int']((roi_coordinates.T+offset).T))
    return mip,cell_rois
    
def images2mip(rawdata, timeseries_dimension = 0):
    return rawdata.max(axis=timeseries_dimension)
    
def get_roi_curves(rawdata, cell_rois):
    return [numpy.cast['float'](rawdata[cell_roi[0], cell_roi[1], :,0]).mean(axis=0) for cell_roi in cell_rois]
        
def get_data_timing(filename):
    from visexpA.engine.datahandlers import matlabfile
    m=matlabfile.MatData(filename.replace('.hdf5', '.mat'))
    indexes = numpy.where(m.get_field('DATA.0.DI0.y',copy_field=False)[0][0][0][1])[0]
    stimulus_time = m.get_field('DATA.0.DI0.y',copy_field=False)[0][0][0][0][indexes]/1e6#1 us per count
    indexes = numpy.where(m.get_field('DATA.0.SyncFrame.y',copy_field=False)[0][0][0][1])[0]
    imaging_time = m.get_field('DATA.0.SyncFrame.y',copy_field=False)[0][0][0][0][indexes]/1e6#1 us per count
    h=hdf5io.Hdf5io(filename,filelocking=False)
    if 1:
        import visexpA.engine.component_guesser as cg
        rawdata = h.findvar('rawdata')
        sfi = h.findvar('_'.join(cg.get_mes_name_timestamp(h)))['stimulus_frame_info']
        scale = h.findvar('image_scale')['row'][0]
    else:
        rawdata = utils.array2object(numpy.load(os.path.split(filename)[0]+'/rawdata.npy'))
        sfi = hdf5io.read_item(os.path.split(filename)[0]+'/sfi.hdf5', 'sfi', filelocking=False)
        scale = 1.42624
    imaging_time = imaging_time[:rawdata.shape[2]]
    try:
        block_times, stimulus_parameter_times,block_info, organized_blocks = process_stimulus_frame_info(sfi, stimulus_time, imaging_time)
        if 'grating' not in filename.lower() and 0:
            print 'Detect cells'
            mip,cell_rois = detect_cells(rawdata, scale, 12)
            roi_curves = get_roi_curves(rawdata, cell_rois)
        h.quick_analysis = {}
        if 'grating' not in filename.lower() and 0:
            h.quick_analysis['roi_curves']=roi_curves
            h.quick_analysis['cell_rois']=cell_rois
        h.quick_analysis['block_times']=block_times
        h.quick_analysis['stimulus_parameter_times']=utils.object2array(stimulus_parameter_times)
        h.quick_analysis['block_info']=block_info
        h.quick_analysis['organized_blocks']=organized_blocks
        h.save('quick_analysis')
        if 'receptive' in filename.lower() and 0:
            plot_receptive_field_stimulus(organized_blocks,roi_curves, mip)
    except:
        import traceback
        print traceback.format_exc()
    h.close()
    
def plot_receptive_field_stimulus(organized_blocks,roi_curves, mip):
    '''match positions with curve fragments'''
    from pylab import imshow,show,plot,figure,title,subplot,clf,savefig#TMP
    positioned_curves = []
    positions = []
    for ob in organized_blocks:
        pos = ob[0]['sig'][2]['pos']
        positions.append([pos['col'], pos['row']])
        roi_curve_fragment = [[roi_curve[obi['start']:obi['end']] for obi in ob] for roi_curve in roi_curves]
        positioned_curves.append([pos, ob[0]['sig'][2]['color'], roi_curve_fragment])
    positions = numpy.array(positions)
    nrows = len(set(positions[:,1]))
    ncols = len(set(positions[:,0]))
    col_start = positions[:,0].min()
    row_start = positions[:,1].min()
    grid_size = organized_blocks[0][0]['sig'][2]['size']['row']
    selected_roi = 1
    for roi_i in range(len(roi_curves)):
        for positioned_curve in positioned_curves:
            ploti = (positioned_curve[0]['row']-row_start)/grid_size*ncols+(positioned_curve[0]['col']-col_start)/grid_size+1
            subplot(nrows, ncols, ploti)
            for i in range(len(positioned_curve[2][roi_i])):
                title(numpy.round(utils.nd(positioned_curve[0])))
                plot(positioned_curve[2][roi_i][i], color = [1.0, 0.0, 0.0] if positioned_curve[1] == 1 else [0.0, 0.0, 0.0])
        outfolder = tempfile.gettempdir() if 1 else os.path.join(os.path.split(filename)[0], out, os.path.split(filename)[1])
        if not os.path.exists(outfolder):
            os.path.makedirs(outfolder)
        fn=os.path.join(outfolder, '{1}-{0:0=3}.png'.format(roi_i, os.path.split(filename)[1]))
        savefig(fn,dpi=300)
        clf()
        plotim=numpy.asarray(Image.open(fn))
        mip_with_cell = numpy.zeros((mip.shape[0], mip.shape[1], 3),dtype=numpy.float)
        mip_with_cell[:,:,1] = mip/mip.max()
        for i in range(cell_rois[roi_i][0].shape[0]):
            mip_with_cell[cell_rois[roi_i][0][i],cell_rois[roi_i][1][i], 0] = 0.5
        scaling_factor = plotim.shape[0]/float(mip_with_cell.shape[0])
        new_size = (int(mip_with_cell.shape[0]*scaling_factor),int(mip_with_cell.shape[1]*scaling_factor))
        scaled = numpy.asarray(Image.fromarray(numpy.cast['uint8'](255*mip_with_cell)).resize(new_size))
        merged = numpy.zeros((max(scaled.shape[0],plotim.shape[0]), scaled.shape[1]+plotim.shape[1], 3))
        merged[:scaled.shape[0], :scaled.shape[1],:] = scaled
        merged[:plotim.shape[0], scaled.shape[1]:,:] = plotim[:,:,:3]
        Image.fromarray(numpy.cast['uint8'](merged)).save(fn)
    
def sfi2signature(sfi):
    '''
    Remove varying keys from stimulus frame info
    '''
    import copy
    sfisig = []
    for sfii in sfi:
        if sfii.has_key('parameters'):
            item = copy.deepcopy(sfii)
            item.update(item['parameters'])
            removable_keys = ['elapsed_time', 'counter', 'data_series_index', 'flip', 'parameters', 'count', 'frame_trigger']
            for k in removable_keys:
                if item.has_key(k):
                    del item[k]
            sfisig.append(item)
    return sfisig

def cmp_signature(sig1, sig2):
    '''
    Compares two stimulus block signatures
    '''
    if len(sig1) != len(sig2):
        return False
    else:
        for i in range(len(sig1)):
            if cmp(sig1[i], sig2[i]) != 0:
                return False
        return True
    
def sfi2blocks(sfi):
    '''
    Group stimulus frame info entries into blocks
    '''
    block_start_indexes = [i for i in range(len(sfi)) if sfi[i].has_key('block_start')]
    block_end_indexes = [i for i in range(len(sfi)) if sfi[i].has_key('block_end')]
    grouped_sfi_by_blocks = []
    for i in range(len(block_start_indexes)):
        grouped_sfi_by_blocks.append(sfi[block_start_indexes[i]+1:block_end_indexes[i]])
    return grouped_sfi_by_blocks
    
def stimulus_frame_counter2image_frame_counter(ct, imaging_time, stimulus_time):
    '''
    stimulus frame counter values is converted to image data frame index using timing information
    '''
    try:
        stim_time_value = stimulus_time[ct]
    except:
        stim_time_value = stimulus_time[-1]
    return numpy.where(imaging_time>=stim_time_value)[0][0]
    
def process_stimulus_frame_info(sfi, stimulus_time, imaging_time):
    '''
    1) Organizes stimulus frame info into blocks and repetitions
    2) Stimulus function call parameters (size, position, color etc) are matched with imaging frame index
    '''
    #Collect parameter names
    parnames = []
    for sfii in sfi:
        if sfii.has_key('parameters'):
            parnames.extend(sfii['parameters'].keys())
    parnames = list(set(parnames))
    [parnames.remove(pn) for pn in ['frame_trigger', 'count', 'flip'] if pn in parnames]
    #assign frame counts and values to each parameters
    stimulus_parameter_times = {}
    block_times = []
    for sfii in sfi:
        if sfii.has_key('parameters'):
            for k in parnames:
                if sfii['parameters'].has_key(k):
                    if not stimulus_parameter_times.has_key(k):
                        stimulus_parameter_times[k] = []
                    if sfii['parameters'][k] is not None and sfii['parameters'][k] != {} and sfii['parameters'][k] != []:#hdf5io cannot handle this data
                        stimulus_parameter_times[k].append([sfii['counter'], stimulus_frame_counter2image_frame_counter(sfii['counter'], imaging_time, stimulus_time), sfii['parameters'][k]])
        elif sfii.has_key('block_start'):
            block_times.append([stimulus_frame_counter2image_frame_counter(sfii['block_start'], imaging_time, stimulus_time), 1])
        elif sfii.has_key('block_end'):
            block_times.append([stimulus_frame_counter2image_frame_counter(sfii['block_end'], imaging_time, stimulus_time), 0])
    for k in stimulus_parameter_times.keys():
        if stimulus_parameter_times[k] == []:
            del stimulus_parameter_times[k]
    block_times = numpy.array(block_times)
    grouped_sfi_by_blocks = sfi2blocks(sfi)
    block_signatures = [sfi2signature(block_sfi) for block_sfi in grouped_sfi_by_blocks]
    block_boundaries = []
    for b in grouped_sfi_by_blocks:
        c=[item['counter'] for item in b]
        block_boundaries.append([min(c), max(c)])
    block_info = [{'sig': block_signatures[i], 'start': block_boundaries[i][0], 'end': block_boundaries[i][1]} for i in range(len(block_boundaries))]
    #Calculate time and frame indexes for each block
    for block_info_i in block_info:
        for e in ['start', 'end']:
            block_info_i[e] = stimulus_frame_counter2image_frame_counter(block_info_i[e], imaging_time, stimulus_time)
    if len(block_info) ==0:
        return None, stimulus_parameter_times,None,None
    #Find repetitions
    organized_blocks = [[block_info[0]]]
    import itertools
    for b1, b2 in itertools.combinations(block_info, 2):
        if not cmp_signature(b1['sig'],b2['sig']) and len([ob for ob in organized_blocks if cmp_signature(ob[0]['sig'], b2['sig'])])==0:
            organized_blocks.append([b2])
    #Find repetitions and group them
    for organized_block in organized_blocks:
        for block_info_i in block_info:
            if cmp_signature(block_info_i['sig'],organized_block[0]['sig']) and block_info_i not in organized_block:
                organized_block.append(block_info_i)
    return block_times, stimulus_parameter_times,block_info, organized_blocks


import paramiko,platform,time
class RlvivoBackup(object):
    def __init__(self, files,user,id,animalid, todatabig=False):
        '''
        Assumes that:
        1) /mnt/databig is mounted as u drive
        2) files reside on v: drive
        3) v:\\codes\\jobhandler\\pw.txt is accessible
        '''
        if os.name!='nt':
            raise RuntimeError('Not supported OS')
        pwfile='v:\\codes\\jobhandler\\pw.txt'
        if not os.path.exists(pwfile):
            raise RuntimeError('Password file does not exist')
        fp=open('v:\\log\\bu_{0}.txt'.format(platform.node()),'at')
        [fp.write('{0}\t{1}\n'.format(utils.timestamp2ymdhms(time.time()),f)) for f in files]
        fp.close()
        self.files=files
        self.user=user
        self.id=id if isinstance(id, str) else utils.timestamp2ymd(float(self.id),'')
        self.animalid=animalid
        self.connect()
        self.target_folder()
        self.copy()
        if todatabig:
            root= '/mnt/databig/data' if user=='daniel' or user=='default_user' else  '/mnt/databig/processed'
            self.target_folder(root=root)
            self.copy()
        self.close()
        
    def connect(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect('rlvivo1.fmi.ch', username='mouse',password=file.read_text_file('v:\\codes\\jobhandler\\pw.txt'))
        
    def close(self):
        self.ssh.close()
        
    def check_ssh_error(self,e):
        emsg=e.readline()
        if emsg!='':
            raise RuntimeError(emsg)
        
    def target_folder(self,root='/mnt/databig/backup'):
        self.target_dir='/'.join([root,self.user,self.id,str(self.animalid)])
        i,o,e1=self.ssh.exec_command('mkdir -p {0}'.format(self.target_dir))
        i,o,e2=self.ssh.exec_command('chmod 777 {0} -R'.format(self.target_dir))
        #for e in [e1,e2]:
        print e2.readline()
        self.check_ssh_error(e1)
        
    def copy(self):
        for f in self.files:
            flinux='/'.join(f.replace('v:\\', '/mnt/datafast/').replace('V:\\', '/mnt/datafast/').split('\\'))
            i,o,e=self.ssh.exec_command('cp {0} {1}'.format(flinux,self.target_dir))
            self.check_ssh_error(e)
   
class TestExperimentData(unittest.TestCase):
    @unittest.skip("")
    def test_01_read_merge_rois(self):
        path = '/mnt/databig/testdata/read_merge_rois/mouse_test_1-1-2012_1-1-2012_0_0.hdf5'
        cells = hdf5io.read_item(path, 'cells',filelocking=False)
        roi_locations, rois = read_merge_rois(cells, 'g2', 'scanned_2vessels_0_0', -130, 0, 80, 4)
        roi_locations, rois = add_auxiliary_rois(rois, 9, -130, -100, aux_roi_distance = 5.0)
        
    def test_02(self):
        get_data_timing('/mnt/datafast/experiment_data/fragment_xy_tr_0_0_0.0_ReceptiveFieldExploreNew_1424686117_0.hdf5')
        
if __name__=='__main__':
    unittest.main()
    
    
    
    
    
