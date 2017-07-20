from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.generic import signal
import numpy
from pylab import plot,show

ai='Dev1/ai3:4'
ao='Dev1/ao1'
fsample=5000#Ao max rate

def generate_sweep(f):
    duration=0.3
    a=1
    nsample=duration*fsample
    t=numpy.arange(nsample, dtype=numpy.float)/fsample
    tf=[]
    for fi in f:
        print fi
        wf=a*numpy.sin(numpy.pi*2*fi*t)+a
        aih=daq_instrument.SimpleAnalogIn(ai, fsample, duration)
        daq_instrument.set_waveform( ao,wf.reshape(1, wf.shape[0]),sample_rate = fsample)
        aidata=aih.finish()
        amp_in, frq=signal.measure_sin(aidata[:,0],fsample, p0=[1, fi, 0, a])
        amp_out, frq=signal.measure_sin(aidata[:,1],fsample, p0=[1, fi, 0, a])
        gain=10*numpy.log10(abs(amp_out/amp_in))
        tf.append([fi, gain])
    tf=numpy.array(tf)
    semilogx(tf[:, 0], tf[:, 1], 'o-')
    show()
    
def test_pwm():
    pw1=0.2
    pw2=0.7
    pw_frq=1000
    duration=1.0
    nsamples_period=1./pw_frq*fsample
    npulses=int(duration*fsample/nsamples_period)
    
    wf1=numpy.tile(numpy.concatenate((numpy.ones(nsamples_period*pw1), numpy.zeros(nsamples_period*(1-pw1)))), npulses)
    wf2=numpy.tile(numpy.concatenate((numpy.ones(nsamples_period*pw2), numpy.zeros(nsamples_period*(1-pw2)))), npulses)
    wf=numpy.concatenate((wf1, wf2))
    
    aih=daq_instrument.SimpleAnalogIn(ai, fsample, duration*2)
    daq_instrument.set_waveform( ao,wf.reshape(1, wf.shape[0]),sample_rate = fsample)
    aidata=aih.finish()
    t=numpy.arange(aidata[:, 0].shape[0], dtype=numpy.float)/fsample
    plot(t, aidata[:, 0])
    plot(t, aidata[:, 1])
    show()
    
    
    
if __name__ == "__main__":
    test_pwm()
    #generate_sweep(numpy.linspace(10,1000,15))
