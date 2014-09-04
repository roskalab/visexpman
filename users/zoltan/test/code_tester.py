
import numpy
import zlib
import blosc
import pickle
from visexpA.engine.datahandlers import hdf5io

import scipy.io

datas = [hdf5io.read_item('u:\\software_test\\ref_data\\aod_converter\\fragment_ReceptiveFieldExplore_1405536218_0.hdf5','call_parameters', filelocking=False)]
data = {}
data['a'] =numpy.random.random(100000)
data['b'] =numpy.random.random(1000)
data['c'] ='abcdef'
data['d'] ={}
datas.append(data)
#datas.append(scipy.io.loadmat('r:\\dataslow\\temp\\test.mat', mat_dtype=True))


for d in datas:
    from visexpman.engine.generic.introspect import Timer
    with Timer('no_comp'):
        n=numpy.fromstring(pickle.dumps(d, 2), numpy.uint8).shape
    with Timer('blosc'):
        b=numpy.fromstring(blosc.compress(pickle.dumps(d, 2),6), numpy.uint8).shape
    with Timer('zlib'):
        z=numpy.fromstring(zlib.compress(pickle.dumps(d, 2),6), numpy.uint8).shape
    print n,b,z
    
