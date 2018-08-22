import numpy
from PIL import Image
from visexpman.engine.generic import fileop
import unittest
from pylab import imshow, show,figure

class Test(unittest.TestCase):
    def test(self):
        root='/home/rz/mysoftware/data/merge'
        irscale=3.9#um/pixel
        offsety=120
        offsetx=73
        for folder in fileop.listdir(root):
            scale2p=float(folder.split('x')[-1])
            side=numpy.asarray(Image.open([f for f in fileop.listdir(folder) if 'side' in f][0]))[:,:,0]
            ir=numpy.asarray(Image.open([f for f in fileop.listdir(folder) if 'infrared' in f][0]))
            scale_ratio=irscale/scale2p
            newsize=[side.shape[0]*scale_ratio, side.shape[1]*scale_ratio]
            newsize=map(int,newsize)
            side_scaled=numpy.asarray(Image.fromarray(side).resize(newsize))
            merged=numpy.zeros([ir.shape[0],ir.shape[1],3], dtype=numpy.uint8)
            merged[:,:,2]=ir
            merged[offsetx*scale2p:offsetx*scale2p+side_scaled.shape[0],offsety*scale2p:offsety*scale2p+side_scaled.shape[1],0]=side_scaled
            
            pass
            
        
if __name__=='__main__':
    unittest.main()
