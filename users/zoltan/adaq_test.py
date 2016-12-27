from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.generic import signal
import numpy, serial, time
from pylab import *

ai='Dev1/ai3:4'
ao='Dev1/ao1'
fsample=5000#Ao max rate

ontime=5e-3
offtime=10e-3
duration=20.0
amp=5
if __name__=='__main__':
    reps=int(duration/(ontime+offtime))
    wf=amp*numpy.concatenate((numpy.ones(int(ontime*fsample)), numpy.zeros(int(offtime*fsample))))
    wf=numpy.tile(wf, reps)
    #wf[-1]=5

    #s=serial.Serial('COM8','115200',  timeout=0.1)
    #time.sleep(100e-3)
    #s.flushInput()
    #time.sleep(100e-3)
    #s.write('e')
    #s.write('e')
    #print s.read(1)
    #print s.read(8000)
    #time.sleep(100e-3)
    buf=''
    analog_output, wf_duration = daq_instrument.set_waveform_start(ao,wf.reshape(1, wf.shape[0]),sample_rate = fsample)
    
#    for i in range(int(duration)*10):
#        buf+=s.read(100)
    time.sleep(duration)
#    print len(buf)
    daq_instrument.set_waveform_finish(analog_output, wf_duration)
    #s.write('d')
#    s.close()
#    plot(numpy.where(numpy.fromstring(buf,dtype=numpy.uint8) & 0x04==0,0,1))
#    show()
