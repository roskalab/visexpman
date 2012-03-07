import visexpA.engine.datahandlers.importers as importers
import visexpA.engine.datahandlers.hdf5io as hdf5io
import visexpA.engine.datahandlers.matlabfile as matlabfile
from visexpman.engine.hardware_interface import mes_interface
from visexpman.engine.generic import utils
from visexpman.engine.generic import file
import os
import os.path
import numpy
import Image
from visexpman.engine.generic import introspect
from visexpman.users.daniel import moving_dot, configurations
import pp
import random
import re
from matplotlib.pyplot import figure,  plot, show, legend

s0 = 0.0
s1 = 10.0
v0 = 0.0
v1 = 10.0

T = 1.0
dt = 1e-3
t = numpy.linspace(0, T, T/dt+1)

A = 1.0

a = -A*numpy.cos(2*numpy.pi*t/T)+A
v = v0 + A*t - A*T/(2*numpy.pi)*numpy.sin(2*numpy.pi*t/T)
s_corr = A*T**2/(4*numpy.pi**2)
s = s0 + v0 * t + 0.5*A*t**2+ A*T**2/(4*numpy.pi**2)*numpy.cos(2*numpy.pi*t/T) - s_corr

dv = A*T
ds = v0 * T + 0.5*A*T**2
print dv, v[-1]-v[0]
print ds, s[-1]-s[0]
plot(t, a)
plot(t, v)
plot(t, s)
legend(('a', 'v', 's'))
show()

#a = numpy.linspace(-20.0, 20.0, 41)
#ti = numpy.linspace(0, t, 20)
#for ai in a:
#    s = s0+v0*ti+0.5*ai*ti**2
#    figure(1)
#    plot(ti, s)
#    figure(2)
#    plot(ti[:-1], numpy.diff(s))
#show()
