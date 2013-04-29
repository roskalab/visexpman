import time
import numpy
from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.hardware_interface import camera_interface
from visexpman.engine.generic import configuration
class TestConfig(configuration.Config):
    def _create_application_parameters(self):
        self.CAMERA_FRAME_RATE = 30.0
        VIDEO_FORMAT = 'RGB24 (744x480)'
        DAQ_CONFIG = [
        {
        'ANALOG_CONFIG' : 'ao',
        'DAQ_TIMEOUT' : 2.0, 
        'AO_SAMPLE_RATE' : 40000,
        'AO_CHANNEL' : 'Dev1/ao1',
        'MAX_VOLTAGE' : 8.0,
        'MIN_VOLTAGE' : -8.0,
        'DURATION_OF_AI_READ' : 2.0,
        'ENABLE' : True
        },
        ]
        self._create_parameters_from_locals(locals())
if __name__ == "__main__":
    duration = 1
    f = [500, 800, 1000, 1500, 2000, 2200]
    f = [10, 100]
#    f = numpy.logspace(2,4,5)
    A = 2.0
    config = TestConfig()
    cam = camera_interface.ImagingSourceCamera(config)
    aio = daq_instrument.AnalogIO(config)
    fs = aio.ao_sample_rate
    t = numpy.linspace(0, duration,  duration*fs, False)
    signal = numpy.zeros(t.size*len(f))
    for i in range(len(f)):
        signal_i = 0.5*A*numpy.sin(2*numpy.pi*t*f[i])
        signal[signal_i.size*i:signal_i.size*(i+1)] = signal_i
    import copy
    signal[-1] = 0
    aio.waveform = copy.deepcopy(signal)
    cam.start()
    aio.start_daq_activity()
    for i in range(int(len(f)*duration*config.CAMERA_FRAME_RATE)):
        cam.save()
    cam.stop()
    cam.close()
#    time.sleep(len(f)*duration)
    aio.release_instrument()
    print cam.video.shape
#    from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
#    t = numpy.linspace(0,  len(f)*duration,  len(f)*duration*fs, False)
#    plot(t, signal)
#    show()
