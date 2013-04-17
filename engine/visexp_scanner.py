import time
import PyDAQmx.DAQmxConstants as DAQmxConstants
from visexpman.engine.generic import configuration
from visexpman.engine.hardware_interface import scanner_control
from visexpman.engine.generic import utils
from visexpman.engine.generic import file

class ScannerTestConfig(configuration.Config):
    def _create_application_parameters(self):
        self.SCANNER_MAX_SPEED = utils.rc((1e7, 1e7))#um/s
        self.SCANNER_MAX_ACCELERATION = utils.rc((1e12, 1e12)) #um/s2
        self.SCANNER_SIGNAL_SAMPLING_RATE = 250000 #Hz
        self.SCANNER_DELAY = 0#As function of scanner speed
        self.SCANNER_START_STOP_TIME = 0.02
        self.SCANNER_MAX_POSITION = 200.0
        self.POSITION_TO_SCANNER_VOLTAGE = 2.0/128.0
        self.XMIRROR_OFFSET = 0.0#um
        self.YMIRROR_OFFSET = 0.0#um
        self.SCANNER_RAMP_TIME = 70.0e-3
        self.SCANNER_HOLD_TIME = 30.0e-3
        self.SCANNER_SETTING_TIME = 1e-3
        self.SCANNER_TRIGGER_CONFIG = {}
        self.SCANNER_TRIGGER_CONFIG['amplitude'] = 3.3
        self.SCANNER_TRIGGER_CONFIG['offset'] = 0
        self.SCANNER_TRIGGER_CONFIG['width'] = 150e-6
        
        sample_rate = 100000*2
        DAQ_CONFIG = [
        {
        'ANALOG_CONFIG' : 'aio',
        'DAQ_TIMEOUT' : 10.0, 
        'AO_SAMPLE_RATE' : sample_rate,
        'AI_SAMPLE_RATE' : 2*sample_rate,
        'AO_CHANNEL' : 'Dev1/ao0:2',
        'AI_CHANNEL' : 'Dev1/ai0:1',
        'MAX_VOLTAGE' : 5.0,
        'MIN_VOLTAGE' : -5.0,
        'DURATION_OF_AI_READ' : 2.0,
        'ENABLE' : True, 
#        'AI_TERMINAL': DAQmxConstants.DAQmx_Val_PseudoDiff, 
        'AO_SAMPLING_MODE': 'cont', 
        },
        {
        'DAQ_TIMEOUT' : 1.0, 
        'DO_CHANNEL' : 'Dev1/port0/line0',
        'ENABLE' : True
        }
        ]
        self._create_parameters_from_locals(locals())

if __name__ == "__main__":
    config = ScannerTestConfig()
    config.SCANNER_SIGNAL_SAMPLING_RATE = config.DAQ_CONFIG[0]['AO_SAMPLE_RATE']
    lines = [
             {'p0': utils.rc((50, 0)), 'p1': utils.rc((-50, 0)), 'v': 1000.0}, 
             {'p0': utils.rc((-50, 0)), 'p1': utils.rc((50, 0)), 'v': 1000.0}, 
             ]
    lines = scanner_control.generate_test_lines(100, 1, [500, 1000, 2000, 4000])
    tp = scanner_control.TwoPhotonScanner(config)
    tp.start_rectangular_scan(utils.rc((10, 20)), spatial_resolution = 0.10, setting_time = 0.3e-3, trigger_signal_config = config.SCANNER_TRIGGER_CONFIG)
    
#    tp.start_line_scan(lines, setting_time = 20e-3)

    st=time.time()
    for j in range(int(tp.frame_rate*60)):
        for i in range(1):
            tp.read_pmt()
    print time.time()-st
    print tp.frame_rate
    tp.finish_measurement()
    tp.release_instrument()
    #Image.fromarray(normalize(tp.images[0][:,:,0],numpy.uint8)).save('v:\\debug\\pmt1.png')
    from visexpA.engine.datahandlers import hdf5io
    h = hdf5io.Hdf5io(file.generate_filename('c:\\_del\\test.hdf5'), filelocking=False)
    h.data = tp.data
    h.save('data')
    h.close()
    from matplotlib.pyplot import plot, show, figure, legend, savefig, subplot, title
    figure(1)
    plot(tp.pmt_raw[0])
    figure(2)
    plot(tp.data[0][0][:,0])
    plot(tp.data[0][0][:,1])
    figure(3)
    plot(tp.data[0][1][:,0])
    plot(tp.data[0][1][:,1])
    figure(4)
    plot(tp.scanner_positions.T)
    plot(tp.scan_mask)
    plot(tp.trigger_signal)
    show()
    #show image
    import Image
    from visexpA.engine.dataprocessors.generic import normalize
    import numpy
    Image.fromarray(normalize(tp._raw2frame(tp.pmt_raw[-1])[:, :, 0], outtype = numpy.uint8)).show()
    Image.fromarray(normalize(tp.data[9,:,:,0], outtype = numpy.uint8)).show()
    Image.fromarray(normalize(tp.data.mean(axis=0)[:,:,0], outtype = numpy.uint8)).show()
    Image.fromarray(normalize(tp.data.mean(axis=0)[:,:,1], outtype = numpy.uint8)).show()
    
