import tables
import os.path
import os
import numpy
from visexpA.engine.datahandlers import hdf5io
from visexpman.engine.generic import utils
import pickle as pickle
#N = 100
#Cell = {
#    'id' : tables.StringCol(32), 
#    'scan_region' : tables.StringCol(64), 
#    'group' : tables.StringCol(32), 
#    'depth' : tables.Float64Col(), 
#    'origin_row' : tables.Float64Col(), 
#    'origin_col' : tables.Float64Col(), 
#    'scale_row' : tables.Float64Col(), 
#    'scale_col' : tables.Float64Col(), 
#    
#    'roi_curve' : tables.Float64Col(shape = (N)), 
#    'soma_roi' : tables.Float64Col(shape = (N)), 
#    }
#    
#path = "c:\\_del\\mouse.hdf5"
#if os.path.exists(path):
#    os.remove(path)
#h5file = tables.openFile(path, mode = "w", title = "Test file")
#group = h5file.createGroup("/", 'cell_group', 'Cell group')
#table = h5file.createTable(group, 'cells', Cell, "Cells")
#row = table.row
#for i in range(30):
#    row['id'] = '1234567' + str(i)
#    row['depth'] = -100.0
#    row['group'] = 'ok'
#    row['roi_curve'] = numpy.arange(100)
#    row.append()
#table.flush()
#
#table = h5file.root.cell_group.cells
#ct = 0
#for x in table.iterrows():
#    print x['id'],  x['depth'], ct
#    ct +=1
#h5file.close()
#pass
#Open question: store arrays, rec arrays, 
#plan: def save_cells, def load_cells

cells = hdf5io.read_item("c:\\_del\\mouse_big.hdf5", 'cells')
for sr in list(cells.values()):
    for cell in list(sr.values()):
        if cell['group'] == '':
            cell['group'] = 'None'
        cell['roi_center'] = utils.rcd((cell['roi_center']['row'], cell['roi_center']['col'], cell['roi_center']['depth']))
h1 = hdf5io.Hdf5io('c:\\_del\cells.hdf5')
h1.cells = cells
utils.object2hdf5(h1, 'cells')
h1.close()
h2 = hdf5io.Hdf5io('c:\\_del\cells.hdf5')
cells_readback = utils.hdf52object(h2, 'cells')
h2.close()
pass
#Compare
for sr in list(cells.keys()):
    for cell_name in list(cells[sr].keys()):
        if cells[sr][cell_name]['origin']['col'] != cells_readback[sr][cell_name]['origin']['col'] and \
            cells[sr][cell_name]['origin']['row'] != cells_readback[sr][cell_name]['origin']['row']:
                print('origin',  cells[sr][cell_name]['origin'],  cells_readback[sr][cell_name]['origin'])
        if cells[sr][cell_name]['scale']['col'] != cells_readback[sr][cell_name]['scale']['col'] and\
            cells[sr][cell_name]['scale']['row'] != cells_readback[sr][cell_name]['scale']['row']:
                print('scale',  cells[sr][cell_name]['scale'],  cells_readback[sr][cell_name]['scale'])
        if cells[sr][cell_name]['roi_center']['col'] != cells_readback[sr][cell_name]['roi_center']['col'] and\
            cells[sr][cell_name]['roi_center']['row'] != cells_readback[sr][cell_name]['roi_center']['row'] and\
            cells[sr][cell_name]['roi_center']['depth'] != cells_readback[sr][cell_name]['roi_center']['depth']:
                print('roi_center',  cells[sr][cell_name]['roi_center'],  cells_readback[sr][cell_name]['roi_center'])
                print('roi_center',  cells[sr][cell_name]['roi_center'].dtype,  cells_readback[sr][cell_name]['roi_center'].dtype)
pass
