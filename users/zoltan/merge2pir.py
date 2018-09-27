import numpy,os,shutil
from PIL import Image
from visexpman.engine.generic import fileop
import unittest
from pylab import imshow, show,figure,savefig,cla,clf,plot,xlabel,ylabel,title,legend
from skimage.feature import register_translation
from skimage.filters import threshold_otsu

def linear(x, *p):
    return p[0]*x+p[1]

class Test(unittest.TestCase):
    @unittest.skip('') 
    def test_export_for_annotation(self):
        src='/home/rz/mysoftware/data/merge/2'
        dst='/tmp/2p'
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src,dst)
        for folder in fileop.listdir(dst):
            irfn=[f for f in fileop.listdir(folder) if 'infrared' in f][0]
            sidefn=[f for f in fileop.listdir(folder) if 'side' in f][0]
            for f  in [irfn, sidefn]:
                Image.open(f).save(os.path.join(dst, '{0}_{1}.png'.format(os.path.basename(folder), f.split('_')[-3])))
            pass
    
    @unittest.skip('')
    def test_extract_centers(self):
        db={}
        for f in fileop.listdir('/home/rz/mysoftware/data/merge/annotation'):
            im=numpy.asarray(Image.open(f))
            x,y=numpy.nonzero(im[:,:,0]-im[:,:,1])
            center=x.mean(), y.mean()
            resolution=int(os.path.basename(f).split('x')[-1].split('_')[0])
            twophoton_side=int(os.path.basename(f).split('x')[-2])
            if 'infrared' in f:
                resolution=3.9
            roi_size=15
            roi_size_pixel=roi_size*resolution
            roi=im[center[0]-roi_size_pixel/2:center[0]+roi_size_pixel/2,center[1]-roi_size_pixel/2:center[1]+roi_size_pixel/2,2]
            offset=center[0]-roi_size_pixel/2, center[1]-roi_size_pixel/2
            import scipy.ndimage.measurements
            if 'infrared' in f:
                channel='ir'
                bw=numpy.where(roi>threshold_otsu(roi),1,0)
                labeled,n=scipy.ndimage.measurements.label(bw)
                selected=numpy.where(labeled==numpy.array([numpy.where(labeled==l)[0].shape[0] for l in range(1,n)]).argmax()+1,1,0)
                x,y=numpy.nonzero(selected)
                bead_center=x.mean()+offset[0], y.mean()+offset[1]
            else:
                channel='2p'
                from scipy.ndimage.morphology import binary_erosion
                bw=binary_erosion(numpy.where(roi>threshold_otsu(roi),1,0))
                labeled,n=scipy.ndimage.measurements.label(bw)
                selected=numpy.where(labeled==numpy.array([numpy.where(labeled==l)[0].shape[0] for l in range(1,n)]).argmax()+1,1,0)
                x,y=numpy.nonzero(selected)
                bead_center=x.mean()+offset[0], y.mean()+offset[1]
                
            db[(twophoton_side, resolution, channel)]=int(bead_center[0]), int(bead_center[1])
            print (twophoton_side, resolution, channel), round(bead_center[0]/resolution,1), round(bead_center[1]/resolution,1)
            imout=numpy.copy(im)
            imout[bead_center[0],bead_center[1],2]=255
            imout[bead_center[0],bead_center[1],1]=255
            Image.fromarray(imout).save(os.path.join('/tmp', os.path.basename(f)))
        print db
        
    #@unittest.skip('')
    def test_plot_bead_centers(self):
        db=numpy.array([
                [100, 1,  48.5, 60.9],
                [100, 2,  48.0, 54.9],
                [100, 3, 48.1, 52.9],
                [100, 4, 48.0, 51.9],
                [200, 1, 92.3, 106.3],
                [200, 2, 98.0, 104.8],
                [50, 2, 23.6, 30.0],
                [50, 3, 23.2, 28.0],
                [50, 4, 23.3, 27.2]
                ])
        
        for axis in ['y']:
            ff=2 if axis=='x' else 3
            figure(ff)
            x=[]
            y=[]
            for s in set(db[:,0]):
                size_offset=s/2
                title(axis)
                dat=numpy.array([dbi[[1,ff]] for dbi in db if dbi[0]==s])
                plot(dat[:,0],dat[:,1]-size_offset, 'o-')
                x.extend(dat[:,0].tolist())
                y.extend((dat[:,1]-size_offset).tolist())
            legend(set(db[:,0]))
        import scipy.optimize
        p0=[1,5]
        p=zip(x,y)
        p.sort()
        p=numpy.array(p)
        coeff, var_matrix = scipy.optimize.curve_fit(linear, p[:,0], p[:,1], p0=p0)
        plot(p[:,0], linear(p[:,0], *coeff))
        ylabel('um')
        print coeff
        show()
        
    def xcorrection(self,resolution):
        return -2.125*resolution+9.85
        
    def test_merge(self):
        for f in fileop.listdir('/home/rz/mysoftware/data/merge/2'):
            print f
            resolution2p=float(f.split('x')[-1])
            resolutionir=3.9
            side=numpy.asarray(Image.open([fi for fi in fileop.listdir(f) if 'side' in fi][0]))[:,:,0]
            ir=numpy.asarray(Image.open([fi for fi in fileop.listdir(f) if 'infra' in fi][0]))
            scale_ratio=resolutionir/resolution2p
            newsize=[side.shape[0]*scale_ratio, side.shape[1]*scale_ratio]
            newsize=map(int,newsize)
            side=numpy.asarray(Image.fromarray(side).resize(newsize))
            side_size_um=float(f.split('x')[-2])
            yoffset_um=-14.5*0+100+20
            xoffset_um=-27.4*0+100-16
            xshift_um=xoffset_um-side_size_um/2
            yshift_um=yoffset_um-side_size_um/2-self.xcorrection(resolution2p)
            merged=numpy.zeros((ir.shape[0], ir.shape[1], 3),dtype=numpy.uint8)
            merged[:,:,1]=ir
            xshift_pixel=int(xshift_um*resolutionir)
            yshift_pixel=int(yshift_um*resolutionir)
            merged_xmax=xshift_pixel+side.shape[0]
            side_xmax=side.shape[0]
            if merged_xmax>merged.shape[0]:
                merged_xmax=merged.shape[0]
                side_xmax=merged_xmax-xshift_pixel
            merged_ymax=yshift_pixel+side.shape[1]
            side_ymax=side.shape[1]
            if merged_ymax>merged.shape[1]:
                merged_ymax=merged.shape[1]
                side_ymax=merged_ymax-yshift_pixel
            try:
                merged[xshift_pixel:merged_xmax, yshift_pixel:merged_ymax,0]=side[:side_xmax,:side_ymax]*1.5
            except:
                if xshift_pixel<0:
                    try:
                        merged[:, yshift_pixel:merged_ymax,0]=side[-xshift_pixel:merged.shape[0]-xshift_pixel,:side_ymax]*1.5
                    except:
                        pass
                        pass
                        pass
                print 'error'
                pass
            #title(f)
            #imshow(merged);show()
            Image.fromarray(merged).save('/tmp/{0}.png'.format(os.path.basename(f)))
    
    
        
if __name__=='__main__':
    unittest.main()
