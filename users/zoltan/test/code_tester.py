import numpy
from visexpA.engine.datahandlers import datatypes
a=numpy.ones((1000,1000,1,1),dtype=numpy.uint16)
h=datatypes.ImageData('v:\\debug\\tma5.hdf5')#,filelocking=False)
# h=datatypes.ImageData('/mnt/datafast/debug/tma4.hdf5',filelocking=False)
h.rawdata=a
h.save('rawdata')

