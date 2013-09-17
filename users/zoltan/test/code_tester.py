import tables
from visexpA.engine.datahandlers import hdf5io
import os
import os.path
import numpy
import time

if not True:
    
    
    import socket

#    HOST = 'localhost'    # The remote host
#    PORT = 22002              # The same port as used by the server
#    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#    s.bind((HOST, PORT))
    
    import SocketServer
    address=('localhost', 22000)
    s1=SocketServer.TCPServer(address, None)
    import time
    time.sleep(1.0)
#    s1.socket.bind(s1.server_address)
##    s1.server_bind()
    pass
    
    
    
else:
    def append2hdf5():
        p='/mnt/datafast/debug/ea.hdf5'
        p='v:\\debug\\ea.hdf5'
        if os.path.exists(p):
            os.remove(p)
        handle=hdf5io.Hdf5io(p, filelocking=False)
        h=100
        w=100
        array_c = handle.h5f.createEArray(handle.h5f.root, 'array_c', tables.UInt8Atom(), (0,))#,  filters=tables.Filters(complevel=1, complib='lzo', shuffle = 1))
        array_c.append(numpy.cast['float64'](numpy.cast['uint8'](numpy.random.random(h))))
        array_c.append(numpy.cast['float64'](numpy.cast['uint8'](numpy.random.random(h))))
    #    from visexpman.engine.generic.introspect import Timer
    #    for i in range(10):
    #        with Timer(''):
    #            array_c.append(numpy.cast['float64'](numpy.random.random((2*h, w,))[0:h, :]))
        handle.close()
        pass

from multiprocessing import Queue, Process
if __name__ == '__main__':
    append2hdf5()
#    p='/mnt/datafast/debug/earray1.hdf5'
#    if os.path.exists(p):
#        os.remove(p)
#    fileh = tables.openFile(p, mode='w')
#    a = tables.Float64Atom()
#    # Use ``a`` as the object type for the enlargeable array.
#    array_c = fileh.createEArray(fileh.root, 'array_c', a, (0,))
#    array_c.append(numpy.ones((10,)))
#    array_c.append(0*numpy.ones((10,)))
#
#    # Read the string ``EArray`` we have created on disk.
#    for s in array_c:
#        print 'array_c[%s] => %r' % (array_c.nrow, s)
#    # Close the file.
#    fileh.close()
