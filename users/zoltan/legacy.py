import numpy
import os
import os.path
import itertools
from visexpman.engine.generic import fileop,utils
import unittest

class PhysTiff2Hdf5(object):
    '''
    Convert phys/tiff data into hdf5
    '''
    def __init__(self, folder):
        self.folder=folder
        self.maximal_timediff = 120
        self.match_files()
        pass
        
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
                if tdiff>60:
                    continue
                elif not assignments.has_key(fphys):
                    assignments[fphys] = [ftif, tdiff]
                elif assignments[fphys][1]>tdiff:
                    assignments[fphys] = [ftif, tdiff]
            pass
        #check assignment for redundancy
        assigned_tiffiles = [fn for fn, tdiff in assignments.values()]
        if len(assigned_tiffiles) != len(set(assigned_tiffiles)):
            raise RuntimeError('A tifffile is assigned to multiple phys files')
            
        
        pass
        
        
        
        
class TestConverter(unittest.TestCase):
    def test_01_phystiff2hdf5(self):
        p=PhysTiff2Hdf5('/mnt/rzws/dataslow/rei_data/20150206')
#        p=PhysTiff2Hdf5('/mnt/rzws/dataslow/rei_data')
        
if __name__ == '__main__':
    unittest.main()

    

