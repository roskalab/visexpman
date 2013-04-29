import time
import numpy
from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.hardware_interface import camera_interface
from visexpman.engine.generic import configuration
from visexpman.engine.generic import file
class TestConfig(configuration.Config):
    def _create_application_parameters(self):
        self.CAMERA_FRAME_RATE = 30.0
        VIDEO_FORMAT = 'RGB24 (744x480)'
        DAQ_CONFIG = [
        {
        'ANALOG_CONFIG' : 'ao',
        'DAQ_TIMEOUT' : 2.0, 
        'AO_SAMPLE_RATE' : 40000,
        'AO_CHANNEL' : 'Dev1/ao0',
        'MAX_VOLTAGE' : 8.0,
        'MIN_VOLTAGE' : -8.0,
        'DURATION_OF_AI_READ' : 2.0,
        'ENABLE' : True
        },
        ]
        self._create_parameters_from_locals(locals())
        
class ScannerCalibration(camera_interface.ImagingSourceCamera, daq_instrument.AnalogIO):
    def __init__(self, config):
        camera_interface.ImagingSourceCamera.__init__(self, config)
        daq_instrument.AnalogIO.__init__(self, config)
        self.f = [100, 1000]
        self.A = [1, 2]
        self.duration = 0.5
        self.generate_signal(self.f, self.A, self.duration)
        
    def generate_signal(self, f, A, duration):
        self.t = numpy.linspace(0, duration,  duration*self.ao_sample_rate, False)
        signal = numpy.zeros(self.t.size*len(f)*len(A))
        for i in range(len(A)):
            for j in range(len(f)):
                signal_i = 0.5*A[i]*numpy.sin(2*numpy.pi*self.t*f[j])
                index = len(f)*i+j
                signal[signal_i.size*index:signal_i.size*(index+1)] = signal_i
        signal[-1] = 0.0
        self.waveform = signal
        
    def run(self):
        camera_interface.ImagingSourceCamera.start(self)
        self.start_daq_activity()
        for i in range(int(len(self.A)*len(self.f)*self.duration*config.CAMERA_FRAME_RATE)):
            camera_interface.ImagingSourceCamera.save(self)
        
    def close(self):
        daq_instrument.AnalogIO.release_instrument(self)
        camera_interface.ImagingSourceCamera.stop(self)
        camera_interface.ImagingSourceCamera.close(self)
        self.process_data()
        
    def process_data(self):
        import tiffile
        tiffile.imsave(file.generate_filename('c:\\_del\\calib.tiff'), self.video, software = 'visexpman')
        from visexpA.engine.datahandlers import hdf5io
        hdf5io.save_item(file.generate_filename('c:\\_del\\calib.hdf5'), 'data', self.video, filelocking = False)
        
    
if __name__ == "__main__":
    config = TestConfig()
    sc = ScannerCalibration(config)
    sc.run()
    sc.close()
