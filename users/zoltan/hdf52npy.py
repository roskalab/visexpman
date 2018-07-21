import hdf5io,numpy,os,shutil
from visexpman.engine.generic import utils,fileop

def hdf52npy(filename,out=None):
    h=hdf5io.Hdf5io(filename)
    rootnodes=[v for v in dir(h.h5f.root) if v[0]!='_']
    attrs= [a for a in dir(h.h5f.root._v_attrs) if a[0]!='_' and a.islower()]
    rootnodes.extend(attrs)
    mat_data={}
    for rn in rootnodes:
        rnt=rn
        mat_data[rnt]=h.findvar(rn)
    if mat_data.has_key('software'):
        for k in mat_data['software']['module_version'].keys():
            if mat_data['software']['module_version'][k]=='':
                mat_data['software']['module_version'][k]='unknown'
    h.close()
    matfile=filename.replace('.hdf5', '.npy')
    if out !=None:
        matfile=os.path.join(out, os.path.basename(matfile))
        dirname=os.path.dirname(matfile)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
    numpy.save(matfile,utils.object2array(mat_data))
    return matfile
    
def npy2hdf5(filename,out =None):
    data=utils.array2object(numpy.load(filename))
    if out ==None:
        fn=filename.replace('.npy', '_.hdf5')
    else:
        fn=filename.replace('.npy', '.hdf5')
    if out !=None:
        if not os.path.exists(out):
            os.makedirs(out)
        fn=os.path.join(out, os.path.basename(fn))
    h=hdf5io.Hdf5io(fn)
    for k,v in data.items():
        setattr(h, k, v)
        h.save(k)
    h.close()
    
def tree2npy(src,dst):
    files=fileop.find_files_and_folders(src)[1]
    files.sort()
    for f in files:
        print(f)
        dfolder=os.path.dirname(f.replace(src,dst))
        if not os.path.exists(dfolder):
            os.makedirs(dfolder)
        if 'hdf5' not in f:
            shutil.copy(f, dfolder)
        else:
            hdf52npy(f,dfolder)
    
def npy2tree(src,dst):
    files=fileop.find_files_and_folders(src)[1]
    files.sort()
    for f in files:
        print(f)
        dfolder=os.path.dirname(f.replace(src,dst))
        if not os.path.exists(dfolder):
            os.makedirs(dfolder)
        if 'npy' == f[-3:]:
            npy2hdf5(f,dfolder)
        else:
            shutil.copy(f, dfolder)
            
def merge_animalfiles(folder,out):
    files=fileop.find_files_and_folders(folder, filter='animal')[1]
    animal_names=set([os.path.basename(f) for f in files])
    for a in animal_names:
        matching_animal_files=[f for f in files if os.path.basename(f)==a]
        if len(matching_animal_files)>1:
            weights=[hdf5io.read_item(f, 'weight', filelocking=False) for f in matching_animal_files]
            weights=[w for w in weights if w.shape[0]>0]
            weights=numpy.concatenate(weights)    
            weights=weights[weights.argsort(axis=0)[:,0]]
            h=hdf5io.Hdf5io(os.path.join(out, a))
            h.weights=weights
            h.save('weights')
            h.close()
    
if __name__ == '__main__':
    if 1:
        f1='b:\\Zoli\\merged'
        f2='b:\\Zoli\\merged_npy'
        f3='b:\\Zoli\\merged_hdf5'
        
        #tree2npy(f1,f2)
        npy2tree(f2,f3)
    elif 0:
        merge_animalfiles('b:\\Zoli\\2merge', 'b:\\Zoli\\merged')
    
