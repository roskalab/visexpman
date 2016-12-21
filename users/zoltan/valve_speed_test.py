from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.generic import signal
import numpy, time, hdf5io,os
from pylab import *

ai='Dev1/ai1:2'
ao='Dev1/ao1'
fsample=1000#Ao max rate
opentime=100e-3
offtime=0.2
repeats=10

def measure():
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

def process():
    folder='/home/rz/mysoftware/data/'
    files=[os.path.join(folder,f) for f in os.listdir(folder) if os.path.splitext(f)[1]=='.hdf5']
    import scipy.signal
    lowpass=scipy.signal.bessel(2,500/float(fsample),'low')
    pulses=[]
    for f in files:
        data=hdf5io.read_item(f,'data')
        indexes=numpy.where(numpy.diff(numpy.where(data[:,1]>2.5,1,0))==1)[0]+1
        for i in indexes:
            start=i#-int(offtime*fsample)
            end=i+int((opentime+offtime)*fsample)
            pulses.append(data[start:end])
    ct=1
    first_peak=[]
    last_peak=[]
    figure(1)
    for p in pulses:
        #subplot(len(pulses)/5,5,ct%5+1)
        ct+=1
        t=numpy.arange(p.shape[0])/float(fsample)*1000
        lowpassfiltered=scipy.signal.filtfilt(lowpass[0],lowpass[1], p[:,0]).real
        #lowpassfiltered=p[:,0]
        plot(t,lowpassfiltered-lowpassfiltered.mean()+ct/5*.01)
        xlabel('ms')
        first_peak.append(t[lowpassfiltered.argmax()])
        last_peak.append(t[lowpassfiltered.argmin()])
        #plot(t,p[:,1])
        pass
    figure(2)
    plot(first_peak,'o')
    plot(last_peak,'o')
    legend(['first peak', 'last peak'])
    ylabel('ms')
    show()
    pass
if __name__ == "__main__":
    process()
