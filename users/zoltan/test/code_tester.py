import visexpA.engine.datahandlers.hdf5io as hdf5io
import numpy
myvar = numpy.array([1, 2, 3])
h=hdf5io.Hdf5io('/media/Common/test2.hdf5')
#h.myvar = myvar
#h.save('myvar')
h.load('myvar')
print h.myvar
h.close()



