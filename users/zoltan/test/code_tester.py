import tables
import os.path
import os
import numpy
class Cell(tables.IsDescription):
    id = tables.StringCol(16)
    group = tables.StringCol(255)
    depth = tables.Float64Col()
    
    
path = "c:\\_del\\mouse.hdf5"
if os.path.exists(path):
    os.remove(path)
h5file = tables.openFile(path, mode = "w", title = "Test file")
group = h5file.createGroup("/", 'cell_group', 'Cell group')
table = h5file.createTable(group, 'cells', Cell, "Cells")
row = table.row
for i in range(3000):
    row['id'] = '1234567' + str(i)
    row['depth'] = -100.0
    row['group'] = 'ok'
    row.append()
table.flush()


table = h5file.root.cell_group.cells
for x in table.iterrows():
    print x['id'],  x['depth']
h5file.close()
pass
#Open question: store arrays, rec arrays, 
