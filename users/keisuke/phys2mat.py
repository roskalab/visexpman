import sys,scipy.io,os,numpy
from visexpman.engine.vision_experiment import experiment_data
from visexpman.engine.generic import fileop,utils

def convert(folder):
    files=fileop.find_files_and_folders(folder)[1]
    for f in files:
        if os.path.splitext(f)[1]=='.phys':
            matched=[fi for fi in files if os.path.basename(f) in os.path.basename(fi) and os.path.splitext(fi)[1]=='.mat']
            if len(matched)==1:
                matdata=scipy.io.loadmat(matched[0])
                if not matdata.has_key('serialized'):
                    continue
                matdata1=utils.array2object(matdata['serialized'])
                physdata=experiment_data.read_phys(f)
                stim_sync=physdata[0][3]
                elphys=physdata[0][0]
                fsample=float(physdata[1]['Sample Rate'].replace(',','.'))
                scale=map(float,physdata[1]['Waveform Scale Factors'].replace(',','.').split(' '))                    
                matdata1['fsample']=fsample
                matdata1['sync_data']=numpy.array([elphys,stim_sync]).T
                os.remove(matched[0])
                scipy.io.savemat(matched[0],matdata1,long_field_names=True)
                print 'saved to {0}'.format(matched[0])
                
            
    
    
if __name__ == '__main__':

    convert(sys.argv[1])
