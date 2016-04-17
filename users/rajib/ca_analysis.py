import os
from PIL import Image
import numpy
import tifffile
from visexpman.engine.vision_experiment import cone_data,experiment_data
import scipy.ndimage.interpolation
import scipy.ndimage.filters
from pylab import *
from visexpman.engine.generic import fileop, utils,introspect,geometry,signal
image_scale = 0.3225#Scale Factor for X

def file2cells(filename, maxcellradius=65, sigma=0.2):
    if os.path.isdir(filename):
        tfs=fileop.listdir_fullpath(filename)
        tfs.sort()
        image=numpy.array([tifffile.imread(fi) for fi in tfs if 'tif' in os.path.splitext(fi)[1]])
    else:
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
    
def process_file(filename,baseline_duration=5.0,export_fileformat = 'png', center_tolerance = 100, dfpf_threshold=0.2, maxcellradius=65, sigma=0.2, frame_rate=1):
    f=filename
    sr,image=file2cells(f, maxcellradius=maxcellradius, sigma=sigma)
    img=image.reshape((image.shape[0],1, image.shape[1],image.shape[2]))
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
    max_response=0
    baselines = []
    stimulated_cell_index = -1
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
            stimulated_cell_curve = roi_curves[i]/baselines[i]
            stimulated_cell_fn = fn
            stimulated_cell_curve_integral = roi_curves_integral[i]
            stimulated_cell_index=i
            
    import shutil
    shutil.copy(stimulated_cell_fn,os.path.dirname(f))
    
    import scipy.io
    data={}
    data['roi_curves']=roi_curves
    data['roi_curves_normalized']=[roi_curves[i]/baselines[i] for i in range(len(roi_curves))]
    data['roi_curves_integral']=roi_curves_integral
    data['stimulated_cell_curve']=stimulated_cell_curve
    data['stimulated_cell_curve_integral']=stimulated_cell_curve_integral
    data['roi_areas']=sr
    data['image']=image
    import copy
    nonresponding_roi_curves = copy.deepcopy(data['roi_curves_normalized'])
    del nonresponding_roi_curves[stimulated_cell_index]
    nonresponding_roi_curves_integral = copy.deepcopy(roi_curves_integral)
    del nonresponding_roi_curves_integral[stimulated_cell_index]
    scipy.io.savemat(f.replace('.tif','.mat'), data,oned_as='column')
    return stimulated_cell_curve,nonresponding_roi_curves,stimulated_cell_curve_integral,nonresponding_roi_curves_integral
    
def plot_aggregated_curves(curves, legendtxt, filename,baseline_duration,ylab,plot_mean_only=False,frame_rate=1):
    figure(1)
    shifts=numpy.array([numpy.diff(c).argmax() for c in curves])
    shifts-=shifts.min()
    aligned_plots = [numpy.roll(curves[i],-shifts[i]) for i in range(len(curves))]
    aligned_plots = [p-p[-baseline_duration*frame_rate:].mean() for p in aligned_plots]
    trace_min_size=min([p.shape[0] for p in aligned_plots])
    truncated = [p[:trace_min_size] for p in aligned_plots]
    mean=numpy.array(truncated).mean(axis=0)
    std=numpy.array(truncated).std(axis=0)
    clf()
    if not plot_mean_only:
        [plot(numpy.arange(p.shape[0])/frame_rate, p,'x-') for p in aligned_plots]
        legend(legendtxt)
        ylabel(ylab)
        xlabel('time [s]')
        savefig(filename,dpi=200)
    clf()
    t=numpy.arange(mean.shape[0])/frame_rate
    plot(t,mean,'o-')
    plot(t,mean-std,'^-')
    plot(t,mean+std,'v-')
    ylabel(ylab)
    xlabel('time [s]')
    meanlegend=['mean', 'std', 'std']
    legend(meanlegend)
    tags=filename.split('.')
    tags[-2]+='_mean_std'
    savefig('.'.join(tags), dpi=200)
    return mean,std
    
def process_folder(folder, baseline_duration=5,export_fileformat = 'png',center_tolerance = 100, dfpf_threshold=0.2, maxcellradius=65, sigma=0.2, frame_rate=1, ppenable=False):
    files=[f for f in fileop.listdir_fullpath(folder) if 'tif' in f[-3:]]
    if len(files)==0:#series of tifffiles in folder
        files=[f for f in fileop.listdir_fullpath(folder) if os.path.isdir(f)]
    cc=[]#center cell curve
    cc_int=[]#central cell integral curve
    nrc=[]#not responding cell curves
    nrc_int = []#not responding cell integral curves
    legendtxt=[os.path.basename(f) for f in files]
    if ppenable:
        import multiprocessing
        pars=[[f, baseline_duration,export_fileformat,center_tolerance, dfpf_threshold, maxcellradius, sigma,frame_rate] for f in files]
        p=multiprocessing.Pool(introspect.get_available_process_cores())
        res=[p.apply_async(process_file, par) for par in pars]
        p.close()
        p.join()
        for r in res:
            stimulated_cell_curves,nonresponding_roi_curves,stimulated_cell_curves_integral,nonresponding_roi_curves_integral=r.get()
            cc.append(stimulated_cell_curves)
            cc_int.append(stimulated_cell_curves_integral)
            nrc.extend(nonresponding_roi_curves)
            nrc_int.extend(nonresponding_roi_curves_integral)
    else:
        for f in files:
            print 'processing', f
            with introspect.Timer():
                try:
                    stimulated_cell_curves,nonresponding_roi_curves,stimulated_cell_curves_integral,nonresponding_roi_curves_integral=\
                                    process_file(f,baseline_duration=baseline_duration,export_fileformat=export_fileformat,center_tolerance = center_tolerance, dfpf_threshold=dfpf_threshold, maxcellradius=maxcellradius, sigma=sigma,frame_rate=frame_rate)
                    cc.append(stimulated_cell_curves)
                    cc_int.append(stimulated_cell_curves_integral)
                    nrc.extend(nonresponding_roi_curves)
                    nrc_int.extend(nonresponding_roi_curves_integral)
                except:
                    pass
    cc_mean,cc_std=plot_aggregated_curves(cc, legendtxt, os.path.join(folder, 'stimulated_cell.'+export_fileformat),baseline_duration,'df/f',frame_rate=frame_rate)
    cc_int_mean,cc_int_std=plot_aggregated_curves(cc_int, legendtxt, os.path.join(folder, 'stimulated_cell_integrated.'+export_fileformat),baseline_duration, 'integral activity',frame_rate=frame_rate)
    nrc_mean,nrc_std=plot_aggregated_curves(nrc, legendtxt, os.path.join(folder, 'not_responding_cells.'+export_fileformat),baseline_duration,'df/f',plot_mean_only=True,frame_rate=frame_rate)
    nrc_int_mean, nrc_int_std = plot_aggregated_curves(nrc_int, legendtxt, os.path.join(folder, 'not_responding_cells_intergated.'+export_fileformat),baseline_duration, 'integral activity',plot_mean_only=True,frame_rate=frame_rate)
    
    #Saving aggregated data
    data ={'stimulated_cell': cc, 'stimulated_cell_mean': cc_mean, 'stimulated_cell_std': cc_std, 
                'stimulated_cell_integrated': cc_int, 'stimulated_cell_integrated_mean': cc_int_mean, 'stimulated_cell_integrated_std': cc_int_std, 
                'not_responding_cells': nrc, 'not_responding_cells_mean': nrc_mean, 'not_responding_cells_std': nrc_std, 
                'not_responding_cells_integrated': nrc_int, 'not_responding_cells_integrated_mean': nrc_int_mean, 'not_responding_cells_integrated_std': nrc_int_std}
    analysis_parameters = {'folder':folder, 'baseline_duration':baseline_duration,'export_fileformat' : export_fileformat,'center_tolerance' : center_tolerance, 'dfpf_threshold':dfpf_threshold, maxcellradius:'maxcellradius', sigma:'sigma', frame_rate:'frame_rate'}
    data['analysis_parameters']=analysis_parameters
    scipy.io.savemat(os.path.join(folder, 'aggregated_curves.mat'), data,oned_as='column')

if __name__ == "__main__":
    folder='/mnt/rzws/dataslow/rajib/'
#    folder='/home/rz/codes/data/rajib/'
    folder='/tmp/tiffs'
    baseline_duration=5
    export_fileformat = 'png'
    frame_rate=1/0.64#s
    frame_rate=1#s
    process_folder(folder, baseline_duration,export_fileformat,center_tolerance = 100, dfpf_threshold=0.2, maxcellradius=65/2, sigma=0.2, frame_rate=frame_rate,ppenable=not True)    
    
