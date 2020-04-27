'''
Classes related to two photon scanning:
    Waveform generator
    DAQ process for data acquisition

'''

import numpy, unittest, pdb, itertools,multiprocessing,time,os
from visexpman.engine.generic import utils
from visexpman.engine.hardware_interface import instrument,daq
import PyDAQmx
import PyDAQmx.DAQmxConstants as DAQmxConstants
import PyDAQmx.DAQmxTypes as DAQmxTypes

class ScannerWaveform(object):
    '''
    '''
    MIN_SAMPLES_X_FLYBACK=10
    IMAGING_FRAME_RATE_RANGE=[0.1, 100.0]
    #Depends on computer RAM 
    MAX_FRAME_PIXELS=500e3 
    #Depends on scanner model
    MIN_X_SCANNER_PERIOD=1/3000#TODO: this limitation should depend on scan area width. Lower widths work on higher frequencies
    SCANNER_VOLTAGE_RANGE=[0.05, 5.0]
    
    def __init__(self, machine_config=None,  **kwargs):
        if hasattr(machine_config, 'AO_SAMPLE_RATE'):
            self.fsample=machine_config.AO_SAMPLE_RATE
        else:
            self.fsample=kwargs['fsample']
        for pn in ['SCAN_VOLTAGE_UM_FACTOR',  'PROJECTOR_CONTROL_VOLTAGE', 'FRAME_TIMING_PULSE_WIDTH']:
            if hasattr(machine_config, pn):
                setattr(self,  pn.lower(), getattr(machine_config, pn))
            else:
                setattr(self,  pn.lower(), kwargs[pn.lower()])
            
    def generate(self,  height, width, resolution, xflyback, yflyback=2, pulse_width=0, pulse_phase=0):
        '''
        Generates x, y scanner waveforms, timing signal for projector and imaging frame timing pulses.
        height: height of scan area in um
        width: width of scan area in um
        resolution: number of pixels/um
        xflyback: x scanner flyback time in % of x sweep time
        yflyback: flyback time of y scanner in x sweep units.
        pulse_width: pulse width for triggering projector in us
        pulse_phase: projector trigger's phase relative to the start of x flyback in us
        
        '''
        if yflyback<1:
            raise ValueError('minimum value for y_flyback_lines is 1')
        line_length = int(utils.roundint(width * resolution)*(1+xflyback*1e-2))  # Number of samples for scanning a line
        if line_length/self.fsample<self.MIN_X_SCANNER_PERIOD:
            raise ValueError("X line length is too short, increase resolution or scan area width")
        return_x_samps=int(utils.roundint(width * resolution)*(xflyback*1e-2))
        if return_x_samps<self.MIN_SAMPLES_X_FLYBACK:
            raise ValueError('X flyback time is too short, number of flyback samples is {0}'.format(return_x_samps))
        if pulse_width*self.fsample<1 and pulse_width>0:
            raise ValueError('Projector control pulse width is too short')
        return_y_samps = line_length* yflyback
        n_x_lines= utils.roundint(height * resolution)+yflyback
        # X signal
        ramp_up_x = numpy.linspace(-0.5*width, 0.5*width, num=line_length - return_x_samps)
        ramp_down_x = numpy.linspace(0.5*width, -0.5*width, num=return_x_samps + 2)[1:-1] # Exclude extreme values (avoiding duplication during concatenation)
        line_scan_x= numpy.concatenate((ramp_up_x,  ramp_down_x))
        scan_mask=numpy.concatenate((numpy.ones_like(ramp_up_x), numpy.zeros_like(ramp_down_x)))
        waveform_x = numpy.tile(line_scan_x, n_x_lines)
        imaging_period=round(self.fsample/waveform_x.shape[0], 1)
        if imaging_period<self.IMAGING_FRAME_RATE_RANGE[0] or imaging_period>self.IMAGING_FRAME_RATE_RANGE[1]:
            raise ValueError('Imaging period ({0:0.2f} Hz does not fall into {1} range'.format(imaging_period,  self.IMAGING_FRAME_RATE_RANGE))
        scan_mask= numpy.tile(scan_mask, n_x_lines-yflyback)
        scan_mask=numpy.pad(scan_mask, (0,waveform_x.shape[0]-scan_mask.shape[0]), 'constant')
        # Y signal
        ramp_up_y = numpy.linspace(-0.5*height, 0.5*height, num=waveform_x.shape[0] - return_y_samps)
        ramp_down_y = numpy.linspace(0.5*height, -0.5*height, num=return_y_samps+1) # Exclude maximum value
        waveform_y = numpy.concatenate((ramp_up_y, ramp_down_y[1:]))
        #Scale to V
        waveform_y*=self.scan_voltage_um_factor
        waveform_x*=self.scan_voltage_um_factor
        if abs(waveform_x).max()<self.SCANNER_VOLTAGE_RANGE[0] or abs(waveform_x).max()>self.SCANNER_VOLTAGE_RANGE[1]:
            raise ValueError('Max scanner voltage ({0} V) is beyond working range ({1})'.format(waveform_x.max(),  self.SCANNER_VOLTAGE_RANGE))
        if abs(waveform_y).max()<self.SCANNER_VOLTAGE_RANGE[0] or abs(waveform_y).max()>self.SCANNER_VOLTAGE_RANGE[1]:
            raise ValueError('Max scanner voltage ({0} V) is beyond working range ({1})'.format(waveform_y.max(),  self.SCANNER_VOLTAGE_RANGE))
        # Projector control
        phase_nsamples  = utils.roundint(pulse_phase * self.fsample)
        pulse_width_nsamples = utils.roundint(pulse_width*self.fsample)
        if phase_nsamples  > ramp_down_x.shape[0]:
            raise ValueError('Phase ({0}) cannot exceed x flyback ({1})'.format(phase_nsamples, ramp_down_x.shape[0]))
        off_nsamples=ramp_down_x.shape[0]-phase_nsamples -pulse_width_nsamples 
        if off_nsamples<0:
            off_nsamples=0
        projector_control =numpy.tile(numpy.concatenate((numpy.zeros(ramp_up_x.shape[0]+phase_nsamples), numpy.full(pulse_width_nsamples,  self.projector_control_voltage),  numpy.zeros(off_nsamples))), n_x_lines)
        frame_timing=numpy.zeros_like(projector_control)
        frame_timing[-utils.roundint(self.fsample*self.frame_timing_pulse_width):]=self.projector_control_voltage
        #Calculate indexes for extractable parts of pmt signal
        boundaries = numpy.nonzero(numpy.diff(scan_mask))[0]+1
        boundaries=numpy.insert(boundaries, 0, 0)
        if scan_mask.sum()>self.MAX_FRAME_PIXELS:
            raise ValueError('Too many pixels to scan: {0}, limit {1}'.format(scan_mask.sum(),  self.MAX_FRAME_PIXELS))
        frame_timing[-1]=0
        projector_control[-1]=0
        return waveform_x,  waveform_y, projector_control,  frame_timing,  boundaries
        
def binning_data(data, factor):
    '''
    data: two dimensional pmt data : 1. dim: pmt signal, 2. dim: channel
    '''
    return numpy.reshape(data, (int(data.shape[0]/factor), factor, data.shape[1])).mean(1)

def rawpmt2image(rawdata, boundaries, binning_factor=1,  offset = 0):
    binned_pmt_data = binning_data(rawdata, binning_factor)
    if offset != 0:
        binned_pmt_data = numpy.roll(binned_pmt_data, -offset)
    return numpy.array((numpy.split(binned_pmt_data, boundaries)[0::2]))
    
class SyncAnalogIORecorder(daq.SyncAnalogIO, instrument.InstrumentProcess):
    """
    Queue interface for process control
    Logger interface
    File saving
    Waveform generator+data acquisition synchronized
    
    """
    def __init__(self, ai_channels,  ao_channels, logger, **kwargs):
        self.queues={'command': multiprocessing.Queue(), 'response': multiprocessing.Queue(), 'data': multiprocessing.Queue()}
        instrument.InstrumentProcess.__init__(self, 'daq', self.queues, logger)
        daq.SyncAnalogIO.__init__(self,  ai_channels,  ao_channels,  kwargs['timeout'])
        self.kwargs=kwargs
        
    def start(self):
        instrument.InstrumentProcess.start(self)
        
    def start_(self, waveform, filename):
        self.queues['command'].put(('start', waveform, filename))
        
    def stop(self):
        self.queues['command'].put(('stop',))
        
    def open_shutter(self):
        value=1
        self.digital_output.WriteDigitalLines(1,
                                    True,
                                    1.0,
                                    DAQmxConstants.DAQmx_Val_GroupByChannel,
                                    numpy.array([int(value)], dtype=numpy.uint8),
                                    None,
                                    None)
        self.printl('Shutter opened')
        
    def close_shutter(self):
        value=0
        self.digital_output.WriteDigitalLines(1,
                                    True,
                                    1.0,
                                    DAQmxConstants.DAQmx_Val_GroupByChannel,
                                    numpy.array([int(value)], dtype=numpy.uint8),
                                    None,
                                    None)
        self.printl('Shutter closed')
        
    def run(self):
        try:
            self.digital_output = PyDAQmx.Task()
            self.digital_output.CreateDOChan(self.kwargs['shutter_port'],'do', DAQmxConstants.DAQmx_Val_ChanPerLine)
            self.create_channels()
            ct=0
            self.running=False
            while True:
                if not self.queues['command'].empty():
                    cmd=self.queues['command'].get()
                    self.printl(cmd)
                    if cmd[0]=='start':
                        waveform=cmd[1]
                        filename=cmd[2]
                        #TODO: create file
                        daq.SyncAnalogIO.start(self,  self.kwargs['ai_sample_rate'], self.kwargs['ao_sample_rate'],  waveform)
                        self.printl('Started to save to {0}'.format(filename))
                        self.open_shutter()
                        self.running=True
                    elif cmd[0]=='stop':
                        self.printl("Terminate recording")
                        time.sleep(3)
                        self.close_shutter()
                        readout=daq.SyncAnalogIO.stop(self)
                        self.running=False
                        break
                    else:
                        self.printl("Unknown command: {0}".format(cmd))
                        #TODO: save readout and close file
                if self.running:
                    data_chunk=self.read()
                    if ct%self.kwargs['display_rate']==0:
                        self.queues['data'].put(data_chunk)
                time.sleep(0.1)
            
            
            #Clean up
            self.digital_output.ClearTask()
        except:
            import traceback
            self.printl(traceback.format_exc())


        
class Test(unittest.TestCase):
    def test_recorder_process(self):
        from visexpman.engine.generic import log,fileop
        logfile=r'f:\tmp\log.txt'
        if os.path.exists(logfile):
            os.remove(logfile)
        logger=log.Logger(filename=logfile)
        logger.add_source('daq')
        logger.start()
        recorder=SyncAnalogIORecorder('Dev1/ai14:15','Dev1/ao0:1',logger,timeout=1,ai_sample_rate=800e3,ao_sample_rate=400e3,
                        shutter_port='Dev1/port0/line0',display_rate=3)
        recorder.start()
        filename=r'f:\tmp\2pdata.hdf5'
        waveform=numpy.array([numpy.linspace(1,2,50000), numpy.linspace(3,2,50000)])
        time.sleep(0.5)
        recorder.start_(waveform,filename)
        time.sleep(2)
        recorder.stop()
        time.sleep(1)
        self.assertFalse(recorder.queues['data'].empty())
        while not recorder.queues['data'].empty():
            readout=recorder.queues['data'].get()
            numpy.testing.assert_almost_equal(waveform,readout[:,1::2],2)
        self.assertFalse('error' in fileop.read_text_file(logfile).lower())
        #TODO: check datafile
        logger.flush()
        logger.terminate()
    
    
    
    @unittest.skip('')
    def test_waveform_generator(self):
        #Input parameter ranges
        from pylab import plot, show
        height=[10, 50, 100, 200, 500]
        width=[10, 50, 100, 200, 500]
        resolution=[0.1, 0.5,  1,  3, 10]
        xflyback=[0, 2, 10, 20, 100]
        yflyback=[0, 1, 2, 10]
        pulse_width=numpy.array([0,1, 10, 100, 1000])*1e-6
        pulse_phase=numpy.array([0,1, 10, 100, 500])*1e-6
        fsample=[10e3, 100e3, 400e3, 1e6]
        scan_voltage_um_factor=1/128.
        frame_timing_pulse_width=1e-3
        import itertools
        par1=[pars for pars in itertools.product(height,width,resolution,xflyback,yflyback,pulse_width,pulse_phase,fsample) if pars[3]==0][0]
        params=[pars for pars in itertools.product(height,width,resolution,xflyback,yflyback,pulse_width,pulse_phase,fsample) if pars[3]!=0]
        par2=[pars for pars in params if pars[4]==0][0]
        params=[pars for pars in params if pars[4]!=0]
        par3=[pars for pars in params if pars[-3]==1000*1e-6][0]
        params=[pars for pars in params if pars[-3]!=1000*1e-6]
        par4=[pars for pars in params if pars[-2]==500*1e-6][0]
        params=[pars for pars in params if pars[-2]!=500*1e-6]
        params.extend([par1, par2, par3, par4])
#        params=[(50, 50, 0.5, 100, 1, 0.0, 0.0, 10000.0)]
        for height,width,resolution,xflyback,yflyback,pulse_width,pulse_phase,fsample in params:
            sw=ScannerWaveform(fsample=fsample, scan_voltage_um_factor=scan_voltage_um_factor, projector_control_voltage=3.3, frame_timing_pulse_width=frame_timing_pulse_width)
            xsamples=int(round(width*resolution))
            waveform_length=(((xsamples)*(1+xflyback/100))*(height*resolution+yflyback))
            if waveform_length==0:
                fimg=1e6
            else:
                fimg=numpy.round(fsample/waveform_length, 1)
            npixels=height*resolution*width*resolution
            scanner_voltage=min(height/2, width/2)*scan_voltage_um_factor
            pars=(height,width,resolution,xflyback,yflyback,pulse_width,pulse_phase,fsample)
            print((params.index(pars),  len(params), pars))
            if yflyback<1 or \
                    xsamples/fsample*(1+xflyback*1e-2) < sw.MIN_X_SCANNER_PERIOD or \
                    xsamples*xflyback/100<sw.MIN_SAMPLES_X_FLYBACK  or \
                    fimg<sw.IMAGING_FRAME_RATE_RANGE[0] or fimg>sw.IMAGING_FRAME_RATE_RANGE[1] or\
                    scanner_voltage<sw.SCANNER_VOLTAGE_RANGE[0] or scanner_voltage>sw.SCANNER_VOLTAGE_RANGE[1] or\
                    xflyback*xsamples*1e-2<pulse_phase*fsample or\
                    npixels>sw.MAX_FRAME_PIXELS or\
                    (pulse_width*fsample<1 and pulse_width>0):
                try:
                    with self.assertRaises(ValueError):
                        sw.generate(height, width, resolution, xflyback, yflyback, pulse_width, pulse_phase)
                except:
                    print((height,width,resolution,xflyback,yflyback,pulse_width,pulse_phase,fsample))
                    pdb.set_trace()
            else:
                try:
                    waveform_x,  waveform_y, projector_control,  frame_timing,  boundaries= sw.generate(height, width, resolution, xflyback, yflyback, pulse_width, pulse_phase)
                    self.assertEqual(projector_control[0], 0)
                    self.assertEqual(projector_control[-1], 0)
                    self.assertEqual(frame_timing[0], 0)
                    self.assertEqual(frame_timing[-1], 0)
                    self.assertEqual(frame_timing.max(), sw.projector_control_voltage)
                    if pulse_width>0:
                        self.assertLess(abs(numpy.nonzero(projector_control)[0].shape[0]-(height*resolution+yflyback)*pulse_width*fsample), 5)
                    else:
                        self.assertEqual(projector_control.sum(), 0)
                    self.assertEqual(boundaries.shape[0]/2, height*resolution) #number of boundaries corresond to number y lines
                    self.assertEqual(numpy.diff(boundaries)[::2][0], width*resolution)#spacing between boundaries correspond to number of lines
                    self.assertEqual(numpy.diff(boundaries)[::2].std(), 0)
                    #Check y scanner signal
                    self.assertTrue(len(set(numpy.sign(waveform_y)))>1)#Is it bipolar signal?
                    extremes=numpy.nonzero(numpy.round(numpy.diff(numpy.diff(waveform_y)),10))[0]
                    self.assertEqual(extremes.shape[0], 1)#There is only one extreme
                    self.assertLess(numpy.diff(waveform_y[0:extremes[0]]).std(), 1e-6)#Does ramp up rate constant?
                    self.assertLess(numpy.diff(waveform_y[extremes[0]+1:-1]).std(), 1e-6)#Does ramp down rate constant?
                    #Check x scanner signal
                    extremes=numpy.nonzero(numpy.round(numpy.diff(numpy.diff(waveform_x)),4))[0]
                    nxlines=height*resolution+yflyback
                    self.assertEqual(extremes.shape[0], nxlines*2-1)
                    self.assertTrue(len(set(numpy.sign(waveform_x)))>1)#Is it bipolar signal?
                    rates=list(map(numpy.diff, numpy.split(waveform_x,extremes+1)))
                    for ri in rates:
                        self.assertLess(ri.std(), 1e-6)
                except:
                    pdb.set_trace()
                
    @unittest.skip('')
    def test_rawpmt2img(self):
        '''
        Generate valid scanning waveforms and feed them as raw pmt signals
        '''
        height=[20, 50, 100, 300]
        width=[20, 50, 100, 300]
        resolution=[0.5,  1,  5]
        xflyback=[20, 50]
        yflyback=[1, 2]
        pulse_width=numpy.array([0])*1e-6
        pulse_phase=numpy.array([0])*1e-6
        fsample=[100e3, 400e3, 1e6]
        scan_voltage_um_factor=1/128.
        frame_timing_pulse_width=1e-3
        params=[pars for pars in itertools.product(height,width,resolution,xflyback,yflyback,pulse_width,pulse_phase,fsample)]
        params=[pi for pi in params if pi[0]*pi[2]>90]
        for height,width,resolution,xflyback,yflyback,pulse_width,pulse_phase,fsample in params:
            try:
                sw=ScannerWaveform(fsample=fsample, scan_voltage_um_factor=scan_voltage_um_factor, projector_control_voltage=3.3, frame_timing_pulse_width=frame_timing_pulse_width)
                try:
                    waveform_x, waveform_y, projector_control, frame_timing, boundaries= sw.generate(height, width, resolution, xflyback, yflyback, pulse_width, pulse_phase)
                except ValueError:
                    import traceback
                    if 'X line length is too short' not in traceback.format_exc() and 'Too many pixels to scan:' not in traceback.format_exc() and 'does not fall into' not in traceback.format_exc():
                        raise RuntimeError()
                pmt=numpy.array([waveform_x,  waveform_y]).T
                img=rawpmt2image(pmt, boundaries[1:], binning_factor=1,  offset = 0)
                self.assertLess(numpy.diff(img[:,:,0].mean(axis=0)).std(), 1e-6)#All lines are same
                self.assertTrue((numpy.diff(img[:,:,0].mean(axis=0))>0).all())#check uniform gradient
                self.assertLess(numpy.diff(img[:,:,1].mean(axis=1)).std(), 1e-6)
                self.assertTrue((numpy.diff(img[:,:,1].mean(axis=1))>0).all())
            except:
                pass

if __name__ == "__main__":
    unittest.main()
