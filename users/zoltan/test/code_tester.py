import visexpA.engine.datahandlers.importers as importers
import visexpA.engine.datahandlers.hdf5io as hdf5io
import visexpA.engine.datahandlers.matlabfile as matlabfile
from visexpman.engine.hardware_interface import mes_interface
from visexpman.engine.generic import utils
import os
import os.path
import numpy
import Image
#
#path = '/home/zoltan/visexp/debug/data/line_scan_parameters_00004.mat'
#path1 = '/home/zoltan/visexp/debug/data/test.mat'
#mes_interface.set_line_scan_time(100.0, path, path1)

#path = '/home/zoltan/visexp/debug/data/mouse_bl6_1-1-2012_1-1-2012_0_0.hdf5'
#print os.path.exists(path)
#h = hdf5io.Hdf5io(path)
#print h.findvar('master_posi1tion')
#h.load('master_position')
#print h.master_position
#h.close()
#pass

#if os.name == 'nt':
#    path = 'v:\\debug\\data\\fragment_MovingDot_1326914934_0.hdf5'
#else:
#path = '/home/zoltan/visexp/debug/data/fragment_-2819.2_-5279.0_-83.94_MovingDot_1327080475_2.hdf5'
#path = '/home/zoltan/visexp/debug/data/test.hdf5'
#path1 = utils.generate_filename(path)
#import shutil
#shutil.copy(path, path1)
#
#hdf5_handler = hdf5io.Hdf5io(path1)
#fragment_data = importers.MESExtractor(hdf5_handler)
#res = fragment_data.parse()
#hdf5_handler.close()
#print res
#pass

#import visexpman.engine.hardware_interface.mes_interface as mes_interface
##16 - one roi
##20 two roi
#masked_line, roi,  line, mask, x, y, z = mes_interface.read_rc_scan('/home/zoltan/visexp/data/rc_scan_00023.mat', 50)
#pass
##plt.figure(1)
##plt.plot(line)
##plt.plot(10*roi)
##plt.legend(('image', 'roi*10'))
#
#plt.figure(1)
#plt.plot(x)
#plt.plot(y)
#plt.plot(z)
#plt.plot(10*roi)
#plt.plot(0.01*line)
#plt.legend(('x', 'y', 'z', '10*roi', '0.01*image'))
#plt.ylabel('[um]')
#
#import matplotlib.pyplot as plt
#from mpl_toolkits.mplot3d import Axes3D
#fig = plt.figure(2)
#ax = fig.add_subplot(111, projection='3d')
#rate  = 10
#ax.scatter((x*mask)[::rate], (y*mask)[::rate], (z*mask)[::rate],  c = masked_line[::rate])
#ax.set_xlabel('x')
#ax.set_ylabel('y')
#ax.set_zlabel('z')
#
#plt.show()
#

