import matplotlib.pyplot as plt
import numpy
mes = numpy.loadtxt('/home/zoltan/visexp/debug/mes1.txt')
visexp = numpy.loadtxt('/home/zoltan/visexp/debug/visexp.txt')
plt.figure(1)
plt.plot(mes)
plt.plot(visexp)
plt.show()

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
#import numpy
#import visexpA.engine.datahandlers.hdf5io as hdf5io
#p = '/home/zoltan/d1.hdf5'
#h1 = hdf5io.Hdf5io(p)
#h1.a=numpy.ones(3)
#h1.save('a')
#h1.close()
#h2 = hdf5io.Hdf5io(p)
#h2.load('a')
#h2.a = numpy.ones(3)*2
#h2.save('a')
#h2.close()
#h3 = hdf5io.Hdf5io(p)
#h3.load('a')
#print h3.a
#h3.close()
