import numpy,unittest,os
from visexpman.engine.generic import fileop
from visexpman.engine.vision_experiment import experiment_data

settings= [{'name': 'Bouton Analysis', 'type': 'group', 'expanded' : True, 'children': [
                                {'name': 'Baseline', 'type': 'int', 'value': 3, 'siPrefix': True, 'suffix': 'frames'},
                                {'name': 'Preflash', 'type': 'int', 'value': 3, 'siPrefix': True, 'suffix': 'frames'},
                                {'name': 'Postflash', 'type': 'int', 'value': 3, 'siPrefix': True, 'suffix': 'frames'},
                                {'name': 'Significance Threshold', 'type': 'float', 'value': 3.0, 'siPrefix': True, 'suffix': 'std'},
                                {'name': 'Mean Method', 'type': 'list', 'value': 'mean', 'values':['mean','median']},
                                ]},
                {'name': 'Bouton Detection', 'type': 'group', 'expanded' : True, 'children': [
                                {'name': 'Expected cell number', 'type': 'int', 'value': 100},
                                {'name': 'Gaussian fit std', 'type': 'float', 'value': 3},
                                {'name': 'Expected response type', 'type': 'list', 'value': 'rising and falling (2)', 'values': ['rising and falling (2)', 'decay only (1)', 'any amplitude change (0)']},
                                {'name': 'Merge threshold', 'type': 'float', 'value': 0.9},
                                ]},
                                ]

def extract_bouton_increase(raw_data, rois, stimulus_parameters,baseline_n_frames,preflash_nframes,postflash_nframes,significant_threshold_std,mean_method):
    
    saturated_frames_1=numpy.where(raw_data.mean(axis=2)==255)[0]
    saturated_frames_2=numpy.where(raw_data.mean(axis=3)==255)[0]
    #It is considered saturated if a row or a column has max values
    saturated_frame_indexes=list(set(numpy.concatenate((saturated_frames_1,saturated_frames_2))))
    expected_nflashes=stimulus_parameters['NUMBER_OF_FLASHES']
    detected_nflashes=numpy.where(numpy.diff(saturated_frame_indexes)>1)[0].shape[0]+1
    if expected_nflashes < detected_nflashes:
        raise RuntimeError('Number of expected ({0}) and detected ({1}) flashes do not match'.format(expected_nflashes, detected_nflashes))
    mask=numpy.zeros(raw_data.shape[0])
    mask[saturated_frame_indexes]=1
    boundaries=numpy.nonzero(numpy.diff(mask))[0]
    boundaries+=1
    #Extract pre and post flash std values
    stats={'increase':0, 'decrease':0, 'nboutons': len(rois)}
    for roii in range(len(rois)):
        #Baseline: first n samples of raw roi trace
        baseline=rois[roii]['raw'][:baseline_n_frames].mean()
        #dF/F: raw-baseline divided by baseline
        dfoverF=(rois[roii]['raw']-baseline)/baseline
        preflash=numpy.zeros(preflash_nframes)
        postflash=numpy.zeros(postflash_nframes)
        #print boundaries
        for flashi in range(detected_nflashes):
            preflash_end=boundaries[flashi*2]
            preflash_start=preflash_end-preflash_nframes
            postflash_start=boundaries[flashi*2+1]
            postflash_end=postflash_start+postflash_nframes
            preflash+=dfoverF[preflash_start:preflash_end]/detected_nflashes
            postflash+=dfoverF[postflash_start:postflash_end]/detected_nflashes
        preflash_std=preflash.std()
        postflash_std=postflash.std()
        #Signal increase:
        preflash=getattr(numpy,mean_method)(preflash)
        postflash=getattr(numpy,mean_method)(postflash)
        increase=postflash-preflash
        is_significant=significant_threshold_std*preflash_std<abs(increase)
        rois[roii]['bouton_analysis']={'preflash_end':preflash_end,
                                                                'preflash_start':preflash_start,
                                                                'postflash_start':postflash_start,
                                                                'postflash_end':postflash_end,
                                                                'preflash_std':preflash_std,
                                                                'postflash_std':postflash_std,
                                                                'postflash':postflash,
                                                                'preflash':preflash,
                                                                'increase':increase,
                                                                'is_significant':is_significant,
                                                                }
        if is_significant:
            if increase>0:
                stats['increase']+=1
            else:
                stats['decrease']+=1
    return rois, stats
    
def find_boutons(rawdata, K, tau, p, merge_thr):
    #remove saturated frames
    saturation_value=255 if rawdata.dtype.name=='uint8' else 2**16-1
    row_means=rawdata.mean(axis=2)
    indexes=[i for i in range(row_means.shape[0]) if saturation_value in row_means[i]]
    col_means=rawdata.mean(axis=3)
    indexes.extend([i for i in range(col_means.shape[0]) if saturation_value in col_means[i]])
    keep_frame_indexes=[i for i in range(rawdata.shape[0]) if i not in indexes]
    rawdata = rawdata[keep_frame_indexes]
    import matlab.engine, scipy.io, tempfile
    fn=os.path.join(tempfile.gettempdir(), 'rd.mat')
    rd=rawdata[:,0]
    rd=numpy.rollaxis(rd, 0,3)
    scipy.io.savemat(fn, {'rawdata':rd, 'params': [float(K), float(tau), float(p), float(merge_thr)]})
    eng = matlab.engine.start_matlab()
    rois=eng.find_cells(fn)
    rois=scipy.io.loadmat(fn)['rois']
    return image2soma_rois(rois)
    
def image2soma_rois(rois):
    return [numpy.array(numpy.nonzero(rois[:,:,i])).T for i in range(rois.shape[2])]

class TestFileops(unittest.TestCase):
    @unittest.skip("")
    def test_image2soma_rois(self):
        import scipy.io
        r=scipy.io.loadmat('/home/rz/mysoftware/data/caiman/var.mat')['roiLoc']
        rois=image2soma_rois(r)
        
    @unittest.skip("")
    def test(self):
        #TODO: test for baseline and response n_frames=1 too
        #TODO: handle multiple datafolders
        #TODO: Aggregate to excel
        #TODO: give warning: preflash_nframes==1
        from pylab import plot,show
        folder='/tmp/20170711'
        baseline_n_frames=5
        preflash_nframes=5
        postflash_nframes=1
        significant_threshold_std = 3
        mean_method='mean'
        files=fileop.listdir(folder)
        files.sort()
        for f in files:
            print f
            if os.path.splitext(f)[1]!='.hdf5':
                continue
            e=experiment_data.CaImagingData(f)
            e.load('raw_data')
            e.load('rois')
            e.load('stimulus_parameters')
            if not hasattr(e, 'rois') or len(e.rois)==0:
                continue
            r,s=extract_bouton_increase(e.raw_data, e.rois, e.stimulus_parameters,baseline_n_frames,preflash_nframes,postflash_nframes,significant_threshold_std,mean_method)
            e.close()
            print s
            
    def indexofsmallestpositive(self,a):
        m=numpy.where(a<0, 0, a)
        return numpy.where(a==a[numpy.nonzero(m)[0]].min())[0][0]
    
    @unittest.skip("")
    def test_dropped_frames(self):
        folder='x:\\santiago-setup\\Acute Slice Recordings'
        import hdf5io
        fs=fileop.find_files_and_folders(folder)[1]
        for f in fs:
            if f[-5:]!='.hdf5': continue
            #if 'region18_LedConfig_201806302032023' not in f: continue
            try:
                hh=hdf5io.Hdf5io(f)
                hh.load('raw_data')
                hh.load('dropped_frames')
                hh.load('tstim')
                hh.load('timg')
                if not hasattr(hh, 'raw_data') or (not hasattr(hh, 'tstim') and all(hh.raw_data.mean(axis=2).mean(axis=2)[100:110].flatten()==0)):
                    hh.close()
                    continue
                indexes=[self.indexofsmallestpositive(hh.timg-s) for s in hh.tstim]
                if any(hh.raw_data.mean(axis=2).mean(axis=2)[indexes[0]-2:indexes[0]-1,0]>200):
                    print('Dropped frame, {0}'.format(f))
                    if hasattr(hh, 'dropped_frames'):
                        print(hh.dropped_frames)
                msg=[fs.index(f), len(fs)]
                if hasattr(hh, 'dropped_frames'):
                    msg.append(any(hh.dropped_frames))
                msg.append(hh.tstim.shape)
                print msg
                hh.close()
            except:
                pass
                
    def test_01_find_cells_and_export(self):
        folder='/data/santiago-setup/test'
        folder='y:\\santiago-setup\\test'
        for f in fileop.find_files_and_folders(folder, extension='hdf5')[1]:
            if 'data_773-1-region14_LedConfig_201806301138399' not in f:
                continue
            try:
                import hdf5io
                rawdata=hdf5io.read_item(f, 'raw_data', filelocking=False)
                K=100
                tau=3
                p=0
                merge_thr=0.9
                res=find_boutons(rawdata, K, tau, p, merge_thr)
                from pylab import savefig, imshow,cla,clf,show
                mip=rawdata.max(axis=0)[0]
                ima=numpy.zeros((mip.shape[0], 3*mip.shape[1], 3))
                ima[:,:mip.shape[1],1]=mip
                ima[:,mip.shape[1]:2*mip.shape[1],1]=mip
                for r in res:
                    for p in r:
                        ima[p[0], p[1], 0]=255
                        ima[p[0], 2*mip.shape[1]+p[1], 0]=255
                #import pdb;pdb.set_trace()
                imshow(ima/255.)
                savefig(os.path.join(folder, os.path.basename(fileop.replace_extension(f, '.png'))))
                cla()
                clf()
            except:
                import traceback
                print traceback.format_exc()
                #import pdb;pdb.set_trace()
            
            
            
            
            

if __name__=='__main__':
        unittest.main()
