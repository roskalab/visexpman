import zipfile
import io
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
import StringIO

from visexpman.engine.generic import utils,fileop
from visexpman.engine import generic
from visexpA.engine.datahandlers import hdf5io

import unittest

def check(h, config):
    h_opened = False
    error_messages = []
    if not hasattr(h, 'filename'):
        h = hdf5io.Hdf5io(h, filelocking=False)
        map(h.load, config.DATA_FILE_NODES)
        h_opened = True
    for node in config.DATA_FILE_NODES:
        if not hasattr(h, node):
            error_messages.append('missing node: {0}'.format(node))
    if h_opened:
        h.close()
    return error_messages
    #TODO: check if all software are identical

def generate_filename(config, id, experiment_name = '',  cell_name = '', nfragments = 1, region_name = '',  depth = '',  scan_mode = '', end_tag = '', user_extensions = [], tmp_folder = None, experiment_config = None, output_folder = None):
    '''
    Format:
    scan_mode, region_name, cell_name, depth, experiment_name, id, fragment_id
    '''
    #OBSOLETE
    filenames = {}
    filenames['names']= []
    filenames['datafile'] = []
    filenames['local_datafile'] = []
    filenames['other_files'] = []
    if config.PLATFORM == 'rc_cortical':
        filenames['mes_files'] = []
        prefix = 'fragment'#FIXME: this is obsolete
    else:
        prefix = ''
    if output_folder is None:
        output_folder = config.EXPERIMENT_DATA_PATH
    for fragment_id in range(nfragments):
        if hasattr(experiment_config, 'USER_FRAGMENT_NAME'):
            name = self.experiment_config.USER_FRAGMENT_NAME
        else:
            if depth != '':
                depth_formatted = str(numpy.round(depth, 1))
            else:
                depth_formatted = depth
            name = ''
            for tag in [prefix, scan_mode, region_name, cell_name, depth_formatted, experiment_name, id, str(fragment_id)]:
                if tag != '':
                    name += tag + '_'
            name = name[:-1]
        filenames['names'].append(name)
        filename = '{0}{1}.{2}'.format(name, end_tag, config.EXPERIMENT_FILE_FORMAT)
        filenames['datafile'].append(os.path.join(output_folder, filename))
        if tmp_folder is None or not os.path.exists(tmp_folder):
            tmp_folder = tempfile.mkdtemp()
        filenames['local_datafile'].append(os.path.join(tmp_folder, filename))
        for ext in user_extensions:
            filenames['other_files'].append(os.path.join(output_folder, '.'.join(filename.split('.')[:-1])+'.' + ext))
    return filenames

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
def pack_software_environment(experiment_source_code = None):
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
        if experiment_source_code is not None:
            software_environment['experiment_source_code'] = numpy.fromstring(experiment_source_code, dtype = numpy.uint8)
        zipfile_handler.close()
        return software_environment


def load_config(numpy_array):
    return utils.array2object(numpy_array)
    
def save_config(file_handle, machine_config, experiment_config = None):
    if hasattr(file_handle, 'save'):
        if 0:
            file_handle.machine_config = copy.deepcopy(machine_config.get_all_parameters()) #The deepcopy is necessary to avoid conflict between daqmx and hdf5io        
            file_handle.experiment_config = experiment_config.get_all_parameters()
        #pickle configs
        file_handle.machine_config = pickle_config(machine_config)
        if experiment_config is not None:
            file_handle.experiment_config = pickle_config(experiment_config)
            file_handle.save(['experiment_config', 'machine_config'])#, 'experiment_config_pickled', 'machine_config_pickled'])
        else:
            file_handle.save(['machine_config'])
    elif file_handle is None:
        config = {}
        config['machine_config'] = copy.deepcopy(machine_config.get_all_parameters())
        config['experiment_config'] = experiment_config.get_all_parameters()
        return config
        
def pickle_config(config):#OBSOLETE
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
        try:
            import Image
        except ImportError:
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
    
def read_phys(filename):
    import struct
    f =open(filename,  'rb')
    offset = f.read(4)
    offset = struct.unpack('>i',offset)[0]
    header= f.read(offset)
    metadata = {}
    for item in [param.split(':') for param in header.split('\r')]:
        if len(item)==2:
            metadata[item[0]] = item[1]
    f.seek(4+offset)
    dim1 = f.read(4)
    dim2 = f.read(4)
    dim1 = struct.unpack('>i',dim1)[0]
    dim2 = struct.unpack('>i',dim2)[0]
    data = f.read(2*dim1*dim2)
    data = numpy.array(struct.unpack('>'+''.join(dim1*dim2*['h']),data), dtype = numpy.int16).reshape((dim1, dim2))
#    data = numpy.fromfile(f, dtype=numpy.int16, count=dim1*dim2).reshape((dim1, dim2))
    f.close()
    return data, metadata

def phys2clampfit(filename):
    '''
    Converts phys file with trigger information to be readable by clampfit software
   ''' 
    data = read_phys(filename)
    data = data.flatten('F').reshape(dim1, dim2)
    data.tofile(filename.replace('.phys', 'c.phys'))
    
def read_machine_config(h):
    return utils.array2object(h.findvar('machine_config'))
    
def read_machine_config_name(h):
    return read_machine_config(h).__class__.__name__
    
def read_smr_file(fn):
    from neo import Block
    from neo.io import Spike2IO, NeoMatlabIO
    name=os.path.split(fn)[1].replace('.smr','')
    tmp_matfile=os.path.join(tempfile.gettempdir(), name+'.mat')
    r = Spike2IO(filename=fn)
    w = NeoMatlabIO(filename=tmp_matfile)
    seg = r.read_segment()
    bl = Block(name=name)
    bl.segments.append(seg)
    w.write_block(bl)
    data=scipy.io.loadmat(tmp_matfile, mat_dtype=True)['block']['segments'][0][0][0][0][0]['analogsignals'][0][0]
#    from pylab import plot, show
#    plot(data[0]['signal'][0][0][0][::100]);show()
#    os.remove(tmp_matfile)
   
class TestExperimentData(unittest.TestCase):
    @unittest.skip("")
    def test_01_read_merge_rois(self):
        path = '/mnt/databig/testdata/read_merge_rois/mouse_test_1-1-2012_1-1-2012_0_0.hdf5'
        cells = hdf5io.read_item(path, 'cells', filelocking = self.config.ENABLE_HDF5_FILELOCKING)
        roi_locations, rois = read_merge_rois(cells, 'g2', 'scanned_2vessels_0_0', -130, 0, 80, 4)
        roi_locations, rois = add_auxiliary_rois(rois, 9, -130, -100, aux_roi_distance = 5.0)
        pass
        
    def test_02_elphys(self):
        from visexpman.users.test import unittest_aggregator
        working_folder = unittest_aggregator.prepare_test_data('elphys')
        convert_phys(os.path.join(working_folder,os.listdir(working_folder)[0]))
        
    def test_03_smr(self):
        folder='/home/rz/rzws/temp/santiago/181214_Lema_offcell'
        for fn in fileop.listdir_fullpath(folder):
            if '.smr' in fn:
                read_smr_file(fn)
            
        
        
if __name__=='__main__':
    unittest.main()
        
    
    
    
    
