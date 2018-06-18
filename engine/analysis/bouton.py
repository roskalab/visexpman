from skimage.feature import register_translation
from PIL import Image
import numpy,os,unittest
from visexpman.engine.generic import fileop
            
def motion_correction(images):
    corrected=numpy.copy(images)
    for i in range(images.shape[0]):
        if i>0:
            res= register_translation(images[0], images[i])[0]
            corrected[i]=numpy.roll(numpy.roll(images[i],int(res[0]), axis=0),int(res[1]),axis=1)
    return corrected

class Test(unittest.TestCase):
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
        
if __name__ == "__main__":
    unittest.main()
