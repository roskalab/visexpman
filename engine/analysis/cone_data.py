'''
This module contains Calcim imaging related analysis functions
'''
import numpy
import scipy.interpolate
import os.path
import copy
import unittest
try:
    import hdf5io
except ImportError:
    pass
import itertools
try:
    from visexpA.engine.dataprocessors import roi
    from visexpA.engine.dataprocessors import signal as signal2
except ImportError:
    print 'cell detector not installed'

from visexpman.engine.generic import utils,fileop,signal,geometry,introspect,stringop
from visexpman.engine.vision_experiment import experiment_data
import scipy.optimize
try:
    from skimage import filters
except ImportError:
    from skimage import filter as filters

from pylab import plot,show,figure,title,imshow,subplot,clf,savefig

import warnings

def exp(t,tconst, a,b):
    return a*numpy.exp(-t/tconst)+b
    
def sigmoid(t, t0, sigma,a,b):
    return a/(1+numpy.exp(-(t-t0)/sigma))+b
    
def calculate_trace_parameters(trace, tstim, timg,baseline_length):
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
    response_start = signal.time2index(timg, tstim[0])
    response_end = signal.time2index(timg, tstim[1])
    baseline_start = signal.time2index(timg, tstim[0]-baseline_length)
    baseline_end = signal.time2index(timg, tstim[0])
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
    import scipy.ndimage.measurements
    p=im1.max()
    im = gaussian_filter(im1, sigma)
    centers = signal2.getextrema(im, method = 'regmax')
    wrange = range(minsomaradius, maxsomaradius,stepsize)
    ims=signal.scale(im, 0.0, 1.0)
    res = roi.ratio_center_perimeter(ims, centers,  wrange)
    maskcum = numpy.zeros_like(im1,dtype=numpy.float)
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
        if  numpy.nonzero(central_segment)[0].shape[0] < 0.95*numpy.nonzero(mask)[0].shape[0]:#Valid roi
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
    x,y = pixels_below_threshold(rawdata,threshold)
    return rawdata[:,x,y].mean(axis=1)
    
def pixels_below_threshold(rawdata,threshold):
    mi=rawdata.mean(axis=0)
    #until now all values under threshold% of max intensity was considered as background, 
    #now the dimest threshold% of pixels are the backgound
    th=(mi.max()-mi.min())*threshold+mi.min()
    x,y = numpy.where(mi<th)
    return x,y
    
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
    allhdf5files = [f for f in allhdf5files if experiment_data.is_recording_filename(f)]
    allhdf5files = [f.replace('\\\\','\\') for f in allhdf5files]#Temporary solution
    if filename not in allhdf5files:
        raise RuntimeError('{0} is not in {1}'.format(filename, folder))
    ids = [experiment_data.parse_recording_filename(f)['id'] for f in allhdf5files]
    if len(ids) != len(set(ids)):
        import collections
        duplicates = [x for x, y in collections.Counter(ids).items() if y > 1]
        raise RuntimeError('Some files are duplicated: {0}'.format([f for f in allhdf5files if stringop.string_in_list(duplicates, f, any_match=True)]))
    #Identify files that are linked together
    links = [(f, fast_read(f, 'repetition_link')) for f in allhdf5files]#This takes long, cannot be run in parallel processes
    links=[[experiment_data.parse_recording_filename(link[0])['id'], link[1][0]] for link in links if link[1] is not None]
    filenameid = experiment_data.parse_recording_filename(filename)['id']
    experiment_name = experiment_data.parse_recording_filename(filename)['experiment_name']
    repetitions = []
#    remaining_links = copy.deepcopy(links)
#    next_ids = [l for l in remaining_links if filenameid in l]
#    map(remaining_links.remove, next_ids)
#    next_ids = [ni[0 if ni.index(filenameid) == 1 else 1 ] for ni in next_ids]
    next_ids = [filenameid]
    while True:
        next_id_raw=[]
        for next_id in next_ids:
            idlist=[link for link in links if next_id in link]
            idlist = list(set([nii for ni in idlist for nii in ni]))#flatten list, remove repetitions
            idlist = [i for i in idlist if i != next_id]
            next_id_raw.extend(idlist)
        next_ids= list(set(next_id_raw))
        prev_repetitions = copy.deepcopy(repetitions)
        repetitions.extend(next_ids)
        repetitions=list(set(repetitions))
        if len(repetitions)==len(prev_repetitions):
            break
    #Read roi info from assigned files
    aggregated_rois = dict([(f, hdf5io.read_item(f, 'rois', filelocking=False)) for f in allhdf5files if stringop.string_in_list(repetitions, f, any_match=True) and (experiment_name == experiment_data.parse_recording_filename(f)['experiment_name'] if filter_by_stimulus_type else True)])
    for fn in aggregated_rois.keys():#Remove recordings that do not contain roi
        if aggregated_rois[fn] is None:
            del aggregated_rois[fn]
    #take rectangle center for determining mathcing roi
    aggregated_rectangles = {}
    for fn, rois in aggregated_rois.items():
        if len(rois)>0 and rois is not None:#Skip if link exists but rois do not
            aggregated_rectangles[fn] = [r['rectangle'][:2] for r in rois]
    #Match rois from different repetitions
    if not aggregated_rectangles.has_key(filename):
        raise RuntimeError('{0} does not contain rois. Make sure that rois are saved'.format(filename))
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
                matched_roi=aggregated_rois[fn][index]
                matched_roi['match_weight']= match_weight
                aggregated_rois[filename][roi_ct]['matches'][os.path.split(fn)[1]] = matched_roi
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
    skip_ids = []
    aggregated_cells = []
    allhdf5files.sort()
    for hdf5file in allhdf5files:
        print allhdf5files.index(hdf5file)+1,len(allhdf5files), len(aggregated_cells)
        #Check if hdf5file is a valid recording file and hdf5file is not already processed during a previuous search for repetitions
        fntags= experiment_data.parse_recording_filename(hdf5file)
        if fntags['id'] in skip_ids or not experiment_data.is_recording_filename(hdf5file):
            continue
        try:
            aggregated_rois = find_repetitions(hdf5file, folder, filter_by_stimulus_type = False)
        except RuntimeError,e:
            if 'does not contain rois' not in str(e):
                raise e
            else:
                continue
        scan_region_name = fntags['tag']
        for roi in aggregated_rois:
            main_roi = copy.deepcopy(roi)
            try:
                del main_roi['matches']
            except:
                continue
            matched_rois = {os.path.basename(hdf5file): main_roi}
            matched_rois.update(roi['matches'])
            #Organize by stimulus type:
            organized_rois = {}
            [v['stimulus_name'] for v in matched_rois.values()]
            for stimulus_name in list(set([v['stimulus_name'] for v in matched_rois.values()])):
                organized_rois[stimulus_name]={}
                for fn in [fn for fn,v in matched_rois.items() if v['stimulus_name'] == stimulus_name]:
                    organized_rois[stimulus_name][fn.replace('.hdf5', '')]=matched_rois[fn]
            organized_rois['scan_region']=scan_region_name
            aggregated_cells.append(organized_rois)
            skip_ids.extend([experiment_data.parse_recording_filename(fn)['id'] for fn in roi['matches'].keys()])
        skip_ids = list(set(skip_ids))
    return aggregated_cells
    
def aggregate_stage_coordinates(folder):
    allhdf5files = experiment_data.find_recording_files(folder)
    rp=[[os.path.basename(f).replace('.hdf5',''), hdf5io.read_item(f, 'recording_parameters', filelocking=False)] for f in allhdf5files]
    return dict([(rpi[0], rpi[1]['absolute_stage_coordinates']) for rpi in rp if rpi[1].has_key('absolute_stage_coordinates')])
    
def cell_trace_params(cell):
    keys=[]
    for sn,v in cell.items():
        if 'scan_region' in sn: continue
        keys.extend(zip(len(v.keys())*[sn], v.keys()))
    for key in keys:
        baseline_mean, response_amplitude, response_rise_sigma, T_falling, T_initial_drop,fitted_traces = \
                    calculate_trace_parameters(cell[key[0]][key[1]]['normalized'],
                                                                 cell[key[0]][key[1]]['tstim'], 
                                                                 cell[key[0]][key[1]]['timg'], 
                                                                 cell[key[0]][key[1]]['baseline_length'])
        cell[key[0]][key[1]]['response_amplitude']=response_amplitude
        cell[key[0]][key[1]]['response_rise_sigma']=response_rise_sigma
    return cell
    
def quantify_cells(cells):
    #Calculate trace parameters
    if 0:
        import multiprocessing
        p=multiprocessing.Pool(introspect.get_available_process_cores())
        cells=p.map(cell_trace_params,cells)
    else:
        cells=[cell_trace_params(cell) for cell in cells]
    #Average repetitions
    cell_parameters=[]
    for cell in cells:
        cell_parameter = {}
        for sn in cell.keys():
            if 'scan_region' in sn: continue
            pars=numpy.array([[v['response_amplitude'], v['response_rise_sigma']] for v in cell[sn].values()]).mean(axis=0)
            cell_parameter[sn] = {'response_amplitude': pars[0], 'response_rise_sigma': pars[1]}
        cell_parameters.append(cell_parameter)
    #Distribution of different stimuli
    parameter_distributions = {}
    parameter_names = list(set([cpii for cp in cell_parameters for cpi in cp.values() for cpii in cpi.keys()]))
    for stimulus_name in list(set([cpi for cp in cell_parameters for cpi in cp.keys()])):
        parameter_distributions[stimulus_name]={}
        for parname in parameter_names:
            parameter_distributions[stimulus_name][parname] = numpy.array([cp[stimulus_name][parname] if cp.has_key(stimulus_name) else numpy.nan for cp in cell_parameters])
    return parameter_distributions
    
def roi_redetect(rectangle, meanimage, subimage_size=3):
    subimage=meanimage[rectangle[0]-rectangle[2]*0.5*subimage_size:rectangle[0]+rectangle[2]*0.5*subimage_size,rectangle[1]-rectangle[3]*0.5*subimage_size:rectangle[1]+rectangle[3]*0.5*subimage_size]
    binary=numpy.where(subimage>filters.threshold_otsu(subimage),1,0)
    import scipy.ndimage.measurements
    labeled, nsegments = scipy.ndimage.measurements.label(binary)
    #Take item in the center
    area=numpy.where(labeled==labeled[binary.shape[0]/2,binary.shape[1]/2])
    area=numpy.copy(area)
    area[0]+=numpy.cast['int'](rectangle[0]-rectangle[2]*subimage_size*0.5)
    area[1]+=numpy.cast['int'](rectangle[1]-rectangle[3]*subimage_size*0.5)
    return numpy.array(area).T
    
class TestCA(unittest.TestCase):
    def setUp(self):
        if '_01_' in self._testMethodName or '_02_' in self._testMethodName or '_03_' in self._testMethodName:
            from visexpman.users.test import unittest_aggregator
            self.files = fileop.listdir_fullpath(os.path.join(fileop.select_folder_exists(unittest_aggregator.TEST_test_data_folder), 'trace_analysis'))
        
    def test_01_trace_parameters(self):
        ct=0
        for f in self.files:
            h=experiment_data.CaImagingData(f,filelocking=False)
            rc=[r['raw'] for r in h.findvar('rois')]
            tstim,timg, meanimage, image_scale, raw_data = h.prepare4analysis()
#            with introspect.Timer(''):
            res = map(calculate_trace_parameters, rc, len(rc)*[tstim], len(rc)*[timg], len(rc)*[1])
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
            self.assertEqual([len(r['matches'].keys()) for r in res if r.has_key('matches')], [2]*len(res))
        
    
    def test_06_aggregate_cells(self):
        from visexpman.users.test.unittest_aggregator import prepare_test_data
        wf='/tmp/wf'
        fns = fileop.listdir_fullpath(prepare_test_data('aggregate',working_folder=wf))
        fns.sort()
        cells = aggregate_cells(wf)
        self.assertTrue(isinstance(cells,list))
        [self.assertTrue('scan_region' in cell.keys()) for cell in cells]
        [self.assertGreater(len(cell.keys()),0) for cell in cells]
        expected_cell_properties = ['image_scale', 'area', 'match_weight', 'meanimage', 'stimulus_name', 'tstim', 'raw', 'baseline_length', 'normalized', 'background', 'background_threshold', 'rectangle', 'timg', 'red']
        for cell in cells:
            repeats=cell[[c for c in cell.keys() if 'scan_region' !=c][0]].values()
            for r in repeats:
                self.assertGreaterEqual(len([True for p in expected_cell_properties if p in r.keys()]),11)#11...13. Some old files does not have area key or match_weight
    
    def test_07_quantify_cells(self):
        folder = fileop.select_folder_exists(['/home/rz/rzws/test_data/', '/home/rz/codes/data/test_data'])
        cells=hdf5io.read_item(os.path.join(folder, 'aggregated_cells.hdf5'), 'cells',filelocking=False)
        parameter_distributions = quantify_cells(cells)
        self.assertTrue(isinstance(parameter_distributions,dict))
        ref=parameter_distributions.values()[0].keys()
        for parnames in [v.keys() for v in parameter_distributions.values()]:
            self.assertEqual(ref,parnames)
        self.assertTrue(all([hasattr(vv, 'shape') for vv in v.values() for v in parameter_distributions.values()]))
        
    def test_08_local_cell_detection(self):
        from visexpman.users.test.unittest_aggregator import prepare_test_data
        wf='/tmp/wf'
        fn = fileop.listdir_fullpath(prepare_test_data('local_cell_detection',working_folder=wf))[0]
        #fn='/home/rz/codes/data/test_data/data_C6_SpotPar_209592957_0.hdf5'
        rois=hdf5io.read_item(fn,'rois',filelocking=False)
        roi=rois[18]
        meanimage=roi['meanimage']
        area=roi_redetect(roi['rectangle'], meanimage, subimage_size=3)
        meanimage[area[:,0],area[:,1]]=meanimage.max()
        print roi['rectangle']
        imshow(meanimage);show()
        pass
    
    @unittest.skip('')
    def test_debug(self):
        aggregate_cells('/mnt/rzws/experiment_data/test')
    
if __name__=='__main__':
    unittest.main()
