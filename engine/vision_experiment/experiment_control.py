import time,pdb
import os.path
import tempfile
import scipy.io
import numpy
import traceback
import shutil
import copy
import tables
import sys
import zmq
try:
    import PyDAQmx
    import PyDAQmx.DAQmxConstants as DAQmxConstants
    import PyDAQmx.DAQmxTypes as DAQmxTypes
except:
    pass

import experiment_data
import visexpman.engine
from visexpman.engine.generic import utils,fileop,introspect,signal
from visexpman.engine.generic.graphics import is_key_pressed,check_keyboard
from visexpman.engine.hardware_interface import mes_interface,daq_instrument,stage_control,digital_io,queued_socket
from visexpman.engine.vision_experiment.screen import CaImagingScreen
try:
    import hdf5io
except ImportError:
    print 'hdf5io not installed'

from visexpman.engine.generic.command_parser import ServerLoop
try:
    from visexpman.users.test import unittest_aggregator
    test_mode=True
except:
    test_mode=False
import unittest

ENABLE_16_BIT = True

class CaImagingLoop(ServerLoop, CaImagingScreen):#OBSOLETE
    def __init__(self, machine_config, socket_queues, command, log):
        ServerLoop.__init__(self, machine_config, socket_queues, command, log)
        CaImagingScreen.__init__(self)
        self.limits = {}
        self.limits['min_ao_voltage'] = -self.config.MAX_SCANNER_VOLTAGE
        self.limits['max_ao_voltage'] = self.config.MAX_SCANNER_VOLTAGE
        self.limits['min_ai_voltage'] = -self.config.MAX_PMT_VOLTAGE
        self.limits['max_ai_voltage'] = self.config.MAX_PMT_VOLTAGE
        self.limits['timeout'] = self.config.TWO_PHOTON_DAQ_TIMEOUT
        self.instrument_name = 'daq'
        self.laser_on = False
        self.projector_state = False
        self.daq_logger_queue = self.log.get_queues()[self.instrument_name]
        
        self.daq_queues = daq_instrument.init_daq_queues()
        self.imaging_started = False
        self.experiment_running = False
        self.load_image_context()
        #Request for sending display_configuration
        self.send({'function': 'remote_call', 'args': ['self.visualisation_control.generate_display_configuration', [True]]})
        self.ct=0
        
    def application_callback(self):
        '''
        Watching keyboard commands, refreshing screen and saving data to file in case of experiment comes here
        '''
        if self.exit:
            return 'terminate'
        for key_pressed in check_keyboard():
            if key_pressed == self.config.KEYS['exit']:#Exit application
                if self.imaging_started:
                    self.printl('Terminate running imaging')
                    if self.imaging_started:
                        self.printl('Stopping live imaging')
                        self.live_scan_stop()
                if hasattr(self, 'daq_process') and self.daq_process.is_alive():
                    self.daq_process.terminate()
                    self.printl('Daq process terminated')
                return 'terminate'
            elif key_pressed == self.config.KEYS['snap']:
                if hasattr(self, 'imaging_parameters'):
                    self.snap_ca_image(self.imaging_parameters)
                else:
                    self.printl('Imaging parameters are not available. Initiate imaging from main_ui')
            elif key_pressed == self.config.KEYS['transfer_function']:
                self.record_tranfer_function()
            elif key_pressed == self.config.KEYS['live_start_stop']:
                if not hasattr(self, 'imaging_parameters'):
                    self.printl('Imaging parameters are not available. Initiate imaging from main_ui')
                elif self.imaging_started:
                    self.live_scan_stop()
                else:
                    self.live_scan_start(self.imaging_parameters)
            else:
                print key_pressed
                
        if self.abort:
            if self.imaging_started:
                self.live_scan_stop()
            self.abort = False
        if not self.imaging_started and self.projector_state:
            waveform = numpy.ones((1,100))*self.config.STIMULATION_TRIGGER_AMPLITUDE
            waveform[0,0]=0.0
            waveform[0,-1]=0.0
            daq_instrument.set_waveform(self.config.TWO_PHOTON['PROJECTOR_CONTROL'],waveform,sample_rate = 10000)
        self.read_imaging_data()
        self.refresh()
#        self.printl(self.ct)
#        time.sleep(1.0)
#        self.ct+=1
        
    def read_imaging_data(self):
        '''
        Read imaging data when live imaging is ongoing
        '''
        if hasattr(self, 'daq_process') and self.imaging_started is not False and hasattr(self, 'imaging_parameters'):
            while True:
                frame = self.daq_process.read_ai()
                if frame is None:
                    break
                else:
                    #Transform frame to image
                    self.images['display'], self.images['save'] = scanner_control.signal2image(frame, self.imaging_parameters, self.config.PMTS)
                    self.images['display']/=self.config.MAX_PMT_VOLTAGE
                    self.frame_ct+=1
                    if ENABLE_16_BIT:
                        self.images['save'] = self._pmt_voltage2_16bit(self.images['save'])
                    self._save_data(self.images['save'])
                    self._send_meanimage_data()
            
    def _send_meanimage_data(self):
        now = time.time()
        entry = map(int, list(numpy.cast['float'](self.images['save']).mean(axis=1).mean(axis=1)))
        entry.insert(0,round(now,2))
        self.data2plot.append(entry)
        if now - self.last_send_time> 1.0 and len(self.data2plot)>0:#sending data in every 1 second
            self.send({'plot': self.data2plot})
            self.data2plot = []
            self.last_send_time = now
                
    def _init_meanimage_data_send(self):
        self.last_send_time = time.time()
    
        self.data2plot = []
        
    def test(self):
        self.printl('test1')
        
    def load_image_context(self):
        '''
        Loads ca imaging application's context
        '''
        context_filename = fileop.get_context_filename(self.config)
        if os.path.exists(context_filename):
            self.images = utils.array2object(hdf5io.read_item(context_filename, 'context', self.config))
        else:
            self.images = {}
            
    def save_image_context(self):
        hdf5io.save_item(fileop.get_context_filename(self.config), 'context', utils.object2array(self.images), self.config,  overwrite = True)
        
    def _pack_waveform(self,parameters,xy_scanner_only=False):
        waveforms = numpy.array([parameters['xsignal'], 
                                parameters['ysignal'],
                                parameters['stimulus_flash_trigger_signal']*parameters['enable_scanner_synchronization']*self.config.STIMULATION_TRIGGER_AMPLITUDE,
                                parameters['frame_trigger_signal']*self.config.FRAME_TIMING_AMPLITUDE])
        if xy_scanner_only:
            waveforms *= numpy.array([[1,1,0,0]]).T
        return waveforms

    def live_scan_start(self, parameters):
        if self.imaging_started:
            self.printl('Live scan already running, stoping it then starting')
            self.live_scan_stop()
        self.printl('Prepare imaging')
        self.prepare_screen_for_live_imaging()
        self.frame_ct=0
        self.imaging_parameters = parameters
        self._init_meanimage_data_send()
        self._prepare_datafile()
        self.imaging_started = None
        self.record_ai_channels = daq_instrument.ai_channels2daq_channel_string(*self._pmtchannels2indexes(parameters['recording_channels']))
        self.daq_process = daq_instrument.AnalogIOProcess(self.instrument_name, self.daq_queues, self.daq_logger_queue,
                                ai_channels = self.record_ai_channels,
                                ao_channels= self.config.TWO_PHOTON['CA_IMAGING_CONTROL_SIGNAL_CHANNELS'],limits=self.limits)
        self.daq_process.start()
        #Waveforms are fetched from parameters (generated by GUI).
        #TODO: consider if not all signals are to be generated
        #Opening shutter takes place before scanners are started because it takes some time
        self._shutter(True)
        imaging_started_result = self.daq_process.start_daq(ai_sample_rate = parameters['analog_input_sampling_rate'], 
                                                            ao_sample_rate = parameters['analog_output_sampling_rate'], 
                                                            ao_waveform = self._pack_waveform(parameters), 
                                                            timeout = 30)
        self.t0=time.time()
        if parameters.has_key('experiment_name'):
            self.send({'trigger': 'imaging started',  'arg': imaging_started_result})#notifying main_ui that imaging started and stimulus can be launched
        self.printl('Imaging started {0}'.format('' if imaging_started_result else imaging_started_result))
        self.imaging_started = False if imaging_started_result == 'timeout' else imaging_started_result
        
    def live_scan_stop(self):
        if not self.imaging_started:
            self.printl('Live scan is not running')
            return
        self.t2=time.time()
        #Closing shutter before terminating scanning
        self._shutter(False)
        try:
            parameters = self.imaging_parameters
            unread_data = self.daq_process.stop_daq()
            if isinstance(unread_data ,str):
                self.printl(unread_data)
            else:
                self.printl('acquired frames {0} read frames {1}, expected number of frames {2}'.format(
                                unread_data[1],
                                self.frame_ct, 
                                (self.t2-self.t0) * parameters['frame_rate']))
                #Check if all frames have been acquired
                if unread_data[0].shape[0] + self.frame_ct != unread_data[1] or\
                    unread_data[1] < (self.t2-self.t0) * parameters['frame_rate']:
                    self.printl('WARNING: Some frames are lost')
                self._close_datafile(unread_data)
        except:
            self.printl(traceback.format_exc())
        finally:
            self.imaging_started = False
            self.daq_process.terminate()
            #Wait till process terminates
            while self.daq_process.is_alive():
                time.sleep(0.2)
            #Set scanner voltages to 0V
            daq_instrument.set_voltage(self.config.TWO_PHOTON['CA_IMAGING_CONTROL_SIGNAL_CHANNELS'], 0.0)
            self.printl('Imaging stopped')
            if parameters.has_key('experiment_name'):
                self.send({'trigger':'imaging data ready'})
        time.sleep(0.5)
        #TODO:
        #Make sure that file is not open
        #Notify man_ui that data imaging
#        self.send({'update': ['data saved', imaging_started]})
        
    def snap_ca_image(self, parameters):
        '''
        Snap a single two photon image
        '''
        #TODO: rename this function
        if self.imaging_started:
            self.printl('Live scan already running')
            return
        self.printl('Snap')
        self.live_scan_start(parameters)
        frames2acquire = parameters['averaging'] if parameters['averaging']>0 else 1
        frames=[]
        for ii in range(int(frames2acquire)):
            while True:
                frame = self.daq_process.read_ai()
                if frame is not None:
                    frames.append(frame)
                    self.frame_ct+=1
                    break
        frame = numpy.array(frames).mean(axis=0)
        self.images['display'], self.images['save'] = scanner_control.signal2image(frame, self.imaging_parameters, self.config.PMTS)
        self.images['display']/=self.config.MAX_PMT_VOLTAGE
        if ENABLE_16_BIT:
            self.images['save'] = self._pmt_voltage2_16bit(self.images['save'])
        self._save_data(self.images['save'])
        self.live_scan_stop()
        
    def _pmtchannels2indexes(self, recording_channels):
        daq_device = self.config.TWO_PHOTON['PMT_ANALOG_INPUT_CHANNELS'].split('/')[0]
        channel_indexes = [self.config.PMTS[ch]['CHANNEL'] for ch in recording_channels]
        channel_indexes.sort()
        return channel_indexes, daq_device
        
    def _prepare_datafile(self):
        if self.imaging_parameters['save2file']:
            self.datafile = hdf5io.Hdf5io(experiment_data.get_recording_path(self.imaging_parameters, self.config, prefix = 'ca'),filelocking=False)
            self.datafile.imaging_parameters = copy.deepcopy(self.imaging_parameters)
            self.image_size = (len(self.imaging_parameters['recording_channels']), self.imaging_parameters['scanning_range']['row'] * self.imaging_parameters['resolution'],self.imaging_parameters['scanning_range']['col'] * self.imaging_parameters['resolution'])
            datacompressor = tables.Filters(complevel=self.config.DATAFILE_COMPRESSION_LEVEL, complib='blosc', shuffle = 1)
            if ENABLE_16_BIT:
                datatype = tables.UInt16Atom(self.image_size)
            else:
                datatype = tables.Float32Atom(self.image_size)
            self.raw_data = self.datafile.h5f.create_earray(self.datafile.h5f.root, 'raw_data', datatype, 
                    (0,),filters=datacompressor)
        
    def _close_datafile(self, data=None):
        if self.imaging_parameters['save2file']:
            self.printl('Saved frames at the end of imaging: {0}'.format(data[0].shape[0]))
            if data is not None:
                for frame in data[0]:
                    frame_converted = scanner_control.signal2image(frame, self.imaging_parameters, self.config.PMTS)[1]
                    if ENABLE_16_BIT:
                        frame_converted = self._pmt_voltage2_16bit(frame_converted)
                    self._save_data(frame_converted)
                    self.frame_ct += 1
            self.datafile.imaging_run_info = {'acquired_frames': self.frame_ct, 'start': self.t0, 'end':self.t2, 'duration':self.t2-self.t0 }
            setattr(self.datafile, 'software_environment_{0}'.format(self.machine_config.user_interface_name), experiment_data.pack_software_environment())
            setattr(self.datafile, 'configs_{0}'.format(self.machine_config.user_interface_name), experiment_data.pack_configs(self))
            nodes2save = ['imaging_parameters', 'imaging_run_info', 'software_environment_{0}'.format(self.machine_config.user_interface_name), 'configs_{0}'.format(self.machine_config.user_interface_name)]
            self.datafile.save(nodes2save)
            self.printl('Stimulus info saved to {0}'.format(self.datafile.filename))
            self.datafile.close()
        
    def _save_data(self,frame):
        if self.imaging_parameters['save2file']:
            self.raw_data.append(numpy.array([frame]))
            
    def _pmt_voltage2_16bit(self,image):
        '''
        Limit PMT voltage between -MAX_PMT_NOISE_LEVEL...self.config.MAX_PMT_VOLTAGE+MAX_PMT_NOISE_LEVEL range. 
        The MAX_PMT_NOISE_LEVEL extension to both extremes ensures that noise is not distorted with limiting PMT voltage values,
        but ensures that no invalid value is generated by scale and converting image data to 0...2**16-1 range
        '''
        #Subzero PMT voltages are coming from noise. Voltages below MAX_PMT_NOISE_LEVEL are ignored. 
        image_cut = numpy.where(image<-self.config.MAX_PMT_NOISE_LEVEL,-self.config.MAX_PMT_NOISE_LEVEL,image)
        #Voltages above MAX_PMT_VOLTAGE+max_noise_level are considered to be saturated
        image_cut = numpy.where(image>self.config.MAX_PMT_VOLTAGE+self.config.MAX_PMT_NOISE_LEVEL,self.config.MAX_PMT_VOLTAGE+self.config.MAX_PMT_NOISE_LEVEL,image_cut)
        return numpy.cast['uint16'](((image_cut+self.config.MAX_PMT_NOISE_LEVEL)/(2*self.config.MAX_PMT_NOISE_LEVEL+self.config.MAX_PMT_VOLTAGE))*(2**16-1))
        
    def _shutter(self,state):
        daq_instrument.set_digital_line(self.config.TWO_PHOTON['LASER_SHUTTER_PORT'], int(state))
        self.laser_on = state
        
    def record_tranfer_function(self):
        from pylab import plot,show,figure,title
        ao_sample_rate = 2000000
        amplitudes = [1.0, 1.5, 2.0, 3.0, 4.0,4.5]
        frq = numpy.arange(50,1400,50)
        frq = numpy.insert(frq, 0, 25)
        frq = numpy.insert(frq, 0, 10)
        nperiods =  10
        xoffset = -0.65*0
        yoffset = 0.585*0
        self.printl('Started')
        fns = []
#        amplitudes = amplitudes[3:]
#        frq = frq[:5]
        plotdata = {}
        for amplitude in amplitudes:
            with introspect.Timer(''):
                self.printl('Preparing, {0} V'.format(amplitude))
                waveformx,boundaries,amplitude_frequency = signal.sweep_sin([amplitude], frq, nperiods, ao_sample_rate)
                waveform = numpy.zeros((2,waveformx.shape[0]),dtype=numpy.float64)
                waveform[0] = waveformx+xoffset
                waveform[1] = yoffset
                aio = daq_instrument.AnalogIOProcess(self.instrument_name, self.daq_queues, self.logger_queue,
                                            ai_channels = 'Dev1/ai0',
                                            ao_channels= 'Dev1/ao0:1',limits=self.limits)
    #                                        ao_channels= self.config.TWO_PHOTON['CA_IMAGING_CONTROL_SIGNAL_CHANNELS'],limits=self.limits)
                aio._create_tasks()
                #Open shutter
                daq_instrument.set_digital_line(self.config.TWO_PHOTON['LASER_SHUTTER_PORT'], 1)
                #Generate waveform and start data acquisition
                aio._start(ai_sample_rate = ao_sample_rate, ao_sample_rate = ao_sample_rate, 
                              ao_waveform = waveform,
                              finite_samples=True,timeout = 30)
                self.printl('Recording')
                ai_data = aio._stop()
                #Close shutter
                daq_instrument.set_digital_line(self.config.TWO_PHOTON['LASER_SHUTTER_PORT'], 0)
                aio._close_tasks()
                data2save = {}
                ai_data = numpy.cast['float32'](ai_data)
                waveformx = numpy.cast['float32'](waveformx)
                vn = ['ao_sample_rate', 'amplitude', 'frq', 'nperiods', 'xoffset','xoffset','waveformx', 'boundaries','ai_data','amplitude_frequency']
                for v in vn:
                    data2save[v] = locals()[v]
                fn=os.path.join(tempfile.gettempdir(), 'c.npy')
                self.printl('Saving data')
                numpy.save(fn,utils.object2array(data2save))
                fns.append(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'calib_{0:.1f}.npy'.format(amplitude)))
                shutil.move(fn,fns[-1])
            si = numpy.nonzero(numpy.where(boundaries==1,1,0))[0][0]
            ei = numpy.nonzero(numpy.where(boundaries==-1,1,0))[0][0]/nperiods
            hsi = numpy.nonzero(numpy.where(boundaries==1,1,0))[0][-1]
            hei = hsi+(waveformx.shape[0] - hsi)/nperiods
            import pdb
#            pdb.set_trace()
            first_rec = copy.deepcopy(ai_data[si:ei])
            first_scan = copy.deepcopy(waveformx[si:ei])
            last_rec = copy.deepcopy(ai_data[hsi:hei])
            last_scan = copy.deepcopy(waveformx[hsi:hei])
            plotdata[amplitude] = [first_rec,first_scan, last_rec, last_scan]
        self.printl('Done')
        ct=0
        for k,v in plotdata.items():
            figure(ct)
            plot(v[0])
            plot(v[1])
            title((k, 'lowest frq'))
            figure(ct+1)
            plot(v[2])
            plot(v[3])
            title((k, 'highest frq'))
            ct+=2
        show()
        
    def at_process_end(self):
        self.save_image_context()
        self.close_screen()

class Trigger(object):
    '''
    Provides methods for detecting/generating triggers
    Logging takes place outside this class
    '''
    def __init__(self,machine_config, queues, digital_output):
        self.machine_config=machine_config
        self.queues = queues
        self.digital_io = digital_output
        
    def _wait4trigger(self, timeout, wait_method, args=[], kwargs={}):
        '''
        wait_method is a callable function that returns True when trigger event occured
        '''
        to = utils.Timeout(timeout)
        while True:
            self.check_abort()
            if to.is_timeout() or self.abort:
                return False
            elif wait_method(*args, **kwargs):
                return True
            time.sleep(0.01)
                
    def wait4queue_trigger(self, keyword): 
        return self._wait4trigger(utils.is_keyword_in_queue, (self.queues['command'], keyword), {})
        
    def wait4keyboard_trigger(self, key):
        return self._wait4trigger(is_key_pressed, (self.machine_config.KEYS[key]), {})
        
    def wait4digital_input_trigger(self, pin):
        result=False
        if isinstance(pin,str) and 'Dev' in pin:
            digital_input = PyDAQmx.Task()
            digital_input.CreateDIChan(pin,'di', DAQmxConstants.DAQmx_Val_ChanPerLine)
            data = numpy.zeros((1,), dtype=numpy.uint8 )
            total_samps = DAQmxTypes.int32()
            total_bytes = DAQmxTypes.int32()
            while True:
                digital_input.ReadDigitalLines(1,0.1,DAQmxConstants.DAQmx_Val_GroupByChannel,data,1,DAQmxTypes.byref(total_samps),DAQmxTypes.byref(total_bytes),None)
                if data[0]==True:
                    result=True
                    break
                self.check_abort()
                if self.abort:
                    break
            digital_input.ClearTask()
        else:
            while True:
                if self.digital_io.read_pin(self.machine_config.STIM_START_TRIGGER_PIN, inverted=self.machine_config.PLATFORM=='epos'):
                    result = True
                    break
                self.check_abort()
                if self.abort:
                    break
        return result
    
    def wait4newfiletrigger(self):
        files = os.listdir(self.machine_config.TRIGGER_PATH)
        def is_new_file(files):
            return len(files) < len(os.listdir(self.machine_config.TRIGGER_PATH))
        return self._wait4trigger(is_new_file, (files), {})
            
    def set_trigger(self, pin):
        self.digital_io.set_pin(pin, True)
        
    def clear_trigger(self,pin):
        self.digital_io.set_pin(pin, False)
        
class StimulationControlHelper(Trigger,queued_socket.QueuedSocketHelpers):
    '''
    Provides access to:
            1. digital IO for generating sync signals
            2. LED controller (if enabled)
            3. Other stimulus generating device
            4. Objective control (cortical setups)
            5. Stage controller (cortical)
    Takes care of communication of stim during experiment
    Handles datafiles related to displaying stimulation
    Ensures that no file operation take place during stimulation (writing to file in logger process is suspended)
    '''
    def __init__(self, machine_config, parameters, queues, log):
        self.machine_config = machine_config
        self.parameters = parameters
        self.log = log
        if self.machine_config.DIGITAL_IO_PORT =='daq':
            self.digital_io=digital_io.DaqDio(self.machine_config.TIMING_CHANNELS)
        elif self.machine_config.DIGITAL_IO_PORT != False and parameters!=None:#parameters = None if experiment duration is calculated
            digital_output_class = instrument.ParallelPort if self.machine_config.DIGITAL_IO_PORT == 'parallel port' else digital_io.SerialPortDigitalIO
            self.digital_io = digital_output_class(self.machine_config, self.log)
        else:
            self.digital_io = None
        Trigger.__init__(self, machine_config, queues, self.digital_io)
        if self.digital_io!=None:#Digital output is available
            self.clear_trigger(self.config.BLOCK_TIMING_PIN)
            self.clear_trigger(self.config.FRAME_TIMING_PIN)
        #Helper functions for getting messages from socket queues
        queued_socket.QueuedSocketHelpers.__init__(self, queues)
        if self.machine_config.PLATFORM=='epos':
            self.camera_trigger=digital_io.ArduinoIO(self.machine_config.CAMERA_TRIGGER_PORT)
        self.user_data = {}
        self.abort = False
        
    def start_sync_recording(self):
        class Conf(object):
            DAQ_CONFIG = [
                    {
                    'ANALOG_CONFIG' : 'ai', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 3.0,
                    'SAMPLE_RATE'  :self.machine_config.SYNC_RECORDER_SAMPLE_RATE,
                    'AI_CHANNEL' : self.machine_config.SYNC_RECORDER_CHANNELS,
                    'MAX_VOLTAGE' : 10.0,
                    'MIN_VOLTAGE' : -10.0,
                    'DURATION_OF_AI_READ' : 2*self.sync_recording_duration,
                    'ENABLE' : True
                    },]
        
        config=Conf()
        self.analog_input = daq_instrument.AnalogIO(config)
        self.sync_recorder_started=time.time()
        self.abort=not self.analog_input.start_daq_activity()
        
    def start_ao(self):
        if hasattr(self.machine_config,'TRIGGER_MES') and not self.machine_config.TRIGGER_MES:
            return
        while not self.mes_interface['mes_response'].empty():
            self.mes_interface['mes_response'].get()#Make sure that response buffer is empty
        if not mes_interface.check_mes_connection(self.mes_interface['mes_command'], self.mes_interface['mes_response']):
            self.send({'notify':['Error', 'MES not connected to stim']})
            self.send({'trigger': 'stim error'})
            self.abort=True
            return
        mesfn=self.outputfilename.replace('.hdf5','.mat')
        fp=open(mesfn,'wt')
        fp.write(str(self.parameters['mes_record_time']))
        fp.close()
        self.mes_interface['mes_command'].put('SOCstart_recordingEOC{0}EOP' .format(mesfn))
        t0=time.time()
        while True:
            if time.time()-t0>self.machine_config.MES_TIMEOUT:
                self.printl('MES did not start')
                self.send({'notify':['Warning', 'MES did not start']})
                self.send({'trigger': 'stim error'})
                os.remove(mesfn)
                self.abort=True
                break
            if not self.mes_interface['mes_response'].empty():
                if 'SOCstart_recordingEOCstartedEOP' in self.mes_interface['mes_response'].get():
                    self.printl('MES started')
                    break
            time.sleep(1)
        self.ao_expected_finish=time.time()+self.parameters['mes_record_time']/1000
        if self.parameters['duration']>self.machine_config.MES_LONG_RECORDING:
            time.sleep(self.machine_config.MES_RECORD_START_WAITTIME_LONG_RECORDING)
        else:
            time.sleep(self.machine_config.MES_RECORD_START_WAITTIME)
        
    def wait4ao(self):
        if self.abort:
            return
        while True:
            if self.abort or time.time()-self.ao_expected_finish>self.machine_config.SYNC_RECORD_OVERHEAD:
                self.printl('Go to Matlab window and make sure that "RECORDING FINISHED" message has shown up.')
                #self.send({'notify':['Info', 'Go to Matlab window and make sure that "RECORDING FINISHED" message has shown up.']})
                break
            if not self.mes_interface['mes_response'].empty():
                msg=self.mes_interface['mes_response'].get()
                self.printl(msg)
                if 'SOCacquire_line_scanEOCsaveOKEOP' in msg:
                    break
            time.sleep(0.1)
        
    def execute(self):
        '''
        Calls the run method of the experiment class. 
        Also takes care of all communication, synchronization with other applications and file handling
        '''
        try:
            prefix='stim' if self.machine_config.PLATFORM != 'ao_cortical' else 'data'
            if self.machine_config.PLATFORM in ['behav', 'standalone',  'intrinsic']:#TODO: this is just a hack. Standalone platform has to be designed
                self.parameters['outfolder']=self.machine_config.EXPERIMENT_DATA_PATH
                if hasattr(self, 'calculate_stimulus_duration'):
                    self.parameters['stimclass']=self.__class__.__name__
                else:
                    self.parameters['stimclass']=self.experiment_config.__class__.__name__
                from visexpman.engine.vision_experiment.experiment import get_experiment_duration
                #self.parameters['duration']=get_experiment_duration(self.parameters['stimclass'], self.config)                    
            self.outputfilename=experiment_data.get_recording_path(self.machine_config, self.parameters,prefix = prefix)
            #Computational intensive precalculations for stimulus
            self.prepare()
            #Control/synchronization with platform specific recording devices
            time.sleep(0.1)
            if self.machine_config.PLATFORM=='ao_cortical':
                self.sync_recording_duration=self.parameters['mes_record_time']/1000+1#little overhead making sure that the last sync pulses from MES are recorded
                self.start_sync_recording()
                self.printl('Sync signal recording started')
                self.start_ao()
            elif self.machine_config.PLATFORM=='hi_mea':
                #send start signal
                self._send_himea_cmd("start")
            elif self.machine_config.PLATFORM=='elphys_retinal_ca':
                self.send({'trigger':'stim started'})
            elif self.machine_config.PLATFORM=='mc_mea':
                pass
            elif self.machine_config.PLATFORM=='us_cortical' and self.machine_config.ENABLE_ULTRASOUND_TRIGGERING:
                import serial
                from contextlib import closing
                with closing(serial.Serial(port='COM1',baudrate=9600)) as s:
                    s.write('e')
                self.send({'trigger':'stim started'})
            elif self.machine_config.PLATFORM=='intrinsic':
                from visexpA.engine.datahandlers.ximea_camera import XimeaCamera
                self.camera = XimeaCamera(config=self.machine_config)
                self.camera.start()
                self.camera.trigger.set()  # starts acquisition
            elif self.machine_config.PLATFORM in ['behav','epos']:
                if self.machine_config.PLATFORM=='behav':
                    self.sync_recording_duration=self.parameters['duration']
                    self.start_sync_recording()
                    self.printl('Sync signal recording started')
                self.printl('Waiting for external trigger')
                if hasattr(self.machine_config,'INJECT_START_TRIGGER'):
                    import threading
                    t=threading.Thread(target=inject_trigger, args=('/dev/ttyACM1',5,2))
                    t.start()
                if self.machine_config.WAIT4TRIGGER_ENABLED and not self.wait4digital_input_trigger(self.machine_config.STIM_START_TRIGGER_PIN):
                    self.abort=True
                if self.machine_config.PLATFORM=='epos':
                    self.camera_trigger.enable_waveform(self.machine_config.CAMERA_TRIGGER_PIN, self.machine_config.CAMERA_TRIGGER_FRAME_RATE)
                    time.sleep(self.machine_config.CAMERA_PRE_STIM_WAIT)
            self.log.suspend()#Log entries are stored in memory and flushed to file when stimulation is over ensuring more reliable frame rate
            try:
                self.printl('Starting stimulation {0}/{1}'.format(self.name,self.parameters['id']))
                self._start_frame_capture()
                self.run()
                self._stop_frame_capture()
            except:
                self.send({'trigger':'stim error'})
                exc_info = sys.exc_info()
                raise exc_info[0], exc_info[1], exc_info[2]#And reraise exception such that higher level modules could display it
            self.log.resume()
            #Terminate recording devices
            if self.machine_config.PLATFORM in ['elphys_retinal_ca', 'mc_mea', 'us_cortical', 'ao_cortical']:
                self.printl('Stimulation ended')
                self.send({'trigger':'stim done'})#Notify main_ui about the end of stimulus. sync signal and ca signal recording needs to be terminated
            if self.machine_config.PLATFORM=='hi_mea':
                #send stop signal
                self._send_himea_cmd("stop")
            elif self.machine_config.PLATFORM=='intrinsic':
                self.camera.trigger.clear()
                self.camera.join()
            elif self.machine_config.PLATFORM=='ao_cortical':
                self.wait4ao()
            elif self.machine_config.PLATFORM=='epos':
                time.sleep(self.machine_config.CAMERA_POST_STIM_WAIT)
                self.camera_trigger.disable_waveform()
            if self.machine_config.PLATFORM in ['behav', 'ao_cortical']:
                self.analog_input.finish_daq_activity(abort = self.abort)
                self.printl('Sync signal recording finished')
            #Saving data
            if not self.abort:
                self._save2file()
                self.printl('Stimulus info saved to {0}'.format(self.datafilename))
                if self.machine_config.PLATFORM in ['elphys_retinal_ca', 'us_cortical', 'ao_cortical']:
                    self.send({'trigger':'stim data ready'})
                if self.machine_config.PLATFORM in ['ao_cortical']:
                    self._backup(self.datafilename)
                    self.printl('{0} backed up'.format(self.datafilename))
                elif self.machine_config.PLATFORM in ['behav']:
                    experiment_data.hdf52mat(self.outputfilename)
            else:
                self.printl('Stimulation stopped')
            if self.machine_config.PLATFORM=='mc_mea':
                self.trigger_pulse(self.machine_config.ACQUISITION_TRIGGER_PIN, self.machine_config.START_STOP_TRIGGER_WIDTH,polarity=self.machine_config.ACQUISITION_TRIGGER_POLARITY)
            self.frame_rates = numpy.array(self.frame_rates)
            if len(self.frame_rates)>0:
                fri = 'mean: {0}, std {1}, max {2}, min {3}, values: {4}'.format(self.frame_rates.mean(), self.frame_rates.std(), self.frame_rates.max(), self.frame_rates.min(), numpy.round(self.frame_rates,0))
                self.log.info(fri, source = 'stim')
                expfr=self.machine_config.SCREEN_EXPECTED_FRAME_RATE
                if abs((expfr-self.frame_rates.mean())/expfr)>self.machine_config.FRAME_RATE_ERROR_THRESHOLD and not self.abort:
                    raise RuntimeError('Mean frame rate {0} does not match with expected frame {1}'.format(self.frame_rates.mean(), expfr))
        except:
            exc_info = sys.exc_info()
            raise exc_info[0], exc_info[1], exc_info[2]#And reraise exception such that higher level modules could display it
        finally:
            self.close()#If something goes wrong, close serial port

    def close(self):
        if hasattr(self.digital_io, 'release_instrument'):
                self.digital_io.release_instrument()
        if hasattr(self, 'camera_trigger'):
            self.camera_trigger.close()

    def printl(self, message, loglevel='info', stdio = True):
        utils.printl(self, message, loglevel, stdio)

    def check_abort(self):
        if is_key_pressed(self.machine_config.KEYS['abort']) or utils.get_key(self.recv(put_message_back=True), 'function') == 'stop_all':
            self.abort = True
            
    def _start_frame_capture(self):
        '''
        ensures that frame capture is started when stimulus is running
        
        '''
        if self.machine_config.ENABLE_FRAME_CAPTURE:
           self.screen.start_frame_capture=True
           
    def _stop_frame_capture(self):
        self.screen.start_frame_capture=False
        
    def _blocks2table(self):
        '''
        Prepare stimulus block table
        '''
        block_info=[sfi for sfi in self.stimulus_frame_info if sfi.has_key('block_name')]
        if len(block_info)==0: return
        #convert block names to column headers
        signatures=[b['block_name'] for b in block_info]
        if not isinstance(signatures[0],tuple):
            self.printl('Block info cannot be converted to table, block names must be tuples')
            return
        if any(numpy.array(map(len, signatures))-len(signatures[0])):
            self.printl('Block info cannot be converted to a table')
            return
        if isinstance(signatures[0][0],str):
            #Assume, that first item in signature is always an enumerated string
            #none, all and both are reserved keywords
            enum_values=list(set([s[0] for s in signatures if s[0] not in ['none', 'all','both']]))
            enum_values.sort()
            nblocks=len(block_info)/2
            block_table=numpy.zeros((nblocks, len(enum_values)+2+len(signatures[0])-1))
            for bi in range(nblocks):
                start=block_info[2*bi]
                end=block_info[2*bi+1]
                if start['block_name']!=end['block_name']:
                    self.printl('Block info cannot be converted to a table')
                    return
                pars=start['block_name'][1:]
                parnames=['par{0}'.format(i) for i in range(len(pars))]
                block_table[bi,:len(pars)]=pars
                block_table[bi,len(pars):len(pars)+len(enum_values)]=numpy.array([int(start['block_name'][0]== e) for e in enum_values])
                if start['block_name'][0] in ['all', 'both']:
                    block_table[bi,len(pars):len(pars)+len(enum_values)]=1
                block_table[bi,len(pars)+len(enum_values):]=numpy.array([start['block_start'],end['block_end']-1])
        else:
            raise NotImplementedError('Block signatures without string/enumerated')
        block_table_header=parnames
        block_table_header.extend(enum_values)
        block_table_header.extend(['start counter', 'end counter'])
        self.block={'table':block_table, 'column_names': block_table_header}
        
    def _prepare_data2save(self):
        '''
        Pack software enviroment and configs
        '''
        if self.machine_config.EXPERIMENT_FILE_FORMAT == 'hdf5':
            setattr(self.datafile, 'software_environment',experiment_data.pack_software_environment())
            setattr(self.datafile, 'configs', experiment_data.pack_configs(self))
            self.datafile.frame_times=self.screen.frame_times
        elif self.machine_config.EXPERIMENT_FILE_FORMAT == 'mat':
            self.datafile['software_environment'] = experiment_data.pack_software_environment()
            self.datafile['configs'] = experiment_data.pack_configs(self)
            self.datafile['frame_times']=self.screen.frame_times
        
    def _save2file(self):
        '''
        Certain variables are saved to hdf5 file
        '''
        self._blocks2table()
        variables2save = ['parameters', 'stimulus_frame_info', 'configs', 'user_data', 'software_environment', 'block']#['experiment_name', 'experiment_config_name', 'frame_times']
        if self.machine_config.EXPERIMENT_FILE_FORMAT == 'hdf5':
            self.datafile = experiment_data.CaImagingData(self.outputfilename)
            self._prepare_data2save()
            [setattr(self.datafile, v, getattr(self,v)) for v in variables2save if hasattr(self, v) and v not in ['configs', 'software_environment']]
            self.datafile.save(variables2save)
            if hasattr(self, 'analog_input'):#Sync signals are recorded by stim
                self.datafile.sync, self.datafile.sync_scaling=signal.to_16bit(self.analog_input.ai_data)
                self.datafile.save(['sync', 'sync_scaling'])
                self.datafile.sync2time()
                self.datafile.check_timing()
            self.datafile.close()
            self.datafilename=self.datafile.filename
        elif self.machine_config.EXPERIMENT_FILE_FORMAT == 'mat':
            self.datafile = {}
            self._prepare_data2save()
            for v in variables2save:
                if hasattr(self, v):
                    self.datafile[v] = getattr(self,v)
            self._data2matfile_compatible()
            if self.machine_config.PLATFORM == 'hi_mea':
                #the latest file's name with a specific format
                latest_file = fileop.find_latest(os.path.split(experiment_data.get_user_experiment_data_folder(self.machine_config))[0],extension=None)#TODO: extension tbd
                if latest_file is None:
                    filename_prefix = ''
                else:
                    filename_prefix = str(os.path.split(latest_file)[1].replace(os.path.splitext(latest_file)[1],'')[:-1])
                fn = experiment_data.get_recording_path(self.machine_config, self.parameters, prefix = filename_prefix)
                fn = os.path.join(os.path.split(os.path.split(fn)[0])[0], os.path.split(fn)[1])
            else:
                if self.machine_config.PLATFORM == 'epos':
                    filename_prefix = ''
                else:
                    filename_prefix = 'stim'
                fn = experiment_data.get_recording_path(self.machine_config, self.parameters, prefix = filename_prefix)
            self.datafilename=fn
            scipy.io.savemat(fn, self.datafile, oned_as = 'column',do_compression=not True) 
            
    def _backup(self, filename):
        dst=os.path.join(self.machine_config.BACKUP_PATH, 'raw', os.path.join(*str(self.parameters['outfolder']).split(os.sep)[-2:]))
        if not os.path.exists(dst):
            os.makedirs(dst)
        try:
            shutil.copy(filename, dst)
        except:
            raise RuntimeError('Saving {0} to backup failed'.format(filename))
            
    def _data2matfile_compatible(self):
        '''Make sure that keys are not longer than 31 characters'''
        max_len = 31
        for k1 in self.datafile.keys():
            if (isinstance(self.datafile[k1], dict) and self.datafile[k1] == {}) or (isinstance(self.datafile[k1], list) and self.datafile[k1] == []):
                del self.datafile[k1]
            elif len(k1)>max_len:
                self.datafile[k1[:max_len]] = self.datafile[k1]
                del self.datafile[k1]
            if self.datafile.has_key(k1) and hasattr(self.datafile[k1], 'keys'):
                for k2 in self.datafile[k1].keys():
                    if (isinstance(self.datafile[k1][k2], dict) and self.datafile[k1][k2] == {}) or (isinstance(self.datafile[k1][k2], list) and self.datafile[k1][k2] == []):
                        del self.datafile[k1][k2]
                    elif len(k2)>max_len:
                        self.datafile[k1][k2[:max_len]] = self.datafile[k1][k2]
                        del self.datafile[k1][k2]
                    if self.datafile[k1].has_key(k2) and hasattr(self.datafile[k1][k2], 'keys'):
                        for k3 in self.datafile[k1][k2].keys():
                            if (isinstance(self.datafile[k1][k2][k3], dict) and self.datafile[k1][k2][k3] == {}) or (isinstance(self.datafile[k1][k2][k3], list) and self.datafile[k1][k2][k3] == []):
                                del self.datafile[k1][k2][k3]
                            elif len(k3)>max_len:
                                self.datafile[k1][k2][k3[:max_len]] = self.datafile[k1][k2][k3]
                                del self.datafile[k1][k2][k3]

    def _send_himea_cmd(self, cmd):
       if self.config.ENABLE_MEA_START_COMMAND:
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.connect("tcp://12.0.1.1:75000")
            socket.send(cmd)
            socket.recv()#This is blocking!!!
        
def inject_trigger(port,pin,delay):
    d=digital_io.ArduinoIO(port)
    d.set_pin(pin,1)
    time.sleep(delay)
    d.set_pin(pin,1)
    time.sleep(1.0)
    d.set_pin(pin,1)
    d.close()
    
    
        
        
if test_mode:        
    class TestCaImaging(unittest.TestCase):
        def setUp(self):
            self.configname = 'GUITestConfig'
            #Erase work folder, including context files
            import visexpman.engine.vision_experiment.configuration
            self.machine_config = utils.fetch_classes('visexpman.users.test', 'GUITestConfig', required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig,direct = False)[0][1]()
            self.machine_config.user_interface_name='ca_imaging'
            self.machine_config.user = 'test'
            fileop.cleanup_files(self.machine_config)
            self.context = visexpman.engine.application_init(user = 'test', config = self.configname, user_interface_name = 'ca_imaging')
            self.dont_kill_processes = introspect.get_python_processes()
            self._scanning_params()
            
        def tearDown(self):
            print 1
            if hasattr(self, 'context'):
                visexpman.engine.stop_application(self.context)
                print 2
            introspect.kill_python_processes(self.dont_kill_processes)
            
        def _send_commands_to_stim(self, commands):
            from visexpman.engine.hardware_interface import queued_socket
            import multiprocessing
            client = queued_socket.QueuedSocket('{0}-{1} socket'.format('main_ui', 'ca_imaging'), 
                                                                                        False, 
                                                                                        10001,
                                                                                        multiprocessing.Queue(), 
                                                                                        multiprocessing.Queue(), 
                                                                                        ip= '127.0.0.1',
                                                                                        log=None)
            client.start()
            for command in commands:
                client.send(command)
            return client
            
        def _scanning_params(self):
            parameters = {
                'recording_channels' : ['SIDE', 'TOP'], 
                'enable_scanner_synchronization' : False, 
                'save2file' : True,
                'scanning_range' : utils.rc((110.0, 100.0)),
                'resolution' : 1.0, 
                'resolution_unit' : 'um/pixel', 
                'scan_center' : utils.rc((120.0, 120.0)),
                'trigger_width' : 0.0,
                'trigger_delay' : 0.0,
                'status' : 'preparing', 
                'averaging':2,
                'id':str(int(numpy.round(time.time(), 2)*100)),
                'analog_input_sampling_rate': 500000,
                'analog_output_sampling_rate': 500000,
                'stimulus_flash_trigger_duty_cycle' : 0.5, 
                'stimulus_flash_trigger_delay' : 0.0, }
            constraints = {}
            constraints['enable_flybackscan']=False
            constraints['enable_scanner_phase_characteristics']=True
            constraints['scanner_position_to_voltage']=self.machine_config.POSITION_TO_SCANNER_VOLTAGE
            constraints['xmirror_max_frequency']=self.machine_config.XMIRROR_MAX_FREQUENCY
            constraints['ymirror_flyback_time']=self.machine_config.Y_MIRROR_MIN_FLYBACK_TIME
            constraints['sample_frequency']=parameters['analog_output_sampling_rate']
            constraints['max_linearity_error']=5e-2
            constraints['phase_characteristics']=self.machine_config.SCANNER_CHARACTERISTICS['PHASE']
            constraints['gain_characteristics']=self.machine_config.SCANNER_CHARACTERISTICS['GAIN']
            #Generate scanner signals and data mask
            xsignal,ysignal,frame_trigger_signal, valid_data_mask,signal_attributes =\
                                scanner_control.generate_scanner_signals(parameters['scanning_range'], 
                                                                                    parameters['resolution'], 
                                                                                    parameters['scan_center'], 
                                                                                    constraints)
            #Generate stimulus strigger signal
            stimulus_flash_trigger_signal, signal_attributes['real_duty_cycle'] = scanner_control.generate_stimulus_flash_trigger(
                                                                                                                        parameters['stimulus_flash_trigger_duty_cycle'], 
                                                                                                                        parameters['stimulus_flash_trigger_delay'], 
                                                                                                                        signal_attributes, 
                                                                                                                        constraints)
            for pn in ['xsignal', 'ysignal', 'stimulus_flash_trigger_signal', 'frame_trigger_signal', 'valid_data_mask']:
                parameters[pn] = locals()[pn]
            parameters.update(constraints)
            parameters.update(signal_attributes)
            self.parameters=parameters
            
        def test_01_ca_imaging_app(self):
            from visexpman.engine.visexp_app import run_ca_imaging
            commands = [{'function': 'test'}]
            commands.append({'function': 'exit_application'})
            client = self._send_commands_to_stim(commands)
            run_ca_imaging(self.context, timeout=None)
            t0=time.time()
            while True:
                msg = client.recv()
                if msg is not None or time.time() - t0>20.0:
                    break
                time.sleep(1.0)
            client.terminate()
            self.assertNotIn('error', fileop.read_text_file(self.context['logger'].filename).lower())
            self.assertIn('test1', fileop.read_text_file(self.context['logger'].filename).lower())
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq,  'Daq tests disabled')
        def test_02_run_experiment(self):
            source = fileop.read_text_file(os.path.join(fileop.visexpman_package_path(), 'users', 'test', 'test_stimulus.py'))
            experiment_names = ['GUITestExperimentConfig', 'TestCommonExperimentConfig']
            parameters = {
                'experiment_name': '',
                'experiment_config_source_code' : source,
                'cell_name': 'cell0', 
                'averaging':1,
                'stimulation_device' : '', 
                'recording_channels' : ['SIDE'], 
                'save2file' : True,
                'enable_scanner_synchronization' : False, 
                'scanning_range' : utils.rc((100.0, 100.0)),
                'resolution' : 1.0, 
                'resolution_unit' : 'um/pixel', 
                'scan_center' : utils.rc((0.0, 0.0)),
                'trigger_width' : 0.0,
                'trigger_delay' : 0.0,
                'status' : 'preparing', 
                'id':str(int(numpy.round(time.time(), 2)*100)),
                'xsignal':numpy.ones(10000),
                'ysignal':numpy.ones(10000),
                'stimulus_flash_trigger_signal':numpy.ones(10000),
                'frame_trigger_signal':numpy.ones(10000),
                'analog_input_sampling_rate': 10000,
                'analog_output_sampling_rate': 10000,}
            commands = []
            for experiment_name in experiment_names:
                import copy
                pars = copy.deepcopy(parameters)
                pars['experiment_name'] = experiment_name
                commands.append({'function': 'start_imaging', 'args': [pars]})
            commands.append({'function': 'exit_application'})
            client = self._send_commands_to_stim(commands)
            from visexpman.engine.visexp_app import run_ca_imaging
            run_ca_imaging(self.context, timeout=None)
            t0=time.time()
            while True:
                msg = client.recv()
                if msg is not None or time.time() - t0>20.0:
                    break
                time.sleep(1.0)
            client.terminate()
            self.assertNotIn('error', fileop.read_text_file(self.context['logger'].filename).lower())
            
        @unittest.skipIf(not unittest_aggregator.TEST_daq, 'Daq tests disabled')
        def test_03_snap_and_live_imaging(self):
            commands = []
            commands.append({'function': 'live_scan_start', 'args': [self.parameters]})
            commands.append({'function': 'live_scan_stop'})
            p2=copy.deepcopy(self.parameters)
            time.sleep(0.1)
            p2['id'] = str(int(numpy.round(time.time(), 2)*100))
            commands.append({'function': 'snap_ca_image', 'args': [p2]})
            commands.append({'function': 'live_scan_stop'})
            p3=copy.deepcopy(self.parameters)
            time.sleep(0.1)
            p3['id'] = str(int(numpy.round(time.time(), 2)*100))
            commands.append({'function': 'live_scan_start', 'args': [p3]})
            commands.extend([{'function': 'dummy'} for i in range(10)])
            commands.append({'function': 'live_scan_stop'})
            p4=copy.deepcopy(self.parameters)
            time.sleep(0.1)
            p4['id'] = str(int(numpy.round(time.time(), 2)*100))
            commands.append({'function': 'snap_ca_image', 'args': [p4]})
            commands.append({'function': 'exit_application'})
            client = self._send_commands_to_stim(commands)
            from visexpman.engine.visexp_app import run_ca_imaging
            run_ca_imaging(self.context, timeout=None)
            t0=time.time()
            while True:
                msg = client.recv()
                if msg is not None or time.time() - t0>20.0:
                    break
                time.sleep(1.0)
            client.terminate()
            time.sleep(2)
            self.assertNotIn('error', fileop.read_text_file(self.context['logger'].filename).lower().replace('max_linearity_error',''))
            #check context file
            image_context = utils.array2object(hdf5io.read_item(fileop.get_context_filename(self.context['machine_config']),'context', filelocking=False))
            self.assertIn('save', image_context.keys())
            self.assertIn('display', image_context.keys())
            self.assertEqual(image_context['display'].shape, (self.parameters['scanning_range']['row']*self.parameters['resolution'],self.parameters['scanning_range']['col']*self.parameters['resolution'],3))
            self.assertEqual(image_context['save'].shape, 
                        (len(self.parameters['recording_channels']),
                        self.parameters['scanning_range']['row']*self.parameters['resolution'],
                        self.parameters['scanning_range']['col']*self.parameters['resolution']))
            self.assertLess(abs(image_context['save'][0].std(axis=0)).max(), 10e-3*2**16)#no big difference between lines
            self.assertLess(abs(image_context['save'][1].std(axis=1)).max(), 10e-3*2**16)#no big difference between columns
            self.assertLess(numpy.diff(numpy.cast['float'](image_context['save'][0,0,:])).max(),0)#The intensity in each line decreases
            self.assertGreater(numpy.diff(numpy.cast['float'](image_context['save'][1,:,0])).min(),0)#The intensity in each column increase
            #saved and displayed images should be the same
            #return numpy.cast['uint16'](((image_cut+self.config.MAX_PMT_NOISE_LEVEL)/(2*self.config.MAX_PMT_NOISE_LEVEL+self.config.MAX_PMT_VOLTAGE))*(2**16-1))
            display_vs_scaled_image_scaling_factor = \
                        self.context['machine_config'].MAX_PMT_VOLTAGE/(self.context['machine_config'].MAX_PMT_VOLTAGE+2*self.context['machine_config'].MAX_PMT_NOISE_LEVEL)
            maxpmtvoltage = self.context['machine_config'].MAX_PMT_VOLTAGE
            maxnoiselevel = self.context['machine_config'].MAX_PMT_NOISE_LEVEL
            scaling16bit = (2**16-1)
            saved = numpy.cast['float'](image_context['save'][0])
            displayed = image_context['display'][:,:,1]
            numpy.testing.assert_almost_equal(saved/scaling16bit*(maxpmtvoltage+2*maxnoiselevel) - maxnoiselevel, displayed*maxpmtvoltage,3)
            saved = numpy.cast['float'](image_context['save'][1])
            displayed = image_context['display'][:,:,0]
            numpy.testing.assert_almost_equal(saved/scaling16bit*(maxpmtvoltage+2*maxnoiselevel) - maxnoiselevel, displayed*maxpmtvoltage,3)
            datafiles = experiment_data.listdir_fullpath(fileop.get_user_experiment_data_folder( self.context['machine_config']))
            datafiles.sort()
            self.assertEqual(numpy.array(map(os.path.getsize,datafiles)).argmax(),2)
            #check content of datafiles
            for datafile in datafiles:
                print datafile
                h=hdf5io.Hdf5io(datafile,filelocking=False)
                saved_parameters = h.findvar('imaging_parameters')
                nframes = h.findvar('imaging_run_info')['acquired_frames']
                self.assertTrue(isinstance(saved_parameters,dict))
                h.load('raw_data')
                self.assertEqual(h.raw_data.shape[1], len(self.parameters['recording_channels']))#Check if number of recorded channels is correct            
                for frame_i in range(h.raw_data.shape[0]):
                    numpy.testing.assert_almost_equal(numpy.cast['float'](h.raw_data[frame_i,0]),numpy.cast['float'](image_context['save'][0,:,:]),-2)
                    numpy.testing.assert_almost_equal(numpy.cast['float'](h.raw_data[frame_i,1]),numpy.cast['float'](image_context['save'][1,:,:]),-2)
                h.close()
                
if __name__=='__main__':
    unittest.main()
