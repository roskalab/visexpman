'''
This module contains Calcim imaging related analysis functions
'''

import numpy
import scipy.interpolate
import os.path
import unittest
import hdf5io
from visexpA.engine.dataprocessors import roi
from visexpA.engine.dataprocessors import signal as signal2
from visexpman.engine.generic import utils,fileop,signal,geometry
import scipy.optimize
from pylab import plot,show,figure,title,imshow,subplot

import warnings

def exp(x,tconst, a,b):
    return a*numpy.exp(-tconst*x)+b

class TransientAnalysator(object):
    def __init__(self, baseline_t_start, baseline_t_end, post_response_duration):
        self.baseline_t_start = baseline_t_start
        self.baseline_t_end = baseline_t_end
        self.post_response_duration = post_response_duration
        
    def scale_std(self, trace, mean, std):
        if std<1e-10:
            std = 1e-10
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
        if numpy.isnan(scaled_trace).any():
            print scaled_trace.std()
        #Cut out baseline, response and post response traces
        post_response = numpy.array(scaled_trace[response_end:signal.time2index(ti, ts[1]+self.post_response_duration)])
        baseline=numpy.array(scaled_trace[baseline_start:baseline_end])
        response = numpy.array(scaled_trace[response_start:response_end])
        #response size is the mean of the trace when stimulus presented
        response_amplitude = response.mean()
        #quantify transient
        rise_time_constant, response_amplitude = self.calculate_time_constant(response)
        rise_time_constant*=tsample
        fall_time_constant, post_response_signal_level = self.calculate_time_constant(post_response)
        fall_time_constant*=tsample
        #Initial drop
        initial_drop = 0
        return scaled_trace, rise_time_constant, fall_time_constant, response_amplitude, post_response_signal_level, initial_drop
        
    def calculate_time_constant(self, trace):
        x=numpy.arange(numpy.array(trace).shape[0])
        try:
            coeff, cov = scipy.optimize.curve_fit(exp,x,trace,p0=[1,1,trace[0]])
        except:
            coeff = [0,0,0]
        time_constant = coeff[0]
        response_amplitude = coeff[2]
        return time_constant, response_amplitude
        
def find_rois(im1, minsomaradius, maxsomaradius, sigma, threshold_factor):
    '''
    Dani's algorithm:
    -gaussian filtering
    -finding local maximums
    -estimate circle radius
    In each circle:
    -Determine threshold with otsu's method
    -Segment and select central object
    '''
    from scipy.ndimage.filters import gaussian_filter
    try:
        from skimage import filters
    except ImportError:
        from skimage import filter as filters
    import scipy.ndimage.measurements
    p=im1.max()
    im = gaussian_filter(im1, sigma)
    centers = signal2.getextrema(im, method = 'regmax')
    wrange = range(minsomaradius, maxsomaradius)
    res = roi.ratio_center_perimeter(signal.scale(im, 0.0, 1.0), centers,  wrange)
    maskcum = numpy.zeros_like(im1)
    c=numpy.zeros_like(im1)
    soma_rois = []
    for i in range(res[1].shape[0]):
        c[res[1][i]['row'],res[1][i]['col']]=p
        roi_radius = 0.5*res[0][i]
        roi_center = res[1][i]
        mask = geometry.circle_mask(roi_center, roi_radius, im.shape)
        maskcum+=mask
        masked = im1*mask
        th=filters.threshold_otsu(masked)
        thresholded = numpy.where(masked<th*threshold_factor, 0, 1)
        labeled, nsegments = scipy.ndimage.measurements.label(thresholded)
        central_segment = numpy.where(labeled==labeled[roi_center[0],roi_center[1]],1,0)
        if numpy.nonzero(central_segment)[0].shape[0] < 0.95*numpy.nonzero(mask)[0].shape[0]:#Valid roi
            soma_rois.append(numpy.array(zip(*numpy.nonzero(central_segment))))
    return soma_rois
    
def area2edges(soma_roi):
    edge_pixels = []
    for i in range(soma_roi.shape[0]):
        col_diff=abs(soma_roi[:,0]-soma_roi[i][0])
        row_diff=abs(soma_roi[:,1]-soma_roi[i][1])
        if sum([(r+c==1 or (r==1 and c== 1)) for r,c in zip(col_diff,row_diff)])<8:
            edge_pixels.append(soma_roi[i])
    return numpy.array(edge_pixels)

def calculate_background(rawdata,threshold=0.1):
    mi=rawdata.mean(axis=0).mean(axis=0)
    x,y = numpy.where(mi<mi.max()*threshold)
    return rawdata[:,:,x,y].mean(axis=2).flatten()

class TestCA(unittest.TestCase):
    def setUp(self):
        from visexpman.users.test import unittest_aggregator
        self.files = fileop.listdir_fullpath(os.path.join(fileop.select_folder_exists(unittest_aggregator.TEST_test_data_folder), 'trace_analysis'))
        
    @unittest.skip('')
    def test_01_trace_parameters(self):
        ta=TransientAnalysator(-5, 0, 3)
        ct=0
        for f in self.files:
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
        
    def test_02_detect_cell(self):
        for f in self.files:
            
            minsomaradius = 3*2
            maxsomaradius = 3*3
            h=hdf5io.Hdf5io(f,filelocking=False)
            im1 = h.findvar('raw_data').mean(axis=0)[0]
            rois = find_rois(im1, minsomaradius, maxsomaradius, 0.2*maxsomaradius,1)
            im=numpy.zeros((im1.shape[0],im1.shape[1], 3))
            im[:,:,1]=signal.scale(im1,0,1)
            mi=numpy.copy(im)
            numpy.random.seed(0)
            for r in rois:
                im[r[:,0],r[:,1],0]=numpy.random.random()*0.7+0.3
                im[r[:,0],r[:,1],2]=numpy.random.random()*0.7+0.3
            
            figure(1)
            subplot(1,2,1)
            imshow(mi)
            subplot(1,2,2)
            imshow(im)
#            show()
            h.close()
            break
            
    def test_03_calculate_background(self):
        for f in self.files:
            h=hdf5io.Hdf5io(f,filelocking=False)
            rawdata=h.findvar('raw_data')
            calculate_background(rawdata)
            h.close()
            
    def test_04_area2edges(self):
        areas = [
            numpy.array([[ 1, 77],[ 1, 78],[ 1, 79],[ 1, 80],[ 1, 81],[ 1, 82],[ 1, 83],[ 1, 84],[ 1, 85],[ 2, 77],[ 2, 78],[ 2, 79],[ 2, 80],[ 2, 81],
                    [ 2, 82],[ 2, 83],[ 2, 84],[ 2, 85],[ 3, 77],[ 3, 78],[ 3, 79],[ 3, 80],[ 3, 81],[ 3, 82],[ 3, 83],[ 3, 84],[ 3, 85],[ 4, 78],
                    [ 4, 79],[ 4, 80],[ 4, 81],[ 4, 82],[ 5, 79],[ 5, 80],[ 5, 81]]),
            numpy.array([[  1, 144],[  1, 145],[  1, 146],[  1, 147],[  1, 148],[  2, 144],[  2, 145],[  2, 146],[  2, 147],[  2, 148],[  3, 144],
                        [  3, 145],[  3, 146],[  3, 147],[  4, 145],[  4, 146],[  4, 147],[  4, 148],[  5, 146],[  5, 148]])]
        import multiprocessing
        p=multiprocessing.Pool(4)
        res=p.map(area2edges, areas)
    
if __name__=='__main__':
    unittest.main()
