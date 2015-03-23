'''
This module contains Calcim imaging related analysis functions
'''

import numpy
import scipy.interpolate
import os.path
import unittest
import hdf5io
from visexpman.engine.generic import utils,fileop,signal
from pylab import plot,show

def calculate_trace_parameters(trace, roi):
    '''
    Calculates: 
    1) Response size in baseline std
    2) Polarity
    3) Rise time (exponential time constant
    4) Fall time
    5) Difference between pre and post baselines (sustained response)
    
    '''
    
    pass


class TestCA(unittest.TestCase):
    def setUp(self):
        from visexpman.users.test import unittest_aggregator
        self.files = fileop.listdir_fullpath(os.path.join(fileop.select_folder_exists(unittest_aggregator.TEST_test_data_folder), 'trace_analysis'))
        
    def test_01_trace_parameters(self):
        for f in self.files:
            h=hdf5io.Hdf5io(f,filelocking=False)
            h.load('timing')
            map(calculate_trace_parameters, h.findvar('roi_curves'))
            h.close()

    
if __name__=='__main__':
    unittest.main()
