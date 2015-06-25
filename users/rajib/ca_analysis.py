import os
from PIL import Image
import numpy
import tifffile
from visexpman.engine.vision_experiment import cone_data,experiment_data
import scipy.ndimage.interpolation
import scipy.ndimage.filters
from pylab import *
from visexpman.engine.generic import fileop, signal,stringop,utils,introspect,geometry
frame_rate=1/0.64#s
image_scale = 0.3225#Scale Factor for X

def file2cells(filename, maxcellradius=65, sigma=0.2):
    
    image=tifffile.imread(filename)
    meanimage = image.mean(axis=0)
    try:
        from skimage.filters import threshold_otsu
    except:
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
        if 0:
            cellfolder=os.path.join(os.path.dirname(filename),'cells')
            if not os.path.exists(cellfolder):
                os.mkdir(cellfolder)
            Image.fromarray(i).save(os.path.join(cellfolder, 'cell_{0}_{1}_{2}.png'.format(os.path.basename(filename), c['row'],c['col'])))
        soma_roi=numpy.nonzero(i[:,:,0])
        if soma_roi[0].shape[0]>maxcellradius**2*numpy.pi*0.1:
            soma_rois.append(soma_roi)
    iout=numpy.zeros((meanimage.shape[0],meanimage.shape[1],3),dtype=numpy.uint8)
    iout[:,:,1]=numpy.cast['uint8'](signal.scale(meanimage,0,255))
    for r in soma_rois:
        iout[r[0],r[1],0]=60+int(100*numpy.random.random())
        iout[r[0],r[1],2]=60+int(100*numpy.random.random())
    if 0:
        for c in centers:
            iout[c['row']-2:c['row']+2,c['col']-2:c['col']+2,0]=255
    Image.fromarray(iout).save(os.path.join(os.path.dirname(filename), 'all_cells_{0}.png'.format(os.path.basename(filename))))
    return soma_rois,image
    
def process_file(filename,baseline_duration=5.0,export_fileformat = 'png', center_tolerance = 100, dfpf_threshold=0.2, maxcellradius=65, sigma=0.2):
    sr,image=file2cells(f, maxcellradius=maxcellradius, sigma=sigma)
    img=image.reshape((image.shape[0],1, image.shape[1],image.shape[2]))
#            bg=cone_data.calculate_background(img)
    bgmask=numpy.ones((image.shape[1],image.shape[2]))
    for sri in sr:
        bgmask[sri[0],sri[1]]=0
    import scipy.ndimage
    bgmask=scipy.ndimage.morphology.binary_erosion(bgmask,iterations=20,border_value=1)
    bg_activity=numpy.cast['float']((image*bgmask).mean(axis=1).mean(axis=1))
    from scipy.ndimage.filters import gaussian_filter
    bg=gaussian_filter(img.mean(axis=0)[0],150)#sigma is much bigger than cell size
    roi_curves = experiment_data.get_roi_curves(img-0*bg,sr)
    roi_curves_integral = [roi_curves[i]*sr[i][0].shape[0] for i in range(len(roi_curves))]
#            roi_curves= [rc-bg_activity for rc in roi_curves]
    max_response=0
    baselines = []
    center_cell_index = -1
    for i in range(len(roi_curves)):
        figure(1)
        clf()
        ima=numpy.zeros((image.shape[1],image.shape[2],3))
        ima[:,:,1]=signal.scale(image.mean(axis=0))
        ima[sr[i][0],sr[i][1],2]=0.4
        subplot(2,1,2)
        imshow(ima)
        subplot(2,1,1)
        baseline=roi_curves[i][:frame_rate*baseline_duration].mean()
        baselines.append(baseline)
        reponse_size=(roi_curves[i].max()-baseline)/baseline
        t=numpy.arange(roi_curves[i].shape[0])/frame_rate
        plot(t,roi_curves[i]/baseline-1)
        xlabel('t [s]')
        ylabel('df/f')
        title('max df/f: {0:0.3f}'.format(reponse_size))
        cellfolder=os.path.join(os.path.dirname(f),'cells_and_plots')
        if not os.path.exists(cellfolder):
            os.mkdir(cellfolder)
        fn=os.path.join(cellfolder, '{0}_{1}.{2}'.format(os.path.basename(f),i,export_fileformat))
        savefig(fn,dpi=200)
        roi_center = numpy.array([sr[i][0].mean(),sr[i][1].mean()])
        image_center = numpy.array(image.shape[1:])/2
        if numpy.sqrt(((image_center-roi_center)**2).sum()) < center_tolerance and reponse_size>dfpf_threshold and reponse_size>max_response:
            max_response = reponse_size
            center_cell_curve = roi_curves[i]
            center_cell_fn = fn
            center_cell_curve_integral = roi_curves_integral[i]
            center_cell_index=i
    import shutil
    shutil.copy(center_cell_fn,os.path.dirname(f))
    import scipy.io
    data={}
    data['roi_curves']=roi_curves
    data['roi_curves_normalized']=[roi_curves[i]/baselines[i] for i in range(len(roi_curves))]
    data['roi_curves_integral']=roi_curves_integral
    data['center_cell_curve']=center_cell_curve
    data['center_cell_curve_integral']=center_cell_curve_integral
    data['roi_areas']=sr
    data['image']=image
    import copy
    nonresponding_roi_curves = copy.deepcopy(roi_curves)
    del nonresponding_roi_curves[center_cell_index]
    nonresponding_roi_curves_integral = copy.deepcopy(roi_curves_integral)
    del nonresponding_roi_curves_integral[center_cell_index]
    scipy.io.savemat(f.replace('.tif','.mat'), data,oned_as='column')
    return center_cell_curve,nonresponding_roi_curves,center_cell_curve_integral,nonresponding_roi_curves_integral
    
def plot_aggregated_curves(curves, legendtxt, filename):
    figure(1)
    shifts=numpy.array([numpy.diff(c).argmax() for c in curves])
    shifts-=shifts.min()
    aligned_plots = [numpy.roll(curves[i],-shifts[i]) for i in range(len(curves))]
    clf()
    [plot(numpy.arange(p.shape[0])/frame_rate) for p in aligned_plots];
    legend(legendtxt)
    savefig(filename)

if __name__ == "__main__":
    folder='/mnt/rzws/dataslow/rajib/'
#    folder='/home/rz/codes/data/rajib/'
    folder='/tmp/rajib'
    center_cell_curves=[]
    center_cell_curves_integral=[]
    nonresponding_roi_curves = []
    nonresponding_roi_curves_integral=[]
    legendtxt=[]
    for f in fileop.listdir_fullpath(folder):
        if 'tif' not in f[-3:]: continue
#        if '006' not in f: continue
        with introspect.Timer():
            center_cell_curve,nonresponding_roi_curve,center_cell_curve_integral,nonresponding_roi_curve_integral=process_file(f)
            center_cell_curves.append(center_cell_curve)
            center_cell_curves_integral.append(center_cell_curve_integral)
            nonresponding_roi_curves.append(nonresponding_roi_curve)
            nonresponding_roi_curves_integral.append(nonresponding_roi_curve_integral)
            legendtxt.append(os.path.basename(f))
    #Saving aggregated data
    data = {'center_cell_curves':center_cell_curves, 'center_cell_curves_integral': center_cell_curves_integral,
            'nonresponding_roi_curves':nonresponding_roi_curves, 'nonresponding_roi_curve_integral':nonresponding_roi_curve_integral}
                
    scipy.io.savemat(os.path.join(folder, 'aggregated_curves.mat'), data,oned_as='column')
    plot_aggregated_curves(center_cell_curves, legendtxt, os.path.join(folder, 'center_cell_activity.png'))
    plot_aggregated_curves(center_cell_curves_integral, legendtxt, os.path.join(folder, 'center_cell_activity.png'))
#    figure(1)
#    shifts=numpy.array([numpy.diff(c).argmax() for c in center_cell_curves])
#    shifts-=shifts.min()
#    aligned_plots = [numpy.roll(center_cell_curves[i],-shifts[i]) for i in range(len(center_cell_curves))]
#    clf()
#    [plot(p) for p in aligned_plots];
#    legend(legendtxt)
#    savefig()
#    figure(2)
#    aligned_plots = [numpy.roll(center_cell_curves_integral[i],-shifts[i]) for i in range(len(center_cell_curves_integral))]
#    clf()
#    [plot(p) for p in aligned_plots];
#    legend(legendtxt)
#    savefig(os.path.join(folder, 'center_cell_activity_integral.png'))
    
    
            
            
            
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
