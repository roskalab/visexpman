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
import tifffile
from visexpman.engine.generic import fileop,utils,signal
from visexpman.engine.vision_experiment import experiment_data
from visexpA.engine.datahandlers import importers
import unittest

def _pickle_method(m):
    if m.im_self is None:
        return getattr, (m.im_class, m.im_func.func_name)
    else:
        return getattr, (m.im_self, m.im_func.func_name)

copy_reg.pickle(types.MethodType, _pickle_method)

class PhysTiff2Hdf5(object):
    '''
    Convert phys/tiff data into hdf5
    '''
    def __init__(self, folder):
        self.folder=folder
        self.maximal_timediff = 3
        self.use_tiff = True
        self.skipped_files = []
        self.match_files()
        if 1:
            for k,v in self.assignments.items():
                print k
                self.build_hdf5(k, v[0])
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
        
    def build_hdf5(self,fphys,ftiff):
        tmptiff = '/tmp/temp.tiff'
        if self.use_tiff:
            if os.path.exists(tmptiff):
                os.remove(tmptiff)
            fileop.write_text_file('/tmp/m.txt', 'saveAs("tiff","/tmp/temp.tiff");')
            cmd = 'imagej "{0}" -batchpath /tmp/m.txt'.format(ftiff)
            subprocess.call(cmd,shell=True)
            time.sleep(4)
            if not os.path.exists(tmptiff):
                self.skipped_files.append(ftiff)
                return
            raw_data = tifffile.imread(tmptiff)[1::2]
            raw_data = raw_data.reshape((raw_data.shape[0], 1, raw_data.shape[1], raw_data.shape[2]))
            recording_parameters = {}
            recording_parameters['resolution_unit'] = 'pixel/um'
            recording_parameters['pixel_size'] = float(ftiff.split('_')[-1].replace('.'+fileop.file_extension(ftiff), ''))
            recording_parameters['scanning_range'] = utils.rc((map(float,ftiff.split('_')[-5:-3])))
            recording_parameters['elphys_sync_sample_rate'] = 10000
        data, metadata = experiment_data.read_phys(fphys)
        sync_and_elphys = numpy.zeros((data.shape[1], 5))
        sync_and_elphys[:,2] = self.sync_signal2block_trigger(data[1])#stim sync
        sig = self.yscanner_signal2trigger(data[2], float(metadata['Sample Rate']), raw_data.shape[2])
        if sig is None:
            return
        sync_and_elphys[:,4] = sig
        id = int(os.path.getmtime(fphys))
        folder = os.path.join('/tmp', os.path.split(ftiff)[0].split('rei_data')[1][1:])
        if not os.path.exists(folder):
            os.makedirs(folder)
        filename = os.path.join(folder, 'data_cx_unknownstim_{0}_0.hdf5'.format(id))
        h=hdf5io.Hdf5io(filename,filelocking=False)
        h.raw_data = raw_data
        h.fphys = fphys
        h.ftiff = ftiff
        h.recording_parameters=recording_parameters
        h.sync_and_elphys_data = sync_and_elphys
        h.conversion_factor=1
        h.phys_metadata = utils.object2array(metadata)
        h.configs_stim = {'machine_config':{'ELPHYS_SYNC_RECORDING': {'ELPHYS_INDEXES': [0,1],'SYNC_INDEXES': [2,3,4]}}}
        h.save(['raw_data', 'fphys', 'ftiff', 'recording_parameters', 'sync_and_elphys_data', 'conversion_factor', 'phys_metadata', 'configs_stim'])
        h.close()
        print filename
        #TODO: use pool for parallel processing
        
    def sync_signal2block_trigger(self, sig):
        indexes = signal.trigger_indexes(sig)
        if (10000.0/numpy.diff(indexes)[1::2]).mean()<55:
            return sig
        else:
            #assuming
            delay_before_start=15
            ontime=2
            frame_rate=60
            sig2=numpy.zeros_like(sig)
            rising_index = delay_before_start*frame_rate
            falling_index = (delay_before_start+ontime)*frame_rate
            sig2[indexes[2*rising_index]:indexes[2*falling_index]]=5
            return sig2
        
    def yscanner_signal2trigger(self,waveform, fsample,nxlines):
        #First harmonic will be the frame rate
        factor=5
        f=numpy.fft.fft(waveform[:waveform.shape[0]/factor])
        f=f[:f.shape[0]/2]
        df=1.0/(waveform.shape[0]/fsample)
        frame_rate = factor*abs(f)[1:].argmax()*df#First harmonic has the highest amplitude
        if frame_rate>30:#Then probably x scanner signal
            frame_rate /= nxlines
            start_of_first_frame = numpy.where(abs(numpy.diff(waveform))>2000)[0][0]
        else:
            start_of_first_frame = numpy.where(abs(numpy.diff(waveform))>1000)[0][0]
        if frame_rate<5 or frame_rate>12:
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
        nperiods = (waveform.shape[0]-start_of_first_frame)/nsample_per_period
        trigger_signal = numpy.zeros_like(waveform)
        pulses = numpy.concatenate((numpy.zeros(start_of_first_frame), numpy.tile(one_period, nperiods)))
        trigger_signal[:pulses.shape[0]]=pulses
        return trigger_signal
        
class TestConverter(unittest.TestCase):
    def test_01_phystiff2hdf5(self):
        p=PhysTiff2Hdf5('/mnt/rzws/dataslow/rei_data')
#        p=PhysTiff2Hdf5('/home/rz/codes/data/rei_data/20150206')
#        p=PhysTiff2Hdf5('/home/rz/codes/data/rei_data')
#        p=PhysTiff2Hdf5('/mnt/rzws/dataslow/rei_data/20150206')
        
        
if __name__ == '__main__':
    unittest.main()

    

