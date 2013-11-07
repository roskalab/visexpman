import tables
from visexpA.engine.datahandlers import hdf5io
from visexpman.engine.hardware_interface import instrument
import os
import os.path
import numpy
import time
from visexpman.engine.generic import utils

class Cfg():
    def __init__(self):
        self.ENABLE_PARALLEL_PORT = True
        self.d=range(1000000)
        self.d1=range(-1000000,110000)
        
def fun():
    cfg=Cfg()
    import cPickle as pickle
    import json
    import simplejson
    import blosc
    from visexpman.engine.generic.introspect import Timer
    o = [range(1000000),range(-1000000,0),cfg]
    o=cfg
    rep=3
#    for i in range(rep):
#        with Timer('json'):
#            j = json.dumps(o)
#        print len(j)
#        
#    for i in range(rep):
#        with Timer('simplejson'):
#            j = simplejson.dumps(o)
#        print len(j)
        
    for i in range(rep):
        with Timer('blosc'):
            b = blosc.pack_array(numpy.array([o]))
    print len(b)
        
    for i in range(rep):
        with Timer('pickle'):
            p = utils.object2array(o)
    print p.shape[0]
        
        
    for i in range(rep):
        with Timer('blosc'):
            b1 = blosc.unpack_array(b)[0]
        
    for i in range(rep):
        with Timer('pickle'):
            p1 = utils.array2object(p)
    pass


if True:
    pass
#    class Cfg():
#        def __init__(self):
#            self.ENABLE_PARALLEL_PORT = True
#    
#    parallel_port = instrument.ParallelPort(Cfg())
#    state=True
#    while True:
#        print  parallel_port.read_pin(11)
#        parallel_port.set_data_bit(1, state)
#        state = not state
#        time.sleep(0.1)
#    parallel_port.release_instrument()
#    import unit_test_runner
#    unit_test_runner.run_test('visexpman.engine.visexp_runner.TestVisionExperimentRunner.test_11_microled')
    
else:
    def append2hdf5():
#        p='/mnt/datafast/debug/ea.hdf5'
        p='v:\\debug\\ea.hdf5'
        if os.path.exists(p):
            os.remove(p)
        handle=hdf5io.Hdf5io(p, filelocking=False)
        h=500
        w=540
        sh = h
#        array_c = handle.h5f.create_earray(handle.h5f.root, 'array_c', tables.UInt8Atom(), (0,))#,  filters=tables.Filters(complevel=1, complib='lzo', shuffle = 1))
        array_c = handle.h5f.create_earray(handle.h5f.root, 'array_c', tables.UInt8Atom((h, w)), shape=(0, ), filters=tables.Filters(complevel=1, complib='lzo', shuffle = 1), expectedrows=100)
        array_c.append(numpy.cast['uint8'](256*numpy.random.random((1, h, w))))
        
        from visexpman.engine.generic.introspect import Timer
        for i in range(60*10):
            with Timer(''):
                array_c.append(numpy.cast['uint8'](256*numpy.random.random((1, h, w))))
        handle.close()
        pass

    def read_hdf5():
        p='v:\\debug\\ea.hdf5'
        handle=hdf5io.Hdf5io(p, filelocking=False)
        print handle.h5f.root.array_c.read().shape
        handle.close()

#from multiprocessing import Queue, Process
if __name__ == '__main__':
<<<<<<< HEAD
    utils.array2object(utils.object2array([1,2,3,'a']))
    fun()
=======
    hdf5io.save_item('/mnt/datafast/debug/tmp3.hdf5',  'data',  range(1000), filelocking=False)
    pass
>>>>>>> d2926119e4468b93ff0a075c8b380e3577c7f852
#    if False:
#        append2hdf5()
#        read_hdf5()
#    p='/mnt/datafast/debug/earray1.hdf5'
#    if os.path.exists(p):
#        os.remove(p)
#    fileh = tables.open_file(p, mode='w')
#    a = tables.Float64Atom()
#    # Use ``a`` as the object type for the enlargeable array.
#    array_c = fileh.create_earray(fileh.root, 'array_c', a, (0,))
#    array_c.append(numpy.ones((10,)))
#    array_c.append(0*numpy.ones((10,)))
#
#    # Read the string ``EArray`` we have created on disk.
#    for s in array_c:
#        print 'array_c[%s] => %r' % (array_c.nrow, s)
#    # Close the file.
#    fileh.close()
