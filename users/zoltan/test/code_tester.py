import matplotlib.pyplot as plt
import visexpman.engine.hardware_interface.mes_interface as mes_interface
#16 - one roi
#20 two roi
masked_line, roi,  line, mask, x, y, z = mes_interface.read_rc_scan('/home/zoltan/visexp/data/rc_scan_00023.mat', 50)
pass
#plt.figure(1)
#plt.plot(line)
#plt.plot(10*roi)
#plt.legend(('image', 'roi*10'))

plt.figure(1)
plt.plot(x)
plt.plot(y)
plt.plot(z)
plt.plot(10*roi)
plt.plot(0.01*line)
plt.legend(('x', 'y', 'z', '10*roi', '0.01*image'))
plt.ylabel('[um]')

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
fig = plt.figure(2)
ax = fig.add_subplot(111, projection='3d')
rate  = 10
ax.scatter((x*mask)[::rate], (y*mask)[::rate], (z*mask)[::rate],  c = masked_line[::rate])
ax.set_xlabel('x')
ax.set_ylabel('y')
ax.set_zlabel('z')

plt.show()
