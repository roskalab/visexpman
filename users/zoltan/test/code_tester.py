from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
from visexpA.engine.datahandlers.hdf5io import Hdf5io, read_item
import numpy
from visexpman.engine.hardware_interface import scanner_control
import Image
from visexpA.engine.dataprocessors.generic import normalize
import os
import os.path
from visexpman.engine.generic import utils
fs = 1000
f = 10
t = numpy.linspace(0, 1,fs, False)
x = numpy.sin(numpy.pi*2*t*f)
X = numpy.fft.fft(x)
ns = t.shape[0]/2
gain = numpy.ones(ns)*0.5
#gain = numpy.linspace(1, 0, ns, False)
phase = numpy.pi*numpy.arange(0, ns)/ns
phase = numpy.ones(ns)*numpy.pi/2
#phase *= 0
#phase[1] = numpy.pi
phase_r = phase.tolist()
phase_r.reverse()
phase = numpy.concatenate((phase, -numpy.array(phase_r)))
gain_r = gain.tolist()
gain_r.reverse()
gain = numpy.concatenate((gain, numpy.array(gain_r)))

H = numpy.vectorize(complex)(gain, phase)
y = numpy.fft.ifft(H*X)
#y = numpy.fft.ifft(X)
figure(1)
plot(t, x)
plot(t, y.real)
plot(t, y.imag)
#plot(t, numpy.arctan(y.imag, y.real)*0)
#legend(('x', 'y real', 'y imag', ''))
figure(2)
plot(gain)
plot(phase)
figure(3)
plot(X.real)
plot(X.imag)
show()
pass
