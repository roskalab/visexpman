import matplotlib.pyplot as plt
import visexpman.engine.hardware_interface.mes_interface as mes_interface

masked_line, roi,  line, mask, x, y, z = mes_interface.read_rc_scan('/home/zoltan/visexp/data/rc_scan_00010.mat')

plt.figure(1)
plt.plot(masked_line)

plt.figure(5)
plt.plot(x*mask)
plt.plot(y*mask)
plt.plot(z*mask)

#plt.figure(6)
#plt.plot(line[5])
#
#plt.figure(7)
#plt.plot(line[6])
plt.show()
