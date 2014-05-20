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
    return numpy.linspace(0, duration, duration*fs+1)

def wf_sin(a, f, duration, fs, phase = 0, offset = 0):
    t = time_series(duration, fs)
    return offset + 0.5*a*numpy.sin(t*2*numpy.pi*f+phase*numpy.pi/180.0)
    
def wf_triangle(a, t_up, t_down, duration, fs, offset = 0):
    if t_up + t_down > duration:
        raise ValueError('t_up and t_down must be less than duration')
    nsample_up = t_up*fs
    nsample_down = t_down*fs
    triangle = numpy.concatenate((numpy.linspace(a/nsample_up, a, nsample_up), numpy.linspace(a-a/nsample_down, 0, nsample_down)))
    sig = numpy.zeros(int(fs*duration))
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
    
def generate_natural_stimulus_intensity_profile(duration, speed, minimal_spatial_period,spatial_resolution, intensity_levels = 255):
    '''
    duration: duration of stimulus
    speed: um/s
    minimal_spatial_period: um
    spatial resolution is determined from pixel2um config parameter
    
    '''
    spatial_range = duration * speed
    if minimal_spatial_period < 5 * spatial_resolution:
        raise RuntimeError('minimal_spatial_period ({0}) shall be bigger than 5 x spatial_resolution ({0}) ' .format(minimal_spatial_period, spatial_resolution))
    spatial_frequencies = numpy.arange(1.0/spatial_range, 1.0/minimal_spatial_period+1.0/spatial_range, 1.0/spatial_range)
    amplitudes = 1.0/spatial_frequencies
    phases = generate_random_angles(spatial_frequencies.shape[0])
    intensity_profile = numpy.zeros(int(spatial_range/spatial_resolution))
    s = numpy.arange(0, spatial_range, spatial_resolution)
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
    
def sinus_linear_range(f, fs, error):
    pass
    
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
        generate_natural_stimulus_intensity_profile(20.0, 300.0, 20.0,2.0)
    
if __name__=='__main__':
    unittest.main()
