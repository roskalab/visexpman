import numpy,os
from PIL import Image
from visexpman.engine.generic import fileop
import unittest
from pylab import imshow, show,figure,savefig,cla,clf
from skimage.feature import register_translation
from skimage.filters import threshold_otsu

class Test(unittest.TestCase):
    def test(self):
        root='/tmp/snapshots'
        irscale=3.9#um/pixel
        offsetx=28*0
        offsety=71*0
        for folder in fileop.listdir(root):
            if not os.path.isdir(folder): continue
            scale2p=float(folder.split('x')[-1])
            side=numpy.asarray(Image.open([f for f in fileop.listdir(folder) if 'side' in f][0]))[:,:,0]
            ir=numpy.asarray(Image.open([f for f in fileop.listdir(folder) if 'infrared' in f][0]))
            ir=numpy.cast['uint8'](ir/float(ir.max())*255)
            scale_ratio=irscale/scale2p
            newsize=[side.shape[0]*scale_ratio, side.shape[1]*scale_ratio]
            newsize=map(int,newsize)
            side_scaled=numpy.asarray(Image.fromarray(side).resize(newsize))
            side_scaled=numpy.cast['uint8'](side_scaled/float(side_scaled.max())*255)
            merged=numpy.zeros([ir.shape[0],ir.shape[1],3], dtype=numpy.uint8)
            merged[:,:,1]=ir
            ir_extended=numpy.zeros((ir.shape[0]*2, ir.shape[1]*2),dtype=numpy.uint8)
            ir_extended[:ir.shape[0], :ir.shape[1]]=ir
            side_extended=numpy.zeros((ir.shape[0]*2, ir.shape[1]*2),dtype=numpy.uint8)
            side_extended[:side_scaled.shape[0], :side_scaled.shape[1]]=side_scaled
            print os.path.basename(folder), register_translation(ir_extended, side_extended)[0]
            try:
                merged[offsetx*scale2p:offsetx*scale2p+side_scaled.shape[0],offsety*scale2p:offsety*scale2p+side_scaled.shape[1],0]=side_scaled
            except:
                p=merged[offsetx*scale2p:offsetx*scale2p+side_scaled.shape[0],offsety*scale2p:offsety*scale2p+side_scaled.shape[1],0]
                side_scaled=side_scaled[:p.shape[0], :p.shape[1]]
                merged[offsetx*scale2p:offsetx*scale2p+side_scaled.shape[0],offsety*scale2p:offsety*scale2p+side_scaled.shape[1],0]=side_scaled
#            cla()
#            clf()
#            imshow(merged)
#            savefig(folder+'.png')
            Image.fromarray(merged).save(folder+'.png')
            ir_extended=numpy.where(ir_extended>threshold_otsu(ir_extended),255,0)
            side_extended=numpy.where(side_extended>threshold_otsu(side_extended),255,0)
            y,x=register_translation(ir_extended, side_extended)[0]
            shifted=numpy.zeros((ir_extended.shape[0], ir_extended.shape[1],3),dtype=numpy.uint8)
            shifted[:,:,1]=ir_extended
            p=shifted[x:x+side_extended.shape[0],y:y+side_extended.shape[1],0]
            shifted[x:x+side_extended.shape[0],y:y+side_extended.shape[1],0]=side_extended[:p.shape[0], :p.shape[1]]
#            cla()
#            clf()
#            imshow(shifted)
#            savefig(folder+'_shifted.png')
            
            
        
if __name__=='__main__':
    unittest.main()
