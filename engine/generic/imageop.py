'''
Image related operations
'''
import unittest,os, numpy
from PIL import Image
from visexpman.engine.generic import fileop

def save(fn, img):
    '''
    Save numpy array as image, pixel values shall be in 0..1 range. grayscale or rgb numpy arrays supported
    '''
    Image.fromarray(numpy.cast['uint8'](img*255)).save(fn)
    
def torgb(img, channel=1):
    imgout=numpy.zeros((img.shape[0], img.shape[1], 3), dtype=img.dtype)
    imgout[:, :, channel]=img
    return imgout

def rotate_folder(src, dst, rot):
    print(src)
    files=fileop.find_files_and_folders(src)[1]
    for f in files:
        img=Image.open(f)
        rotated=img.rotate(rot)
        fout=os.path.join(dst, os.path.relpath(f,src))
        if not os.path.exists(os.path.dirname(fout)):
            os.makedirs(os.path.dirname(fout))
        rotated.save(fout)
        
def get_edge_pixels(img):
    return numpy.concatenate((img[0,:],img[-1,:],img[:,0],img[:,-1]))
        
def object_touching_edges(img):
    return get_edge_pixels(img).any()
    
def remove_edge_objects(img):
    if len(img.shape)!=2:
        raise NotImplementedError()
    import scipy.ndimage
    labels, n=scipy.ndimage.label(img)
    edge_pixels=list(set(get_edge_pixels(labels).tolist()))
    edge_pixels.sort()
    edge_pixels=edge_pixels[1:]
    if len(edge_pixels)==0:
        return img
    pixels2remove=numpy.concatenate([numpy.array(numpy.where(labels==ep)).T for ep in edge_pixels])
    img[pixels2remove[:,0],pixels2remove[:,1]]=0
    return img
    
class ImageOpTest(unittest.TestCase):
    def test_01_rotate_folder(self):
        import numpy,tempfile,shutil
        nfiles=10
        wf=os.path.join(tempfile.gettempdir(),'img','imgsub')
        dst=os.path.join(tempfile.gettempdir(),'imgrot')
        for d in [wf, dst]:
            if os.path.exists(d):
                shutil.rmtree(d)
            os.makedirs(d)
        img1=numpy.zeros((100,100,3),dtype=numpy.uint8)
        img1[:,10:20,0]=255
        img2=numpy.zeros((100,100),dtype=numpy.uint8)
        img2[:,20:40]=200
        for i in range(nfiles):
            img=numpy.roll(numpy.copy(img1),i,axis=1)
            Image.fromarray(img).save(os.path.join(wf, 'rgb_{0}.png'.format(i)))
            img=numpy.roll(numpy.copy(img2),i,axis=1)
            Image.fromarray(img).save(os.path.join(wf, 'gray_{0}.jpeg'.format(i)))
        for rot in range(45,180, 45):
            rotate_folder(os.path.dirname(wf), dst+str(rot), rot)
        
if __name__=='__main__':
        unittest.main()
