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
from pylab import plot,show,figure,title,imshow,subplot,clf,savefig

import warnings

def exp(t,tconst, a,b):
    return a*numpy.exp(-t/tconst)+b
    
def sigmoid(t, t0, sigma,a,b):
    return a/(1+numpy.exp(-(t-t0)/sigma))+b
    
def calculate_trace_parameters(trace, tsync, timg,baseline_length):
    '''
    Calculates: 
    1) Response size in baseline std
    2) Polarity
    3) Rise time (exponential time constant
    4) Fall time
    5) Difference between pre and post baselines (sustained response)
    
    '''
    #TODO: test for negative responses
    fitted_traces = []
    tsample=numpy.diff(timg)[0]
    #determine indexes of signal boundaries
    response_start = signal.time2index(timg, tsync[0])
    response_end = signal.time2index(timg, tsync[1])
    baseline_start = signal.time2index(timg, tsync[0]-baseline_length)
    baseline_end = signal.time2index(timg, tsync[0])
    baseline=numpy.array(trace[baseline_start:baseline_end])
    end_of_drop = trace[:response_start].argmin()
    #initial drop quantification
    #Find minimum between start and stimulus start and take the trace from the beginning till this point
    initial_drop_trace=trace[:end_of_drop]
    t=numpy.arange(numpy.array(initial_drop_trace).shape[0])
    #Fit exp(-t/T) and calculate T
    try:
        coeff, cov = scipy.optimize.curve_fit(exp,t,initial_drop_trace,p0=[1,1,initial_drop_trace[-1]])
        fitted_traces.append(exp(t,*coeff))
    except:
        coeff = [0]*3
    T_initial_drop = coeff[0]*tsample
    #Response waveform quantification
    #Fit exp(-t/T) to falling part
    falling_trace = trace[response_end:]
    t=numpy.arange(numpy.array(falling_trace).shape[0])
    try:
        coeff, cov = scipy.optimize.curve_fit(exp,t,falling_trace,p0=[1,1,falling_trace[-1]])
        fitted_traces.append(exp(t,*coeff))
        fitted_traces[-1] = numpy.concatenate((numpy.ones(response_end)*fitted_traces[-1][0], fitted_traces[-1]))
    except:
        coeff = [0]*3
    T_falling=coeff[0]*tsample
    rising_trace = trace[baseline_start:response_end]
    t=numpy.arange(numpy.array(rising_trace).shape[0])
    t0=response_start-baseline_start
    try:
        coeff, cov = scipy.optimize.curve_fit(sigmoid,t,rising_trace,p0=[t0,1,1,rising_trace.mean()])
        fitted_traces.append(sigmoid(t,*coeff))
        fitted_traces[-1] = numpy.concatenate((numpy.ones(baseline_start)*fitted_traces[-1][0], fitted_traces[-1]))
    except:
        coeff = [0]*4
    response_rise_sigma = coeff[1]*tsample
    response_amplitude = sigmoid(t,*coeff)[-1]
    baseline_mean = baseline.mean()
    return baseline_mean, response_amplitude, response_rise_sigma, T_falling, T_initial_drop,fitted_traces

class TransientAnalysator(object):
    def __init__(self, baseline_t_start, baseline_t_end):
        self.baseline_t_start = baseline_t_start
        self.baseline_t_end = baseline_t_end
        
    def scale_std(self, trace, mean, std):
        if std<1e-10:
            std = 1e-10
        return (trace-mean)/std
        
    def calculate_time_constant(self, trace):
        x=numpy.arange(numpy.array(trace).shape[0])
        try:
            coeff, cov = scipy.optimize.curve_fit(exp,x,trace,p0=[1,1,trace[0]])
        except:
            coeff = [0,0,0]
        time_constant = coeff[0]
        response_amplitude = coeff[2]
        return time_constant, response_amplitude
        
def find_rois(im1, minsomaradius, maxsomaradius, sigma, threshold_factor,stepsize=1):
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
    wrange = range(minsomaradius, maxsomaradius,stepsize)
    ims=signal.scale(im, 0.0, 1.0)
    res = roi.ratio_center_perimeter(ims, centers,  wrange)
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
    
def fast_read(f,vn):
    import tables
    h=tables.open_file(f,filelocking=False)
    if hasattr(h.root,vn):
        val = getattr(h.root, vn).read()
    else:
        val = None
    h.close()
    return val
    
def find_repetitions(filename, folder, filter_by_stimulus_type = True):
    allhdf5files = fileop.find_files_and_folders(folder, extension = 'hdf5')[1]
    allhdf5files = [f for f in allhdf5files if fileop.is_recording_filename(f)]
    allhdf5files = [f.replace('\\\\','\\') for f in allhdf5files]#Temporary solution
    if filename not in allhdf5files:
        raise RuntimeError('{0} is not in {1}'.format(filename, folder))
    ids = [fileop.parse_recording_filename(f)['id'] for f in allhdf5files]
    if len(ids) != len(set(ids)):
        import collections
        duplicates = [x for x, y in collections.Counter(ids).items() if y > 1]
        raise RuntimeError('Some files are duplicated: {0}'.format([f for f in allhdf5files if stringop.string_in_list(duplicates, f, any_match=True)]))
    #Identify files that are linked together
    links = [(f, fast_read(f, 'repetition_link')) for f in allhdf5files]#This takes long, cannot be run in parallel processes
    links=[[fileop.parse_recording_filename(link[0])['id'], link[1][0]] for link in links if link[1] is not None]
    filenameid = fileop.parse_recording_filename(filename)['id']
    experiment_name = fileop.parse_recording_filename(filename)['experiment_name']
    repetitions = [filenameid]
    remaining_links = copy.deepcopy(links)
    next_ids = [l for l in remaining_links if filenameid in l]
    map(remaining_links.remove, next_ids)
    next_ids = [ni[0 if ni.index(filenameid) == 1 else 1 ] for ni in next_ids]
    while True:
        repetitions.extend(next_ids)
        #check if any of next_ids can be found in remaining_links
        next_ids= [[l[0 if l.index(next_id)==1 else 1] for l in remaining_links if next_id in l] for next_id in next_ids]
        next_ids = [nii for ni in next_ids for nii in ni]#flatten list
        #remove links containing next_ids from remaining_links
        remaining_links = [rl for rl in remaining_links if rl[0] not in next_ids and rl[1] not in next_ids]
        if len(next_ids)==0:
            break
        repetitions = list(set(repetitions))
    #Read roi info from assigned files
    aggregated_rois = dict([(f, hdf5io.read_item(f, 'rois', filelocking=False)) for f in allhdf5files if stringop.string_in_list(repetitions, f, any_match=True) and (True if filter_by_stimulus_type else experiment_name == fileop.parse_recording_filename(f)['experiment_name'])])
    for fn in aggregated_rois.keys():#Remove recordings that do not contain roi
        if aggregated_rois[fn] is None:
            del aggregated_rois[fn]
    timing = dict([(f, experiment_data.timing_from_file(f)) for f in allhdf5files if stringop.string_in_list(repetitions, f, any_match=True)])
    #take rectangle center for determining mathcing roi
    aggregated_rectangles = {}
    for fn, rois in aggregated_rois.items():
        if len(rois)>0 and rois is not None:#Skip if link exists but rois do not
            aggregated_rectangles[fn] = [r['rectangle'][:2] for r in rois]
    #Match rois from different repetitions
    if not aggregated_rectangles.has_key(filename):
        raise RuntimeError('This file does not contain rois. Make sure that rois are saved')
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
            #Take the smaller number of rois as the basis of the comparison with match_weight
            nrois = min(len(aggregated_rectangles[fn]), len(reference))
            if match_weight>(nrois-1)*0.7:#Match: if there are at least n exact matches where n can be 70 % of number of rois
                if not aggregated_rois[filename][roi_ct].has_key('matches'):
                    aggregated_rois[filename][roi_ct]['matches'] = {}
                index=numpy.array(match_list).argmax()
                timg = timing[fn][1]
                tsync = timing[fn][0]
                aggregated_rois[filename][roi_ct]['matches'][os.path.split(fn)[1]] = {'tsync': tsync, 'timg': timg, 'raw': aggregated_rois[fn][index]['raw'], 'match_weight': match_weight}
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
    
def aggregate_cells(folder):
    '''
    Aggregates cell data from daatafiles in a folder including different stimuli and repetitions
    
    '''
    allhdf5files = fileop.find_files_and_folders(folder, extension = 'hdf5')[1]
    cells = []
    repeats_extracted = []
    for hdf5file in allhdf5files:
        if fileop.parse_recording_filename(hdf5file)['id'] in repeats_extracted:
            continue
        aggregated_rois = find_repetitions(hdf5file, folder, filter_by_stimulus_type = False)
        repeats_extracted.extend([fileop.parse_recording_filename(ar)['id'] for ar in aggregated_rois['matches'].keys()])
        #TODO: Add current file's rois to aggregated_rois
        #TODO: separate aggregated_rois by stimulus
        
        
    

class TestCA(unittest.TestCase):
    def setUp(self):
        from visexpman.users.test import unittest_aggregator
        self.files = fileop.listdir_fullpath(os.path.join(fileop.select_folder_exists(unittest_aggregator.TEST_test_data_folder), 'trace_analysis'))
        
    def test_01_trace_parameters(self):
        ct=0
        for f in self.files:
            h=experiment_data.CaImagingData(f,filelocking=False)
            rc=[r['raw'] for r in h.findvar('rois')]
            tsync,timg, meanimage, image_scale, raw_data = h.prepare4analysis()
#            with introspect.Timer(''):
            res = map(calculate_trace_parameters, rc, len(rc)*[tsync], len(rc)*[timg], len(rc)*[1])
            response_amplitudes = []
            response_rise_sigmas = []
            T_fallings = []
            T_initial_drops = []
            for r in res:
                baseline_mean, response_amplitude, response_rise_sigma, T_falling, T_initial_drop,fitted_traces = r
                response_amplitudes.append(response_amplitude/baseline_mean)
                response_rise_sigmas.append(response_rise_sigma)
                T_fallings.append(T_falling)
                T_initial_drops.append(T_initial_drop)
                trace =rc[res.index(r)]
                if 0:
                    clf()
                    plot(trace)
                    map(plot, fitted_traces)
                    title('response_amplitude {0}, response_rise_sigma {1},\n T_falling {2}, T_initial_drop {3}' .format(response_amplitude, response_rise_sigma, T_falling, T_initial_drop))
                    savefig('r:\\temp\\fitting\\{0}_{1}.png'.format(os.path.split(f)[1], res.index(r)),dpi=300)
                pass
#                if abs(response_amplitude)<3:
#                    continue
#            figure(ct)
#            ct+=1
#            plot(response_amplitudes, 'x');
#            plot(response_rise_sigmas, T_fallings, 'x');show()
#            plot(response_rise_sigmas, response_amplitudes, 'x');show()
#            plot(response_rise_sigmas, T_initial_drops, 'x');show()
            h.close()
#        show()
        
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
        from visexpman.users.test.unittest_aggregator import prepare_test_data
        wf='/tmp/wf'
        fns = fileop.listdir_fullpath(prepare_test_data('aggregate',working_folder=wf))
        fns.sort()
        for fn in fns:
            res = find_repetitions(fn, wf)
            self.assertGreater(sum([r.has_key('matches') for r in res]),0)
#            break
        return
        folder = '/mnt/rzws/experiment_data/test'
        f='/mnt/rzws/experiment_data/test/data_C7_unknownstim_1423223487_0.hdf5'
        res = find_repetitions(f, folder)
        self.assertGreater(sum([r.has_key('matches') for r in res]),0)
        
        
    
if __name__=='__main__':
    unittest.main()
