import scipy.io
from visexpman.engine.generic import utils
import os
import numpy
try:
    import hdf5io
except:
    from visexpA.engine.datahandlers import hdf5io
    
nodenames = ['configs_stim', 'phys_metadata', 'raw_data', 'recording_parameters', 'repetition_link', 'rois', 'sync_and_elphys_data', 'trace_parameters','elphys_sync_conversion_factor', 'fphys', 'ftiff']

def hdf52mat(filename):
    h=hdf5io.Hdf5io(filename, filelocking=False)
    data={}
    for nn in nodenames:
        h.load(nn)
        if nn=='recording_parameters':
            getattr(h,nn)['scanning_range']=utils.nd(getattr(h,nn)['scanning_range'])
            if getattr(h,nn)['experiment_source']=='':
                getattr(h,nn)['experiment_source']='none'
            if getattr(h,nn)['experiment_source_file']=='':
                getattr(h,nn)['experiment_source_file']='none'
        if hasattr(h, nn):
            data[nn] =  utils.object2array(getattr(h,nn))
    scipy.io.savemat(filename.replace('.hdf5','.mat'),data)
    h.close()
    
def mat2hdf5(filename):
    data=scipy.io.loadmat(filename)
    h=hdf5io.Hdf5io(filename.replace('.mat','.hdf5'),filelocking=False)
    nn2save = []
    for nodename, value in data.items():
        if nodename not in nodenames: continue
        try:
            setattr(h, nodename,utils.array2object(value))
            if nodename=='elphys_sync_conversion_factor':
                setattr(h, nodename, float(getattr(h, nodename)))
            nn2save.append(nodename)
        except:
            print nodename
    h.save(nn2save)
    h.close()
    
if __name__=='__main__':
    import sys
    files = os.listdir(sys.argv[1])
    func=sys.argv[2]
    for f in files:
        print files.index(f), len(files), f
        getattr(sys.modules[__name__],func)(os.path.join(sys.argv[1],f))
#    hdf52mat('/tmp/data_C1_annulus_130904850_0.hdf5')
#    mat2hdf5('/tmp/1/data_C1_annulus_130904850_0.mat')
