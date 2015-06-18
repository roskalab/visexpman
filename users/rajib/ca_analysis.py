from PIL import Image
import numpy
import tifffile
from visexpman.engine.vision_experiment import cone_data
import scipy.ndimage.interpolation
import scipy.ndimage.filters
from pylab import *
from visexpman.engine.generic import fileop, signal,stringop,utils,introspect,geometry
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
    maxcellsize=100
    roisonimgr=numpy.zeros_like(meanimage)
    roisonimgb=numpy.zeros_like(meanimage)
    somarois = []
    for c in centers:
        if c['row']!=506: continue
        corner = [c['row']-0.5*maxcellsize,c['row']+0.5*maxcellsize,c['col']-0.5*maxcellsize,c['col']+0.5*maxcellsize]
        for i in range(4):
            if corner[i]<0:
                corner[i]=0
            if corner[i]>meanimage.shape[i/2%2]:
                corner[i]=meanimage.shape[i/2%2]-1
        r=meanimage[corner[0]:corner[1],corner[2]:corner[3]]
        img=gaussian_filter(r,4)#remove scanning aritfact
        labeled, nsegments = scipy.ndimage.measurements.label(numpy.where(img>threshold_otsu(img),1,0))
        roi_pixels_w = utils.rc(numpy.where(labeled ==labeled[c['row']-corner[0]-1, c['col']-corner[2]-1]))
        roi_pixels = numpy.copy(roi_pixels_w)
        roi_pixels['row'] = roi_pixels_w['row'] + corner[0]
        roi_pixels['col'] = roi_pixels_w['col'] + corner[2]
        
        #Check profile (curve between edge and center
        mask=geometry.circle_mask([c['row'],c['col']],maxcellsize,meanimage.shape)
        masked = mask*gaussian_filter(meanimage,2)#Remove scanning artifact
        nbsum=scipy.ndimage.filters.generic_filter(mask,sum,3)
        indexes=numpy.nonzero(numpy.where(numpy.logical_and(nbsum<9,nbsum>0),1,0))
        profile = []
        contour_pix=[]
        ds=[]
        for line in range(0,indexes[0].shape[0],indexes[0].shape[0]/36):
            endx=indexes[0][line]
            endy=indexes[1][line]
            xline=numpy.cast['int'](numpy.round(numpy.linspace(c['row'],endx,maxcellsize),0))
            yline=numpy.cast['int'](numpy.round(numpy.linspace(c['col'],endy,maxcellsize),0))
            profile.append(meanimage[xline,yline])
            d=numpy.diff(gaussian_filter(profile[-1],0.1*maxcellsize)).argmin()
            ds.append(d)
            contour_pix.append([xline[d],yline[d]])
        pass
        filled = []
        for p in range(len(contour_pix)-1):
            npix=numpy.round(numpy.sqrt((numpy.cast['float'](numpy.array(contour_pix[p])-numpy.array(contour_pix[p+1]))**2).sum()))
            filled.extend(zip(numpy.linspace(contour_pix[p][0],contour_pix[p+1][0],npix+1),numpy.linspace(contour_pix[p][1],contour_pix[p+1][1],npix+1)))
        contour_pix=filled
        #TODO: 1 Connect contour points
        #TODO: 2 Fill object
#        for p in profile:
#            numpy.diff(gaussian_filter(p,maxcellsize)).argmin()
        
        i=numpy.zeros((masked.shape[0], masked.shape[1], 3))
        i[:,:,1]=signal.scale(masked)
        coo=numpy.cast['int'](numpy.array(contour_pix).T)
        i[coo[0],coo[1],0]=1
        i=numpy.cast['uint8'](255*i)
        Image.fromarray(i).save('/tmp/1/c_{0}_{1}.png'.format(c['row'],c['col']))
#        figure(1);imshow(i);show()#figure(2);[plot(profile[i*350+170]) for i in range(4)];figure(3);[plot(numpy.diff(gaussian_filter(profile[i*350+170],0.1*maxcellsize))) for i in range(4)];show()
        #Check for further segments within roi
        
        tmp=numpy.zeros_like(r)+1
        tmp[roi_pixels_w['row'],roi_pixels_w['col']]=0
        rr=numpy.copy(r)
        rr[numpy.nonzero(tmp)[0],numpy.nonzero(tmp)[1]]=0
        if img.shape[0]*img.shape[1]*0.25>roi_pixels.shape[0]:
            
            
            
            
            roisonimgr[roi_pixels['row'],roi_pixels['col']]=0.3+0.3*numpy.random.random(1)
            roisonimgb[roi_pixels['row'],roi_pixels['col']]=0.3+0.3*numpy.random.random(1)
            somarois.append(roi_pixels)
            ime=numpy.zeros((meanimage.shape[0],meanimage.shape[1],3),dtype=numpy.uint8)
            ime[corner[0]:corner[1],corner[2]:corner[3],1]=numpy.cast['uint8'](255*signal.scale(r,0.0,1.0))
            ime[numpy.cast['int'](roi_pixels['row']),numpy.cast['int'](roi_pixels['col'] ),2]=255
            
#            Image.fromarray(ime).save('/tmp/1/c_{0}_{1}.png'.format(c['row'],c['col']))
        
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
