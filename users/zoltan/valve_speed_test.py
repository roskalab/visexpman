from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.generic import signal
import numpy, time, hdf5io
from pylab import *

ai='Dev1/ai1:2'
ao='Dev1/ao1'
fsample=1000#Ao max rate
opentime=100e-3
offtime=0.2
repeats=40
waveform=numpy.concatenate((
            numpy.zeros(fsample*offtime),  
            5*numpy.ones(opentime*fsample), 
            numpy.zeros(offtime*fsample)))
waveform=numpy.tile(waveform, repeats)
ai=daq_instrument.SimpleAnalogIn(ai,fsample,waveform.shape[0]/float(fsample))
analog_output, wf_duration = daq_instrument.set_waveform_start(ao,waveform.reshape(1, waveform.shape[0]),sample_rate = fsample)
time.sleep(waveform.shape[0]/float(fsample))
daq_instrument.set_waveform_finish(analog_output, wf_duration)
d=ai.finish()
figure(1)
plot(d[:,0]);plot(d[:,1]);
figure(2);
plot(d[:,0])
show()
fn='c:\\visexp\\data\\ir'+str(time.time())+'.hdf5'
h=hdf5io.Hdf5io(fn)
h.data=d
h.save('data')
h.close()
pass
