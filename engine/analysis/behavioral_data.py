import hdf5io,unittest,numpy,os
from visexpman.engine.generic import introspect
from pylab import *

def extract_eyeball_area(filename,expected_eyeball_position=None, outfolder=None):
    h=hdf5io.Hdf5io(filename)
    h.load('ic_frames')
    h.load('ic_timestamps')
    h.load('airpuff_values')
    frames=h.ic_frames
    h.close()
    frame=numpy.cast['float'](frames[:5].mean(axis=0))
    from skimage.filters import threshold_otsu
    from scipy.ndimage.filters import gaussian_filter
    filtered=gaussian_filter(frame,sigma=5)
    lowest_percentage=0.1
    threshold=(filtered.max()-filtered.min())*lowest_percentage+filtered.min()
    lowest_percentage_thresholded=numpy.where(filtered>threshold,threshold,filtered)
    thresholded=numpy.where(lowest_percentage_thresholded>threshold_otsu(lowest_percentage_thresholded),0,1)
    import scipy.ndimage.measurements
    labeled, n = scipy.ndimage.measurements.label(thresholded)
    if expected_eyeball_position!=None:
        max_area_color=labeled[expected_eyeball_position[0],expected_eyeball_position[1]]
        if max_area_color==0:
            raise RuntimeError('Bad eyeball position')
    elif n==1:
        max_area_color=1
    else:
        max_area=0
        max_area_color=0
        for i in range(1,n):
            max_area = max(max_area,numpy.where(labeled==i)[0].shape[0])
            if numpy.where(labeled==i)[0].shape[0]==max_area:
                max_area_color=i
    x,y=numpy.where(labeled==max_area_color)
    roi_frame=20
    roi=frames[:,x.min()-roi_frame:x.max()+roi_frame,y.min()-roi_frame:y.max()+roi_frame]
    if min(roi.shape)==0:
        roi_frame=0
        roi=frames[:,x.min()-roi_frame:x.max()+roi_frame,y.min()-roi_frame:y.max()+roi_frame]
#    y=roi.mean(axis=1).mean(axis=1)
#    x=h.ic_timestamps
    if outfolder!=None:
        if not os.path.exists(outfolder):
            os.makedirs(outfolder)
        for i in range(frames.shape[0]):
            from PIL import Image
            im1=numpy.cast['uint8'](numpy.where(frames[i]<threshold,255,0))
            im=numpy.zeros((im1.shape[0],2*im1.shape[1],3),dtype=numpy.uint8)
            im[:,:im1.shape[1],1]=im1
            fi=numpy.zeros_like(frames[i])
            fi[x.min()-roi_frame:x.max()+roi_frame,y.min()-roi_frame:y.max()+roi_frame]=255
            im[:,im1.shape[1]:,1]=frames[i]
            im[:,im1.shape[1]:,2]=fi
            Image.fromarray(im).save(os.path.join(outfolder, 'f{0}.png'.format(i)))
    eyeball_area=numpy.where(roi<threshold,1,0).sum(axis=1).sum(axis=1)
    if h.airpuff_values.shape[0]==0:
        ap=[]
        apt=[]
    else:
        ap=h.airpuff_values[:,0]
        apt= h.airpuff_values[:,1]
    return eyeball_area, h.ic_timestamps, ap,apt
    
def eyeball_area2blink(eyeballt,t,merge_event_threshold=0.5):
    diff=numpy.diff(eyeballt)
    blinked=numpy.where(diff<-2500,1,0)
    blink_times=(t[numpy.nonzero(blinked)[0]]).T[0]
    numpy.where(numpy.diff(blink_times)<merge_event_threshold)
    return numpy.delete(blink_times,numpy.where(numpy.diff(blink_times)<merge_event_threshold)[0])

class TestBehavAnalysis(unittest.TestCase):
        
        def test_01_blink_detect(self):
            fn='/tmp/fear/data_FearResponse_1466414204.hdf5'
            folder='/tmp/fear'
            out='/tmp/out/'
            fns=os.listdir(folder)
            fns.sort()
            for fn in fns:
                if fn[-4:]!='hdf5':
                    continue
                print fn
                of=os.path.join(out,fn)
                with introspect.Timer():
                    eba, ebat, apt, ap=extract_eyeball_area(os.path.join(folder,fn),expected_eyeball_position = (360,360), outfolder=of)
                clf()
                plot(eba)
                savefig(os.path.join(out, '{0}.png'.format(fn)))
                clf()
                plot(ebat,eba)
                blink_times=eyeball_area2blink(eba,ebat)
                plot(blink_times,numpy.ones_like(blink_times)*eba.max()/2,'o')
                if apt!=[]:
                    plot(apt,ap*eba.max(),'x')
                savefig(os.path.join(out, '_t{0}.png'.format(fn)))
            pass
            

if __name__ == "__main__":
    unittest.main()
