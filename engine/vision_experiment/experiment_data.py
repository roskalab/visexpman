import zipfile,multiprocessing
import io
import os
import os.path
import copy
import numpy
import scipy.io
import unittest
import shutil
import tempfile
import time,datetime
import StringIO
from PIL import Image,ImageDraw
import matplotlib
matplotlib.use('Qt4Agg')
from pylab import show,plot,imshow,figure,title,subplot,savefig, cla, clf,xlabel,ylabel,gca,Rectangle
from visexpman.engine.generic import utils,fileop,signal,videofile,introspect
try:
    import hdf5io
    hdf5io_available=True
except ImportError:
    print 'hdf5io not installed'
    hdf5io_available=False
FRAME_RATE_TOLERANCE=5    

#### Recording filename handling ####

def add_mat_tag(fn):
    '''
    when hdf5 measurement files converted to mat, a "_mat" tag is appended to the filename
    '''
    if os.path.splitext(fn)[0][-4:]=='_mat':#No modification when already appended
        return fn
    ext=os.path.splitext(fn)[1] 
    if ext in ['.hdf5']:
        return fn.replace(ext, '_mat'+ext)
    else:
        raise NotImplementedError('')
    

def get_recording_name(parameters, separator):
    name = ''
    for k in ['animal_id', 'scan_mode', 'region_name', 'cell_name', 'depth', 'stimclass', 'id', 'counter']:
        if parameters.has_key(k) and parameters[k]!='':
            name += str(parameters[k])+separator
    return name[:-1]
    
def get_recording_filename(config, parameters, prefix):
    if prefix != '':
        prefix = prefix + '_'
    return prefix + get_recording_name(parameters, '_')+'.'+config.EXPERIMENT_FILE_FORMAT

def get_recording_path(config, parameters, prefix = ''):
    return os.path.join(get_user_experiment_data_folder(parameters), get_recording_filename(config, parameters, prefix))
    
def get_user_experiment_data_folder(parameters):
    '''
    Returns path to folder where user's experiment data can be saved
    '''
    if not parameters.has_key('outfolder'):
        raise RuntimeError('outfolder is not available')
    user_experiment_data_folder = parameters['outfolder']
    if not os.path.exists(user_experiment_data_folder):
        os.makedirs(user_experiment_data_folder)
    return user_experiment_data_folder
    
def find_recording_filename(id, config_or_path):
    if isinstance(config_or_path,str):
        foldername = config_or_path
    else:
        foldername = get_user_experiment_data_folder(config_or_path)
    res = [fn for fn in fileop.listdir_fullpath(foldername) if id in fn]
    if len(res)==1:
        return res[0]
    
def parse_recording_filename(filename):
    items = {}
    items['folder'] = os.path.split(filename)[0]
    items['file'] = os.path.split(filename)[1]
    items['extension'] = os.path.splitext(filename)[1]
    fnp = items['file'].replace('.'+items['extension'],'').split('_')
    items['type'] = fnp[0]
    #Find out if there is a counter at the end of the filename. (Is last item 1 character long?)
    offset = 2 if len(fnp[-1]) == 1 else 1
    items['id'] = fnp[-offset]
    items['experiment_name'] = fnp[-1-offset]
    items['tag'] = fnp[1]
    return items
        
def is_recording_filename(filename):
    try:
        items = parse_recording_filename(filename)
        idnum = int(items['id'])
        return True
    except:
        return False
    
def find_recording_files(folder):
    allhdf5files = fileop.find_files_and_folders(folder, extension = 'hdf5')[1]
    return [f for f in allhdf5files if is_recording_filename(f)]
    
#### Check file ####

def check(h, config):
    '''
    Check measurement file
    -Do all expected nodes exist?
    -Does sync data make sense?
    '''
    h_opened = False
    error_messages = []
    if not hasattr(h, 'filename'):
        h = hdf5io.Hdf5io(h, filelocking=False)
        map(h.load, config.DATA_FILE_NODES)
        h_opened = True
    for node in config.DATA_FILE_NODES:
        if not hasattr(h, node):
            error_messages.append('missing node: {0}'.format(node))
    #Check
    if len(error_messages)==0:
        if len(h.raw_data.shape) != 4 or h.raw_data.shape[1]>2:
            error_messages.append('raw_data has invalid shape: {0}'.format(h.raw_data.shape))
        if h.imaging_run_info['end']-h.imaging_run_info['start'] != h.imaging_run_info['duration']:
            error_messages.append('inconsistent imaging_run_info')
        if not isinstance(h.stimulus_frame_info, list):
            error_messages.append('Invalid stimulus_frame_info')
        sync_signals = numpy.cast['float'](h.sync[:,config.ELPHYS_SYNC_RECORDING['SYNC_INDEXES']])/h.ephys_sync_conversion_factor
        ca_frame_trigger = sync_signals[:,2]
        block_trigger = sync_signals[:,0]
        ca_frame_trigger_edges = signal.trigger_indexes(ca_frame_trigger)
        block_trigger_edges = signal.trigger_indexes(block_trigger)
        if block_trigger_edges.shape[0]>0 and (block_trigger_edges.min() < ca_frame_trigger_edges.min() or block_trigger_edges.max() > ca_frame_trigger_edges.max()):
            error_messages.append('Some parts of the stimulus might not have been imaged')
        npulses = 0.5 * (ca_frame_trigger_edges.shape[0]-2)#Last pulse is ignored
        if h.imaging_run_info['acquired_frames'] < npulses and (1-h.imaging_run_info['acquired_frames']/npulses>5e-2 and abs(h.imaging_run_info['acquired_frames'] - npulses) >= 1):
            error_messages.append('Acquired frames ({0}) and generated pulses ({1}) differ'.format(h.imaging_run_info['acquired_frames'], npulses))
        #Check frame rate
        distance_between_edges = numpy.diff(ca_frame_trigger_edges)[:-1]
        if distance_between_edges.shape[0]%2==1:#Sometimes the lenght of this array is odd and it causes errors when resized at frame durations calculations
            distance_between_edges[:-1]
        try:
            frame_durations = numpy.cast['float'](distance_between_edges.reshape(distance_between_edges.shape[0]/2,2).sum(axis=1))/h.recording_parameters['elphys_sync_sample_rate']
        except ValueError:#TMP: this error has to be catched
            import pdb
            import traceback
            traceback.print_exc()
            pdb.set_trace()
        if abs(frame_durations-1/h.recording_parameters['frame_rate']).max()>5./h.recording_parameters['elphys_sync_sample_rate']:#Maximum allowed deviation is 5 sample time
            error_messages.append('Frame rate mismatch')
    if h_opened:
        h.close()
    return error_messages
    
def get_id(timestamp=None):
    '''
    unique id for datafiles:
        v1: unix timestamp
        v2: unix timestamp - epoch to make it shorter
        v3: yyyymmddhhmmss format for better readability
    '''
    version='v3'
    if timestamp is None:
        timestamp = time.time()
    epoch = time.mktime((2014, 11, 01, 0,0,0,0,0,0))
    if version=='v2':
        return str(int(numpy.round(timestamp-epoch, 1)*10))
    elif version=='v1':
        return str(int(numpy.round(timestamp, 1)*10))
    elif version=='v3':
        time_struct = time.localtime(timestamp)
        return '{0:0=4}{1:0=2}{2:0=2}{3:0=2}{4:0=2}{5:0=2}{6}'.format(time_struct.tm_year, time_struct.tm_mon, time_struct.tm_mday, time_struct.tm_hour, time_struct.tm_min, time_struct.tm_sec,int(10*(timestamp-int(timestamp))))

def id2timestamp(id_str):
    format="%Y%m%d%H%M%S"
    return time.mktime(datetime.datetime.strptime(id_str[:-1], format).timetuple())+int(id_str[-1])*0.1
    

############### Preprocess measurement data ####################
if hasattr(hdf5io, 'Hdf5io'):
    supcl=hdf5io.Hdf5io
else:
    supcl=object
class CaImagingData(supcl):
    '''
    datatypes:
        ao: time,channel, roi, height, width
        ca: time, channel, (roi), height, width
        
    Platforms supported:
        Legacy (Rei/Santiago) ca imaging
        AOD
        
    External/legacy converters create the original file from raw datafiles resulting a file with raw image data and raw synchron data.
    Then this class can be used to:
        calculate sync timestamps
        meanimage/mip
        
    In some cases the timg and number of frames do not match:
        legacy ca imaging: y scanner signal is not immediately stopped so more timg pulses are detected than image frames recorded
        AOD: some frames from the beginning should be thrown away
        
    Consequently sync2time function should make sure that the number of timg values is correct
        
    
    '''
    def __init__(self,filename, **kwargs):
        hdf5io.Hdf5io.__init__(self, filename, filelocking=False)
        if os.path.exists(filename):
            self.file_info = os.stat(filename)
        
    def sync2time(self, recreate=False):
        '''
        Reads raw sync traces and converts them to timestamps. If not found in datafile, it is saved
        Channel id is read from saved machine config
        '''
        for vn in ['timg', 'tstim']:
            self.load(vn)
        if not recreate:
            if hasattr(self, 'timg') and hasattr(self , 'tstim'):
                return
        for vn in ['sync', 'configs', 'sync_scaling', 'parameters']:
            self.load(vn)
        if self.sync.dtype.name not in ['float', 'uint8', 'uint16']:
            raise NotImplementedError()
        fsample=float(self.configs['machine_config']['SYNC_RECORDER_SAMPLE_RATE'])
        sync=signal.from_16bit(self.sync,self.sync_scaling)
        sig=sync[:,self.configs['machine_config']['TIMG_SYNC_INDEX']]
        if sig.max()<self.configs['machine_config']['SYNC_SIGNAL_MIN_AMPLITUDE']:
            raise RuntimeError('Imaging timing signal maximum amplitude is only {0:0.2f} V. Make sure that scan sync is enabled and connected'.format(sig.max()))
        self.timg=signal.trigger_indexes(sig)[::2]/fsample
        if 'laser' in str(self.parameters['stimclass']).lower():
            index=self.configs['machine_config']['TSTIM_LASER_SYNC_INDEX']
        else:
            index=self.configs['machine_config']['TSTIM_SYNC_INDEX']
        sig=sync[:,index]
        if sig.max()<self.configs['machine_config']['SYNC_SIGNAL_MIN_AMPLITUDE']:
            raise RuntimeError('Stimulus timing signal maximum amplitude is only {0:0.2f} V. Check connections'.format(sig.max()))
        self.tstim=signal.trigger_indexes(sig)/fsample
        self.save(['timg', 'tstim'])
        
    def crop_timg(self):
        for vn in ['configs', 'raw_data', 'timg']:
            self.load(vn)
        #Crop timg
        if self.configs['machine_config']['PLATFORM']=='elphys_retinal_ca':
            self.timg=self.timg[:self.raw_data.shape[0]]
            dt=numpy.diff(self.timg)[0]
            self.timg+=dt#Not yet understood why this is necessary
        elif self.configs['machine_config']['PLATFORM']=='ao_cortical':
            self.timg=self.timg[int(self.findvar('sync_pulses_to_skip')):]
            #Ignore last frames
            self.timg=self.timg[:self.raw_data.shape[0]]
        if self.timg.shape[0]!=self.raw_data.shape[0]:
            raise RuntimeError('Number of imaging timestamps ({0}) and number of frames ({1}) do not match'.format(self.timg.shape[0],self.raw_data.shape[0]))
        self.save(['timg'])
            
    def check_timing(self, check_frame_rate=True):
        errors=[]
        if self.timg.shape[0]==0:
            errors.append('No imaging sync signal detected.')
        if not (self.timg[0]<self.tstim[0] and self.timg[-1]>self.tstim[-1]):
            errors.append('{0} of stimulus was not imaged'.format('Beginning' if self.timg[0]>self.tstim[0] else 'End') )
        if check_frame_rate:
            #Check frame rate
            self.load('stimulus_frame_info')
            sfi=self.stimulus_frame_info
            if 'laser' in str(self.parameters['stimclass']).lower() or 'led' in str(self.parameters['stimclass']).lower():
                pass
            elif len([1 for s in sfi if 'block_name' in s.keys()])>0:
                bsi=numpy.array([sfi[i]['block_start'] for i in range(len(sfi)) if sfi[i].has_key('block_start')])
                bei=numpy.array([sfi[i]['block_end'] for i in range(len(sfi)) if sfi[i].has_key('block_end')])
                expected_block_durations =(bei-bsi)/ float(self.configs['machine_config']['SCREEN_EXPECTED_FRAME_RATE'])
                measured_block_durations = numpy.diff(self.tstim)[::2]
                measured_frame_rate=(bei-bsi)/measured_block_durations
                error=measured_frame_rate-self.configs['machine_config']['SCREEN_EXPECTED_FRAME_RATE']
                if numpy.where(abs(error)>FRAME_RATE_TOLERANCE)[0].shape[0]>0:
                    errors.append('Measured frame rate(s): {0} Hz, expected frame rate: {1} Hz'.format(measured_frame_rate,self.configs['machine_config']['SCREEN_EXPECTED_FRAME_RATE']))
            else:
                raise NotImplementedError()
        if len(errors)>0:
            raise RuntimeError('\r\n'.join(errors))
        
    def get_image(self, image_type='mip'):
        '''
        loads 2d representation of ca imaging data with scaling information
        self.image and self.image_scale
        '''
        map(self.load, ['parameters', 'configs', 'raw_data'])
        if not hasattr(self, 'configs'):#For older files
            self.load('machine_config')
            self.configs=self.machine_config
        if self.parameters['resolution_unit']=='pixel/um':
            self.scale = 1.0/self.parameters['pixel_size']
        else:
            raise NotImplementedError('')
        if image_type=='mean':
            self.image = self.raw_data.mean(axis=0)[0]
        elif image_type=='mip': 
            #Remove saturated frames
            saturation_value=255 if self.raw_data.dtype.name=='uint8' else 2**16-1
            row_means=self.raw_data.mean(axis=2)
            indexes=[i for i in range(row_means.shape[0]) if saturation_value in row_means[i]]
            col_means=self.raw_data.mean(axis=3)
            indexes.extend([i for i in range(col_means.shape[0]) if saturation_value in col_means[i]])
            keep_frame_indexes=[i for i in range(self.raw_data.shape[0]) if i not in indexes]
            self.image= self.raw_data[keep_frame_indexes].max(axis=0)[0]
        if self.configs['machine_config']['PLATFORM']=='ao_cortical':
            nrois=self.image.shape[0]
            roi_aspect_ratio=self.raw_data.shape[-2]/float(self.raw_data.shape[-1])
            #merge rois to a square image:
            n=int(numpy.ceil(numpy.sqrt(nrois/roi_aspect_ratio)))#number of rois across x axis
            nrow=n
            ncol=int(n*roi_aspect_ratio)
            merged=numpy.zeros((nrow*self.image.shape[1], ncol*self.image.shape[2]), dtype=self.image.dtype)
            rois=[]
            for row in range(nrow):
                for col in range(ncol):
                    roii=row*ncol+col
                    if roii>=nrois:
                        break
                    #Format: center[0], center[1], size[0], size[1]
                    roi=[row*self.image.shape[1]+self.image[roii].shape[0]/2,col*self.image.shape[2]+self.image[roii].shape[1]/2]
                    roi.extend(self.image[roii].shape)
                    roi[-2]-=1
                    roi[-3]-=1
                    raw= self.raw_data[:,0,roii].mean(axis=1).mean(axis=1)
                    rois.append({'rectangle':roi, 'raw': raw})
                    merged[row*self.image.shape[1]:(row+1)*self.image.shape[1], col*self.image.shape[2]:(col+1)*self.image.shape[2]]=self.image[roii]            
            self.load('rois')
            if not hasattr(self, 'rois'):
                vns=['tstim', 'timg']
                map(self.load, vns)
                add2roi={'stimulus_name':str(self.parameters['stimclass']), 'meanimage': merged, 'image_scale': self.scale, 'tstim': self.tstim, 'timg': self.timg}
                for i in range(len(rois)):
                    rois[i].update(add2roi)
                self.rois=rois
                self.save('rois')
            self.image=merged
        self.load('parameters')
        return self.image,self.scale
        
    def convert(self,format):
        '''
        Supported formats: mat, tiff
        '''
        if format == 'mat':
            if not hasattr(self, 'timg'):
                self.sync2time()
            items = [r._v_name for r in self.h5f.list_nodes('/')]
            data={}
            for item in items:
                self.load(item)
                data[item]=getattr(self,item)
                if isinstance(data[item], dict) and len(data[item].keys())==0:
                    data[item]=0
            data['timg']=self.timg
            data['tstim']=self.tstim
            #Make sure that rois field does not contain None:
            if data.has_key('rois'):
                for r in data['rois']:
                    if r.has_key('area') and r['area'] is None:
                        del r['area']
            if not hasattr(self, 'configs'):#TODO: this might be unnecessary
                self.load('configs')
            tag='_mat' if self.configs['machine_config']['PLATFORM']=='ao_cortical' else ''
            self.outfile = fileop.get_convert_filename(self.filename, '.mat', tag)
            #Write to mat file
            scipy.io.savemat(self.outfile, data, oned_as = 'row', long_field_names=True,do_compression=True)
        elif format == 'png':
            self._save_meanimage()
        elif format == 'tif':
            import tifffile
            if not hasattr(self, 'raw_data'):
                self.load('raw_data')
            if not hasattr(self, 'image_scale'):
                self.meanimage, self.scale = self.get_image('mip')
            #um/pixel to dpi
            dpi = 1.0/self.scale*25.4e3
            self.outfile = fileop.get_convert_filename(self.filename, 'tif')
            tifffile.imsave(self.outfile, self.raw_data[:,0,:,:],resolution = (dpi,dpi),description = self.filename, software = 'Vision Experiment Manager')
        elif format == 'rois':
            output_folder=os.path.join(os.path.dirname(self.filename), 'output', os.path.basename(self.filename))
            self.rois_output_folder=output_folder
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            if not hasattr(self, 'raw_data'):
                self.load('raw_data')
            self.meanimage, self.scale = self.get_image('mip')
            #um/pixel to dpi
            dpi = 1.0/self.scale*25.4e3
            #mip
            mip2image=numpy.zeros((self.meanimage.shape[0],self.meanimage.shape[1],3), self.raw_data.dtype)
            mip2image[:,:,1]=numpy.cast[self.raw_data.dtype.name](self.meanimage)
            import tifffile
            tifffile.imsave(os.path.join(output_folder, 'mip.tif'), numpy.rot90(mip2image),resolution = (dpi,dpi),description = self.filename, software = 'Vision Experiment Manager')
            #mip with rois, roi curves
            self.load('rois')
            if hasattr(self, 'rois'):
                from PIL import ImageFont
                fontsize=15
                try:
                    font = ImageFont.truetype("arial.ttf", fontsize)
                except IOError:
                    raise IOError('On linux type: sudo apt-get install ttf-mscorefonts-installer')
                rescale_factor=500/max(mip2image.shape)+1
                new_size=(numpy.array(list(mip2image.shape)[:2])*rescale_factor)[::-1]
                mip2image_with_rectangles=Image.fromarray(mip2image).resize(new_size)
                mip2image_with_rectanglesd=ImageDraw.Draw(mip2image_with_rectangles)
                mip2image_with_rectangles_and_indexes=Image.fromarray(mip2image).resize(new_size)
                mip2image_with_rectangles_and_indexesd=ImageDraw.Draw(mip2image_with_rectangles_and_indexes)
                csvfn=os.path.join(output_folder, os.path.basename(self.filename).replace('.hdf5', '_flash.csv'))
                csvfn_stim=os.path.join(output_folder, os.path.basename(self.filename).replace('.hdf5', '_stim.csv'))
                txtlines_stim=','.join(map(str,numpy.round(self.rois[0]['tstim'],3)))
                txtlines=[','.join(map(str,numpy.round(self.rois[0]['timg'],3)))]
                plotpars=[]
                for i in range(len(self.rois)):
                    roi =self.rois[i]
                    rect=numpy.cast['int'](numpy.array(roi['rectangle'])*rescale_factor)
                    p1=(rect[1]-rect[3], rect[0]-rect[2])
                    p2=(rect[1]+rect[3], rect[0]+rect[2])
                    mip2image_with_rectanglesd.rectangle([p1,p2], outline=(0,0,255))
                    mip2image_with_rectangles_and_indexesd.rectangle([p1,p2], outline=(0,0,255))
                    txt=Image.new('L', (fontsize,fontsize))
                    txtd=ImageDraw.Draw(txt)
                    txtd.text((0,0),str(i), font=font, fill=255)
                    txt=txt.rotate(-90)
                    mip2image_with_rectangles_and_indexes.paste(txt,p1,txt)
                    #mip2image_with_rectangles_and_indexesd.text(p1,str(i), font=font, fill=(0,0,255))
                    plotpars.append([self.filename, os.path.join(output_folder, '{0}.eps'.format(i)), roi])
                    txtlines.append(','.join(map(str, numpy.round(roi['raw'],2))))
                p=multiprocessing.Pool(introspect.get_available_process_cores())
                p.map(roi_plot, plotpars)
                fileop.write_text_file(csvfn, '\r\n'.join(txtlines))
                fileop.write_text_file(csvfn_stim, txtlines_stim)
                mip2image_with_rectangles_and_indexes.rotate(90).save(os.path.join(output_folder, 'rois_and_indexes.png'))
                mip2image_with_rectangles.rotate(90).save(os.path.join(output_folder, 'rois.png'))
                pass
                
        elif format == 'mp4':
            imgarray = self.rawdata2images()
            framefolder=os.path.join(tempfile.gettempdir(), 'frames_tmp')
            fileop.mkdir_notexists(framefolder, remove_if_exists=True)
            ct=0
            resize_factor = 400.0/min(imgarray.shape[1:3]) if min(imgarray.shape[1:3])<400 else 1.0
            for frame in imgarray:
                fn=os.path.join(framefolder, 'f{0:0=5}.png'.format(ct))
                Image.fromarray(frame).resize((int(frame.shape[1]*resize_factor),int(frame.shape[0]*resize_factor))).save(fn)
                ct+=1
            fps = int(numpy.ceil(1.0/numpy.diff(get_sync_events(self)[1]).mean()))
            self.outfile = fileop.get_convert_filename(self.filename, 'mp4')
            videofile.images2mpeg4(framefolder, self.outfile, fps)
            shutil.rmtree(framefolder)
        
    def _save_meanimage(self):
        '''
        Meanimage is calculated from imaging data and saved to file
        '''
        if not hasattr(self, 'meanimage'):
            self.meanimage, self.scale = self.get_image()
        colored_image = numpy.zeros((self.meanimage.shape[0], self.meanimage.shape[1],3),dtype=numpy.uint8)
        colored_image[:,:,1] = numpy.cast['uint8'](signal.scale(self.meanimage)*255)
        Image.fromarray(colored_image).save(fileop.get_convert_filename(self.filename, 'png'))
        
    def rawdata2images(self, nbits = 8):
        '''
        One channel is supported, saved to green
        '''
        if not hasattr(self, 'raw_data'):
            self.load('raw_data')
        if self.raw_data.shape[1]!=1:
            raise NotImplementedError('Only one channel is supported')
        imagearray = numpy.zeros((self.raw_data.shape[0], self.raw_data.shape[2], self.raw_data.shape[3], 3),dtype = numpy.uint16 if nbits == 16 else numpy.uint8)
        if nbits == 16:
            imagearray[:,:,:,1] = self.raw_data[:,0,:,:]
        elif nbits == 8:
            imagearray[:,:,:,1] = numpy.cast['uint8'](numpy.cast['float'](self.raw_data[:,0,:,:])/256)
        else:
            raise NotImplementedError('')
        return imagearray
    
    def backup(self,dst_root, nsubfolders):
        '''
        Backs up file to dst root considering nsubfolders
        '''
        dst=os.path.join(dst_root,*self.filename.split(os.sep)[-(1+nsubfolders):])
        if not os.path.exists(os.path.dirname(dst)):
            os.makedirs(os.path.dirname(dst))
        shutil.copy2(self.filename,dst)
        if os.path.exists(add_mat_tag(self.filename)):
            shutil.copy2(add_mat_tag(self.filename),os.path.dirname(dst))
        return dst
        
def timing_from_file(filename):
    '''
    Shortcut for reading/calculating timing information from file
    '''
    cd=CaImagingData(filename)
    tsync,timg, meanimage, image_scale, raw_data = cd.prepare4analysis()
    cd.close()
    return tsync,timg

def read_sync_rawdata(h):
    '''
    Reads sync traces
    '''
    for v in  ['configs_stim', 'sync', 'sync_conversion_factor']:
        if not hasattr(h, v):
            h.load(v)
    if not hasattr(h, 'sync'):
        h.load('sync_and_elphys_data')
        h.sync=h.sync_and_elphys_data
        h.load('elphys_sync_conversion_factor')
        h.sync_conversion_factor=h.elphys_sync_conversion_factor
    machine_config = h.configs_stim['machine_config']
    sync = numpy.cast['float'](h.sync)
    if hasattr(h, 'sync_conversion_factor'):#Legacy, should be eliminated
        sync /= h.sync_conversion_factor#Scale back to original value
    else:
        h.load('sync_scaling')
        sync=signal.from_16bit(h.sync, h.sync_scaling)
    
    if machine_config.has_key('ELPHYS_SYNC_RECORDING'):
        elphys = sync[:,machine_config['ELPHYS_SYNC_RECORDING']['ELPHYS_INDEXES']]
        stim_sync =  sync[:,machine_config['ELPHYS_SYNC_RECORDING']['SYNC_INDEXES'][0]]
        img_sync =  sync[:,machine_config['ELPHYS_SYNC_RECORDING']['SYNC_INDEXES'][0]+2]
    else:
        elphys = numpy.zeros_like(sync[:,0])
        print "TODO: remove constants from code"
        index=machine_config['TIMG_SYNC_INDEX'] if machine_config.has_key('TIMG_SYNC_INDEX') else 0
        index=3
        img_sync =  sync[:,index]
        stim_sync =  sync[:,machine_config['TSTIM_SYNC_INDEX'] if machine_config.has_key('TSTIM_SYNC_INDEX') else 2]
    return elphys, stim_sync, img_sync

def get_sync_events(h):
    '''
    Detects sync events in stimulus and imaging sync traces
    '''
    elphys, stim_sync, img_sync=read_sync_rawdata(h)
    for v in  ['recording_parameters']:
        if not hasattr(h, v):
            h.load(v)
    if h.configs_stim['machine_config']['PLATFORM']=='ao_cortical':
        fsample=h.configs_stim['machine_config']['SYNC_RECORDER_SAMPLE_RATE']
    else:
        fsample=h.recording_parameters['elphys_sync_sample_rate']
    tsync = numpy.arange(h.sync.shape[0],dtype='float')/fsample
    #calculate time of sync events
    h.tsync = tsync[signal.trigger_indexes(stim_sync)]
    h.timg = tsync[signal.trigger_indexes(img_sync)[0::2]]
    h.tsync-=h.timg[0]
    h.timg-=h.timg[0]
    if h.findvar('datatype')=='ao' and 0:
        h.timg=h.timg[int(h.findvar('sync_pulses_to_skip')):]
    return h.tsync,h.timg
    
def get_ca_activity(h, mask = None):
    '''
    Returns the ca activity curve of the whole recording. The whole recording can be masked
    '''
    if not hasattr(h, 'raw_data'):
        h.load('raw_data')
    if h.raw_data.shape[1] != 1:
        raise NotImplementedError('Two channels are not supported')
    if mask is None:
        mask = numpy.ones(h.raw_data.shape[2:],dtype='bool')
    if h.raw_data.shape[2:] != mask.shape:
        raise RuntimeError('Invalid mask size: {0}, expected: {1}'.format(mask.shape, h.raw_data.shape[2:]))
    masked_data = h.raw_data * mask
    return masked_data.mean(axis=2).mean(axis=2).flatten()
        
def extract_roi_curve(rawdata, roix, roiy, roisize,roitype,scale):
    '''
    Extract a roi curve using provided roi center, roi size
    '''
    if roitype != 'circle':
        raise NotImplementedError('')
    size=roisize/scale
    x=roix/scale
    y=roiy/scale
    bbox=(x, y,x+size, y+size)
    im=Image.fromarray(numpy.zeros((rawdata.shape[2], rawdata.shape[3])))
    draw = ImageDraw.Draw(im)
    draw.ellipse(bbox, fill=1)
    mask = numpy.asarray(im)
    return get_roi_curves(rawdata, [numpy.nonzero(mask)])[0]
    
def get_roi_curves(rawdata, cell_rois):
    if rawdata.shape[3]<rawdata.shape[1]:
        return [numpy.cast['float'](rawdata[cell_roi[0], cell_roi[1], :,0]).mean(axis=0) for cell_roi in cell_rois]
    else:
        return [numpy.cast['float'](rawdata[:, 0, cell_roi[0], cell_roi[1]]).mean(axis=1) for cell_roi in cell_rois]

#################### Saving/loading data to hdf5 ####################

def pack_software_environment(experiment_source_code = None):
        software_environment = {}
        module_names, visexpman_module_paths = utils.imported_modules()
        module_versions, software_environment['module_version'] = utils.module_versions(module_names)
        tostream=False
        if not tostream:
            tmpfn=tempfile.mktemp()+'.zip'
            zipfile_handler = zipfile.ZipFile(tmpfn, 'a')
        else:
            stream=io.BytesIO()
            stream=StringIO.StringIO()
            zipfile_handler = zipfile.ZipFile(stream, 'a')
        import visexpman
        visexpman_module_paths=fileop.find_files_and_folders(fileop.visexpman_package_path(),extension='py')[1]
        vap=fileop.visexpA_package_path()
        if vap != None:
            visexpman_module_paths.extend(fileop.find_files_and_folders(vap,extension='py')[1])
        for module_path in visexpman_module_paths:
            if 'visexpA' in module_path:
                zip_path = '/visexpA' + module_path.split('visexpA')[-1]
            elif 'visexpman' in module_path:
                zip_path = '/visexpman' + module_path.split('visexpman')[-1]
            if os.path.exists(module_path):
                zipfile_handler.write(module_path, zip_path)
        if tostream:
            software_environment['source_code'] = numpy.fromstring(stream.getvalue(), dtype = numpy.uint8)
        if experiment_source_code is not None:
            software_environment['experiment_source_code'] = numpy.fromstring(experiment_source_code, dtype = numpy.uint8)
        zipfile_handler.close()
        if not tostream:
            software_environment['source_code'] = numpy.fromfile(tmpfn, dtype = numpy.uint8)
            os.remove(tmpfn)
        return software_environment
        
def pack_configs(self):
    '''
    machine and experiment config is packed in a serialized and in a dictionary format
    '''
    configs = {}
    configs['serialized'] = {}
    for confname in ['machine_config', 'experiment_config']:
        if hasattr(self, confname):#Experiment config might not be available
            configs['serialized'][confname] = copy.deepcopy(getattr(self,confname).serialize())
            configs[confname] = copy.deepcopy(getattr(self,confname).todict())
            if configs[confname].has_key('GAMMA_CORRECTION'):
                del configs[confname]['GAMMA_CORRECTION']#interpolator object, cannot be pickled
    if not configs.has_key('experiment_config'):
        configs['experiment_config']=self.config2dict()
    return configs
    
def read_machine_config(h):
    return utils.array2object(h.findvar('machine_config'))
    
def read_machine_config_name(h):
    return read_machine_config(h).__class__.__name__
    
#################### End of saving/loading data to hdf5 ####################

def preprocess_stimulus_sync(sync_signal, stimulus_frame_info = None, sync_signal_min_amplitude = 1.5):#OBSOLETE
    #Find out high and low voltage levels
    histogram, bin_edges = numpy.histogram(sync_signal, bins = 20)
    if histogram.max() == histogram[0] or histogram.max() == histogram[-1]:
        pulses_detected = True
        low_voltage_level = 0.5 * (bin_edges[0] + bin_edges[1])
        high_voltage_level = 0.5 * (bin_edges[-1] + bin_edges[-2])
#        print high_voltage_level - low_voltage_level
        if high_voltage_level - low_voltage_level  < sync_signal_min_amplitude:
            pulses_detected = False
            return stimulus_frame_info, 0, pulses_detected
    else:
        pulses_detected = False
        return stimulus_frame_info, 0, pulses_detected
    threshold = 0.5 * (low_voltage_level + high_voltage_level)
    #detect sync signal rising edges
    binary_sync = numpy.where(sync_signal < threshold, 0, 1)
    rising_edges = numpy.where(numpy.diff(binary_sync) > 0, 1, 0)
    rising_edges_indexes = numpy.nonzero(rising_edges)[0] + 1
    stimulus_frame_info_with_data_series_index = []
    if stimulus_frame_info != None:
        for stimulus_item in stimulus_frame_info:
            info = stimulus_item
            try:
                info['data_series_index'] = rising_edges_indexes[info['counter']]
            except IndexError:
                #less pulses detected
                info['data_series_index'] = -1
                print 'less trigger pulses were detected'
            stimulus_frame_info_with_data_series_index.append(info)
    return stimulus_frame_info_with_data_series_index, rising_edges_indexes, pulses_detected

def read_merge_rois(cells, cell_group, region_name, objective_position, objective_origin, z_range, merge_distance):#OBSOLETE
    '''
    Reads rois of selected group, performs filtering based on objective position and merge distance
    '''
    if not cells.has_key(region_name):
        return None, None
    roi_locations = []
    roi_locations_rcd = []
    rois = []
    for cell in cells[region_name].values():
        #Calculate minimal distance of current cell from all the already selected cells
        distances = [abs(utils.rc_distance(roi_location, cell['roi_center'], rc_distance_only = True)) for roi_location in roi_locations_rcd]
        if cell['depth'] > objective_position - 0.5 * z_range and cell['depth'] < objective_position + 0.5 * z_range\
        and cell['group'] == cell_group and cell['accepted']:
            if len(distances) == 0 or min(distances) > merge_distance:
                rois.append(cell)
                roi_locations.append(utils.nd(cell['roi_center'])[0])
                roi_locations_rcd.append(cell['roi_center'])
            else:
                #find indexes
                merge_to_index = ((numpy.array(distances)<merge_distance).tolist()).index(True)
                if not rois[merge_to_index].has_key('merged_rois'):
                    rois[merge_to_index]['merged_rois'] = []
                rois[merge_to_index]['merged_rois'].append(cell)
    if len(roi_locations) == 0:
        return None, None
    else:
        roi_locations = utils.rcd(numpy.array(roi_locations))
        roi_locations['depth'] = objective_position + objective_origin
        return roi_locations, rois
        
#OBSOLETE
def add_auxiliary_rois(rois, roi_pattern_size, objective_position, objective_origin, aux_roi_distance = None, soma_size_ratio = None):
    '''
    aux_roi_distance: fixed distance from soma center
    soma_size_ratio: distance from soma center as fraction of longer radius of soma
    '''
    debug = False
    if debug:
        im = numpy.zeros((1000, 1000, 3),  dtype = numpy.uint8)
    expanded_rois = []
    for roi in rois:
        if debug:
            im[roi['soma_roi']['row'], roi['soma_roi']['col'], :] = 128
        #Center
        roi_center_in_pixels = utils.rc((roi['soma_roi']['row'].mean(), roi['soma_roi']['col'].mean()))        
        #Find two furthest point
        max_distance = 0
        for i in range(roi['soma_roi'].shape[0]):
            for j in range(i, roi['soma_roi'].shape[0]):
                distance = utils.rc_distance(roi['soma_roi'][i], roi['soma_roi'][j])
                if distance > max_distance:
                    max_distance = distance
                    furthest_points = [i, j]
        #"direction" of soma
        point1 = roi['soma_roi'][furthest_points[0]]
        point2 = roi['soma_roi'][furthest_points[1]]
        direction = numpy.arctan2(float(point1['row']-point2['row']), float(point1['col']-point2['col']))
        #Pick from the furthest points the one which distance from roi center is bigger
        if abs(utils.rc_distance(roi_center_in_pixels, point1)) > abs(utils.rc_distance(roi_center_in_pixels, point2)):
            point = point1
        else:
            point = point2
        #determine  point halfway between center and picked point
        if soma_size_ratio is not None:
            aux_roi_distance_pix = soma_size_ratio * utils.rc_distance(roi_center_in_pixels, point)
        else:
            aux_roi_distance_pix = aux_roi_distance / roi['scale']['row']
        roi_to_add = copy.deepcopy(roi)
        roi_to_add['auxiliary'] = False
        expanded_rois.append(roi_to_add)
        if roi_pattern_size == 3:
            angles = [0, numpy.pi/2]
        else:
            angles = numpy.linspace(0, numpy.pi*2, roi_pattern_size)[:-1]
        for angle in angles:
            aux_roi_pix = utils.rc((roi_center_in_pixels['row'] - aux_roi_distance_pix * numpy.sin(direction + angle),
                                     roi_center_in_pixels['col'] - aux_roi_distance_pix * numpy.cos(direction + angle)))
            aux_roi = utils.pixel2um(aux_roi_pix, roi['origin'], roi['scale'])
            roi_to_add = copy.deepcopy(roi)
            roi_to_add['auxiliary'] = True
            roi_to_add['roi_center'] = utils.rcd((aux_roi['row'][0], aux_roi['col'][0], roi['roi_center']['depth']))
            expanded_rois.append(roi_to_add)
            if debug:
                im[int(numpy.round(aux_roi_pix['row'], 0)), int(numpy.round(aux_roi_pix['col'], 0)), 1] = 255
        if debug:
            im[int(roi_center_in_pixels['row']), int(roi_center_in_pixels['col']), :] = 255
    if debug:
        try:
            import Image
        except ImportError:
            from PIL import Image
#        im = im[100:, 100:, :]
        im = Image.fromarray(im)
        try:
            im.save('/mnt/datafast/debug/somaroi.png')
        except:
            im.save('v:\\debug\\somaroi.png')
        pass
    return rois_to_roi_locations(expanded_rois, objective_position, objective_origin), expanded_rois
        
#OBSOLETE
def rois_to_roi_locations(rois, objective_position, objective_origin):
    roi_locations = []
    for roi in rois:
        roi_locations.append(utils.nd(roi['roi_center'])[0])
    roi_locations = utils.rcd(numpy.array(roi_locations))
    roi_locations['depth'] = objective_position + objective_origin
    return roi_locations
    
def read_phys(filename):
    '''
    Read traces and metadata from .phys file
    '''
    import struct
    f =open(filename,  'rb')
    offset = f.read(4)
    offset = struct.unpack('>i',offset)[0]
    header= f.read(offset)
    metadata = {}
    for item in [param.split(': ') for param in header.split('\r')]:
        if len(item)==2:
            metadata[item[0]] = item[1]
    f.seek(4+offset)
    dim1 = f.read(4)
    dim2 = f.read(4)
    dim1 = struct.unpack('>i',dim1)[0]
    dim2 = struct.unpack('>i',dim2)[0]
    data=numpy.fromfile(f,">i2").reshape((dim1, dim2))
#    data = f.read(2*dim1*dim2)
#    data = numpy.array(struct.unpack('>'+''.join(dim1*dim2*['h']),data), dtype = numpy.int16).reshape((dim1, dim2))
    f.close()
    return data, metadata

def phys2clampfit(filename):
    '''
    Converts phys file with trigger information to be readable by clampfit software
   ''' 
    data = read_phys(filename)
    data = data.flatten('F').reshape(dim1, dim2)
    data.tofile(filename.replace('.phys', 'c.phys'))
    
class SmrVideoAligner(object):
    def __init__(self, folders, fps = 29.97):
        filename, outfolder = folders
        self.filename = filename
        self.outfolder = outfolder
        print 'read smr file'
        self.elphys_timeseries, self.elphys_signal = self.read_smr_file(filename, outfolder)
        print 'reading video file'
        framefiles = self.read_video(filename, fps)
        if framefiles is not None:
            self.video_traces = numpy.array(map(self.process_frame, framefiles))
        if 0:
            self.detect_motion(framefiles)
        print 'saving data'
        self.save()
        print 'deleting temporary files'
        self.cleanup()
        
    def cleanup(self):
        if hasattr(self, 'tempdir') and os.path.exists(self.tempdir):
            shutil.rmtree(self.tempdir)
        if os.path.exists(self.matfile):
            os.remove(self.matfile)
        
    def read_smr_file(self, fn, outfolder):
        from neo import Block
        from neo.io import Spike2IO, NeoMatlabIO
        name=os.path.split(fn)[1].replace('.smr','')
        self.matfile=os.path.join(tempfile.gettempdir(), name+'.mat')
        r = Spike2IO(filename=fn)
        w = NeoMatlabIO(filename=self.matfile)
        seg = r.read_segment()
        bl = Block(name=name)
        bl.segments.append(seg)
        w.write_block(bl)
        self.smr_data=scipy.io.loadmat(self.matfile, mat_dtype=True)['block']['segments'][0][0][0][0][0]['analogsignals'][0][0]
        #Select the one where channel name is units
        for item in self.smr_data:
            if str(item['name'][0,0][0]) == 'Units':
                sample_rate = item['sampling_rate'][0][0][0][0]
                signal = item['signal'][0][0][0]
                timeseries = numpy.arange(signal.shape[0])/sample_rate
                return timeseries, signal

    def read_video(self, filename,fps):
        import subprocess
        recording_name = os.path.split(filename)[1].replace('.smr', '')
        avi_file = [fn for fn in fileop.listdir_fullpath(os.path.split(filename)[0]) if recording_name in fn and '.avi' in fn ]
        if len(avi_file) == 1:
            if fileop.free_space(tempfile.gettempdir())<10e9 and os.name == 'nt':
                tmpdir = 'e:\\temp'
            elif fileop.free_space(tempfile.gettempdir())<10e9 and os.name == 'posix':
                tmpdir = '/mnt/rzws/temp'
            else:
                tmpdir = tempfile.gettempdir()
            if fileop.free_space(tmpdir)<10e9:
                raise IOError('Not enough space on {0}.'.format(tmpdir))
            self.tempdir = os.path.join(tmpdir, 'frames_'+recording_name.replace(' ', '_'))
            fileop.mkdir_notexists(self.tempdir, True)
            command = '{0} -i "{1}" {2}'.format('ffmpeg' if os.name == 'nt' else 'avconv', avi_file[0], os.path.join(self.tempdir, 'f%5d.png'))
            subprocess.call(command,shell=True)
            self.frame_files=  fileop.listdir_fullpath(self.tempdir)
            self.frame_files.sort()
            self.video_time_series = numpy.arange(len(self.frame_files),dtype=numpy.float)/videofile.get_fps(avi_file[0])
            return self.frame_files
        else:
            print 'No avi file found for ' + filename
            
    def save(self):
        from pylab import plot,clf,savefig,legend,xlabel
        data = {}
        data['elphys_t'] = self.elphys_timeseries
        data['elphys_signal'] = self.elphys_signal
        if self.elphys_timeseries.shape[0]>1e6:
            self.elphys_timeseries = self.elphys_timeseries[::100]
            self.elphys_signal = self.elphys_signal[::100]
        plot(self.elphys_timeseries, self.elphys_signal)
        lgnd = ['elphys signal']
        if hasattr(self, 'video_time_series'):
            data['video_t'] = self.video_time_series
        if hasattr(self, 'video_traces'):
            data['video_meancontrasts'] = self.video_traces
            if self.video_time_series.shape[0]>1e6:
                self.video_time_series = self.video_time_series[::100]
                self.video_traces = self.video_traces[::100]
            plot(self.video_time_series, signal.scale(self.video_traces, 0, self.elphys_signal.max()))
            lgnd.append('video meanimages')
        fn = os.path.join(self.outfolder, os.path.split(self.filename)[1].replace('.smr', '.mat'))
        legend(lgnd)
        xlabel('time [s]')
        savefig(fn.replace('.mat', '.png'),dpi=300)
        clf()
        for k in data.keys():
            d={}
            d[k]=data[k]
            del data[k]
            try:
                scipy.io.savemat(fn.replace('.mat', '_' + k+'.mat'), d, oned_as = 'column')
            except:
                import pdb
                pdb.set_trace()
        
            
    def process_frame(self, frame_file):
        frame = numpy.cast['float'](numpy.asarray(Image.open(frame_file))).mean()
        return frame
        
    def _read_frame(self,fn):
        return numpy.cast['float'](signal.greyscale(numpy.asarray(Image.open(fn))))

    def detect_motion(self,files):
        meanframe = self._read_frame(files[0])
#        videoadata = numpy.zeros((len(files), frame.shape[0], frame.shape[1], ))
#        videoadata[0] = frame
        for i in range(1,len(files)):
            meanframe += self._read_frame(files[i])
        meanframe /= len(files)
        current_frame = self._read_frame(files[0])
        diff_pixels = []
        cog = []
        threshold = self._threshold_video(files)
        #track biggest object's movement
        from scipy import ndimage
        for i in range(0, len(files)):
            thresholded = numpy.where(self._read_frame(files[i])>threshold,1,0)
            labeled, nfeatures = ndimage.measurements.label(thresholded)
            maxsizecolor = 0
            maxsize = 0
            for c in range(1, nfeatures+1):
                size = numpy.where(labeled == c)[0].shape[0]
                if size>maxsize:
                    maxsize = size
                    maxsizecolor = c
            biggest_feature = numpy.where(labeled == maxsizecolor, 1,0)
            cog.append(ndimage.measurements.center_of_mass(biggest_feature))
            
            pass
        cog_change = numpy.diff(numpy.array(cog),axis=0)
        r = numpy.sqrt(cog_change[:,0]**2, cog_change[:,1]**2)
        phi = numpy.degrees(numpy.arctan2(cog_change[:,0], cog_change[:,1]))
        from pylab import plot, imshow, show
        
        pass
            
    def _threshold_video(self,files):
        return 0.95 * max([self._read_frame(files[i]).max() for i in range(0,len(files))])#assuming that the moving bars are the brightest items 
        from skimage import filter
        return numpy.array([filter.threshold_otsu(self._read_frame(files[i])) for i in range(0,len(files))]).mean()
    
   
#################### Not working/abandoned concepts ####################

def detect_cells(rawdata, scale, cell_size):#This concept does not work
    from scipy.ndimage.filters import gaussian_filter,maximum_filter
    from scipy.ndimage.morphology import generate_binary_structure, binary_erosion
    from scipy.ndimage.measurements import label
    import skimage
    from skimage import filter
    minimal_cell_size = 0.25 #
    maximal_cell_size = 1.1 #
    sigma = 0.1 #cell size scaled
    mip=images2mip(rawdata,2)[:,:,0]
    cell_size_pixel = cell_size*scale
    minimal_cell_area_pixels = (cell_size_pixel*minimal_cell_size*0.5)**2*numpy.pi
    maximal_cell_area_pixels = (cell_size_pixel*maximal_cell_size*0.5)**2*numpy.pi
    gaussian_filtered = gaussian_filter(mip, cell_size_pixel*sigma)
    th=filter.threshold_otsu(gaussian_filtered)
    gaussian_filtered[gaussian_filtered<th] = 0
    neighborhood = generate_binary_structure(gaussian_filtered.ndim,gaussian_filtered.ndim)
    local_max = maximum_filter(gaussian_filtered, footprint=neighborhood)==gaussian_filtered
    background_mask = (gaussian_filtered==0)
    eroded_background_mask = binary_erosion(background_mask, structure=neighborhood, border_value=1)
    centers = numpy.array(numpy.nonzero(local_max - eroded_background_mask)).T
    print 'Found {0} maximums'.format(centers.shape[0])
    cell_rois = []
    if centers.shape[0]>200 and mip.max()<200:
        print 'the recording is probably just noise'
        return mip, cell_rois
    for center in centers:
        distances = list(numpy.sqrt(((centers-center)**2).sum(axis=1)))
        distances.sort()
        if distances[1]<cell_size_pixel:#Use a smaller bounding box if the closest roi is closer than nominal cell size
            roi_size_factor = 1
        else:
            roi_size_factor = 1
        roi_size = int(numpy.round((roi_size_factor*cell_size_pixel)))
        offset = numpy.round(numpy.array([center[0]-0.5*roi_size, center[1]-0.5*roi_size]))
        offset = numpy.where(offset<0, 0, offset)
        for i in range(offset.shape[0]):
            if offset[i]>mip.shape[i]:
                offset[i] = mip.shape[i]-1
        offset=numpy.cast['int'](offset)
        roi = mip[offset[0]:offset[0]+roi_size, offset[1]:offset[1]+roi_size]
        center_pixel_value = roi[roi.shape[0]/2-1:roi.shape[0]/2+1,roi.shape[1]/2-1:roi.shape[1]/2+1].mean()
        bright_pixels_saturated = numpy.where(roi>center_pixel_value,center_pixel_value, roi)
        roi_th = filter.threshold_otsu(bright_pixels_saturated)
        roi_binary = numpy.where(bright_pixels_saturated>roi_th,1,0)
        labeled, nlabels = label(roi_binary)
        center_pixels = labeled[labeled.shape[0]/2-1:labeled.shape[0]/2+1,labeled.shape[1]/2-1:labeled.shape[1]/2+1]
        center_label = center_pixels.mean()
        if center_pixels.std() == 0 and center_label>0:#all pixels are labeled with the same value
            one_labeled = numpy.cast['uint8'](numpy.where(labeled==center_label,1,0))
            roi_coordinates = numpy.array(numpy.nonzero(one_labeled))
            #Exclude roi if roi edges are touched
            if numpy.where(numpy.logical_or(roi_coordinates==0, roi_coordinates==roi_size-1))[0].shape[0]>0.5*roi_size:
                continue
            #calculate perimeter and diameter. Accept as cell if it is close to circle
            inner_pixel_coordinates = numpy.array(numpy.where(scipy.ndimage.filters.convolve(one_labeled, numpy.ones((3,3)))==9))
            perimeter = roi_coordinates.shape[1] - inner_pixel_coordinates[0].shape[0]
            area = roi_coordinates.shape[1]
            #Diameter: get two furthest points
            import itertools
            #Checking the distance between all pixels. Optimal would be to do it for perimeter pixels
            diameter = max([numpy.sqrt(((roi_coordinates[:,ci[0]]-roi_coordinates[:,ci[1]])**2).sum()) for ci in [i for i in itertools.combinations(range(roi_coordinates.shape[1]), 2)]])
            #perimeter/diameter shall be around pi
            peri_diam_ratio = perimeter/diameter
            if (peri_diam_ratio<1.5*numpy.pi) and \
                            (area > minimal_cell_area_pixels and area < maximal_cell_area_pixels):
                #Transform these coordinates back to mip coordinates
                cell_rois.append(numpy.cast['int']((roi_coordinates.T+offset).T))
    return mip,cell_rois
            
def get_data_timing(filename):
    from visexpA.engine.datahandlers import matlabfile
    m=matlabfile.MatData(filename.replace('.hdf5', '.mat'))
    indexes = numpy.where(m.get_field('DATA.0.DI0.y',copy_field=False)[0][0][0][1])[0]
    stimulus_time = m.get_field('DATA.0.DI0.y',copy_field=False)[0][0][0][0][indexes]/1e6#1 us per count
    indexes = numpy.where(m.get_field('DATA.0.SyncFrame.y',copy_field=False)[0][0][0][1])[0]
    imaging_time = m.get_field('DATA.0.SyncFrame.y',copy_field=False)[0][0][0][0][indexes]/1e6#1 us per count
    h=hdf5io.Hdf5io(filename,filelocking=False)
    if 1:
        import visexpA.engine.component_guesser as cg
        rawdata = h.findvar('rawdata')
        idnode = h.findvar('_'.join(cg.get_mes_name_timestamp(h)))
        sfi = idnode['stimulus_frame_info']
        scale = h.findvar('image_scale')['row'][0]
    else:
        rawdata = utils.array2object(numpy.load(os.path.split(filename)[0]+'/rawdata.npy'))
        sfi = hdf5io.read_item(os.path.split(filename)[0]+'/sfi.hdf5', 'sfi', filelocking=False)
        scale = 1.42624
    imaging_time = imaging_time[:rawdata.shape[2]]
    block_times, stimulus_parameter_times,block_info, organized_blocks = process_stimulus_frame_info(sfi, stimulus_time, imaging_time)
    if 'grating' not in filename.lower():
        print 'Detect cells'
        mip,cell_rois = detect_cells(rawdata, scale, 12)
        roi_curves = get_roi_curves(rawdata, cell_rois)
    h.quick_analysis = {}
    if 'grating' not in filename.lower():
        h.quick_analysis['roi_curves']=roi_curves
        h.quick_analysis['cell_rois']=cell_rois
    h.quick_analysis['block_times']=block_times
    h.quick_analysis['stimulus_parameter_times']=utils.object2array(stimulus_parameter_times)
    h.quick_analysis['block_info']=block_info
    h.quick_analysis['organized_blocks']=organized_blocks
    h.save('quick_analysis')
    if 'receptive' in filename.lower():
        plot_receptive_field_stimulus(organized_blocks,roi_curves, mip)
    h.close()
    
def plot_receptive_field_stimulus(organized_blocks,roi_curves, mip):
    '''match positions with curve fragments'''
    from pylab import imshow,show,plot,figure,title,subplot,clf,savefig#TMP
    positioned_curves = []
    positions = []
    for ob in organized_blocks:
        pos = ob[0]['sig'][2]['pos']
        positions.append([pos['col'], pos['row']])
        roi_curve_fragment = [[roi_curve[obi['start']:obi['end']] for obi in ob] for roi_curve in roi_curves]
        positioned_curves.append([pos, ob[0]['sig'][2]['color'], roi_curve_fragment])
    positions = numpy.array(positions)
    nrows = len(set(positions[:,1]))
    ncols = len(set(positions[:,0]))
    col_start = positions[:,0].min()
    row_start = positions[:,1].min()
    grid_size = organized_blocks[0][0]['sig'][2]['size']['row']
    selected_roi = 1
    for roi_i in range(len(roi_curves)):
        for positioned_curve in positioned_curves:
            ploti = (positioned_curve[0]['row']-row_start)/grid_size*ncols+(positioned_curve[0]['col']-col_start)/grid_size+1
            subplot(nrows, ncols, ploti)
            for i in range(len(positioned_curve[2][roi_i])):
                title(numpy.round(utils.nd(positioned_curve[0])))
                plot(positioned_curve[2][roi_i][i], color = [1.0, 0.0, 0.0] if positioned_curve[1] == 1 else [0.0, 0.0, 0.0])
        outfolder = tempfile.gettempdir() if 1 else os.path.join(os.path.split(filename)[0], out, os.path.split(filename)[1])
        if not os.path.exists(outfolder):
            os.path.makedirs(outfolder)
        fn=os.path.join(outfolder, '{1}-{0:0=3}.png'.format(roi_i, os.path.split(filename)[1]))
        savefig(fn,dpi=300)
        clf()
        plotim=numpy.asarray(Image.open(fn))
        mip_with_cell = numpy.zeros((mip.shape[0], mip.shape[1], 3),dtype=numpy.float)
        mip_with_cell[:,:,1] = mip/mip.max()
        for i in range(cell_rois[roi_i][0].shape[0]):
            mip_with_cell[cell_rois[roi_i][0][i],cell_rois[roi_i][1][i], 0] = 0.5
        scaling_factor = plotim.shape[0]/float(mip_with_cell.shape[0])
        new_size = (int(mip_with_cell.shape[0]*scaling_factor),int(mip_with_cell.shape[1]*scaling_factor))
        scaled = numpy.asarray(Image.fromarray(numpy.cast['uint8'](255*mip_with_cell)).resize(new_size))
        merged = numpy.zeros((max(scaled.shape[0],plotim.shape[0]), scaled.shape[1]+plotim.shape[1], 3))
        merged[:scaled.shape[0], :scaled.shape[1],:] = scaled
        merged[:plotim.shape[0], scaled.shape[1]:,:] = plotim[:,:,:3]
        Image.fromarray(numpy.cast['uint8'](merged)).save(fn)
        

#################### End of not working/abandoned concepts ####################

#################### Stimulus frame info processing ####################

def get_block_entry_indexes(sfi, block_name):
    block_start_indexes = [i for i in range(len(sfi)) if sfi[i].has_key('block_start') and sfi[i]['block_name'] == block_name]
    block_end_indexes = [i for i in range(len(sfi)) if sfi[i].has_key('block_end') and sfi[i]['block_name'] == block_name]
    return block_start_indexes, block_end_indexes
    
def sfi2signature(sfi):
    '''
    Remove varying keys from stimulus frame info
    '''
    import copy
    sfisig = []
    for sfii in sfi:
        if sfii.has_key('parameters'):
            item = copy.deepcopy(sfii)
            item.update(item['parameters'])
            removable_keys = ['elapsed_time', 'counter', 'data_series_index', 'flip', 'parameters', 'count', 'frame_trigger']
            for k in removable_keys:
                if item.has_key(k):
                    del item[k]
            sfisig.append(item)
    return sfisig

def cmp_signature(sig1, sig2):
    '''
    Compares two stimulus block signatures
    '''
    if len(sig1) != len(sig2):
        return False
    else:
        for i in range(len(sig1)):
            if cmp(sig1[i], sig2[i]) != 0:
                return False
        return True
    
def sfi2blocks(sfi):
    '''
    Group stimulus frame info entries into blocks
    '''
    block_start_indexes = [i for i in range(len(sfi)) if sfi[i].has_key('block_start')]
    block_end_indexes = [i for i in range(len(sfi)) if sfi[i].has_key('block_end')]
    grouped_sfi_by_blocks = []
    for i in range(len(block_start_indexes)):
        grouped_sfi_by_blocks.append(sfi[block_start_indexes[i]+1:block_end_indexes[i]])
    return grouped_sfi_by_blocks
    
def stimulus_frame_counter2image_frame_counter(ct, imaging_time, stimulus_time):
    '''
    stimulus frame counter values is converted to image data frame index using timing information
    '''
    stim_time_value = stimulus_time[ct]
    return numpy.where(imaging_time>=stim_time_value)[0][0]
    
def process_stimulus_frame_info(sfi, stimulus_time, imaging_time):
    '''
    1) Organizes stimulus frame info into blocks and repetitions
    2) Stimulus function call parameters (size, position, color etc) are matched with imaging frame index
    '''
    #Collect parameter names
    parnames = []
    for sfii in sfi:
        if sfii.has_key('parameters'):
            parnames.extend(sfii['parameters'].keys())
    parnames = list(set(parnames))
    [parnames.remove(pn) for pn in ['frame_trigger', 'count', 'flip'] if pn in parnames]
    #assign frame counts and values to each parameters
    stimulus_parameter_times = {}
    block_times = []
    for sfii in sfi:
        if sfii.has_key('parameters'):
            for k in parnames:
                if sfii['parameters'].has_key(k):
                    if not stimulus_parameter_times.has_key(k):
                        stimulus_parameter_times[k] = []
                    if sfii['parameters'][k] is not None and sfii['parameters'][k] != {} and sfii['parameters'][k] != []:#hdf5io cannot handle this data
                        stimulus_parameter_times[k].append([sfii['counter'], stimulus_frame_counter2image_frame_counter(sfii['counter'], imaging_time, stimulus_time), sfii['parameters'][k]])
        elif sfii.has_key('block_start'):
            block_times.append([stimulus_frame_counter2image_frame_counter(sfii['block_start'], imaging_time, stimulus_time), 1])
        elif sfii.has_key('block_end'):
            block_times.append([stimulus_frame_counter2image_frame_counter(sfii['block_end'], imaging_time, stimulus_time), 0])
    for k in stimulus_parameter_times.keys():
        if stimulus_parameter_times[k] == []:
            del stimulus_parameter_times[k]
    block_times = numpy.array(block_times)
    grouped_sfi_by_blocks = sfi2blocks(sfi)
    block_signatures = [sfi2signature(block_sfi) for block_sfi in grouped_sfi_by_blocks]
    block_boundaries = []
    for b in grouped_sfi_by_blocks:
        c=[item['counter'] for item in b]
        block_boundaries.append([min(c), max(c)])
    block_info = [{'sig': block_signatures[i], 'start': block_boundaries[i][0], 'end': block_boundaries[i][1]} for i in range(len(block_boundaries))]
    #Calculate time and frame indexes for each block
    for block_info_i in block_info:
        for e in ['start', 'end']:
            block_info_i[e] = stimulus_frame_counter2image_frame_counter(block_info_i[e], imaging_time, stimulus_time)
    if len(block_info) ==0:
        return None, stimulus_parameter_times,None,None
    #Find repetitions
    organized_blocks = [[block_info[0]]]
    import itertools
    for b1, b2 in itertools.combinations(block_info, 2):
        if not cmp_signature(b1['sig'],b2['sig']) and len([ob for ob in organized_blocks if cmp_signature(ob[0]['sig'], b2['sig'])])==0:
            organized_blocks.append([b2])
    #Find repetitions and group them
    for organized_block in organized_blocks:
        for block_info_i in block_info:
            if cmp_signature(block_info_i['sig'],organized_block[0]['sig']) and block_info_i not in organized_block:
                organized_block.append(block_info_i)
    return block_times, stimulus_parameter_times,block_info, organized_blocks

class TestExperimentData(unittest.TestCase):
    
    def test_00_pack_swe(self):
        pack_software_environment()
    
    @unittest.skip("")
    def test_00_rlvivobackup(self):
        from visexpman.engine.generic import introspect
        user='default_user'
        animalid='test'
        id=int(time.time())
        files=fileop.listdir_fullpath('v:\\debug\\log')
        with introspect.Timer():
            RlvivoBackup(files,user,id,animalid)
        pass
    
    @unittest.skip("")
    def test_01_read_merge_rois(self):
        path = '/mnt/databig/testdata/read_merge_rois/mouse_test_1-1-2012_1-1-2012_0_0.hdf5'
        cells = hdf5io.read_item(path, 'cells', filelocking = self.config.ENABLE_HDF5_FILELOCKING)
        roi_locations, rois = read_merge_rois(cells, 'g2', 'scanned_2vessels_0_0', -130, 0, 80, 4)
        roi_locations, rois = add_auxiliary_rois(rois, 9, -130, -100, aux_roi_distance = 5.0)
        pass

    @unittest.skip("")
    def test_02_elphys(self):
        from visexpman.users.test import unittest_aggregator
        working_folder = unittest_aggregator.prepare_test_data('elphys')
        map(read_phys, fileop.listdir_fullpath(working_folder))
        
    @unittest.skip("")
    def test_03_smr(self):
        folder=fileop.select_folder_exists(['/home/rz/rzws/temp/santiago/181214_Lema_offcell', '/home/rz/codes/data/181214_Lema_offcell'])
        if folder is None:
            return
        fns =  fileop.listdir_fullpath(folder)
        fns.sort()
        for fn in fns:
            if '.smr' in fn:
                SmrVideoAligner((fn, '/tmp/out'))
                break

    @unittest.skip("")
    def test_04_check_retinal_ca_datafile(self):
        from visexpman.users.test import unittest_aggregator
        from visexpman.users.test.test_configurations import GUITestConfig
        conf = GUITestConfig()
        working_folder = unittest_aggregator.prepare_test_data('retinal_ca_datafiles')
        files = fileop.listdir_fullpath(working_folder)
        res = map(check, files, [conf]*len(files))
        map(self.assertEqual, res, len(res)*[[]])

    @unittest.skip("")
    def test_05_align_stim_with_imaging(self):
        from visexpman.users.test.test_configurations import GUITestConfig
        conf = GUITestConfig()
        from pylab import plot,show,savefig,figure,clf
        for file in fileop.listdir_fullpath('r:\\production\\rei-setup\\zoltan'):
            if parse_recording_filename(file)['type'] == 'data' and '22863' in file:
                if len(check(file,conf))==0:
#                    h=hdf5io.Hdf5io(file,filelocking=False)
                    ts, ti, a = get_activity_plotdata(file)
                    plot(ti,a);plot(ts, a.max()*numpy.ones_like(ts), 'r|');
                    savefig('r:\\temp\\plot\\'+os.path.split(file)[1]+'.png')
                    clf()
#                    h.close()

    @unittest.skip("")
    def test_06_find_cells(self):
        '''
        Issue: two cells close to each other 
        '''
        from pylab import imshow,show,plot,figure,title
        from scipy.ndimage.filters import gaussian_filter,maximum_filter
        from scipy.ndimage.morphology import generate_binary_structure, binary_erosion
        from scipy.ndimage.measurements import label
        import skimage
        from skimage import filter
        from PIL import ImageDraw
        figct = 1
        fn = '/mnt/rzws/temp/cell_detection_test_data.mat'
        folder = '/mnt/rzws/test_data/cortical_cell_detection'
        cell_size = 12#um
        minimal_cell_size = 0.25 #
        maximal_cell_size = 1.1 #
        sigma = 0.1 #cell size scaled
        for fn in fileop.listdir_fullpath(folder):
            if '68975' not in fn: continue
            data = scipy.io.loadmat(fn)
            rawdata = data['rawdata']
            scale = data['image_scale']['row'][0][0][0][0]
            mip,cell_rois = detect_cells(rawdata, scale, cell_size)
            im = numpy.zeros((mip.shape[0],mip.shape[1]*1,3))
#            im[:,:mip.shape[1],0] = numpy.cast['float'](local_max - eroded_background_mask)*mip.max()
            im[:,:mip.shape[1],1] = mip
            for r in cell_rois:
                im[:,:mip.shape[1],2][r[0],r[1]] = mip.max()*(0.4+0.6*numpy.random.random())
                im[:,:mip.shape[1],0][r[0],r[1]] = mip.max()*(0.4+0.6*numpy.random.random())
            Image.fromarray(numpy.cast['uint8'](signal.scale(im, 0, 255))).save('/tmp/1/{0}.png'.format(os.path.split(fn)[1]))
            roi_curves = get_roi_curves(rawdata, cell_rois)
            map(plot, roi_curves);show()

        pass
        
    @unittest.skip("")
    def test_07_receptive_field_stim_plot(self):
        fn='/home/rz/codes/data/recfield/fragment_xy_tr_0_0_0.0_ReceptiveFieldExploreNew_1424256866_0.hdf5'
        get_data_timing(fn)
        
    @unittest.skip("")
    def test_08_cell_detection(self):
        files = fileop.find_files_and_folders('/mnt/rzws/dataslow/rei_data_c')[1]
        from skimage import filter
        otsu=True
        f=[f for f in files if '1423066844' in f][0]
        h=hdf5io.Hdf5io(f, filelocking=False)
        h.load('raw_data')
        meanimage = numpy.cast[h.raw_data.dtype.name]((numpy.cast['float'](h.raw_data).mean(axis=0)[0]))
        g=find_rois(meanimage)
        gcolored=numpy.zeros((g.shape[0],g.shape[1],3))
        for i in range(1,g.max()):
            c=numpy.random.random(3)
            gcolored[numpy.where(g==i)]=c
            
        subplot(1,2,1)
        imshow(meanimage,cmap='gray')
        subplot(1,2,2)
        imshow(gcolored,cmap='gray')
        show()
        if 0:
            maxval=2**int(h.raw_data.dtype.name.replace('uint',''))
            threshold = filter.threshold_otsu(meanimage) if otsu else entropy_threshold(meanimage, maxval)
            marker = numpy.where(meanimage>threshold,1,0)
            geo = geodesic_dilation(marker,meanimage-meanimage.min())
            gm=geo*meanimage
            threshold = filter.threshold_otsu(geo) if otsu else entropy_threshold(geo, maxval)
            geot = numpy.where(geo>threshold,1,0)
            figure(3);subplot(1,3,1);title('meanimg');imshow(meanimage,cmap='gray');
            subplot(1,3,2);title('geot');imshow(geot,cmap='gray')
            subplot(1,3,3);title('marker');imshow(marker,cmap='gray');show()
        pass
        h.close()
        
    @unittest.skip("")
    def test_09_extract_roi_curve(self):
        h=hdf5io.Hdf5io(fileop.listdir_fullpath('/mnt/rzws/test_data/extract_roi')[0],filelocking=False)
        h.load('raw_data')
        roitype='circle'
        roix=10
        roiy=10
        roisize=5
        extract_roi_curve(h.raw_data, roix, roiy, roisize,roitype)
        h.close()
        
    
    @unittest.skip("")    
    def test_10_caimgfile(self):
        h=CaImagingData(fileop.listdir_fullpath('/mnt/rzws/test_data/datafile')[0],filelocking=False)
        h.prepare4analysis()
        h.close()
        
    #@unittest.skip("")
    def test_11_caimgfile_convert(self):
        fn='/home/rz/mysoftware/data/mipexport/data_707-18daypostinfect-animal1-slice1-region8_rep3_1sStim_LedConfig_201702241318216.hdf5'
        fn='e:\\Zoltan\\1\\data_706-mouse1-slice1-reg1-rep1-500ms-1000mA_LedConfig_201703020938240.hdf5'
        fn='/data/data/user/Zoltan/ao/data_719-m2-reg4-rep1-LEDeye-5mA-wLGN-500ms-p50ms_Led2Config_201704202056329.hdf5'
        h=CaImagingData(fn)
        h.sync2time()
        h.get_image()
        h.convert('png')
        h.convert('rois')
        #h.convert('mp4')
        h.close()
        
    @unittest.skip("")
    def test_12_gamma(self):
        gammatext2hdf5('/tmp/g.txt')
        
    @unittest.skip("")
    def test_13_y(self):
        from visexpman.users.test import unittest_aggregator
        f =  fileop.listdir_fullpath(unittest_aggregator.prepare_test_data('yscanner', '/tmp/wf'))[0]
        import scipy.io
        yscanner2sync(scipy.io.loadmat(f)['recorded'][:,3])
        
def find_rois(meanimage):
    from skimage import filter
    import scipy.ndimage.measurements
    threshold = filter.threshold_otsu(meanimage)
    marker = numpy.where(meanimage>threshold,1,0)
    geo = geodesic_dilation(marker,meanimage-meanimage.min())
    threshold2 = filter.threshold_otsu(geo)
    geot = numpy.where(geo>threshold2,1,0)
    labeled, n = scipy.ndimage.measurements.label(geot)
    return labeled
    
        
        
def entropy_threshold(image, maxval):
#    import itk
#    import copy
#    pixelType = itk.US
#    imageType = itk.Image[pixelType, 2]
#    itk_py_converter = itk.PyBuffer[imageType]
#    itk_image = itk_py_converter.GetImageFromArray( image.astype(numpy.uint16) )
#    filter = itk.MaximumEntropyThresholdImageFilter[imageType,imageType].New()
#    
#    return threshold
    hist, bins=numpy.histogram(image,numpy.arange(maxval+1))
    pi=hist/float(image.shape[0]*image.shape[1])
    entropy = []
    for s in range(1,maxval):
        ps=sum([pi[i] for i in range(s)])
        ha=sum([-pi[i]/ps*numpy.log(pi[i]/ps)for i in range(s) if pi[i]>0])
        hb=sum([-pi[i]/(1-ps)*numpy.log(pi[i]/(1-ps))for i in range(s,maxval) if pi[i]>0])
        entropy.append(ha+hb)
        pass
    threshold = numpy.array(entropy).argmax()
    return threshold
    
def geodesic_dilation(marker, mask):
    import scipy.ndimage.morphology
    import itk
    import copy
    pixelType = itk.US
#    pixelType = itk.F
    imageType = itk.Image[pixelType, 2]
    itk_py_converter = itk.PyBuffer[imageType]
#    marker[:,:]=0
#    marker[10,10]=1
#    mask[:,:]=0
#    mask[5:15,5:15]=1
    marker_image = itk_py_converter.GetImageFromArray( marker.astype(numpy.uint16)*mask.max() )
    mask_image = itk_py_converter.GetImageFromArray( mask.astype(numpy.uint16) )
    filter = itk.GrayscaleGeodesicDilateImageFilter[imageType, imageType].New()
#    filter.RunOneIterationOff()
#    filter.SetFullyConnected(True)
    filter.SetMarkerImage(marker_image)
    filter.SetMaskImage(mask_image)
    out_converter = itk.PyBuffer[imageType]
    return copy.deepcopy(out_converter.GetArrayFromImage(filter.GetOutput() ))
        
def anti_zigzag(im):
    shifts = [shift_between_arrays(im[line],im[line+1]) for line in range(im.shape[1]-1)]
    
        
        
        
    

def shift_between_arrays(a1, a2):
    return numpy.array([numpy.correlate(numpy.cast['float'](a1), numpy.roll(numpy.cast['float'](a2),shift)) for shift in range(-a1.shape[0], a1.shape[0])]).argmax()
    
def gammatext2hdf5(filename):
    with open(filename,'rt') as f:
        txt=f.read()
    gc=numpy.array([map(float,line.split('\t')) for line in txt.split('\n')[:-1]]).T
    hdf5io.save_item(os.path.join(os.path.dirname(filename),'gamma.hdf5'),'gamma_correction', gc, filelocking=False)
    
def yscanner2sync(waveform):
    pass
    
def hdf52mat(filename):
    h=hdf5io.Hdf5io(filename)
    ignore_nodes=['hashes']
    rootnodes=[v for v in dir(h.h5f.root) if v[0]!='_' and v not in ignore_nodes]
    mat_data={}
    for rn in rootnodes:
        if os.path.basename(filename).split('_')[-2] in rn:
            rnt='idnode'
        else:
            rnt=rn
        mat_data[rnt]=h.findvar(rn)
        if hasattr(mat_data[rnt], 'has_key') and len(mat_data[rnt].keys())==0:
            mat_data[rnt]=0
    if mat_data.has_key('soma_rois_manual_info') and mat_data['soma_rois_manual_info']['roi_centers']=={}:
        del mat_data['soma_rois_manual_info']
    h.close()
    matfile=add_mat_tag(filename)
    scipy.io.savemat(matfile, mat_data, oned_as = 'row', long_field_names=True,do_compression=True)
    
def read_sync(filename):
    h=hdf5io.Hdf5io(filename)
    idnode=h.findvar('_'.join(os.path.basename(filename).split('.')[-2].split('_')[-3:]))
    sd=idnode['sync_data']
    h.close()
    return sd
    
def roi_plot(pars):
    filename, outfile, roi=pars
    cla()
    clf()
    name=os.path.basename(filename).split('_')[1]
    stimname=os.path.basename(filename).split('_')[-2]
    title('{0}\n{1}'.format(name, stimname))
    plot(roi['timg'], roi['raw'])
    xlabel('time [s]')
    ylabel('raw pixel')
    for rect in range(roi['tstim'].shape[0]/2):
        w=roi['tstim'][2*rect+1]-roi['tstim'][2*rect]
        h=roi['raw'].max()-roi['raw'].min()
        gca().add_patch(Rectangle((roi['tstim'][rect*2], roi['raw'].min()), w, h,alpha=0.7, color=(0.9, 0.9, 0.9)))
    savefig(outfile)

def cm2um(cm, config):
    return cm*config.SCREEN_SIZE_UM['col']/config.SCREEN_WIDTH
    
def um2cm(um, config):
    return um*config.SCREEN_WIDTH/config.SCREEN_SIZE_UM['col']
    
def cpd2um(cpd,retina_scale=30):
    '''
    Converts cycle per degree to um on retina considering retina_scale
    retina_scale is in um (on retina) per degree
    Output: spatial period in um
    '''
    return retina_scale/cpd
    
def um2cpd(um, retina_scale=30):
    raise NotImplementedError('to be fixed')
    return um/(360.*retina_scale)

try:
    import paramiko
except ImportError:
    pass
    
class RlvivoBackup(object):
    def __init__(self, files,user,id,animalid):
        '''
        Assumes that:
        1) /mnt/databig is mounted as u drive
        2) files reside on v: drive
        3) v:\\codes\\jobhandler\\pw.txt is accessible
        '''
        if os.name!='nt':
            raise RuntimeError('Not supported OS')
        pwfile='v:\\codes\\jobhandler\\pw.txt'
        if not os.path.exists(pwfile):
            raise RuntimeError('Password file does not exist')
        self.files=files
        self.user=user
        self.id=id if isinstance(id, str) else utils.timestamp2ymd(float(self.id),'')
        self.animalid=animalid
        self.connect()
        self.target_folder()
        self.copy()
        self.close()
        
        
    def connect(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect('rlvivo1.fmi.ch', username='mouse',password=fileop.read_text_file('v:\\codes\\jobhandler\\pw.txt'))
        
    def close(self):
        self.ssh.close()
        
    def check_ssh_error(self,e):
        emsg=e.readline()
        if emsg!='':
            raise RuntimeError(emsg)
        
    def target_folder(self):
        self.target_dir='/'.join(['/mnt/databig/backup',self.user,self.id,str(self.animalid)])
        i,o,e1=self.ssh.exec_command('mkdir -p {0}'.format(self.target_dir))
        i,o,e2=self.ssh.exec_command('chmod 777 {0} -R'.format(self.target_dir))
        for e in [e1,e2]:
            self.check_ssh_error(e)
        
    def copy(self):
        for f in self.files:
            flinux='/'.join(f.replace('v:\\', '/mnt/datafast/').split('\\'))
            i,o,e=self.ssh.exec_command('cp {0} {1}'.format(flinux,self.target_dir))
            self.check_ssh_error(e)

if __name__=='__main__':
    unittest.main()
        
    
    
    
    
