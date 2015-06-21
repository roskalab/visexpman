import os
from PIL import Image
import numpy
import tifffile
from visexpman.engine.vision_experiment import cone_data,experiment_data
import scipy.ndimage.interpolation
import scipy.ndimage.filters
from pylab import *
from visexpman.engine.generic import fileop, signal,stringop,utils,introspect,geometry
#Questions to Rajib: image scale
#TODO: background !!!!!!
frame_rate=1

def file2cells(filename, maxcellradius=65, sigma=0.2):
    
    image=tifffile.imread(filename)
    meanimage = image.mean(axis=0)
    from skimage.filter import threshold_otsu
    from scipy.ndimage.filters import gaussian_filter
    from skimage.feature import peak_local_max
    centers = utils.rc(peak_local_max(gaussian_filter(meanimage,sigma*maxcellradius),sigma*maxcellradius))
    soma_rois = []
    for c in centers:
        corner = [c['row']-0.5*maxcellradius,c['row']+0.5*maxcellradius,c['col']-0.5*maxcellradius,c['col']+0.5*maxcellradius]
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
        mask=geometry.circle_mask([c['row'],c['col']],maxcellradius,meanimage.shape)
        masked = mask*gaussian_filter(meanimage,2)#Remove scanning artifact
        profile = []
        contour_pix=[]
        ds=[]
        lines=[]
        for angle in range(0, 360,20):
            endx=c['row']+numpy.cos(numpy.radians(angle))*maxcellradius
            endy=c['col']+numpy.sin(numpy.radians(angle))*maxcellradius
            if endx<0:
                endx=0
            if endy<0:
                endy=0
            if endx>meanimage.shape[0]-1:
                endx=meanimage.shape[0]-1
            if endy>meanimage.shape[1]-1:
                endy=meanimage.shape[1]-1
            xline=numpy.cast['int'](numpy.round(numpy.linspace(c['row'],endx,maxcellradius),0))
            yline=numpy.cast['int'](numpy.round(numpy.linspace(c['col'],endy,maxcellradius),0))
            profile.append(meanimage[xline,yline])
            d=numpy.where(numpy.diff(numpy.where(profile[-1]<threshold_otsu(profile[-1]),0,1))==-1)[0]
            #print angle, numpy.where(numpy.diff(numpy.where(profile[-1]<threshold_otsu(profile[-1]),0,1))==-1), numpy.where(numpy.diff(numpy.where(profile[-1]<threshold_otsu(profile[-1]),0,1))==1)
            if d.shape[0]==0:
                if len(ds)>0:
                    d=ds[-1]
                else:
                    d=maxcellradius-1
            else:
                d=d[0]
            ds.append(d)
            lines.append([xline,yline])
        dsf=gaussian_filter(ds,1)
        for a in range(len(lines)):
            xline=lines[a][0]
            yline=lines[a][1]
            d=dsf[a]
            contour_pix.append([xline[d],yline[d]])

        import copy
        cc=copy.deepcopy(contour_pix)
        filled = []
        for p in range(len(contour_pix)):
            if p==len(contour_pix)-1:
                i1=p
                i2=0
            else:
                i1=p
                i2=p+1
            npix=numpy.round(numpy.sqrt((numpy.cast['float'](numpy.array(contour_pix[i1])-numpy.array(contour_pix[i2]))**2).sum()))
            filled.extend(zip(numpy.linspace(contour_pix[i1][0],contour_pix[i2][0],npix+1),numpy.linspace(contour_pix[i1][1],contour_pix[i2][1],npix+1)))
        contour_pix=filled
        coo=numpy.cast['int'](numpy.array(contour_pix).T)
        roimask=numpy.zeros_like(masked)
        roimask[coo[0],coo[1]]=1
        i=numpy.zeros((masked.shape[0], masked.shape[1], 3))
        i[:,:,1]=signal.scale(masked)
        i[coo[0],coo[1],0]=1
        i[:,:,0] = scipy.ndimage.morphology.binary_fill_holes(i[:,:,0])
        i=numpy.cast['uint8'](255*i)
        Image.fromarray(i).save('/tmp/1/c_{0}_{1}_{2}.png'.format(os.path.basename(filename), c['row'],c['col']))
        soma_roi=numpy.nonzero(i[:,:,0])
        if soma_roi[0].shape[0]>maxcellradius**2*numpy.pi*0.1:
            soma_rois.append(soma_roi)
    iout=numpy.zeros((meanimage.shape[0],meanimage.shape[1],3),dtype=numpy.uint8)
    iout[:,:,1]=numpy.cast['uint8'](signal.scale(meanimage,0,255))
    for r in soma_rois:
        iout[r[0],r[1],0]=60+int(100*numpy.random.random())
        iout[r[0],r[1],2]=60+int(100*numpy.random.random())
    for c in centers:
        iout[c['row']-2:c['row']+2,c['col']-2:c['col']+2,0]=255
    Image.fromarray(iout).save('/tmp/2/{0}.png'.format(os.path.basename(filename)))
    return soma_rois
    

    

if __name__ == "__main__":
    folder='/mnt/rzws/dataslow/rajib/'
    folder='/home/rz/codes/data/rajib/'
    ct=1
    curves=[]
    for f in fileop.listdir_fullpath(folder):
        if 'tif' not in f: continue
#        if '006' not in f: continue
        with introspect.Timer():
            sr=file2cells(f)
            image=tifffile.imread(f)
            img=image.reshape((image.shape[0],1, image.shape[1],image.shape[2]))
#            bg=cone_data.calculate_background(img)
            bgmask=numpy.ones((image.shape[1],image.shape[2]))
            for sri in sr:
                bgmask[sri[0],sri[1]]=0
            bgmask=scipy.ndimage.morphology.binary_erosion(bgmask,iterations=20,border_value=1)
            bg_activity=numpy.cast['float']((image*bgmask).mean(axis=1).mean(axis=1))
            from scipy.ndimage.filters import gaussian_filter
            bg=gaussian_filter(img.mean(axis=0)[0],150)#sigma is much bigger than cell size
            roi_curves = experiment_data.get_roi_curves(img-bg,sr)
#            roi_curves= [rc-bg_activity for rc in roi_curves]
            for i in range(len(roi_curves)):
                figure(1)
                clf()
                ima=numpy.zeros((image.shape[1],image.shape[2],3))
                ima[:,:,1]=signal.scale(image.mean(axis=0))
                ima[sr[i][0],sr[i][1],2]=0.4
                subplot(2,1,1)
                imshow(ima)
                subplot(2,1,2)
                baseline=roi_curves[i][:frame_rate*5].mean()
                reponse_size=(roi_curves[i].max()-baseline)/baseline
                plot(roi_curves[i])
                title(reponse_size)
                savefig('/tmp/3/{0}_{1}.png'.format(os.path.basename(f),i))
                curves.append(roi_curves[i])
    figure(2)
    [plot(c) for c in curves];show()
            
            
            
#            plot(roi_curves);show()
#        figure(ct);
#        subplot(1,2,1)
#        imshow(im);
#        subplot(1,2,2)
#        im2=numpy.copy(im)
#        im2[:,:,0]=0
#        im2[:,:,2]=0
#        imshow(im2);
#        title(f);
#        ct+=1
        
#    show()
