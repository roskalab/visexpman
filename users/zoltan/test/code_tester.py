from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
from visexpA.engine.datahandlers.hdf5io import Hdf5io, read_item
import numpy
from visexpman.engine.hardware_interface import scanner_control
import Image
from visexpA.engine.dataprocessors.generic import normalize
import os
import os.path
from visexpman.engine.generic import utils

def test():
    fs = 1e6
    f = 3000
    t = numpy.linspace(0, 1.0/f,fs, False)
    x = numpy.sin(numpy.pi*2*t*f)
    X = numpy.fft.fft(x)
    ns = t.shape[0]/2
    gain = numpy.ones(ns)*1

    #gain = numpy.linspace(1, 0, ns, False)
    #phase = numpy.pi*numpy.arange(0, ns)/ns
    #phase = numpy.ones(ns)*numpy.pi/2
    coeff = [ 0.00043265, -0.02486131]
    phase = numpy.arange(ns)*coeff[0]*fs/ns+coeff[1]
    phase = numpy.where(phase<0, 0, phase)
    #phase *= 0
    #phase[1] = numpy.pi
    #Mirror phase and concatenate 
    phase_r = phase.tolist()
    phase_r.reverse()
    phase = numpy.concatenate((-phase, numpy.array(phase_r)))
    #Mirror gain and multiply the mirror with -1
    gain_r = gain.tolist()
    gain_r.reverse()
    gain = numpy.concatenate((gain, numpy.array(gain_r)))

    H = numpy.vectorize(complex)(gain*numpy.cos(phase), gain*numpy.sin(phase))
    y = numpy.fft.ifft(H*X)
    #y = numpy.fft.ifft(X)
    figure(1)
    title('input, output, time domain')
    plot(t, x)
    plot(t, y.real)
    plot(t, y.imag)
    #plot(t, numpy.arctan(y.imag, y.real)*0)
    #legend(('x', 'y real', 'y imag', ''))
    figure(2)
    title('transfer function')
    plot(gain)
    plot(phase)
    figure(3)
    title('Filter fourier transform')
    plot(H.real)
    plot(H.imag)
    figure(4)
    title('Signal fourier transform')
    plot(X.real)
    plot(X.imag)
    figure(5)
    title('Signal amplitude, phase')
    plot(abs(X))
    plot(numpy.arctan(X.imag,X.real))
    show()
    pass
    
def corr():
    from scipy.signal import correlate
    fs = 1e3
    f = 1
    t = numpy.linspace(0, 1.0/f,fs, False)
    x1 = numpy.sin(numpy.pi*2*t*f)
    x2 = numpy.roll(x1,100)
    
    plot(t,x1)
    plot(t,x2)
    print t.shape[0] - correlate(x1,x2).argmax()
    show()
corr()
