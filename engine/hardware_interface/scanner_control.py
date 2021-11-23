'''
Classes related to two photon scanning:
    Waveform generator
    DAQ process for data acquisition

'''

import numpy, unittest, pdb, itertools,multiprocessing,time,os,tables
from visexpman.engine.generic import utils, fileop
from visexpman.engine.hardware_interface import instrument,daq
try:
    import PyDAQmx
    import PyDAQmx.DAQmxConstants as DAQmxConstants
    import PyDAQmx.DAQmxTypes as DAQmxTypes
except:
    print('no pydaqmx')
    
NFRAMES_SKIP_AT_SCANNING_START=4

class ScannerWaveform(object):
    '''
    '''
    MIN_SAMPLES_X_FLYBACK=5
    IMAGING_FRAME_RATE_RANGE=[0.1, 200.0]
    #Depends on computer RAM 
    MAX_FRAME_PIXELS=500e3 
    #Depends on scanner model
    MIN_X_SCANNER_PERIOD=1./8000#TODO: this limitation should depend on scan area width. Lower widths work on higher frequencies
    SCANNER_VOLTAGE_RANGE=[0.05, 7.0]
    LINE_SCAN_EXTENSION=0.2
    SCANNER_VOLTAGE_DEG_SCALE=0.75#V/deg
    SCANNER_POSITION_VOLTAGE_DEG_SCALE=0.5#V/deg
    
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
        line_length = int(utils.roundint(width * resolution)*(1+xflyback*1e-2+self.LINE_SCAN_EXTENSION))  # Number of samples for scanning a line
        if line_length/self.fsample<self.MIN_X_SCANNER_PERIOD:
            raise ValueError(f"X line length is too short: {line_length}, increase resolution or scan area width")
        return_x_samps=int(utils.roundint(width * resolution)*(xflyback*1e-2))
        if return_x_samps<self.MIN_SAMPLES_X_FLYBACK:
            raise ValueError('X flyback time is too short, number of flyback samples is {0}'.format(return_x_samps))
        if pulse_width*self.fsample<1 and pulse_width>0:
            raise ValueError('Projector control pulse width is too short')
        yflyback=int(yflyback)
        return_y_samps = line_length* yflyback
        n_x_lines= utils.roundint(height * resolution)+yflyback
        # X signal
        ramp_up_x = numpy.linspace(-0.5*width, 0.5*width, num=line_length - return_x_samps)
        ramp_down_x = numpy.linspace(0.5*width, -0.5*width, num=return_x_samps + 2)[1:-1] # Exclude extreme values (avoiding duplication during concatenation)
        line_scan_x= numpy.concatenate((ramp_up_x,  ramp_down_x))*(1+self.LINE_SCAN_EXTENSION)
        half_extension=int((ramp_up_x.shape[0]-utils.roundint(width * resolution))/2)
        scan_mask=numpy.concatenate((numpy.zeros(half_extension),numpy.ones(utils.roundint(width * resolution)), numpy.zeros(half_extension+ramp_down_x.shape[0])))
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
#        boundaries=numpy.insert(boundaries, 0, 0)
        if scan_mask.sum()>self.MAX_FRAME_PIXELS:
            raise ValueError('Too many pixels to scan: {0}, limit {1}'.format(scan_mask.sum(),  self.MAX_FRAME_PIXELS))
        frame_timing[-1]=0
        projector_control[-1]=0
        #Generate position-pixel map, assuming that scan is zero centered
        self.x_scanner_position_start=-0.5*width
        self.x_scanner_position_end=0.5*width
        self.y_scanner_position_start=-0.5*height
        self.y_scanner_position_end=0.5*height
        nxsamples=int(width*resolution)
        nysamples=int(height*resolution)
        #Scale position to voltage: after voltage conversion it is scaled to the feedback position's scale
        scale=self.scan_voltage_um_factor*self.SCANNER_POSITION_VOLTAGE_DEG_SCALE/self.SCANNER_VOLTAGE_DEG_SCALE
        self.x_scanner_position_start*=scale
        self.x_scanner_position_end*=scale
        self.y_scanner_position_start*=scale
        self.y_scanner_position_end*=scale
        import scipy.interpolate
        self.xinterp=scipy.interpolate.interp1d([self.x_scanner_position_start, self.x_scanner_position_end], [0, nxsamples-1], bounds_error=False, fill_value='extrapolate')
        self.yinterp=scipy.interpolate.interp1d([self.y_scanner_position_start, self.y_scanner_position_end], [0, nysamples-1], bounds_error=False, fill_value='extrapolate')
        return waveform_x,  waveform_y, projector_control, frame_timing, boundaries
        
    def generate_smooth(self, height, width, resolution, xflyback, yflyback):
        def smooth(x,h):
            return x - ( smooth_core(x,h)/2+     numpy.floor(x+0.5)-0.5 )

        def smooth_core(x,h):
            return numpy.tanh((   (x+0.5)-numpy.floor(x+0.5)-0.5)*h   )
        nxscans=utils.roundint(height * resolution)+int(yflyback)
        samples_per_xscan=int(utils.roundint(width * resolution)*((100+xflyback)*1e-2+self.LINE_SCAN_EXTENSION))
        x=numpy.linspace(0,nxscans,nxscans*samples_per_xscan)
        h=20
        wf=(smooth(x,h)-0.5)*self.scan_voltage_um_factor*width
        first_zero_crossing=numpy.nonzero(numpy.diff(numpy.sign(wf)))[0][1]
        offset=int(first_zero_crossing-0.5*utils.roundint(width * resolution))
        scan_mask=numpy.zeros(samples_per_xscan)
        scan_mask[offset:offset+utils.roundint(width * resolution)]=1
        scan_mask=numpy.tile(scan_mask,nxscans )
        scan_mask[-2*samples_per_xscan:]=0
        boundaries = numpy.nonzero(numpy.diff(scan_mask))[0]+1
#        from pylab import plot, show
#        plot(wf);plot(scan_mask);show()
#        pdb.set_trace()
        
        return wf, boundaries
        
def binning_data(data, factor):
    '''
    data: two dimensional pmt data : 1. dim: pmt signal's time axis, 2. dim: channel
    '''
    return numpy.reshape(data, (int(data.shape[0]/factor), factor, data.shape[1])).mean(1)

def rawpmt2image(rawdata, boundaries, binning_factor=1,  offset = 0):
    binned_pmt_data = binning_data(rawdata, binning_factor)
    if offset != 0:
        binned_pmt_data = numpy.roll(binned_pmt_data, -offset)
    return numpy.array((numpy.split(binned_pmt_data, boundaries)[1::2]))
    
class SyncAnalogIORecorder(daq.SyncAnalogIO, instrument.InstrumentProcess):
    """
    Queue interface for process control
    Logger interface
    File saving
    Waveform generator+data acquisition synchronized
    
    """
    def __init__(self, ai_channels,  ao_channels, logfile, **kwargs):
        self.logfile=logfile
        self.queues={'command': multiprocessing.Queue(), 'response': multiprocessing.Queue(), 'data': multiprocessing.Queue(),\
                        'rawimage':multiprocessing.Queue(), 'raw':multiprocessing.Queue()}
        instrument.InstrumentProcess.__init__(self, self.queues, logfile)
        daq.SyncAnalogIO.__init__(self,  ai_channels,  ao_channels,  kwargs['timeout'])
        self.kwargs=kwargs
        self.data_range_max=10
        self.data_range_min=0
        self.acquistion_rate=3
        self.max_val=2**16-1
        self.to16bit=1/(self.data_range_max-self.data_range_min)*self.max_val
        
    def start(self):
        instrument.InstrumentProcess.start(self)
        
    def start_(self, waveform, filename, data_format,offset=0):
        """
        data_format: dictionary containing channels to be saved and boundaries
        """
        self.queues['command'].put(('start', waveform, filename, data_format, offset))
        
    def stop(self):
        self.queues['command'].put(('stop',))
        
    def read(self):
        if not self.queues['data'].empty():
            return self.queues['data'].get()
            
    def read_rawimage(self):
        if not self.queues['rawimage'].empty():
            return self.queues['rawimage'].get()
        
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
    
    def data2file(self,readout):
        #Scale readout
        clipped=numpy.clip(readout[:2],self.data_range_min,self.data_range_max)
        scaled=numpy.cast['uint16'](clipped*self.to16bit)
        if self.frame_chunk_size>1:
            split_data=numpy.split(scaled, (numpy.arange(self.frame_chunk_size,dtype=numpy.int)*int(readout.shape[1]/self.frame_chunk_size))[1:],axis=1)
        else:
            split_data=[scaled]
        for chunk_ in split_data:
            if 'channels' in self.data_format:
                scaled=chunk_[self.data_format['channels']]
                image=rawpmt2image(chunk_.T, self.data_format['boundaries']+self.offset, binning_factor=self.binning_factor,  offset = 0)
            else:
                image=chunk_[None,:]
            if hasattr(self,'data_handle'):
                self.data_handle.append(image[None,:])
                self.raw_data_handle.append(readout[None,:])
                
        #Scale back to 0..1 range
        #The 1- is a hack here. TODO: check if raw PMT signal is inverted
        imgs=image/self.to16bit
        self.rawimage=imgs
        image_display=(1-imgs)/1
        #self.printl((self.number_of_ai_samples, image_display.shape, readout.shape, self.data_format))
        return image_display
        
    def run(self):
        try:
            self.setup_logger()
            self.printl(f'pid: {os.getpid()}')
            self.digital_output = PyDAQmx.Task()
            self.digital_output.CreateDOChan(self.kwargs['shutter_port'],'do', DAQmxConstants.DAQmx_Val_ChanPerLine)
            self.create_channels()
            self.running=False
            tlast=time.time()
            frame_counter=0
            while True:
                now=time.time()
                if now-tlast>10:
                    self.printl('Alive')
                    tlast=now
                if not self.queues['command'].empty():
                    cmd=self.queues['command'].get()
                    self.printl(cmd)
                    if cmd[0]=='start':
                        waveform=cmd[1]
                        filename=cmd[2]
                        self.data_format=cmd[3]
                        self.offset=cmd[4]
                        self.binning_factor=int(self.kwargs['ai_sample_rate']/self.kwargs['ao_sample_rate'])
                        if filename is not None:
                            fh=tables.open_file(filename,'w')
                            datacompressor = tables.Filters(complevel=5, complib='zlib', shuffle = 1)
                            if self.data_format=={}:
                                datatype = tables.UInt16Atom((1, 2, int(waveform.shape[1]*self.binning_factor)))
                            elif 'boundaries' in self.data_format:
                                image_width=int(numpy.diff(self.data_format['boundaries'])[0])
                                image_height=int(self.data_format['boundaries'].shape[0]/2)
                                datatype = tables.UInt16Atom((image_height, image_width, len(self.data_format['channels'])))
                                rawdatatype=tables.Float32Atom((4, int(waveform.shape[1]*self.binning_factor)))
                            self.data_handle=fh.create_earray(fh.root, 'twopdata', datatype, (0,),filters=datacompressor)
                            self.raw_data_handle=fh.create_earray(fh.root, 'raw', rawdatatype, (0,),filters=datacompressor)
                            if 'metadata' in self.data_format:
                                for k, v in self.data_format['metadata'].items():
                                    setattr(fh.root.twopdata.attrs,k,v)
                        else:
                            if hasattr(self, 'data_handle'):
                                del self.data_handle
                        frame_rate= self.kwargs['ao_sample_rate']/waveform.shape[1]
                        self.frame_chunk_size=1#int(numpy.ceil(frame_rate/self.acquistion_rate))
                        self.printl(f'frame_chunk_size is {self.frame_chunk_size}')
                        waveform=numpy.tile(waveform,self.frame_chunk_size)
                        self.waveform=waveform
                        bt=waveform.shape[1]/self.kwargs['ao_sample_rate']
                        self.printl(f'buffer time is {bt}')
                        daq.SyncAnalogIO.start(self, self.kwargs['ai_sample_rate'], self.kwargs['ao_sample_rate'],  waveform)
                        self.printl('Started to save to {0}'.format(filename))
                        frame_counter=0
                        self.running=True
                        ct=0
                    elif cmd[0]=='stop':
                        self.printl("Stop recording")
                        self.close_shutter()
                        readout=daq.SyncAnalogIO.stop(self)
                        if hasattr(self,'data_handle'):
                            if readout is not None and len(readout.shape)==2:#In some cases the last readut from daq has an extra dimension. Reason unknown
                                self.data2file(readout)
                            fh.close()
                                
                            import hdf5io, tifffile
                            data=hdf5io.read_item(filename, 'twopdata')
                            tifffn=fileop.replace_extension(filename,'.tiff')
                            tifffile.imwrite(tifffn,data)
                            self.printl(f'Saved to {tifffn}')
                            self.printl('Closing file')
                        self.printl(f'Recorded {frame_counter} frames,  sent {ct} frames to GUI')
                        self.running=False
                    elif cmd=='terminate':
                        self.printl('Terminating')
                        break
                    else:
                        self.printl("Unknown command: {0}".format(cmd))
                if self.running:
                    if frame_counter==NFRAMES_SKIP_AT_SCANNING_START:
                        self.open_shutter()
                    try:
                        data_chunk=daq.SyncAnalogIO.read(self)
                        #utils.object2npy({'waveform':waveform, 'data':data_chunk, 'data_format':self.data_format}, r'c:\data\2p.npy')
                        frame_counter+=1
                        
                    except (PyDAQmx.DAQmxFunctions.SamplesNotYetAvailableError,PyDAQmx.DAQmxFunctions.SamplesNoLongerAvailableError) as e:
                        self.printl(self.number_of_ai_samples)
                        import traceback
                        self.printl(traceback.format_exc())
                        self.printl('Read error')
                        continue
                    if self.queues['raw'].empty():
                        self.queues['raw'].put(data_chunk)
                    if frame_counter>NFRAMES_SKIP_AT_SCANNING_START:
                        frame=self.data2file(data_chunk)
                        if self.queues['data'].empty():
                            self.queues['data'].put(frame)
                            ct+=1
                            self.queues['rawimage'].put(self.rawimage)
                            if data_chunk[:2].min()<0:
                                self.queues['response'].put(f'Negative voltate is detected: {data_chunk[:2].min()} V on PMT output, please adjust offset')
                time.sleep(0.02)
            self.printl('Process done')
            #Clean up
            self.digital_output.ClearTask()
        except:
            import traceback
            self.printl(traceback.format_exc(),loglevel='error')
        self.printl('Exit process')
            
class Test(unittest.TestCase):
    
    @unittest.skip('')
    def test_recorder_process(self):
        from visexpman.engine.generic import log,fileop
        import tempfile
        logfile=os.path.join(tempfile.gettempdir(), 'log_{0}.txt'.format(time.time()))
        self.logfile=logfile
        if os.path.exists(logfile):
            os.remove(logfile)
        recorder=SyncAnalogIORecorder('Dev1/ai14:15','Dev1/ao0:1',logfile,timeout=1,ai_sample_rate=800e3,ao_sample_rate=400e3,
                        shutter_port='Dev1/port0/line0')
        self.recorder=recorder
        recorder.start()
        filename=os.path.join(tempfile.gettempdir(), '2pdata_{0}.hdf5'.format(time.time()))
        waveform=numpy.array([numpy.linspace(1,2,150000), numpy.linspace(3,2,150000)])
        time.sleep(0.5)
        recorder.start_(waveform,filename,{})
        time.sleep(5)
        recorder.stop()
        time.sleep(1)
        self.assertFalse(recorder.queues['data'].empty())
        while not recorder.queues['data'].empty():
            readout=recorder.queues['data'].get()
            if 0:
                from pylab import figure,plot,show,legend
                figure(1);plot(waveform[0]);plot(readout[0,0]);
                legend(['wf','readout'])
                figure(2);plot(waveform[1]);plot(readout[0,1]);
                legend(['wf','readout'])
                show()
                import pdb
                pdb.set_trace()
            if 1:
                numpy.testing.assert_almost_equal(waveform,readout[0,:,1::2],-2)
        self.assertFalse('error' in fileop.read_text_file(logfile).lower())
        fh=tables.open_file(filename,'r')
        data=fh.root.twopdata.read()
        for item in data:
            numpy.testing.assert_almost_equal(waveform,item[0,:,1::2]/(2**16-1)*10,2)
        fh.close()
        time.sleep(2)
        self.scan_test(100, 100, 3,True)
        self.scan_test(100, 100, 1.5,True)
        self.scan_test(200, 200, 1,True)
        self.scan_test(200, 200, 1,False)
        recorder.terminate()
        
    def scan_test(self,height, width, resolution,save):
        from visexpman.engine.generic import fileop
        #Generate a 2p waveform
        sw=ScannerWaveform(fsample=400e3, scan_voltage_um_factor=1/128, projector_control_voltage=3.3, frame_timing_pulse_width=1e-3)
        waveform_x,  waveform_y, projector_control,  frame_timing,  boundaries= sw.generate(height, width, resolution, 20, 2, 0, 0)
        import tempfile
        filename=os.path.join(tempfile.gettempdir(), '2pdata_{0}.hdf5'.format(time.time())) if save else None
        waveform=numpy.array([waveform_x,  waveform_y])
        time.sleep(0.5)
        self.recorder.start_(waveform,filename,{'boundaries': boundaries, 'channels':[0,1]})
        time.sleep(5)
        self.recorder.stop()
        time.sleep(1)
        self.assertFalse(self.recorder.queues['data'].empty())
        while not self.recorder.queues['data'].empty():
            readout=self.recorder.queues['data'].get()
            self.assertTrue((numpy.diff(readout[:,:,1],axis=0)>=0).all())#Check gradient
            readout[0,0,0]=0
            self.assertTrue((numpy.diff(readout[:,:,0],axis=1)>=0).all())
        self.assertFalse('error' in fileop.read_text_file(self.logfile).lower())
        if filename is not None:
            fh=tables.open_file(filename,'r')
            data=fh.root.twopdata.read()
            for item in data:
                self.assertTrue((numpy.diff(item[:,:,1],axis=0)>=0).all())
                self.assertTrue((numpy.diff(item[:,:,0],axis=1)>=0).all())
            fh.close()
            
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
                    waveform_x, waveform_y, projector_control,  frame_timing,  boundaries= sw.generate(height, width, resolution, xflyback, yflyback, pulse_width, pulse_phase)
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
                img=rawpmt2image(pmt, boundaries, binning_factor=1,  offset = 0)
                self.assertLess(numpy.diff(img[:,:,0].mean(axis=0)).std(), 1e-6)#All lines are same
                self.assertTrue((numpy.diff(img[:,:,0].mean(axis=0))>0).all())#check uniform gradient
                self.assertLess(numpy.diff(img[:,:,1].mean(axis=1)).std(), 1e-6)
                self.assertTrue((numpy.diff(img[:,:,1].mean(axis=1))>0).all())
            except:
                pass
                
    @unittest.skip('')
    def test_waveform_generator_test_bench(self):
        fsample=400e3
        scan_voltage_um_factor=3.0/256
        frame_timing_pulse_width=1e-6
        height=100
        width=100
        resolution=2
        xflyback=20
        yflyback=2
        pulse_width=100e-6
        pulse_phase=0
        sw=ScannerWaveform(fsample=fsample, scan_voltage_um_factor=scan_voltage_um_factor, projector_control_voltage=3.3, frame_timing_pulse_width=frame_timing_pulse_width)
        waveform_x, waveform_y, projector_control, frame_timing, boundaries= sw.generate(height, width, resolution, xflyback, yflyback, pulse_width, pulse_phase)
        
        
        from pylab import plot, show
        plot(waveform_x)
        plot(sw.generate_smooth(height, width, resolution, xflyback, yflyback))
        plot(projector_control)
        show()
#        pdb.set_trace()

    def test_image_correction_scanner_position_signal(self):
        fn='C:\\data\\2p\\2p_TEST5_202110131558347.hdf5'
        folder=r'G:\My Drive\2p'
        fsample=250e3
        files=[fn]
        files.extend(fileop.listdir(folder))
        for fn in files:
            hh=tables.open_file(fn, 'r')
            w=hh.root.twopdata.attrs['params_Scan_Width']
            h=hh.root.twopdata.attrs['params_Scan_Height']
            r=hh.root.twopdata.attrs['params_Resolution']
            raw=hh.root.raw.read()
            xpos=raw[:,2,:]
            xpos=xpos.flatten()
            pmt0=raw[:,0].flatten()
            pmt1=raw[:,1].flatten()
            pmt=numpy.array([pmt0,pmt1])
            #y signal would be ignored, since each line is separately extracted
            #Filter xpos signal with butterworth filter
            import scipy.signal
            filt=scipy.signal.butter(4, 10000/fsample, btype='low')
            xposfilt=scipy.signal.filtfilt(filt[0], filt[1], xpos).real
            
            #Detect zero crossing of filtered signal. Scan range can be calculated from um/voltage scale in Volt. This can be converted to feedback signal voltage range 
            #-> assuming that the position  signal is monotonous, the start and end of the x scan can be marked (on time axis)
            #Calculate nonlinearity within this range. Compare this with one pixel's voltage step. If larger then raise error
            #So the idea is to find a linear range where nonlinearity is below one pixel and take PMT signal from this range
            #Zero crossing
            zero_crossing=numpy.where(numpy.diff(numpy.sign(xposfilt))>0)[0][:int(h*r)]
            if zero_crossing.shape[0]>0:
                dwelltime=(1000/fsample)/(xposfilt[zero_crossing[0]+1]-xposfilt[zero_crossing[0]])*0.75/0.5#ms/V
            else:
                dwelltime=0
            #For each scan extract linear range
            linear_range_boundaries=numpy.array([zero_crossing-int(r*w/2),zero_crossing+int(r*w/2)]).T
            if (linear_range_boundaries<0).any():
                raise RuntimeError('Incorrect scan')
            #Extract xpos signal
            sweeps=numpy.array(numpy.split(xposfilt, linear_range_boundaries.flatten())[1::2])
            #Check if signal change is larger than one pixel
            if sweeps.shape[0]>0:
                one_pixel_voltage=abs(sweeps[:,0]-sweeps[:,-1]).mean()/(w*r)
                diff=numpy.diff(sweeps,axis=1)
                from pylab import imshow, show
                #imshow(diff);show()
            if 1:
                from pylab import plot, show, specgram, magnitude_spectrum, ylim, xlim, title, savefig, cla, clf
                cla()
                clf()
                #plot(xpos);plot(xposfilt);show()
                #specgram(xpos,Fs=fsample);show()
                magnitude_spectrum(xpos,Fs=fsample)
                ylim([0, 0.0005])
                xlim([0, 40000])
                title(f'dwelltime {dwelltime:.2f} ms/V, scan with: {w} um, resolution: {r}, \n {raw[0][2].std()}, {raw[0][3].std()}')
                savefig(f'c:\\tmp\\{os.path.basename(fn)}.png', dpi=150)
#                show()
            pass

if __name__ == "__main__":
    unittest.main()
    
