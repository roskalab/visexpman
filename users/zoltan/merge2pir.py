import numpy,os
from PIL import Image
from visexpman.engine.generic import fileop
import unittest
from pylab import imshow, show,figure,savefig,cla,clf,plot,xlabel,ylabel,title
from skimage.feature import register_translation
from skimage.filters import threshold_otsu

def linear(x, *p):
    return p[0]*x+p[1]

class Test(unittest.TestCase):
    def test_01_evaluate_2p_center_shift(self):
        #Size, resolution, centerx, centery
        data=numpy.array([[50,2,119,99], 
                    [50, 3, 108,94],
                    [50, 4, 103, 96],
                    [100, 1, 236, 198],
                    [100, 2, 212, 192],
                    [100, 3, 205, 192],
                    [100, 4, 200, 192],
                    [200, 1, 431, 387],
                    [200, 2, 407, 388]])
        #calculate centers in um, origin is the center of 2p window
        ir_scale=3.9
        coo_pixel=data[:,2:]-data[:,:1]/2*ir_scale
        coo_um=numpy.round(coo_pixel/3.9,2)
        title('Resolution dependency of an object\'s x coordinate')
        xy=numpy.array([data[:,1],coo_um[:,0]])
        xy=xy[:,numpy.argsort(xy)[0]]
        #Fit a linear curve
        import scipy.optimize
        p0=[1,0]
        coeff, var_matrix = scipy.optimize.curve_fit(linear, xy[0][2:], xy[1][2:], p0=p0)
        plot(xy[0], xy[1], 'o');xlabel('resolution [um/pixel]');ylabel('centerx coo [um]');
        plot(xy[0], linear(xy[0], *coeff))
        show()
                    
    def xcorrection(self,resolution):
        return -1.72382353*resolution+8.09235294-2.62
        
    def test_02(self):
        root='/tmp/snapshots'
        irscale=3.9#um/pixel
        offsetxcal=94#in um
        offsetycal=54
        for folder in fileop.listdir(root):
            if not os.path.isdir(folder): continue
            scale2p=float(folder.split('x')[-1])
            scan_size=float(folder.split('x')[-2])/scale2p
            side=numpy.asarray(Image.open([f for f in fileop.listdir(folder) if 'side' in f][0]))[:,:,0]
            ir=numpy.asarray(Image.open([f for f in fileop.listdir(folder) if 'infrared' in f][0]))
            ir=numpy.cast['uint8'](ir/float(ir.max())*255)
            scale_ratio=irscale/scale2p
            newsize=[side.shape[0]*scale_ratio, side.shape[1]*scale_ratio]
            newsize=map(int,newsize)
            #scale up 2p image to ir's resulution
            side_scaled=numpy.asarray(Image.fromarray(side).resize(newsize))
            side_scaled=numpy.cast['uint8'](side_scaled/float(side_scaled.max())*255)
            merged=numpy.zeros([ir.shape[0],ir.shape[1],3], dtype=numpy.uint8)
            merged[:,:,1]=ir
            ir_extended=numpy.zeros((ir.shape[0]*2, ir.shape[1]*2),dtype=numpy.uint8)
            ir_extended[:ir.shape[0], :ir.shape[1]]=ir
            side_extended=numpy.zeros((ir.shape[0]*2, ir.shape[1]*2),dtype=numpy.uint8)
            side_extended[:side_scaled.shape[0], :side_scaled.shape[1]]=side_scaled
            print os.path.basename(folder), register_translation(ir_extended, side_extended)[0]
            #Calculate offsets:
            offsety=offsetycal-(scan_size/2-50/2)#50: image size used for calibration
            offsetx=offsetxcal-(scan_size/2-50/2)-self.xcorrection(scale2p)
            offsety*=irscale
            offsetx*=irscale
            try:
                merged[offsetx*scale2p:offsetx*scale2p+side_scaled.shape[0],offsety*scale2p:offsety*scale2p+side_scaled.shape[1],0]=side_scaled
            except:
                p=merged[offsetx:offsetx+side_scaled.shape[0],offsety:offsety+side_scaled.shape[1],0]
                side_scaled=side_scaled[:p.shape[0], :p.shape[1]]
                merged[offsetx:offsetx+side_scaled.shape[0],offsety:offsety+side_scaled.shape[1],0]=side_scaled
            Image.fromarray(merged).save(folder+'.png')
        
if __name__=='__main__':
    unittest.main()
