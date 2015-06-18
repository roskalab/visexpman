import numpy
import tifffile
from visexpman.engine.vision_experiment import cone_data
import scipy.ndimage.interpolation
from pylab import *
from visexpman.engine.generic import fileop, signal,stringop,utils,introspect
#Questions to Rajib: image scale
#TODO: background !!!!!!

def file2cells(filename):
    image=tifffile.imread(filename)
    meanimage = image.mean(axis=0)
    minsomaradius = int(40*0.2)
    maxsomaradius = int(100*0.2)
    sigma = 3#should be 1 um
    threshold_factor = 1
#    img = numpy.cast['float'](image.reshape((image.shape[0], 1, image.shape[1], image.shape[2])))
#    background = cone_data.calculate_background(img,threshold=10e-2)
#    im=scipy.ndimage.interpolation.zoom(meanimage, 0.2)
#    rois = cone_data.find_rois(im[50:150,100:200], minsomaradius, maxsomaradius, sigma, threshold_factor)
    
    
    from skimage.filters import threshold_otsu
    from scipy.ndimage.filters import gaussian_filter
    from visexpA.engine.dataprocessors import signal as signal2
    centers = signal2.getextrema(gaussian_filter(meanimage,25), method = 'regmax')
    maxcellsize=300
    roisonimgr=numpy.zeros_like(meanimage)
    roisonimgb=numpy.zeros_like(meanimage)
    somarois = []
    for c in centers:
        corner = [c['row']-0.5*maxcellsize,c['row']+0.5*maxcellsize,c['col']-0.5*maxcellsize,c['col']+0.5*maxcellsize]
        for i in range(4):
            if corner[i]<0:
                corner[i]=0
            if corner[i]>meanimage.shape[i/2%2]:
                corner[i]=meanimage.shape[i/2%2]-1
        r=meanimage[corner[0]:corner[1],corner[2]:corner[3]]
        img=gaussian_filter(r,4)
        labeled, nsegments = scipy.ndimage.measurements.label(numpy.where(img>threshold_otsu(img),1,0))
        roi_pixels_w = utils.rc(numpy.where(labeled ==labeled[c['row']-corner[0]-1, c['col']-corner[2]-1]))
        roi_pixels = numpy.copy(roi_pixels_w)
        roi_pixels['row'] = roi_pixels_w['row'] + corner[0]
        roi_pixels['col'] = roi_pixels_w['col'] + corner[2]
        #Check for further segments within roi
        
        tmp=numpy.zeros_like(r)+1
        tmp[roi_pixels_w['row'],roi_pixels_w['col']]=0
        rr=numpy.copy(r)
        rr[numpy.nonzero(tmp)[0],numpy.nonzero(tmp)[1]]=r[roi_pixels_w['row'],roi_pixels_w['col']].mean()*0
        if img.shape[0]*img.shape[1]*0.25>roi_pixels.shape[0]:
            
            
            
            
            roisonimgr[roi_pixels['row'],roi_pixels['col']]=0.3+0.3*numpy.random.random(1)
            roisonimgb[roi_pixels['row'],roi_pixels['col']]=0.3+0.3*numpy.random.random(1)
            somarois.append(roi_pixels)
            ime=numpy.zeros((meanimage.shape[0],meanimage.shape[1],3),dtype=numpy.uint8)
            ime[corner[0]:corner[1],corner[2]:corner[3],1]=numpy.cast['uint8'](255*signal.scale(r,0.0,1.0))
            ime[numpy.cast['int'](roi_pixels['row']),numpy.cast['int'](roi_pixels['col'] ),2]=255
            from PIL import Image
            Image.fromarray(ime).save('/tmp/1/c_{0}_{1}.png'.format(c['row'],c['col']))
        
#        else:
#            roisonimg[c['row']-10:c['row']+10,c['col']-10:c['col']+10]=1
#    for c in centers:
#        roisonimgr[c['row']-5:c['row']+5,c['col']-5:c['col']+5]=1
    i=numpy.zeros((meanimage.shape[0],meanimage.shape[1],3))
    i[:,:,1]=signal.scale(meanimage,0,1)
    i[:,:,0]=roisonimgr
    i[:,:,2]=roisonimgb
    
    return i
    figure(1);imshow(i);show()

if __name__ == "__main__":
    folder='/mnt/rzws/dataslow/rajib/'
    ct=1
    for f in fileop.listdir_fullpath(folder):
        if 'tif' not in f: continue
        if '006' not in f: continue
        im=file2cells(f)
        figure(ct);
        subplot(1,2,1)
        imshow(im);
        subplot(1,2,2)
        im2=numpy.copy(im)
        im2[:,:,0]=0
        im2[:,:,2]=0
        imshow(im2);
        title(f);
        ct+=1
        
    show()
