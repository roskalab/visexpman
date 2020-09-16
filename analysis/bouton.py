from skimage.feature import register_translation
from PIL import Image
import numpy,os,unittest, time
from visexpman.generic import fileop
from visexpman.vision_experiment import experiment_data
            
def motion_correction(images):
    corrected=numpy.copy(images)
    for i in range(images.shape[0]):
        if i>0:
            res= register_translation(images[0], images[i])[0]
            #print((res[0], res[1]))
            corrected[i]=numpy.roll(numpy.roll(images[i],int(res[0]), axis=0),int(res[1]),axis=1)
    return corrected
    
class Test(unittest.TestCase):
    @unittest.skip("")
    def test_01_motion_correction(self):
        from pylab import plot,show,legend,ylim
        folders=['More smear/716-18d-vivo-m1-reg3-rep1-LGN-2levels',
            'No smear/716-18d-vivo-m1-reg4-rep1-LGN',
            'A little bit of smear/716-18d-vivo-m1-reg2-rep1-LGN']

        for folder in folders:
            folder=os.path.join('/home/rz/mysoftware/data/Santiago',folder)
            files=fileop.listdir(folder)
            files.sort()
            images=[numpy.asarray(Image.open(f))for f in files if os.path.splitext(f)[1]=='.png']
            images=[i for i in images if numpy.where(i.sum(axis=1)==255*i.shape[1])[0].shape[0]==0]
            images=numpy.array(images)
            mip=images.max(axis=0)
            
            shift=[]
            for i in range(len(images)):
                if i>0:
                    res= register_translation(images[0], images[i])[0]
                    shift.append(res)
            shift=numpy.array(shift)
            out=motion_correction(images)
            mipout=numpy.array(out).max(axis=0)
            Image.fromarray(mip).save(os.path.join(os.path.dirname(folder), 'mipin_{0}.png'.format(os.path.basename(os.path.dirname(folder)))))
            Image.fromarray(mipout).save(os.path.join(os.path.dirname(folder), 'mipout_{0}.png'.format(os.path.basename(os.path.dirname(folder)))))
            plot(shift[:,0])
            plot(shift[:,1])
        ylim([-10,10])
        legend(['no smear x', 'no smear y', 'little smear x', 'little smear y', 'more smear x', 'more smear y'])
        show()

    @unittest.skip("")        
    def test_02_detect_cell(self):
        for f in fileop.listdir('/tmp'):
            if f[-5:]!='.hdf5':continue
            print(f)
            h=experiment_data.CaImagingData(f)
            h.load('raw_data')
            rd=numpy.array([i for i in h.raw_data if numpy.where(i.sum(axis=1)==255*i.shape[1])[0].shape[0]==0])
            import cone_data
            t0=time.time()
            mc=motion_correction(rd)
            print time.time()-t0
            mi=mc.max(axis=0)[0]
            minsomaradius=2*2
            maxsomaradius=2*4
            rois=cone_data.find_rois(mi, minsomaradius, maxsomaradius, 0.2*maxsomaradius,1)
            rois=[cone_data.area2edges(r) for r in rois]
            minew=numpy.zeros((mi.shape[0], mi.shape[1], 3))
            minew[:,:,1]=mi
            c=100
            for r in rois:
                minew[r[:,0], r[:,1],0]=255
                c+=1
            from pylab import imshow,show
            o=numpy.cast['uint8'](minew/minew.max()*255)
            Image.fromarray(o).save(fileop.replace_extension(f, '.png'))
            continue
            imshow(o);show()
            before=numpy.copy(h.get_image(image_type='mip')[0])
            raw1=numpy.copy(h.raw_data[:,0])
            r1=numpy.copy(h.raw_data[:,0][:,0,0])
            raw2=motion_correction(h.raw_data[:,0])
            h.raw_data[:,0]=raw2
            r2=numpy.copy(h.raw_data[:,0][:,0,0])
            after=h.get_image(image_type='mip', load_raw=False)[0]
            from pylab import figure, imshow,show
#            figure(1);imshow(h.raw_data[:,0].mean(axis=0));figure(2);imshow(corrected.mean(axis=0));show()
            #figure(1);imshow(before);
            #figure(2);imshow(after);
            from skimage import filters
            thr=filters.threshold_otsu(after)
            bw=numpy.where(after>thr,1,0)
            import skimage.segmentation, scipy.ndimage.morphology, scipy.ndimage.measurements
            labeled, n = scipy.ndimage.measurements.label(bw)
            labeled=skimage.segmentation.clear_border(labeled)
            labeled=scipy.ndimage.morphology.binary_fill_holes(labeled)
            
            figure(1);imshow(after)
            figure(2);imshow(labeled)
            
            
            show()
            h.close()

    def test_03_detect_cell_caiman(self):
        folder='D:\\Santiago\\716-18d-vivo-m1-reg4-rep1-LGN'
        import caiman
        from caiman.source_extraction import cnmf as cnmf
        frames=[]
        for f in os.listdir(folder):
            try:
                frame=numpy.asarray(Image.open(os.path.join(folder, f)))
                frames.append(frame)
            except:
                pass
        Y=numpy.array(frames, dtype=numpy.float)
        K = 100
        tau = 3
        p = 1
        merge_thr = 0.8
        n_processes=7
        options = cnmf.utilities.CNMFSetParms(Y, n_processes, p=p, gSig=[tau], K=K,
                method_init='dilate',thr=merge_thr)
        options['spatial_params']['dist']=3
        options['temporal_params']['fudge_factor']=0.98

        res=cnmf.pre_processing.preprocess_data(Y, p)
        Y=res[0]
        P=res[1]
        res=cnmf.initialization.initialize_components(Y,K,[tau, tau],options_total=options,sn=P)
        center=numpy.cast['int'](res[4])
        ca=res[1]
        mi=Y.mean(axis=0)
        mii=numpy.zeros((mi.shape[0]+20, mi.shape[1]+20))
        mii[:mi.shape[0], :mi.shape[1]]=mi
        mii[center[:,1], center[:,0]]=0
        from pylab import imshow, show
        imshow(mii);show()
        import pdb;pdb.set_trace()

        
        
        
if __name__ == "__main__":
    unittest.main()
