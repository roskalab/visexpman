'''
This module contains Calcim imaging related analysis functions
'''

import numpy
import scipy.interpolate
import os.path
import copy
import unittest
import hdf5io
import itertools
from visexpA.engine.dataprocessors import roi
from visexpA.engine.dataprocessors import signal as signal2
from visexpman.engine.generic import utils,fileop,signal,geometry,introspect,stringop
from visexpman.engine.vision_experiment import experiment_data
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
    
def find_repetitions(filename, folder):
    allhdf5files = fileop.find_files_and_folders(folder, extension = 'hdf5')[1]
    allhdf5files = [f for f in allhdf5files if fileop.is_recording_filename(f)]
    if filename not in allhdf5files:
        raise RuntimeError('{0} is not in {1}'.format(filename, folder))
    ids = [fileop.parse_recording_filename(f)['id'] for f in allhdf5files]
    if len(ids) != len(set(ids)):
        import collections
        duplicates = [x for x, y in collections.Counter(ids).items() if y > 1]
        raise RuntimeError('Some files are duplicated: {0}'.format([f for f in allhdf5files if stringop.string_in_list(duplicates, f, any_match=True)]))
    #Identify files that are linked together
    links = [(f, hdf5io.read_item(f, 'repetition_link', filelocking=False)) for f in allhdf5files]#This takes long, cannot be run in parallel processes
    links=dict([[fileop.parse_recording_filename(link[0])['id'], link[1][0]] for link in links if link[1] is not None])
    filenameid = fileop.parse_recording_filename(filename)['id']
    repetitions = [filenameid]
    remaining_links = copy.deepcopy(links)
    next_ids = [remaining_links[filenameid]]
    del remaining_links[filenameid]
    while True:
        repetitions.extend(next_ids)
        next_ids = [remaining_links[next_id] for next_id in next_ids if remaining_links.has_key(next_id)]
        for ni in next_ids:
            del remaining_links[ni]
        if len(next_ids)==0:
            break
    #Read roi info from assigned files
    aggregated_rois = dict([(f, hdf5io.read_item(f, 'rois', filelocking=False)) for f in allhdf5files if stringop.string_in_list(repetitions, f, any_match=True)])
    timing = dict([(f, experiment_data.timing_from_file(f)) for f in allhdf5files if stringop.string_in_list(repetitions, f, any_match=True)])
    #take rectangle center for determining mathcing roi
    aggregated_rectangles = {}
    for fn, rois in aggregated_rois.items():
        aggregated_rectangles[fn] = [r['rectangle'][:2] for r in rois]
    #Match rois from different repetitions
    reference = aggregated_rectangles[filename]
    ref_signatures = point_signature(reference)
    del aggregated_rectangles[filename]
    matches = []
    roi_ct = 0
    for reference_rect in reference:
        ref_sig=find_by_point(reference_rect, ref_signatures)
        for fn in aggregated_rectangles.keys():
            signatures = point_signature(aggregated_rectangles[fn])
            match_list = [compare_signatures(ref_sig, find_by_point(r, signatures)) for r in aggregated_rectangles[fn]]
            match_weight = max(match_list)
            if match_weight>len(aggregated_rectangles[fn])*0.7:#Match: if there are at least n exact matches where n can be 70 % of number of rois
                if not aggregated_rois[filename][roi_ct].has_key('matches'):
                    aggregated_rois[filename][roi_ct]['matches'] = {}
                index=numpy.array(match_list).argmax()
                timg = timing[fn][1]
                tsync = timing[fn][0]
                aggregated_rois[filename][roi_ct]['matches'][fn] = {'tsync': tsync, 'timg': timg, 'raw': aggregated_rois[fn][index]['raw'], 'match_weight': match_weight}
        roi_ct += 1
    return aggregated_rois[filename]
    
def point_signature(points):
    '''
    Calculate relative position (distance, angle) of a point from each other point
    '''
    signatures = numpy.array([[p1, p2, (numpy.array(p2)-numpy.array(p1))] for p1, p2 in itertools.combinations(points,2)])
    return signatures
    
def find_by_point(p1, signatures):
    return signatures[numpy.where(numpy.logical_and(signatures[:, :2,0]==p1[0], signatures[:,:2,1]==p1[1]))[0],2,:]
    
def compare_signatures(sig1, sig2):
    number_of_matches = 0
    for sig1i in sig1:
        number_of_matches += 1 if numpy.where(abs(numpy.array(sig2)-sig1i).sum(axis=1)<1e-9)[0].shape[0] > 0 else 0
    return number_of_matches

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
        
    def test_05_find_repetitions(self):
        fn='/home/rz/rzws/experiment_data/test/data_C3_unknownstim_1423066960_0.hdf5'
        with introspect.Timer(''):
            res = find_repetitions(fn, '/home/rz/rzws/experiment_data/test')
        self.assertEqual(sum([r.has_key('matches') for r in res]),41)
        pass
    
if __name__=='__main__':
    unittest.main()
