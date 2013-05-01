from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
from visexpA.engine.datahandlers.hdf5io import Hdf5io, read_item
import numpy
from visexpman.engine.hardware_interface import scanner_control
import Image
from visexpA.engine.dataprocessors.generic import normalize
b=[]
r = []
for i in range(2):
    pmt_raw = read_item('/mnt/datafast/debug/20130430/raw1/pmt_raw{0}.hdf5'.format(i+1), 'pmt_raw', filelocking=False)
    boundaries = read_item('/mnt/datafast/debug/20130430/raw1/pmt_raw{0}.hdf5'.format(i+1), 'boundaries', filelocking=False)
    data = read_item('/mnt/datafast/debug/20130430/raw1/pmt_raw{0}.hdf5'.format(i+1), 'data', filelocking=False)
    raw_pmt_frame = read_item('/mnt/datafast/debug/20130430/raw1/pmt_raw{0}.hdf5'.format(i+1), 'raw_pmt_frame', filelocking=False)
    frame_i = 3
    b.append(boundaries)
    a=numpy.array(pmt_raw[frame_i])
    r.append(a)
    print a.shape
    if a.shape[1]==2:
        a=a[:,1:]
#    plot(a)
#    Image.fromarray(2*normalize(scanner_control.raw2frame(a, 1, boundaries), numpy.uint8)[:,:,0]).show()
#    Image.fromarray(normalize(data[frame_i, :, :, 1], numpy.uint8)).show()
#plot(numpy.array(r[0]))
plot(r[0])
plot(r[1][:, 0])
plot(r[1][:, 1])
show()
pass
#
#
#
#href1 = Hdf5io('/mnt/datafast/debug/20130430/greenscangood/0.hdf5', filelocking=False)
#href2 = Hdf5io('/mnt/datafast/debug/20130430/greenscangood/frame_problem.hdf5', filelocking=False)
#hx = Hdf5io('/mnt/datafast/debug/20130430/bothscanbad/0.hdf5', filelocking=False)
#h0 = Hdf5io('/mnt/datafast/debug/20130430/bothscanbad/frame_problem.hdf5', filelocking=False)#highest level
#h1= Hdf5io('/mnt/datafast/debug/20130430/bothscanbad/frame_problem1.hdf5', filelocking=False)#2d ai data
#h2 = Hdf5io('/mnt/datafast/debug/20130430/bothscanbad/frame_problem2.hdf5', filelocking=False)#1d ai data
##compare scanner control signals
#d = []
#for h in [href2, h0, h1, h2]:
#    h.load('rawframe')
#    print h.rawframe.shape
#    d.append(h.rawframe)
#h0.load('scan_parameters')
#from visexpman.engine.hardware_interface import scanner_control
#import Image
#from visexpA.engine.dataprocessors.generic import normalize
#Image.fromarray(normalize(scanner_control.raw2frame(d[2], h0.scan_parameters['binning_factor'], h0.scan_parameters['boundaries'])[:, :, 0], numpy.uint8)).show()
#plot(d[0][:, 0]*0)
#plot(d[1][:, 0]*0)
#plot(d[1][:, 1]*1)
#plot(d[2][:, 0]*0)
#plot(d[2][:, 1]*1)#OK
#plot(d[3][d[3].shape[0]/2:]*0)#OK
#legend(('ref', 'high level ch0', 'high level ch1', '2d daq ch 0', '2d daq ch1', 'raw'))
##r = numpy.reshape(d[1].flatten(),(d[1].shape[1], d[1].shape[0]))
##r = d[1].T.flatten()[1::2]
##plot(d[1][:, 0])
##plot(d[2])
#show()
#h2.close()
#h1.close()
#h0.close()
#href2.close()
#href1.close()
