from skimage.feature import register_translation
from PIL import Image
import numpy,os,unittest
from visexpman.engine.generic import fileop
from visexpman.engine.vision_experiment import experiment_data
            
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
        
    def test_02_detect_cell(self):
        for f in fileop.listdir('/tmp'):
            if f[-5:]!='.hdf5':continue
            print f
            h=experiment_data.CaImagingData(f)
            h.load('raw_data')
            before=numpy.copy(h.get_image(image_type='mip')[0])
            raw1=numpy.copy(h.raw_data[:,0])
            r1=numpy.copy(h.raw_data[:,0][:,0,0])
            raw2=motion_correction(h.raw_data[:,0])
            h.raw_data[:,0]=raw2
            r2=numpy.copy(h.raw_data[:,0][:,0,0])
            after=h.get_image(image_type='mip', load_raw=False)[0]
            from pylab import *
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
        
if __name__ == "__main__":
    unittest.main()
