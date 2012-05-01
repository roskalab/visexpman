import visexpA.engine.datahandlers.importers as importers
import visexpA.engine.datahandlers.hdf5io as hdf5io
import visexpA.engine.datahandlers.matlabfile as matlabfile
from visexpman.engine.hardware_interface import mes_interface
from visexpman.engine.generic import utils
from visexpman.engine.generic import file
import os
import os.path
import numpy
import Image
from visexpman.engine.generic import introspect
from visexpman.users.daniel import moving_dot, configurations
import pp
import random
import re
from matplotlib.pyplot import figure,  plot, show, legend
parameters = {}
parameters['cell_explore'] = True
parameters['scan_mode'] = 'xz'
CELL_MERGE_DISTANCE = 10.0
objective_position = -10.0
rois = hdf5io.read_item(os.path.join('/mnt/rzws/debug/data/rois_test_1-1-2012_1-1-2012_0_0.hdf5'), 'rois')
if hasattr(rois, 'has_key'):
    if rois.has_key('r_0_0'):
        roi_layers = rois['r_0_0']
        if not parameters['cell_explore'] and parameters['scan_mode'] == 'xyz':
            #merge cell coordinates from different layers
            merged_list_of_cells = []
            for roi_layer in roi_layers:
                if roi_layer['ready']:
                    for cell in roi_layer['positions']:
                        merged_list_of_cells.append(cell)
            #eliminate redundant cell locations
            filtered_cell_list = []
            for i in range(len(merged_list_of_cells)):
                for j in range(i+1, len(merged_list_of_cells)):
                    if abs(utils.rc_distance(merged_list_of_cells[i], merged_list_of_cells[j])) > CELL_MERGE_DISTANCE:
                        cell = merged_list_of_cells[i]
                        filtered_cell_list.append((cell['row'], cell['col'], cell['depth']))
            cell_locations = utils.rcd(filtered_cell_list)
        elif parameters['cell_explore'] and parameters['scan_mode'] == 'xz':
            for roi_layer in roi_layers:
                if roi_layer['z'] == objective_position:
                    cell_locations = roi_layer['positions']
                    cell_locations['depth'] += -1000#convert to absolute objective value
                    break
