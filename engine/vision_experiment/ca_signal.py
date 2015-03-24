'''
This module contains Calcim imaging related analysis functions
'''

import numpy
import scipy.interpolate
import os.path
import unittest
import hdf5io
from visexpman.engine.generic import utils,fileop,signal
import scipy.optimize
from pylab import plot,show,figure,title

import warnings

def exp(x,tconst, a,b):
    return a*numpy.exp(-tconst*x)+b

class TransientAnalysator(object):
    def __init__(self, baseline_t_start, baseline_t_end, post_response_duration, initial_drop_sample_duration):
        self.baseline_t_start = baseline_t_start
        self.baseline_t_end = baseline_t_end
        self.post_response_duration = post_response_duration
        self.initial_drop_sample_duration = initial_drop_sample_duration
        
    def scale_std(self, trace, mean, std):
        return (trace-mean)/std

    def calculate_trace_parameters(self, trace, timing):
        '''
        Calculates: 
        1) Response size in baseline std
        2) Polarity
        3) Rise time (exponential time constant
        4) Fall time
        5) Difference between pre and post baselines (sustained response)
        
        '''
        ti=timing['ti']
        ts=timing['ts']
        tsample=numpy.diff(ti)[0]
        #determine indexes of signal boundaries
        response_start = signal.time2index(ti, ts[0])
        response_end = signal.time2index(ti, ts[1])
        baseline_start = signal.time2index(ti, ts[0]+self.baseline_t_start)
        baseline_end = signal.time2index(ti, ts[0]+self.baseline_t_end)
        baseline=numpy.array(trace[baseline_start:baseline_end])
        #scale trace with baseline's std
        scaled_trace = self.scale_std(trace, baseline.mean(), baseline.std())
        #Cut out baseline, response and post response traces
        post_response = numpy.array(scaled_trace[response_end:signal.time2index(ti, ts[1]+self.post_response_duration)])
        baseline=numpy.array(scaled_trace[baseline_start:baseline_end])
        response = numpy.array(scaled_trace[response_start:response_end])
        #response size is the mean of the trace when stimulus presented
        response_amplitude = response.mean()
        #quantify transient
        rise_time_constant = self.calculate_time_constant(response)*tsample
        fall_time_constant = self.calculate_time_constant(post_response)*tsample
        post_response_signal_level = post_response.mean()
        #Initial drop
        initial_drop = scaled_trace[:signal.time2index(ti, self.initial_drop_sample_duration)].mean()
        return scaled_trace, rise_time_constant, fall_time_constant, response_amplitude, post_response_signal_level, initial_drop
        
    def calculate_time_constant(self, trace):
        x=numpy.arange(numpy.array(trace).shape[0])
        coeff, cov = scipy.optimize.curve_fit(exp,x,trace,p0=[1,1,trace[0]])
        time_constant = coeff[0]
        return time_constant


class TestCA(unittest.TestCase):
    def setUp(self):
        from visexpman.users.test import unittest_aggregator
        self.files = fileop.listdir_fullpath(os.path.join(fileop.select_folder_exists(unittest_aggregator.TEST_test_data_folder), 'trace_analysis'))
        
    def test_01_trace_parameters(self):
        ta=TransientAnalysator(-5, 0, 3, 1)
        ct=0
        for f in self.files:
            if '023' not in f:
                continue
            h=hdf5io.Hdf5io(f,filelocking=False)
            rc=h.findvar('roi_curves')
            res = map(ta.calculate_trace_parameters, rc, len(rc)*[h.findvar('timing')])
            
            for r in res:
                scaled_trace, rise_time_constant, fall_time_constant, response_amplitude, post_response_signal_level, initial_drop = r
                if abs(response_amplitude)<3:
                    continue
                figure(ct)
                ct+=1
                plot(scaled_trace);
                title('rise_time_constant {0:0.2f}, fall_time_constant {1:0.2f}, response_amplitude {2:0.2f}\npost_response_signal_level: {3:0.2f},initial_drop: {4:0.2f}'.format(rise_time_constant, fall_time_constant, response_amplitude, post_response_signal_level, initial_drop))
            h.close()
        show()

    
if __name__=='__main__':
    unittest.main()
