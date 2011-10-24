#import visexpA.engine.datahandlers.hdf5io as hdf5io
#import numpy
#myvar = numpy.array([1, 2, 3])
#h=hdf5io.Hdf5io('/media/Common/test2.hdf5')
##h.myvar = myvar
##h.save('myvar')
#h.load('myvar')
#print h.myvar
#h.close()
import subprocess
#print dir(subprocess.Popen('uname',  stdout = subprocess.PIPE))
#print subprocess.Popen('uname',  stdout = subprocess.PIPE).poll()

retcode = subprocess.call(["uname"], stdout = subprocess.PIPE)
