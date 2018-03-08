'''
Signal/Image manipulation/filtering functions
'''
import copy
import numpy
import scipy.interpolate

import utils

import unittest

def histogram_shift(data, output_range, min = None, max = None, gamma = 1.0, bandwidth = None, resolution = 256):
    '''
    data's values are shifted such that they are within the range of min and max
    if bandwidth is provided the min and maximum is determined by mean +/- bandwidth * standard deviation
    output_range: data is shifted such that it fits to this range
    min, max: if provided values below or above will be set to this value
    resolution: size of input/output vector
    '''
    if not hasattr(data,'dtype'):
        raise ValueError('Numpy array must be provided, not {0}'.format(type(data)))
    if min is None and max is None and bandwidth is not None:
        mean = data.mean()#alternatively a peak in the histogram could be also used as center but with too much dark or bright pixels in an image might not work well
        band = bandwidth * data.std()
        min = mean - band
        max = mean + band
    data_shifted = copy.deepcopy(data)
    data_shifted = numpy.where(min>data_shifted, min, data_shifted)
    data_shifted = numpy.where(max<data_shifted, max, data_shifted)
    x_axis = numpy.linspace(min, max, resolution+1)
    y_axis = scale(numpy.linspace(0.0, 1.0, resolution+1)**gamma, output_range[0], output_range[1])
    interpolator = scipy.interpolate.interp1d(x_axis, y_axis)#preparation of interpolator is only 20% of the overall runtime
    return interpolator(data_shifted)
    
def scale(data, output_range_min = 0.0, output_range_max =1.0):
    return (numpy.cast['float'](data) - data.min())/(data.max() - data.min())*(output_range_max - output_range_min)+output_range_min
    
def coo_range(d):
    return d.max(axis=0)-d.min(axis=0)
    
    
def greyscale(im, weights = numpy.array([1.0, 1.0, 1.0])):
    '''
    If im is uint8, the result is scaled back to the range of this datatype
    If im is float and all values of im is within the 0...1 range, the result is scaled back to this range
    '''
    if len(im.shape) < 3 or im.shape[-1] != 3:
        raise ValueError('Image array shall be at least three dimensional and last dimension\'s size shall be 3: {0}'.format(im.shape))
    if not hasattr(weights, 'dtype') or not utils.inrange(weights, 0,1):
       raise ValueError('weights shall be numpy array and its values shall be between 0 and 1') 
    if 'float' in im.dtype.name:
        if utils.inrange(im, 0, 1):
            maxval = 1.0
        else:
            raise NotImplementedError('')
    elif 'uint' in im.dtype.name:
        maxval = 2**(im.dtype.itemsize*8)-1
    return numpy.cast[im.dtype.name]((numpy.cast['float'](im)*weights).sum(axis=2)/(maxval*weights.sum())*maxval)
       
############## Waveform generation ##############
def time_series(duration, fs):
    if isinstance(duration, float):
        return numpy.linspace(0, duration, int(numpy.round(duration*fs))+1)
    elif isinstance(duration, int):
        return numpy.arange(duration,dtype=numpy.float)/fs

def wf_sin(a, f, duration, fs, phase = 0, offset = 0):
    t = time_series(duration, fs)
    return offset + 0.5*a*numpy.sin(t*2*numpy.pi*f+phase*numpy.pi/180.0)
    
def wf_triangle(a, t_up, t_down, duration, fs, offset = 0):
    if t_up + t_down > duration:
        raise ValueError('t_up and t_down must be less than duration')
    nsample_up = int(numpy.round(t_up*fs))
    nsample_down = int(numpy.round(t_down*fs))
    triangle = numpy.concatenate((numpy.linspace(a/nsample_up, a, nsample_up), numpy.linspace(a-a/nsample_down, 0, nsample_down)))
    sig = numpy.zeros(int(numpy.round(fs*duration)))
    triangle = numpy.tile(triangle, sig.shape[0]/triangle.shape[0])
    sig[:triangle.shape[0]] = triangle
    return sig+offset
    
def generate_random_angles(n, p = 3559, q = 3571, x0 = 17):
    '''
    Generates n angles (-pi...pi range) using Blum Blum Shub pseudorandom generation algorithm:
    xn+1 = xn**2 mod M where M is the product of two big primes.
    '''
    if p*q<n:
        raise RuntimeError('Bigger prime numbers must be provided as p and q')
    v = []
    xn = x0
    for i in range(n):
        xn = (xn**2) % (p*q)
        v.append(xn/float(p*q))
    return numpy.array(v)*2*numpy.pi - numpy.pi
    
def generate_natural_stimulus_intensity_profile(duration, speed, minimal_spatial_period, spatial_resolution, intensity_levels = 255):
    '''
    duration: duration of stimulus
    speed: um/s
    minimal_spatial_period: um
    spatial resolution is determined from pixel2um config parameter, width of 1 pixel wide bar
    Usage in time domain:
        duration is duration
        speed =1, duration * speed gives the overall time of the stimulation
        minimal_spatial_period: minimal time period
        spatial_resolution: duration of 1 sample in seconds
    '''
    spatial_range = duration * speed
    if minimal_spatial_period < 5 * spatial_resolution:
        raise RuntimeError('minimal_spatial_period ({0}) shall be bigger than 5 x spatial_resolution ({0}) ' .format(minimal_spatial_period, spatial_resolution))
    spatial_frequencies = numpy.arange(1.0/spatial_range, 1.0/minimal_spatial_period+1.0/spatial_range, 1.0/spatial_range)
    amplitudes = numpy.sqrt(1.0/spatial_frequencies**2)#Power spectrum of sunlight which is 1/f**2
    phases = generate_random_angles(spatial_frequencies.shape[0])
    #Since the number fo samples have to be integer, the spatial resolution is slightly modified
    modified_spatial_resolution = float(spatial_range/spatial_resolution)/int(spatial_range/spatial_resolution)*spatial_resolution
    s = numpy.arange(0, spatial_range, modified_spatial_resolution)
    intensity_profile = numpy.zeros_like(s)
    for harmonic in range(spatial_frequencies.shape[0]):
        intensity_profile += amplitudes[harmonic]*numpy.sin(2*numpy.pi*s*spatial_frequencies[harmonic] + phases[harmonic])
        if abs(intensity_profile[0]-intensity_profile[-1])/intensity_profile.max()>1e-3:
            pass
    intensity_profile = scale(intensity_profile)
    if intensity_levels != 0:
        intensity_profile = numpy.cast['int'](intensity_profile*intensity_levels)/float(intensity_levels)
    if not True:
        from pylab import plot,show,figure
        figure(1)
        plot(s, intensity_profile)
        figure(2)
        plot(numpy.linspace(0, 2.0/spatial_resolution, intensity_profile.shape[0]), 0.5*abs(numpy.fft.fft(intensity_profile)/intensity_profile.shape[0])/intensity_profile.shape[0],'o')
        figure(3)
        plot(numpy.tile(intensity_profile,3),'o')
        show()
    return intensity_profile
    
def natural_distribution_morse(duration, sample_time, occurence_of_longest_period = 1.0, n0 = 10):
    '''
    Longest period shall occur once, therefore
    A/((n0+n-1)*ts) = m (I.), where n is the number of different periods, ts is the sample time, A is the constant in the A/x distribution of periods
                                            n0: minimal period/ts, m: occurence of longest period
    
    number of periods where its length is ts: A/(n0*ts), duration of periods with this length: A/(n0*ts)*(n0*ts) = A
    for (n0+1)*ts: A/((n0+1)*ts) 
    ...
    
    A/((n0+n-1)*ts) = m (I.)
    t = A*n, where t is the duration of the stimulus (II.), t determines the number of different period values
    A = t/n
    t/n = m*ts*(n0+n-1)
    n**2+(n0-1)*n-t/(m*ts) = 0
    n12=(-n0+1 +/- sqrt((n0-1)**2+4*t/(m*ts)))/2
    n=(-n0+1 + sqrt((n0-1)**2+4*t/(m*ts)))/2
    '''
    n=(-n0+1 + numpy.sqrt((n0-1.0)**2+4*duration/(occurence_of_longest_period*sample_time)))/2
    n = int(numpy.ceil(n))
    A = duration/n
    periods = numpy.arange(n0,n0+n)*sample_time
    occurence_of_periods =  numpy.round(A/periods,0)
    #Generate pool of periods
    pool = []
    for i in range(n):
        pool.extend([periods[i]]*occurence_of_periods[i])
    import random
    random.seed(0)
    random.shuffle(pool)
    return pool, n, periods[-1]
    
def sinus_linear_range(f, fs, error):
    a=2.0
    s =  wf_sin(a, f, 0.25/f, fs)
    t = time_series(0.25/f, fs)
    linear = numpy.pi*2*t*f*a*0.5
    e = linear-s
    #multiplication with 2: range is to be extended to the negative direction
    return 2*numpy.nonzero(numpy.where(linear-s<error, 1, 0))[0].max()

def sinus_linear_range_slow(error):
    def f(x, e):
        return x - numpy.sin(x)-e
    from scipy.optimize import fsolve
    sol = fsolve(f, numpy.pi/4, args=(error))
    #Between 0 and returned phase linearity error  is below specified
    return sol[0]*2
    
def sweep_sin(amplitudes, frqs, nperiods, sample_rate):
    waveform = numpy.array([])
    boundaries = numpy.array([])
    af = []
    for amplitude in amplitudes:
        for f in frqs:
            sig = wf_sin(amplitude, f, float(nperiods)/f, sample_rate)
            waveform = numpy.concatenate((waveform,sig))
            boundary = numpy.zeros_like(sig)
            boundary[0] = 1
            boundary[-1] = -1
            boundaries = numpy.concatenate((boundaries,boundary))
            af.append([amplitude, f])
    return waveform,boundaries,af
    
def find_bead_center_and_width(curve):
    h=numpy.histogram(curve)
    threshold = (h[1][h[0].argmax()] + h[1][h[0].argmax()+1])*0.5
    edges = numpy.nonzero(numpy.diff(numpy.where(curve>threshold,1,0)))[0]
    return edges.mean(), edges.max()-edges.min(),threshold#center,bead size
    
def signal2binary(waveform):
    '''
    Signal is considered true/logic 1 when signal reached the 'high' voltage level (transient is considered as False)
    '''
    return numpy.where(waveform > numpy.histogram(waveform, bins = 10)[1][-2],  True,  False)
    
def trigger_indexes(trigger,threshold=0.3, abs_threshold=None):
    '''
    Indexes of rising edges in trigger are returned
    '''
    if abs_threshold!=None and trigger.max()<abs_threshold:
        return numpy.array([])
    return numpy.nonzero(abs(numpy.diff(numpy.where(trigger-trigger.min()>threshold*(trigger.max()-trigger.min()),1,0))))[0]+1
    #return numpy.nonzero(numpy.where(abs(numpy.diff(trigger-trigger.min()))>threshold*(trigger.max()-trigger.min()), 1, 0))[0]+1
    
def detect_edges(signal, threshold):
    return numpy.nonzero(numpy.diff(numpy.where(signal>threshold,1,0)))[0]+1
    
def generate_bins(signal, binsize):
    '''
    generate bins such that it is aligned to binsize
    '''
    nsteps_lower=signal.min()/binsize
    range_min=numpy.ceil(abs(nsteps_lower))*numpy.sign(nsteps_lower)*binsize
    nsteps_upper=numpy.ceil(signal.max()/binsize)
    range_max=nsteps_upper*binsize
    bins=numpy.arange(range_min,range_max,binsize)
    bins=numpy.append(bins, range_max)
    return bins

def images2mip(rawdata, timeseries_dimension = 0):
    return rawdata.max(axis=timeseries_dimension)
    
def time2index(times,timepoint):
    '''
    tells at which index happend timepoint in times 
    '''
    return numpy.where(times>timepoint)[0][0]
        
def df_over_f(t, x, tstim, baseline_length):
    baseline = x[numpy.where(numpy.logical_and(t<tstim,t>tstim-baseline_length))].mean()
    return x / baseline - 1.0
    
def average_of_traces(x,y):
    if len(x) != len(y):
        raise RuntimeError('x and y should have the same length: {0}, {1}'.format(len(x), len(y)))
    #Find the common x range
    common_x_min = max([xi.min() for xi in x])
    common_x_max = min([xi.max() for xi in x])
    indexes = numpy.array([numpy.where(numpy.logical_and(x[i]>=common_x_min, x[i]<=common_x_max))[0] for i in range(len(y))])
    length = min([i.shape[0] for i in indexes])
    indexes = numpy.array([i[:length] for i in indexes])
    y_average = numpy.array([y[i][indexes[i]] for i in range(len(y))]).mean(axis=0)
    x_average = numpy.array([x[i][indexes[i]] for i in range(len(x))]).mean(axis=0)
    return x_average, y_average
    
def signal_shift(sig1,sig2):
    c=numpy.correlate(sig1,sig2,'same')
    return sig1.shape[0]/2-c.argmax()

def downsample_2d_array(ar, fact):
    from scipy import ndimage
    assert isinstance(fact, int), type(fact)
    sx, sy = ar.shape
    X, Y = numpy.ogrid[0:sx, 0:sy]
    regions = sy/fact * (X/fact) + Y/fact
    res = ndimage.mean(ar, labels=regions, index=numpy.arange(regions.max() + 1))
    res.shape = (sx/fact, sy/fact)
    return res
    
def downsample_2d_array_1_arg(arg):
    ar, fact=arg
    return downsample_2d_array(ar, fact)
    
def downsample_2d_rgbarray(ar, fact,pool=None):
    newshape=(numpy.array(ar.shape[:2])/fact).tolist()
    newshape.append(3)
    out=numpy.zeros(newshape,dtype=ar.dtype)
    if pool is not None:
        pars=[(ar[:,:,ci],fact) for ci in range(ar.shape[2])]
        res=pool.map(downsample_2d_array_1_arg,pars)
        for i in range(len(res)):
            out[:,:,i]=res[i]
    else:
        for ci in range(ar.shape[2]):
            out[:,:,ci]=downsample_2d_array(ar[:,:,ci],fact)
    return out
    
def to_16bit(data):
    datarange=data.max()-data.min()
    scale=(2**16-1)/datarange
    offset=data.min()
    scaled=numpy.cast['uint16']((data-offset)*scale)
    scale={'scale':scale, 'offset':offset, 'range':datarange}
    return scaled, scale
    
def from_16bit(scaled,scale):
    s=numpy.cast['float'](scaled)
    s/=scale['scale']
    s+=scale['offset']
    return s
    
def measure_sin(sig,  fsample,  p0=[1, 1, 0, 0]):
    import scipy.optimize
    def sinus(x, a, f, ph, o):
        return a*numpy.sin(numpy.pi*2*x*f+ph)+o
    t=numpy.arange(sig.shape[0])/float(fsample)
    par,  cov=scipy.optimize.curve_fit(sinus, t, sig, p0=p0)
    a, f, ph, o=par
    return a, f
    
def shape2distance(im,iterations):
    '''
    im is a binay image representing one object.
    The output is an image showing the distance of each pixel in the object 
    from the edge
    '''
    import scipy.ndimage.morphology, scipy.ndimage.filters
    input=im.copy()
    stages=[input.copy()]
    output=numpy.zeros_like(im)
    for i in range(int(iterations)):
        input=scipy.ndimage.morphology.binary_erosion(input)
        stages.append(input.copy())
        output+=numpy.cast['uint8'](input.copy())*(i+1)
    return output
    
def generate_frequency_modulated_waveform(duration, base_frequency, frequency_step, switch_frequency, fsample,step=True):
    f1=base_frequency+frequency_step
    f2=base_frequency-frequency_step
    if step:
        on_waveform=numpy.sin(numpy.arange(fsample*0.5/switch_frequency)/fsample*2*numpy.pi*f1)
        off_waveform=numpy.sin(numpy.arange(fsample*0.5/switch_frequency)/fsample*2*numpy.pi*f2)
        nshift_periods=int(duration*switch_frequency)
        return numpy.tile(numpy.concatenate((on_waveform, off_waveform)),nshift_periods)
    else:
        t=time_series(float(duration), fsample)
        frequency_values=numpy.sin(t* 2* numpy.pi* switch_frequency)*0.5*abs(f2-f1)+0.5*abs(f2-f1)+f2
        #Reduce frequency levels
  #      fround=int(fsample/100)
#        frequency_values=(numpy.round(frequency_values/fround)*fround)
        frequency_values=numpy.round(frequency_values,-2)
        sig=numpy.sin(t*numpy.pi*2*frequency_values)
        return sig

class TestSignal(unittest.TestCase):
    def test_01_histogram_shift_1d(self):
        #generate test data
        numpy.testing.assert_equal(numpy.array([100,100,100,100,120,140,160,180,200,200],dtype=numpy.float),
                                   histogram_shift(numpy.arange(10,dtype=numpy.float), [100,200],min=3,max=8,resolution=5))
        
    def test_02_histogram_shift_2d(self):
        size = 5
        data = numpy.repeat(numpy.linspace(0, size, size),size).reshape((size,size))
        data += data.T
        expected = numpy.array([[ 0.    ,  0.    ,  0.    ,  0.    ,  0.25  ],
                                                               [ 0.    ,  0.    ,  0.    ,  0.25  ,  0.5625],
                                                               [ 0.    ,  0.    ,  0.25  ,  0.5625,  0.875 ],
                                                               [ 0.    ,  0.25  ,  0.5625,  0.875 ,  1.    ],
                                                               [ 0.25  ,  0.5625,  0.875 ,  1.    ,  1.    ]])
        numpy.testing.assert_equal(expected,
                                   histogram_shift(data, [0.0,1.0],min=4,max=8,resolution=4))
                                   
    def test_03_histogram_shift_band_and_gamma(self):
        shifted = histogram_shift(numpy.linspace(0,10,11), [0.0,1.0],bandwidth = 1, gamma = 2, resolution=10)
        expected = numpy.array([ 0.        ,  0.        ,  0.00256584,  0.03513167,  0.11932028,
        0.25      ,  0.43554805,  0.6675872 ,  0.95124913,  1.        ,  1.        ])
        numpy.testing.assert_allclose(shifted, expected, 0, 1e-5)
        
    def test_04_histogram_shift_on_image(self):
        from fileop import visexpman_package_path
        from PIL import Image
        import os.path
        gamma = 4
        data = greyscale(numpy.asarray(Image.open(os.path.join(visexpman_package_path(), 'data', 'images', 'default.bmp'))))
        data_shifted = histogram_shift(data, [0,255], 0,255,gamma=gamma)
        self.assertGreater(data.sum(), data_shifted.sum())
        self.assertLess(data.sum(), histogram_shift(data, [0,255], 0,255,gamma=1.0/gamma).sum())
        if False:
            out = numpy.zeros((data_shifted.shape[0]*2, data_shifted.shape[1]), numpy.uint8)
            out[:data.shape[0],:]=data
            out[data.shape[0]:,:]=data_shifted
            Image.fromarray(out).show()
            from pylab import plot, show
            plot(numpy.linspace(0,1,10),numpy.linspace(0,1,10)**gamma)
            show()
        
    def test_05_greyscale_invalid_dimension(self):
        self.assertRaises(ValueError, greyscale, numpy.ones((10,10)))
        self.assertRaises(ValueError, greyscale, numpy.ones((10,10,2)))
        
    def test_06_greyscale_conversion(self):
        dimensions = (4,4,3)
        #Test uint8
        data1 = numpy.ones(dimensions,dtype=numpy.uint8)
        data1[:,0,1] = 127#67
        data1[:,0,2] = 10
        data1[:,1,0] = 255#255.75
        expected1 = numpy.ones(dimensions[:2],dtype=numpy.uint8)
        expected1[:,0] = 38
        expected1[:,1] = 146
        numpy.testing.assert_equal(greyscale(data1, numpy.array([1.0, 0.5, 0.25])), expected1)
        #Test float in the range of 0...1
        data2 = numpy.zeros(dimensions,dtype=numpy.float)
        data2[:,-1, 0] = 0.1#0.6
        data2[:,-1, 1] = 1.0
        data2[:,-2, 2] = 0.5#0.125
        expected2 = numpy.zeros(dimensions[:2],dtype=numpy.float)
        expected2[:,-1] = 0.6/1.75
        expected2[:,-2] = 0.125/1.75
        numpy.testing.assert_equal(greyscale(data2, numpy.array([1.0, 0.5, 0.25])), expected2)
        
    def test_07_sin_waveform(self):
        sig=wf_sin(1,2,0.5,100,45,1)
        numpy.testing.assert_allclose(sig.max()-sig.min(), 1, 0, 1e-2)
        numpy.testing.assert_allclose(sig[0], numpy.sin(numpy.pi/4)/2+1, 0, 1e-2)
        self.assertEqual(sig.shape[0], 51)
        
    def test_08_triangle_wf(self):
        a = 1.0
        t_up = 0.2
        t_down = 0.1
        duration = 1.7
        fs = 100
        sig = wf_triangle(a, t_up, t_down, duration, fs)
        self.assertEqual(sig.max(), a)
        self.assertEqual(sig.min(), 0)
        numpy.testing.assert_allclose(numpy.diff(sig[:int(t_up*fs)]).std(), 0.0, 0.0, 1e-5)
        numpy.testing.assert_allclose(numpy.diff(sig[int(t_up*fs): int((t_up+t_down)*fs)]).std(), 0.0, 0.0, 1e-5)
        if False:
            from pylab import plot,show
            print numpy.diff(sig)
            plot(sig)
            show()
            
    def test_09_triangle_wf_single(self):
        a = -1.0
        t_up = 0.02
        t_down = 0.001
        duration = 0.021
        fs = 10000
        sig = wf_triangle(a, t_up, t_down, duration, fs)
        self.assertNotEqual(abs(sig).sum(), 0)

    def test_10_generate_natural_stimulus_intensity_profile(self):
        #duration, speed, minimal_spatial_period, spatial_resolution
        profile = generate_natural_stimulus_intensity_profile(40.0, 300.0, 20.0,2.0)
#        from pylab import plot,show,figure
#        figure(1);plot(profile);plot(profile*0.5+0.5)
#        figure(2);plot(abs(numpy.fft.fft(profile))/profile.shape[0]);plot(abs(numpy.fft.fft(profile*0.5+0.5))/profile.shape[0]);show()

        if 0:
            from pylab import plot,show
            plot(profile)
            show()
            
    def test_11_sinus_linear_range(self):
        sinus_linear_range(1000, 400e3, 1e-2)
        
    def test_12_natural_morse(self):
        sample_time = 1e-2
        duration = 60.0 #s
        occurence_of_longest_period = 1.0
        n0 = 10
        v = natural_distribution_morse(duration, sample_time, occurence_of_longest_period = 1.0, n0 = 10)
    
    def test_13_sinesweep(self):
        ao_sample_rate = 500000
        amplitudes = [1.0, 2.0]
        frq = numpy.arange(100,1500,100)
        frq = numpy.insert(frq, 0, 10)
        nperiods = 10
        waveform,boundaries,af = sweep_sin(amplitudes, frq, nperiods, ao_sample_rate)
        if 0:
            from pylab import plot,show
            plot(waveform)
            plot(boundaries)
            show()
            
    def test_14_trigger_indexes(self):
        trigger = numpy.concatenate((numpy.zeros(2), numpy.ones(10), numpy.zeros(10), numpy.ones(20), numpy.zeros(10)))
        numpy.testing.assert_equal(trigger_indexes(trigger), numpy.array([2, 12, 22, 42]))
    
    def test_15_average_of_traces(self):
        x=[numpy.arange(0,10), numpy.arange(-2,5), numpy.arange(0,9)+0.1]
        y=[numpy.arange(10),2*numpy.arange(7), 3*numpy.arange(9)]
        x_, y_ = average_of_traces(x,y)
        self.assertEqual(x_.shape,y_.shape)
        import hdf5io
        rois = utils.array2object(hdf5io.read_item('/home/rz/rzws/test_data/trace_avg/trace_avg.hdf5','rois', filelocking=False))
        x = [hdf5io.read_item('/home/rz/rzws/test_data/trace_avg/trace_avg.hdf5','timg', filelocking=False)]
        y = [rois[0]['normalized']]
        x.append(rois[0]['matches']['/mnt/rzws/experiment_data/test/20150310/C1_3371241139/data_C1_unknownstim_1425992998_0.hdf5']['timg'])
        y.append(rois[0]['matches']['/mnt/rzws/experiment_data/test/20150310/C1_3371241139/data_C1_unknownstim_1425992998_0.hdf5']['normalized'])
        x_, y_ = average_of_traces(x,y)
        
    def test_15_signal_shift(self):
        signal1=numpy.zeros(100)
        signal1[10:20]=1
        signal2=numpy.roll(signal1,10)
        self.assertEqual(signal_shift(signal1,signal2),10)
        
    def test_16_downsample_2d_array(self):
        a=numpy.random.random((100,100))
        res=downsample_2d_array(a,10)
        numpy.testing.assert_array_equal(numpy.array(a.shape), numpy.array(res.shape)*10)
        a=numpy.random.random((100,100,3))
        import multiprocessing
        import introspect
        pool=multiprocessing.Pool(introspect.get_available_process_cores())
        res=downsample_2d_rgbarray(a,2,pool)
        numpy.testing.assert_array_equal(numpy.array(a.shape[:2]), numpy.array(res.shape[:2])*2)
        
    def test_17_scale_16bit(self):
        data=numpy.random.random((1000,100))*200-50
#        data=numpy.arange(-10,10)
        s,sc=to_16bit(data)
        data_= from_16bit(s,sc)
        numpy.testing.assert_array_almost_equal(data,data_,2)
        
    def test_18_shape2distance(self):
        from PIL import Image
        from fileop import visexpman_package_path
        from pylab import imshow,show,figure
        import os
        im=numpy.asarray(Image.open(os.path.join(visexpman_package_path(), 'data', 'images', 'cross.png')))
        d=shape2distance(im, 4)
        imshow(d)
        show()
        #im=numpy.zeros((16,16),dtype=numpy.uint8)
        #im[2:14, 2:14]=1
        #d=shape2distance(im, 5)
        
    def test_19_fm(self):
        generate_frequency_modulated_waveform(10, 15e3, 1e3, 10,48e3)
        generate_frequency_modulated_waveform(10, 15e3, 1e3, 1,48e3,False)
        
        
    

if __name__=='__main__':
    unittest.main()
