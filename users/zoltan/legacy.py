from pylab import plot,show,imshow
import time
import hdf5io
import subprocess
import numpy
import os
import os.path
import itertools
import tifffile
from visexpman.engine.generic import fileop,utils
from visexpman.engine.vision_experiment import experiment_data
from visexpA.engine.datahandlers import importers
import unittest

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
        for k,v in self.assignments.items():
            self.build_hdf5(k, v[0])
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
            pass
        #check assignment for redundancy
        assigned_tiffiles = [fn for fn, tdiff in assignments.values()]
        if len(assigned_tiffiles) != len(set(assigned_tiffiles)):
            assigned_tiffiles.sort()
            redundant_tiff = [assigned_tiffiles[i] for i in range(len(assigned_tiffiles)-1) if assigned_tiffiles[i] == assigned_tiffiles[i+1]]
            [[k,v] for k,v in assignments.items() if v[0] in redundant_tiff]
            raise RuntimeError('A tifffile is assigned to multiple phys files')
            
        self.assignments = assignments
        pass
        
    def build_hdf5(self,fphys,ftiff):
        tmptiff = '/tmp/temp.tiff'
        if self.use_tiff:
            if os.path.exists(tmptiff):
                os.remove(tmptiff)
            fileop.write_text_file('/tmp/m.txt', 'saveAs("tiff","/tmp/temp.tiff");')
            cmd = 'imagej {0} -batchpath /tmp/m.txt'.format(ftiff)
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
        data, metadata = experiment_data.read_phys(fphys)
        sync_and_elphys = numpy.zeros((data.shape[1], 5))
        sync_and_elphys[:,2] = data[1]#stim sync
        sync_and_elphys[:,4] = data[2]
        id = int(os.path.getmtime(fphys))
        filename = '/tmp/data_{0}.hdf5'.format(id)
        h=hdf5io.Hdf5io(filename,filelocking=False)
        h.raw_data = raw_data
        h.fphys = fphys
        h.ftiff = ftiff
        h.recording_parameters=recording_parameters
        h.sync_and_elphys = sync_and_elphys
        h.phys_metadata = utils.object2array(metadata)
        h.save(['raw_data', 'fphys', 'ftiff', 'recording_parameters', 'sync_and_elphys', 'phys_metadata'])
        h.close()
        #TODO: run for all
        #TODO: y scanner signal to sync signal
        #TODO: save to directory structure
        
    
    
        
        
        
        
        
class TestConverter(unittest.TestCase):
    def test_01_phystiff2hdf5(self):
#        p=PhysTiff2Hdf5('/mnt/rzws/dataslow/rei_data/20150206')
#        p=PhysTiff2Hdf5('/home/rz/codes/data/rei_data/20150206')
        p=PhysTiff2Hdf5('/home/rz/codes/data/rei_data')
#        p=PhysTiff2Hdf5('/mnt/rzws/dataslow/rei_data')
        
if __name__ == '__main__':
    unittest.main()

    

