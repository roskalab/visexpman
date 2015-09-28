import sys
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
import time



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
        self.allfiles = fileop.find_files_and_folders(self.folder)[1]
        self.outfiles = [f for f in fileop.find_files_and_folders(self.outfolder)[1] if fileop.file_extension(f)=='hdf5']
        
        if self.irlaser:
            physfiles = [f for f in self.allfiles if fileop.file_extension(f)=='csv' and 'rect' not in f and 'timestamps' not in f]
        else:
            physfiles = [f for f in self.allfiles if fileop.file_extension(f)=='phys']
        tiffiles = [f for f in self.allfiles if fileop.file_extension(f)==('tif' if self.use_tiff else 'csv')]
        if self.irlaser:
            tiffiles = [tf for tf in tiffiles if tf not in physfiles]
        if not self.use_tiff:
            tiffiles = [f for f in tiffiles if not 'timestamp' in f]
        processable_physfiles = []
        phys_ids = [[str(experiment_data.get_id(os.path.getmtime(f))),f] for f in physfiles]
        out_ids= [str(os.path.split(of)[1].split('_')[-2]) for of in self.outfiles]
        processable_physfiles = [pid[1] for pid in phys_ids if pid[0] not in out_ids]
        #Find corresponding folder with tiff file
        pairs = []
        for pf in processable_physfiles:
            regexp = pf
            found = [tf for tf in tiffiles if os.path.split(regexp.replace(fileop.file_extension(pf),''))[1][:-1] in tf]
            if len(found)>0 and os.path.getsize(pf)>10e3 and os.path.getsize(found[0])>10e3 and [pf,found[0]] not in self.processed_pairs:
                id = str(experiment_data.get_id(os.path.getmtime(pf)))
                if len([f for f in self.outfiles if id in f])==0:
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
        converted=[self.build_hdf5(p[0],p[1], self.outfolder) for p in pairs]
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
            data=numpy.fromfile(ftiff,">f4")
            nframes = int(data.shape[0]/(sizex*res*(sizey*res-1))/2)
            if nframes<10:
                return
            data_=data[:int(2*(sizey*res*(sizex*res-1))*nframes)]
            pixel_per_frame = int(2*(sizex*res)*(sizey*res-1)+4)
            boundaries = numpy.repeat(numpy.arange(nframes)*pixel_per_frame,2)
            boundaries[1::2]+=pixel_per_frame-4
            boundaries = boundaries[numpy.where(boundaries<data_.shape[0])[0]]
            nframes=boundaries.shape[0]/2
            boundaries = boundaries[:2*(boundaries.shape[0]/2)]
            rawdata = numpy.array(numpy.split(data, boundaries)[1:][::2]).reshape((nframes,2, int(sizex*res-1), int(sizey*res)))
            raw_data = numpy.cast['uint16'](signal.scale(rawdata[:,1:,:,:],0,2**16-1))
        print 'rawdata ok', time.time()-t0
        recording_parameters = {}
        recording_parameters['resolution_unit'] = 'pixel/um'
        recording_parameters['pixel_size'] = float(ftiff.split('_')[-1].replace('.'+fileop.file_extension(ftiff), ''))
        recording_parameters['scanning_range'] = utils.rc((map(float,ftiff.split('_')[-5:-3])))
        recording_parameters['elphys_sync_sample_rate'] = 10000
        if self.irlaser:
            experiment_name = 'irlaser'
            with open(fphys,'rt') as f:
                txt=f.read()
            data=numpy.array([map(float,line.split('\t')) for line in txt.split('\n')[:-1]]).T
            metadata={}
            metadata['Sample Rate']=10000
            metadata['repeats'], metadata['pulse_width'], metadata['laser_power']=map(float,fphys.replace('.csv','').split('_')[3:])
            data[1]=data[2]
            data[2]=data[4]
            data=data[:3]
        else:
            data, metadata = experiment_data.read_phys(fphys)
            experiment_name = self.parse_stimulus_name(metadata)
        recording_parameters['experiment_name']=experiment_name
        recording_parameters['experiment_source']= fileop.read_text_file(metadata['Stimulus file']) if metadata.has_key('Stimulus file') and os.path.exists(metadata['Stimulus file']) else ''
        recording_parameters['experiment_source_file'] = metadata['Stimulus file'] if metadata.has_key('Stimulus file') else ''
        recording_parameters['absolute_stage_coordinates'] = absolute_stage_coordinates
        if float(metadata['Sample Rate'])!=10000:
            raise RuntimeError('Sync signal sampling rate is expected to be 10 kHz. Make sure that spike recording is enabled')
        if data.shape[0]!=3:
            raise RuntimeError('Sync signals might not be recorded. Make sure that recording ai4:5 channels are enabled')
        sync_and_elphys = numpy.zeros((data.shape[1], 5))
        sync_and_elphys[:,2] = self.sync_signal2block_trigger(data[1])#stim sync
        sig = self.yscanner_signal2trigger(data[2], float(metadata['Sample Rate']), raw_data.shape[2])
        if sig is None:
            return
        sync_and_elphys[:,4] = sig
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
        self.backup_files(fphys,ftiff,filename)
        return filename
        #TODO: use pool for parallel processing
        
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
        if (10000.0/numpy.diff(indexes)[1::2]).mean()<55:
            return sig
        else:
            #assuming
            delay_before_start=15 if sig.shape[0]/10000 > 30 else 10
            ontime=2
            frame_rate=60
            sig2=numpy.zeros_like(sig)
            rising_index = delay_before_start*frame_rate
            falling_index = (delay_before_start+ontime)*frame_rate
            try:
                sig2[indexes[2*rising_index]:indexes[2*falling_index]]=5
            except:
                print 'sync signal recordifng was aborted'
            pass
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
        if (frame_rate<5 or frame_rate>12) and not self.allow_high_framerate:
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
        
        
class TestConverter(unittest.TestCase):
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
        
        
if __name__ == '__main__':
    if len(sys.argv)==2 or len(sys.argv)==3:
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

    

