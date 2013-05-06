from matplotlib.pyplot import plot, show,figure,legend, savefig, subplot, title
from visexpman.engine.hardware_interface import scanner_control
from visexpA.engine.datahandlers import hdf5io
import Image
from visexpA.engine.dataprocessors.generic import normalize
import os
import os.path
from visexpman.engine.generic import utils
import time
import numpy
from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.hardware_interface import camera_interface
from visexpman.engine.generic import configuration
from visexpman.engine.generic import file

class TestConfig(configuration.Config):
    def _create_application_parameters(self):
        self.F = [20.0, 40.0, 80.0, 100.0, 150.0, 200.0, 250.0, 400.0, 500.0, 700.0, 850.0, 1000.0, 1200.0, 1500.0, 1700.0, 1800.0, 1900.0, 2000.0, 2100.0, 2200.0, 2400.0, 2450.0, 2500.0, 2600.0, 2700.0, 2800.0, 2900.0, 3000.0]
        self.F = numpy.array(self.F*2).reshape((2, len(self.F))).flatten('F')
        self.F[::2] = 0
        self.F = self.F.tolist()
        self.F.append(0)
        self.A = [100/128.0*2]#100 um
        self.DURATION = 3.0
        self.CAMERA_FRAME_RATE = 30.0
        VIDEO_FORMAT = 'RGB24 (320x240)'
        self.PREPOST_DELAYS = 2.0
        DAQ_CONFIG = [
        {
        'ANALOG_CONFIG' : 'ao',
        'DAQ_TIMEOUT' : 2.0, 
        'AO_SAMPLE_RATE' : 400000,
        'AO_CHANNEL' : 'Dev1/ao0:1',
        'MAX_VOLTAGE' : 8.0,
        'MIN_VOLTAGE' : -8.0,
        'DURATION_OF_AI_READ' : 2.0,
        'AO_SAMPLING_MODE' : 'finite', 
        'ENABLE' : True
        },
        ]
        self._create_parameters_from_locals(locals())

class ScannerCalibration(camera_interface.ImagingSourceCamera, daq_instrument.AnalogIO):
    def __init__(self, config):
        camera_interface.ImagingSourceCamera.__init__(self, config)
        daq_instrument.AnalogIO.__init__(self, config)
#        self.generate_square_signal(self.A, self.duration)
        self.generate_signal(self.config.F, self.config.A, self.config.DURATION)
        
    def generate_signal(self, f, A, duration, two_channel = False):
        self.t = numpy.linspace(0, duration,  duration*self.ao_sample_rate, False)
        signal0 = numpy.zeros(self.t.size*len(f)*len(A))
        signal1 = numpy.zeros(self.t.size*len(f)*len(A))
        for i in range(len(A)):
            for j in range(len(f)):
                if f[j] == 0:
                    signal_i0 = numpy.zeros_like(self.t)
                    signal_i1 = numpy.zeros_like(self.t)
                else:
                    signal_i0 = 0.5*A[i]*numpy.sin(2*numpy.pi*self.t*f[j])
                    if two_channel:
                        signal_i1 = 0.5*A[i]*numpy.cos(2*numpy.pi*self.t*f[j])
                    else:
                        signal_i1 = numpy.zeros_like(self.t)
                index = len(f)*i+j
                signal0[signal_i0.size*index:signal_i0.size*(index+1)] = signal_i0
                signal1[signal_i1.size*index:signal_i1.size*(index+1)] = signal_i1
        self.waveform = numpy.array([signal0, signal1]).T
        from matplotlib.pyplot import plot, show
#        plot(self.waveform[:,0])
#        plot(self.waveform[:,1])
#        show()
        pass
        
    def generate_square_signal(self, A, duration):
        self.waveform = numpy.zeros(duration*self.ao_sample_rate)
        self.waveform[0.1*self.waveform.shape[0]:0.6*self.waveform.shape[0]] = A

    def run(self):
        camera_interface.ImagingSourceCamera.start(self)
        self.start_daq_activity()
        for i in range(int((len(self.config.A)*len(self.config.F)*self.config.DURATION+ self.config.PREPOST_DELAYS)*config.CAMERA_FRAME_RATE)):
            camera_interface.ImagingSourceCamera.save(self)
        
    def close(self):
        self.finish_daq_activity()
        self.waveform = numpy.zeros((100, 2))#Make sure that outputs are on 0V
        daq_instrument.AnalogIO.run(self)
        daq_instrument.AnalogIO.release_instrument(self)
        camera_interface.ImagingSourceCamera.stop(self)
        camera_interface.ImagingSourceCamera.close(self)
        self.process_data()
        
    def process_data(self):
        import tiffile
        tiffile.imsave(file.generate_filename('v:\\debug\\20130503\\camcalibs\\calib.tiff'), self.video, software = 'visexpman')
        p = file.generate_filename('v:\\debug\\20130503\\camcalibs\\calib.hdf5')
        hdf5io.save_item(p, 'video', self.video, filelocking = False)
        hdf5io.save_item(p, 'config', self.config.get_all_parameters(), filelocking = False)
        
def scanner_calib():
    config = TestConfig()
    sc = ScannerCalibration(config)
    sc.run()
    sc.close()
    print 'DONE'
    
def evaluate_calibdata():
    p = '/mnt/datafast/debug/20130503/calibs'
    max_linearity_error = 10e-2
    a = []
    fi = []
    frq = []
    fs =os.listdir(p)[:-2]
    fs.reverse()
    for f in fs:
        calibdata = hdf5io.read_item(os.path.join(p, f), 'calibdata', filelocking=False)
    #    pmt = calibdata['pmt']
    #    mask = utils.resample_array(calibdata['mask'], calibdata['parameters']['binning_factor'])
        res = scanner_control.scanner_bode_diagram(calibdata['pmt'], utils.resample_array(calibdata['mask'], calibdata['parameters']['binning_factor']), calibdata['parameters']['scanner_speed'], max_linearity_error)
        a.append(res['sigmas'][0])
        fi.append(res['means'][0])
        frq.append(res['frq'][0])
    #    figure(len(frq))
        t = numpy.linspace(0, 1, res['signals'][0].shape[0])
    #    plot(t, res['signals'][0])
    #    plot(t, scanner_control.gauss(t, res['gauss_amplitudes'][0], fi[-1], a[-1]))
    #    title('{0} Hz, {1}, {2}'.format(frq[-1], fi[-1], a[-1]))
    #print frq
    figure(len(frq)+1)
    plot(frq, a/a[-1])
    plot(frq, 2*utils.sinus_linear_range(max_linearity_error)*(fi-fi[-1]))
    legend(('gain', 'phase'))
    show()

if __name__ == "__main__":
    if True:
        evaluate_calibdata()
    elif False:
        scanner_calib()
