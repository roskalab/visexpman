import sys,scipy.io
import copy_reg
import types
import multiprocessing
import pdb
from pylab import plot,show,imshow
import time
import hdf5io
import subprocess
import numpy
import os
import os.path
import itertools
from visexpman.engine.generic import fileop,utils,signal,introspect,stringop
from visexpman.engine.vision_experiment import experiment_data
import unittest
import tempfile
FIX1KHZ= False
NOMATFILE= False
NWEEKS=2
NOT_50X50UM= not True
VERTICAL_FLIP=True

class PhysTiff2Hdf5(object):
    '''
    Convert phys/tiff data into hdf5
    '''
    def __init__(self, folder, outfolder=None,allow_high_framerate=False):
        self.allow_high_framerate=allow_high_framerate
        self.folder=folder
        self.outfolder=outfolder
        self.maximal_timediff = 3
        self.use_tiff = True
        self.skipped_files = []
        self.processed_pairs = []
        self.irlaser = len(sys.argv) == 3 and sys.argv[2]=='irlaser'
        
    def detect_and_convert(self):
        now=time.time()
        recent_folders=[f for f in fileop.listdir_fullpath(self.folder) if os.path.isdir(f) and now-os.path.getctime(f)<3600*168*NWEEKS]
        self.allfiles=[]
        for folder in recent_folders:
            self.allfiles.extend(fileop.find_files_and_folders(folder)[1])
        if self.outfolder==self.folder:
            self.outfiles=self.allfiles
            self.outfiles = [f for f in self.outfiles if fileop.file_extension(f)=='hdf5']
        else:
            self.outfiles = [f for f in fileop.find_files_and_folders(self.outfolder)[1] if fileop.file_extension(f)=='hdf5']
        
        excluded_extensions=['txt','hdf5','tif' if not self.use_tiff else 'csv']
        self.allfiles = [f for f in self.allfiles if not 'timestamp' in f and fileop.file_extension(f) not in excluded_extensions]
        #self.allfiles = [f for f in self.allfiles if now - os.path.getmtime(f)<2*168*3600]#Considering files not older than 2 weeks
        #Exclude unclosed files
        now=time.time()
        self.allfiles = [f for f in self.allfiles if now-os.path.getctime(f)>10 and now-os.path.getmtime(f)>10]
        
        if self.irlaser:
            physfiles = [f for f in self.allfiles if fileop.file_extension(f)=='csv' and 'rect' not in f and 'timestamps' not in f]
        else:
            physfiles = [f for f in self.allfiles if fileop.file_extension(f)=='phys']
        tiffiles = [f for f in self.allfiles if fileop.file_extension(f)==('tif' if self.use_tiff else 'csv')]
        if self.irlaser:
            tiffiles = [tf for tf in tiffiles if tf not in physfiles]
        #if not self.use_tiff:
         #   tiffiles = [f for f in tiffiles if not 'timestamp' in f]
        processable_physfiles = []
        if 1:
            phys_ids = [[str(experiment_data.get_id(os.path.getmtime(f))),f] for f in physfiles]
            out_ids= [str(os.path.split(of)[1].split('_')[-2]) for of in self.outfiles]
            processable_physfiles = [pid[1] for pid in phys_ids if pid[0] not in out_ids]
        #Find corresponding folder with tiff file
        pairs = []
        #ids=[str(os.path.basename(o).split('_')[-2]) for o in self.outfiles]
        for pf in processable_physfiles:
            if 1:
                regexp = pf
                tiffiles_current_folder=[tf for tf in tiffiles if os.path.dirname(pf) in tf]
                found = [tf for tf in tiffiles_current_folder if os.path.basename(regexp.replace(fileop.file_extension(pf),''))[:-1] in tf]
                foundmat=[f for f in self.allfiles if f[-4:]=='.mat' and os.path.basename(pf) in f or NOMATFILE or self.irlaser]
                
            if 1:
                if len(found)>0 and len(foundmat)>0 and [pf,found[0]] not in self.processed_pairs:
                    if os.path.getsize(pf)>10e3 and os.path.getsize(found[0])>10e3:
#                        id = str(experiment_data.get_id(os.path.getmtime(pf)))
#                        if id not in ids:# len([f for f in self.outfiles if id in f])==0
                            pairs.append([pf, found[0]])
        if len(pairs)>0:
            print 'converting pairs'
            for p in pairs:
                print p[0]
                print p[1]
                print ''
               
#        converted=[]
#        for p in pairs:
#            try:
#                converted.append(self.build_hdf5(p[0],p[1], self.outfolder))
#            except:
#                pass
        
        self.processed_pairs.extend(pairs)
        converted=[]
        for p in pairs:
            try:
                res=self.build_hdf5(p[0],p[1], self.outfolder)
                converted.append(res)
            except:
                import traceback
                print traceback.format_exc()
            
        return converted
        
    def convert_old_files(self):
        self.match_files()
        if 1:
            for k,v in self.assignments.items():
                print k
                self.build_hdf5(k, v[0], None)#self.folder)
        else:
            p=multiprocessing.Pool(processes=14)
            pars = [(k, v[0]) for k, v in self.assignments.items()]
            res = p.map(self.build_hdf5_2,pars)
        print self.skipped_files
        
    def match_files(self):
        self.allfiles = fileop.find_files_and_folders(self.folder)[1]
        self.filetimes = [[f, os.path.getmtime(f)] for f in self.allfiles]
        self.files = {}
        for filetype in ['phys', 'tif']:
            self.files[filetype] = [f for f in self.filetimes if fileop.file_extension(f[0]) == filetype]
        assignments = {}
        for fphys, tphys in self.files['phys']:
            for ftif, ttif in self.files['tif']:
                tdiff = abs(tphys-ttif)
                if tdiff>self.maximal_timediff:
                    continue
                elif not assignments.has_key(fphys):
                    assignments[fphys] = [ftif, tdiff]
                elif assignments[fphys][1]>tdiff:
                    assignments[fphys] = [ftif, tdiff]
        #check assignment for redundancy
        assigned_tiffiles = [fn for fn, tdiff in assignments.values()]
        if len(assigned_tiffiles) != len(set(assigned_tiffiles)):
            assigned_tiffiles.sort()
            redundant_tiff = [assigned_tiffiles[i] for i in range(len(assigned_tiffiles)-1) if assigned_tiffiles[i] == assigned_tiffiles[i+1]]
            [[k,v] for k,v in assignments.items() if v[0] in redundant_tiff]
            raise RuntimeError('A tifffile is assigned to multiple phys files')
        self.assignments = assignments
        pass
        
    def build_hdf5_2(self,entry):
        fphys,ftiff = entry
        self.build_hdf5(fphys,ftiff)
        
    def backup_files(self,fphys,ftiff,fhdf5):
        bu_folder = 'D:\\backup'
        if not os.path.exists(bu_folder) or os.name=='posix':
            return
        import shutil
        shutil.copy(fphys, bu_folder)
        shutil.copy(fhdf5, bu_folder)
        os.path.join(bu_folder, os.path.basename(os.path.dirname(ftiff))+'_'+os.path.basename(ftiff))
        shutil.copy(ftiff, os.path.join(bu_folder, os.path.basename(os.path.dirname(ftiff))+'_'+os.path.basename(ftiff)))
        
    def build_hdf5(self,fphys,ftiff,folder=None):
        t0=time.time()
        coordsfn=os.path.join(os.path.dirname(ftiff), 'coords.txt')
        absolute_stage_coordinates=numpy.zeros(3)
        if os.path.exists(coordsfn):
            try:
                absolute_stage_coordinates=numpy.array(map(float, fileop.read_text_file(coordsfn).split('\r\n')[0].split('\t')))
                print 'coords file processed'
            except:
                print 'coords file cannot be read'
        else:
            print 'coords file not found', coordsfn
            
        if self.use_tiff:
            tmptiff = os.path.join(tempfile.gettempdir(), 'temp.tiff')
            if os.path.exists(tmptiff):
                os.remove(tmptiff)
            fileop.write_text_file(os.path.join(tempfile.gettempdir(),'m.txt'), 'saveAs("tiff","{0}");'.format(tmptiff))
            cmd = 'imagej "{0}" -batchpath {1}'.format(ftiff, os.path.join(tempfile.gettempdir(),'m.txt'))
            subprocess.call(cmd,shell=True)
            time.sleep(4)
            if not os.path.exists(tmptiff):
                self.skipped_files.append(ftiff)
                return
            import tifffile
            raw_data = tifffile.imread(tmptiff)[1::2]
            raw_data = raw_data.reshape((raw_data.shape[0], 1, raw_data.shape[1], raw_data.shape[2]))
        else:
#            import struct
#            f =open(ftiff, 'rb')
            sizex, sizey, a,b, res = map(float, os.path.split(ftiff)[1].replace('.csv','').split('_')[-5:])
#            data_s = f.read()
#            data=numpy.array(struct.unpack('>'+''.join(len(data_s)/4*['f']),data_s), dtype = numpy.float32)
            try:
                data=numpy.fromfile(ftiff,">f4")
            except IOError:
                time.sleep(10)
                data=numpy.fromfile(ftiff,">f4")
            nframes = int(data.shape[0]/(sizex*res*(sizey*res-1))/2)
            if nframes<10:
                return
            try:
                data_=data[:int(2*(sizey*res*(sizex*res-1))*nframes)]
                pixel_per_frame = int(2*(sizex*res)*(sizey*res-1)+4)
                boundaries = numpy.repeat(numpy.arange(nframes)*pixel_per_frame,2)
                boundaries[1::2]+=pixel_per_frame-4
                boundaries = boundaries[numpy.where(boundaries<data_.shape[0])[0]]
                nframes=boundaries.shape[0]/2
                boundaries = boundaries[:2*(boundaries.shape[0]/2)]
                if NOT_50X50UM:
                    rawdata = numpy.array(numpy.split(data, boundaries)[1:][::2]).reshape((nframes,2, int(sizey*res-1), int(sizex*res)))
                else:
                    rawdata = numpy.array(numpy.split(data, boundaries)[1:][::2]).reshape((nframes,2, int(sizex*res-1), int(sizey*res)))
                #Memory error here
#                rd=(rawdata-rawdata.min())
#                rd/=(rd.max()-rd.min())
#                rd*=(2**16-1)
#                raw_data = numpy.cast['uint16'](rd)
               # if rawdata.shape[0]>800:return None#TMP fix for memory error
                raw_data = numpy.cast['uint16'](signal.scale(rawdata[:,::-1,:,:],0,2**16-1))
            except MemoryError:#Too long recording
                return None
        #Up-down flip
        raw_data = numpy.flipud(raw_data.swapaxes(2,0).swapaxes(3,1)).swapaxes(0,2).swapaxes(1,3)
        print 'rawdata ok', time.time()-t0
        recording_parameters = {}
        recording_parameters['resolution_unit'] = 'pixel/um'
        recording_parameters['pixel_size'] = float(ftiff.split('_')[-1].replace('.'+fileop.file_extension(ftiff), ''))
        recording_parameters['scanning_range'] = utils.rc((map(float,ftiff.split('_')[-5:-3])))
        recording_parameters['elphys_sync_sample_rate'] = 10000 if not FIX1KHZ else 1000
        if self.irlaser:
            experiment_name = 'irlaser'
            with open(fphys,'rt') as f:
                txt=f.read()
            data=numpy.array([map(float,line.split('\t')) for line in txt.split('\n')[:-1]]).T
            metadata={}
            metadata['Sample Rate']=10000
            try:
                metadata['repeats'], metadata['pulse_width'], metadata['laser_power']=map(float,os.path.basename(fphys).replace('.csv','').split('_')[-3:])
            except:
                pass
            data[1]=data[2]
            data[2]=data[4]
            data=data[:3]
        else:
            data, metadata = experiment_data.read_phys(fphys)
            if data.shape[0]!=3:
                time.sleep(3)
                data, metadata = experiment_data.read_phys(fphys)
            experiment_name = self.parse_stimulus_name(metadata)
#        if 'spot' not in experiment_name.lower() or 'annulus' not in experiment_name.lower():
#            return None
        recording_parameters['experiment_name']=experiment_name
        recording_parameters['experiment_source']= fileop.read_text_file(metadata['Stimulus file']) if metadata.has_key('Stimulus file') and os.path.exists(metadata['Stimulus file']) else ''
        recording_parameters['experiment_source_file'] = metadata['Stimulus file'] if metadata.has_key('Stimulus file') else ''
        recording_parameters['absolute_stage_coordinates'] = absolute_stage_coordinates
        if float(metadata['Sample Rate'])!=(10000 if not FIX1KHZ else 1000):
            if 1:
                raise RuntimeError('Sync signal sampling rate is expected to be 10 kHz. Make sure that spike recording is enabled')
        if data.shape[0]!=3:
            raise RuntimeError('Sync signals might not be recorded. Make sure that recording ai4:5 channels are enabled, {0}'.format(data.shape))
        sync_and_elphys = numpy.zeros((data.shape[1], 5))
        matfile=[f for f in os.listdir(os.path.dirname(fphys)) if os.path.basename(fphys) in f and f[-4:]=='.mat']
        stiminfo_available=False
        if len(matfile)>0:
            stimdata=scipy.io.loadmat(os.path.join(os.path.dirname(fphys),matfile[0]))
            supported_stims=['FlashedShapePar','MovingShapeParameters', 'Annulus', 'Spot', 'LargeSpot10sec','Fullfield10min']
            stiminfo_available=str(stimdata['experiment_config_name'][0]) in supported_stims
        else:
            print 'no stim metadata found'
            if not NOMATFILE and not self.irlaser:
                return
        if stiminfo_available:
            if stimdata['experiment_config_name'][0]=='MovingShapeParameters':
                block_startend=[item['counter'][0][0][0][0] for item in stimdata['stimulus_frame_info'][0] if item['stimulus_type']=='show_fullscreen'][1:-1]
                block_startend+=numpy.append(numpy.where(numpy.diff(block_startend)==0,-1,0),0)
            elif stimdata['experiment_config_name'][0] in ['FlashedShapePar','Annulus','Spot', 'LargeSpot10sec']:
                block_startend=[item['counter'][0][0][0][0] for item in stimdata['stimulus_frame_info'][0] if item['stimulus_type']=='show_shape']
            elif stimdata['experiment_config_name'][0]=='Fullfield10min':
                block_startend=[item['counter'][0][0][0][0] for item in stimdata['stimulus_frame_info'][0] if item['stimulus_type']=='show_fullscreen' and item['parameters'][0][0]['color'][0][0]==1]
            pulse_start=signal.trigger_indexes(data[1])[::2]
            sig=numpy.zeros_like(data[1])
            boundaries=pulse_start[block_startend]
            for i in range(boundaries.shape[0]/2):
                sig[boundaries[2*i]:boundaries[2*i+1]]=5
            sync_and_elphys[:,2]=sig
        else:
            sync_and_elphys[:,2] = self.sync_signal2block_trigger(data[1])#stim sync
        sig = self.yscanner_signal2trigger(data[2], float(metadata['Sample Rate']), raw_data.shape[2])
        if sig is None:
            return
        sync_and_elphys[:,4] = sig
        #a=raw_data.mean(axis=2).mean(axis=2)[:,0]
        #plot(2*a);plot(data[1]);plot(data[2]);show()
        print 'sync data ok', time.time()-t0
        id = experiment_data.get_id(os.path.getmtime(fphys))
        if folder is None:
            folder = os.path.join(tempfile.gettempdir(), os.path.split(ftiff)[0].split('rei_data')[1][1:])
        folder = os.path.dirname(fphys)#(tempfile.gettempdir(), os.path.split(ftiff)[0].split('rei_data')[1][1:])
        if not os.path.exists(folder):
            os.makedirs(folder)
        cellid=os.path.split(ftiff)[1].split('_')[0]
        filename = os.path.join(folder, 'data_{1}_{2}_{0}_0.hdf5'.format(id, cellid, experiment_name))
        print utils.timestamp2ymdhms(time.time()), 'saving to file', time.time()-t0,filename
        h=hdf5io.Hdf5io(filename,filelocking=False)
        h.raw_data = numpy.rollaxis(raw_data, 2,4)#Make sure that analysis and imaging software show the same orientations

        h.fphys = fphys
        h.ftiff = ftiff
        h.recording_parameters=recording_parameters
        h.sync_and_elphys_data = sync_and_elphys
        h.elphys_sync_conversion_factor=1
        h.phys_metadata = utils.object2array(metadata)
        h.configs_stim = {'machine_config':{'ELPHYS_SYNC_RECORDING': {'ELPHYS_INDEXES': [0,1],'SYNC_INDEXES': [2,3,4]}}}
        h.save(['raw_data', 'fphys', 'ftiff', 'recording_parameters', 'sync_and_elphys_data', 'elphys_sync_conversion_factor', 'phys_metadata', 'configs_stim'])
        h.close()
        fileop.set_file_dates(filename, id)
        if 0: self.backup_files(fphys,ftiff,filename)
        return filename
        
    def parse_stimulus_name(self,metadata):
        if not metadata.has_key('Stimulus file'):
            return 'unknown'
        if os.path.exists(metadata['Stimulus file']):
            m=introspect.import_code(fileop.read_text_file(metadata['Stimulus file']),'experiment_config_module', add_to_sys_modules=1)
            for cl in dir(m):
                if getattr(m, cl).__bases__[0].__name__ == 'ExperimentConfig':
                    return cl
        else:
            return os.path.split(metadata['Stimulus file'])[1].split('\\')[-1].replace('.py','')
        
    def sync_signal2block_trigger(self, sig):
        if self.irlaser:
            return sig*5.0/sig.max()
        indexes = signal.trigger_indexes(sig)
        if ((10000.0 if not FIX1KHZ else 1000.0)/numpy.diff(indexes)[1::2]).mean()<55:
            return sig
        else:
            #assuming
            delay_before_start=15 if sig.shape[0]/(10000.0 if not FIX1KHZ else 1000.0) > 30 else 10
            ontime=2
            frame_rate=60
            sig2=numpy.zeros_like(sig)
            rising_index = delay_before_start*frame_rate
            falling_index = (delay_before_start+ontime)*frame_rate
            try:
                sig2[indexes[2*rising_index]:indexes[2*falling_index]]=5
            except:
                print 'sync signal recording was aborted'
            SR=(10000.0 if not FIX1KHZ else 1000.0)
            if indexes.shape[0]/(2*sig.shape[0]/SR)>66:
                print 'sync signal not detected, assuming timing'
                sig2=numpy.zeros_like(sig)
                sig2[delay_before_start*SR:(delay_before_start+ontime)*SR]=5
            return sig2
        
    def yscanner_signal2trigger(self,waveform, fsample,nxlines):
        if self.irlaser:
            threshold_factor = 1e-5
        else:
            threshold_factor = 1.0
        #First harmonic will be the frame rate
        factor=5
        f=numpy.fft.fft(waveform[:waveform.shape[0]/factor])
        f=f[:f.shape[0]/2]
        df=1.0/(waveform.shape[0]/fsample)
        frame_rate = factor*abs(f)[1:].argmax()*df#First harmonic has the highest amplitude
        if abs(f)[1:].argmax()==0:
            frame_rate=10.0
        if frame_rate>30 and not self.allow_high_framerate:#Then probably x scanner signal
            frame_rate /= nxlines
            start_of_first_frame = numpy.where(abs(numpy.diff(waveform))>2000*threshold_factor)[0][0]
            end_of_last_frame = numpy.where(abs(numpy.diff(waveform))>2000*threshold_factor)[0][-1]
        else:
            start_of_first_frame = numpy.where(abs(numpy.diff(waveform))>1000*threshold_factor)[0][0]
            end_of_last_frame = numpy.where(abs(numpy.diff(waveform))>1000*threshold_factor)[0][-1]
        #Try to extract first period
        th=numpy.histogram(waveform[start_of_first_frame+1:])[1][1]
        widths=numpy.diff(numpy.nonzero(numpy.diff(numpy.where(waveform[start_of_first_frame+1:]<th,1,0)))[0])
        period_time=numpy.median(widths[0::2])+numpy.median(widths[1::2])
        frame_rate=fsample/period_time        
        frame_rate=10.0
        if NOT_50X50UM:
            frame_rate=20.0
        if (frame_rate<5 or frame_rate>20) and not self.allow_high_framerate:
            pdb.set_trace()
            raise RuntimeError(frame_rate)
        #first frame's start time has to be calculated
        if start_of_first_frame>fsample*10:
            pdb.set_trace()
            raise RuntimeError(start_of_first_frame)
        flyback_duration = 10#sample
        nsample_per_period = int(fsample/frame_rate)
        try:
            one_period = numpy.concatenate((numpy.ones(nsample_per_period-flyback_duration), numpy.zeros(flyback_duration)))
        except:
            pdb.set_trace()
#        nperiods = (waveform.shape[0]-start_of_first_frame)/nsample_per_period
        nperiods = (end_of_last_frame-start_of_first_frame)/nsample_per_period
        trigger_signal = numpy.zeros_like(waveform)
        pulses = numpy.concatenate((numpy.zeros(start_of_first_frame), numpy.tile(one_period, nperiods)))
        trigger_signal[:pulses.shape[0]]=pulses
        return trigger_signal
        
def phys2mat(filename):
    if os.path.isdir(filename):
        filename = fileop.find_files_and_folders(filename, extension = 'phys')[1]
    import scipy.io
    from visexpman.engine.vision_experiment.experiment_data import read_phys
    for f in filename:
        data, metadata = read_phys(f)
        for k in metadata.keys():
            metadata[stringop.to_variable_name(k)] = metadata[k]
            del metadata[k]
        scipy.io.savemat(f.replace('.phys','.mat'), {'data': data, 'metadata': metadata}, oned_as='column')
        
def merge_ca_data(folder,**kwargs):
    files=os.listdir(folder)
    #Stimulus info
    stimdatafile=os.path.join(folder,[f for f in files if os.path.splitext(f)[1]=='.mat'][0])
    #    raise RuntimeError('Stimulus datafile is missing')
    stimulus = utils.array2object(scipy.io.loadmat(stimdatafile)['serialized'])
    keep_keys=['experiment_config_name', 'stimulus_frame_info', 'generated_data', 'experiment_name', 'experiment_source', 'config', 'software_environment']
    stimulus=dict([(k, stimulus[k]) for k in keep_keys])#!!!!
    #Imaging data
    #try:
    imaging_folder=[os.path.join(folder,f) for f in files if os.path.isdir(os.path.join(folder,f))][0]
    #except:
    #    raise RuntimeError('Imaging datafiles are missing')
    recording_name=os.path.basename(imaging_folder)
    frames=[]
    while True:#Wait until all files are copied
        frames_new=[os.path.join(imaging_folder,f) for f in os.listdir(imaging_folder) if os.path.splitext(f)[1]=='.png']
        if len(frames_new)==len(frames):
            break
        import copy
        frames=copy.deepcopy(frames_new)
        time.sleep(1.0)
    if len(frames)==0:
        raise RuntimeError('No image frame files found. Make sure that TOP and/or SIDE channels are enabled')
    channels=['side','top']
    from PIL import Image
    rawdata=[]
    for channel in channels[::-1]:
        chframes=[f for f in frames if os.path.basename(f).split('_')[-2]==channel]
        chframes.sort()
        rawdata.append([numpy.asarray(Image.open(chf)) for chf in chframes])
    raw_data=numpy.copy(numpy.array(rawdata).swapaxes(0,1))
    raw_data = numpy.fliplr(raw_data.swapaxes(2,0).swapaxes(3,1)).swapaxes(0,2).swapaxes(1,3)
    #Sync data
    syncfile=os.path.join(folder,[f for f in files if os.path.splitext(f)[1]=='.hdf5'][0])
    hsync=hdf5io.Hdf5io(syncfile)
    machine_config=hsync.findvar('machine_config')
    sync_scaling=hsync.findvar('sync_scaling')
    recording_parameters = {}
    recording_parameters['resolution_unit'] = 'pixel/um'
    recording_parameters['pixel_size'] = float(os.path.splitext(os.path.basename(frames[0]))[0].split('_')[-3])
    recording_parameters['scanning_range'] = utils.rc((map(float,os.path.splitext(os.path.basename(frames[0]))[0].split('_')[-7:-5])))
    recording_parameters['elphys_sync_sample_rate'] = machine_config['machine_config']['SYNC_RECORDER_SAMPLE_RATE']
    recording_parameters['experiment_name']=stimulus['experiment_name']
    recording_parameters['experiment_source']= kwargs['stimulus_source_code']
    recording_parameters['experiment_source_file'] = kwargs['stimfile']
    for k,v in kwargs.items():
        if not recording_parameters.has_key(k):
            recording_parameters[k]=v
    hsync.load('sync')
    hsync.sync=numpy.cast['float'](hsync.sync)/sync_scaling['scale']-sync_scaling['offset']#Scale back to voltage range
    sync_and_elphys = numpy.zeros((hsync.sync.shape[0], 5))
    sync_and_elphys[:,2]=hsync.sync[:,2]#block trigger
    #TODO: convert y scanner to binary
    sync_and_elphys[:,4]=yscanner2sync(hsync.sync[:,0], machine_config['machine_config']['SYNC_RECORDER_SAMPLE_RATE'])#frame trigger
    hsync.close()
    #Save everything to final file
    filename=os.path.join(os.path.dirname(folder), os.path.basename(syncfile).replace('sync', 'data_' + recording_name))
    h=hdf5io.Hdf5io(filename)
    h.recording_parameters=recording_parameters
    h.sync_and_elphys_data = sync_and_elphys
    h.fsync=syncfile
    h.fimg=imaging_folder
    h.fstim=stimdatafile
    h.elphys_sync_conversion_factor=1
    h.raw_data=raw_data
    h.sync_scaling=sync_scaling
    h.configs_stim = {'machine_config':{'ELPHYS_SYNC_RECORDING': {'ELPHYS_INDEXES': [0,1],'SYNC_INDEXES': [2,3,4]}}}
    h.configs_stim['machine_config']=machine_config['machine_config']
    h.machine_config=machine_config
    h.save(['raw_data', 'fsync', 'fimg', 'fstim', 'recording_parameters', 'sync_and_elphys_data', 'elphys_sync_conversion_factor', 'sync_scaling', 'configs_stim', 'machine_config'])
    h.close()
    return filename
    
def yscanner2sync(sig,fsample):
    indexes=numpy.where(abs(numpy.diff(sig))>0.05)[0]
    start=indexes[0]
    end=indexes[-1]
    fft=numpy.fft.fft(sig[start:start+fsample*10 if start+fsample*10<end else end])
    frqs=numpy.fft.fftfreq(fft.shape[0],1.0/fsample)
    d=numpy.sign(numpy.diff(abs(fft)))
    peaks=frqs[numpy.nonzero(numpy.roll(d,1)-d)[0]-1]
    frame_rate=peaks[1]#First peak is considered as frame rate
    if frame_rate<0.2 or frame_rate>15:
        raise RuntimeError('{0} Hz frame rate found,{1}'.format(frame_rate,peaks))
    nperiods=numpy.floor((end-start)/float(fsample)*frame_rate)
    period=int(numpy.round(fsample/frame_rate,0))
    ontime=int(1/1.2*period)
    oneperiod=5*numpy.concatenate((numpy.ones(ontime),numpy.zeros(period-ontime)))
    sigout=numpy.zeros_like(sig)
    sigout[start:start+period*nperiods]=numpy.tile(oneperiod,nperiods)
    return sigout

class TestConverter(unittest.TestCase):
    @unittest.skip('')
    def test_01_phystiff2hdf5(self):
#        p=PhysTiff2Hdf5('/tmp/rei_repeats','/tmp/rei_repeats')
        p=PhysTiff2Hdf5('/tmp/rei_data','/tmp/rei_data')
#        p=PhysTiff2Hdf5('/mnt/rzws/dataslow/rei_data', '/mnt/rzws/dataslow/rei_data_c2')
        p.use_tiff=not False
#        p.detect_and_convert()
        p.convert_old_files()
#        p=PhysTiff2Hdf5('/home/rz/codes/data/rei_data/20150206')
#        p=PhysTiff2Hdf5('/home/rz/codes/data/rei_data')
#        p=PhysTiff2Hdf5('/mnt/rzws/dataslow/rei_data/20150206')
        
    def test_02_merge_ca_data(self):
        folder='/data/data/user/Zoltan/20160817/not enough frames'
        filename=merge_ca_data(folder,stimulus_source_code='',stimfile='')
        
if __name__ == '__main__':
    if len(sys.argv)==2 or len(sys.argv)==3:
        if fileop.free_space(sys.argv[1])<30e9:
            raise RuntimeError('{0} is running out of free space'.format(sys.argv[1]))
        elif fileop.free_space(sys.argv[1])<100e9:
            print 'Only {1} GB free space is left on {0}'.format(sys.argv[1], int(fileop.free_space(sys.argv[1])/1e9))
        p=PhysTiff2Hdf5(sys.argv[1], sys.argv[1],sys.argv[2])
        p.use_tiff=False
        print 'Close window to exit program'
        while True:
            try:
                if os.name != 'nt' and utils.enter_hit():
                    break
                t0=time.time()
                r=p.detect_and_convert()
                if len(r)>0:
                    print 'runtime', time.time()-t0
                    print 'New files', r
            except:
                import traceback
                print traceback.format_exc()
#                pdb.set_trace()
            time.sleep(1.0)
        print 'DONE'
    else:
        unittest.main()

    

