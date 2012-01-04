import matplotlib.pyplot as plt
import visexpman.engine.hardware_interface.mes_interface as mes_interface

masked_line, roi,  line, mask, x, y, z = mes_interface.read_rc_scan('/home/zoltan/visexp/data/rc_scan_00023.mat', 50)
pass
#plt.figure(1)
#plt.plot(line)
#plt.plot(10*roi)
#plt.legend(('image', 'roi*10'))

plt.figure(2)
plt.plot(x)
plt.plot(y)
plt.plot(z)
plt.plot(10*roi)
plt.plot(0.01*line)
plt.legend(('x', 'y', 'z', '10*roi', '0.01*image'))
plt.ylabel('[um]')

plt.show()
