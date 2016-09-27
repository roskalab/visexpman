import time
import os.path
import tempfile
import uuid
import hashlib
import scipy.io
import io
import StringIO
import zipfile
import numpy
import inspect
import cPickle as pickle
import traceback
import gc
import shutil
import copy
import multiprocessing
import tables
import sys
import zmq

import experiment_data
import visexpman.engine
from visexpman.engine.generic import log,utils,fileop,introspect,signal
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
except IOError:
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
                                parameters['frame_trigger_signal']*self.config.FRAME_TRIGGER_AMPLITUDE])
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
        self.digital_output = digital_output
        
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
        pass
    
    def wait4newfiletrigger(self):
        files = os.listdir(self.machine_config.TRIGGER_PATH)
        def is_new_file(files):
            return len(files) < len(os.listdir(self.machine_config.TRIGGER_PATH))
        return self._wait4trigger(is_new_file, (files), {})
            
    def set_trigger(self, pin):
        self.digital_output.set_pin(pin, True)
        
    def clear_trigger(self,pin):
        self.digital_output.set_pin(pin, False)
        
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
        if self.machine_config.DIGITAL_IO_PORT != False and parameters!=None:#parameters = None if experiment duration is calculated
            digital_output_class = instrument.ParallelPort if self.machine_config.DIGITAL_IO_PORT == 'parallel port' else digital_io.SerialPortDigitalIO
            self.digital_output = digital_output_class(self.machine_config, self.log)
        else:
            self.digital_output = None
        Trigger.__init__(self, machine_config, queues, self.digital_output)
        if self.digital_output!=None:#Digital output is available
            self.clear_trigger(self.config.BLOCK_TRIGGER_PIN)
            self.clear_trigger(self.config.FRAME_TRIGGER_PIN)
        #Helper functions for getting messages from socket queues
        queued_socket.QueuedSocketHelpers.__init__(self, queues)
        self.user_data = {}
        self.abort = False
        
    def execute(self):
        '''
        Calls the run method of the experiment class. 
        Also takes care of all communication, synchronization with other applications and file handling
        '''
        try:
            self.prepare()#Computational intensive precalculations for stimulus
            self.printl('Starting stimulation {0}/{1}'.format(self.name,self.parameters['id']))
            time.sleep(0.1)
            
            if self.machine_config.PLATFORM=='hi_mea':
                #send start signal
                self._send_himea_cmd("start")
            elif self.machine_config.PLATFORM=='elphys_retinal_ca':
                self.send({'trigger':'stim started'})
            elif self.machine_config.PLATFORM=='mc_mea':
                pass
            elif self.machine_config.PLATFORM=='us_cortical' and self.machine_config.ENABLE_ULTRASOUND_TRIGGERING:
                import serial
                s=serial.Serial(port='COM1',baudrate=9600)
                s.write('e')
                s.close()
                self.send({'trigger':'stim started'})
            self.log.suspend()#Log entries are stored in memory and flushed to file when stimulation is over ensuring more reliable frame rate
            try:
                self.run()
            except:
                self.send({'trigger':'stim error'})
                exc_info = sys.exc_info()
                raise exc_info[0], exc_info[1], exc_info[2]#And reraise exception such that higher level modules could display it
            self.log.resume()
            if self.machine_config.PLATFORM=='hi_mea':
                #send stop signal
                self._send_himea_cmd("stop")
            elif self.machine_config.PLATFORM=='elphys_retinal_ca' or self.machine_config.PLATFORM=='mc_mea' or self.machine_config.PLATFORM=='us_cortical':
                self.send({'trigger':'stim done'})#Notify main_ui about the end of stimulus. sync signal and ca signal recording needs to be terminated
            if not self.abort:
                self.printl('Stimulation ended')
                self._save2file()
                self.printl('Stimulus info saved to {0}'.format(self.datafilename))
                if self.machine_config.PLATFORM=='elphys_retinal_ca' or self.machine_config.PLATFORM=='us_cortical':
                    self.send({'trigger':'stim data ready'})
            else:
                self.printl('Stimulation stopped')
            if self.machine_config.PLATFORM=='mc_mea':
                self.trigger_pulse(self.machine_config.ACQUISITION_TRIGGER_PIN, self.machine_config.START_STOP_TRIGGER_WIDTH,polarity=self.machine_config.ACQUISITION_TRIGGER_POLARITY)
            self.frame_rates = numpy.array(self.frame_rates)
            if len(self.frame_rates)>0:
                fri = 'mean: {0}, std {1}, max {2}, min {3}, values: {4}'.format(self.frame_rates.mean(), self.frame_rates.std(), self.frame_rates.max(), self.frame_rates.min(), numpy.round(self.frame_rates,0))
                self.log.info(fri, source = 'stim')
        except:
            exc_info = sys.exc_info()
            raise exc_info[0], exc_info[1], exc_info[2]#And reraise exception such that higher level modules could display it
        finally:
            s.close()#If something goes wrong, close serial port
            

    def close(self):
        if hasattr(self.digital_output, 'release_instrument'):
                self.digital_output.release_instrument()

    def printl(self, message, loglevel='info', stdio = True):
        utils.printl(self, message, loglevel, stdio)

    def check_abort(self):
        if is_key_pressed(self.machine_config.KEYS['abort']) or utils.get_key(self.recv(put_message_back=True), 'function') == 'stop_all':
            self.abort = True

    def _prepare_data2save(self):
        '''
        Pack software enviroment and configs
        '''
        if self.machine_config.EXPERIMENT_FILE_FORMAT == 'hdf5':
            setattr(self.datafile, 'software_environment_{0}'.format(self.machine_config.user_interface_name), experiment_data.pack_software_environment())
            setattr(self.datafile, 'configs_{0}'.format(self.machine_config.user_interface_name), experiment_data.pack_configs(self))
        elif self.machine_config.EXPERIMENT_FILE_FORMAT == 'mat':
            self.datafile['software_environment_{0}'.format(self.machine_config.user_interface_name)] = experiment_data.pack_software_environment()
            self.datafile['configs_{0}'.format(self.machine_config.user_interface_name)] = experiment_data.pack_configs(self)
        #Organize stimulus frame info. 'stimulus function' block starts saved after sfi entry and block ends before sfi entry. This has to be reordered
        block_start_indexes, block_end_indexes = experiment_data.get_block_entry_indexes(self.stimulus_frame_info, block_name = 'stimulus function')
        for i in block_start_indexes:
            self.stimulus_frame_info = utils.list_swap(self.stimulus_frame_info, i, i-1)
        for i in block_end_indexes:
            self.stimulus_frame_info = utils.list_swap(self.stimulus_frame_info, i, i+1)
        self.datafile.frame_times=self.screen.frame_times()
        
    def _save2file(self):
        '''
        Certain variables are saved to hdf5 file
        '''
        variables2save = ['parameters', 'stimulus_frame_info', 'configs_{0}', 'frame_times'.format(self.machine_config.user_interface_name), 'user_data', 'software_environment_{0}'.format(self.machine_config.user_interface_name)]#['experiment_name', 'experiment_config_name']
        if self.machine_config.EXPERIMENT_FILE_FORMAT == 'hdf5':
            self.datafile = hdf5io.Hdf5io(experiment_data.get_recording_path(self.parameters, self.machine_config, prefix = 'stim'),filelocking=False)
            self._prepare_data2save()
            res=[setattr(self.datafile, v, getattr(self,v)) for v in variables2save if hasattr(self, v)]
            self.datafile.save(variables2save)
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
                    filename_prefix = str(os.path.split(latest_file)[1].replace(fileop.file_extension(latest_file),'')[:-1])
                fn = experiment_data.get_recording_path(self.parameters, self.machine_config, prefix = filename_prefix)
                fn = os.path.join(os.path.split(os.path.split(fn)[0])[0], os.path.split(fn)[1])
            else:
                filename_prefix = 'stim'
                fn = experiment_data.get_recording_path(self.parameters, self.machine_config, prefix = filename_prefix)
            self.datafilename=fn
            scipy.io.savemat(fn, self.datafile, oned_as = 'column',do_compression=True) 
            
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
        
        
class ExperimentControl(object):#OBSOLETE
    '''
    Reimplemented version: 
    
    Call parameters:
    1. machine config
    2. queued sockets
    (3. mes connection)
    4. Application log

    Provides methods for running a single experiment or a series of experiments at different depths. These methods are inherited by experiment classes
    that contain the user defined stimulations and other experiment specific functions.
    
    This class supports the following platforms:
    1. MES - RC microscope for in vivo cortical Ca imaging/stimulation
    2. [NOT TESTED] Electrophysiology setup for single cell recordings: stimulation and recording electrophysiology data
    3. [PLANNED] Virtual reality /behavioral experiments
    4. [PLANNED] Multielectrode array experiments / stimulation
    '''

    def __init__(self, config, application_log):
        '''
        Performs some basic checks and sets call parameters
        '''
        if self.config.PLATFORM=='undefined':
            raise RuntimeError('Machine config should contain a valid platform name')
        self.application_log = application_log
        self.config = config
        if not hasattr(self, 'number_of_fragments'):
            self.number_of_fragments = 1
        from experiment import PreExperiment
        if not issubclass(self.__class__,PreExperiment): #In case of preexperiment, fragment durations are not expected
            if self.config.PLATFORM == 'rc_cortical' and not hasattr(self, 'fragment_durations'):
                raise RuntimeError('At MES platform self.fragment_durations variable is mandatory')
            if hasattr(self, 'fragment_durations'):
                if not hasattr(self.fragment_durations, 'index') and not hasattr(self.fragment_durations, 'shape'):
                    self.fragment_durations = [self.fragment_durations]

    def run_experiment(self, context, **kwargs):
        '''
        Runs a series or a single experiment depending on the call parameters
        
        Objective positions and/or laser intensity is adjusted at a series or experiments.
        '''
        self.kwargs = kwargs
        message_to_screen = ''
        if hasattr(self, 'objective_positions'):
            for i in range(len(self.objective_positions)):
                context['objective_position'] = self.objective_positions[i]                
                if hasattr(self, 'laser_intensities'):
                    context['laser_intensity'] = self.laser_intensities[i]
                context['experiment_count'] = '{0}/{1}'.format(i+1, len(self.objective_positions))
                message_to_screen += self.run_single_experiment(context)
                if self.abort:
                    break
                time.sleep(3.0)#Later connection with MES shall be checked
            self.queues['gui']['out'].put('Experiment sequence complete')
        else:
            message_to_screen = self.run_single_experiment(context)
        if self.abort:#Commands sent after abort are ignored
            utils.empty_queue(self.queues['gui']['in'])
        return message_to_screen

    def run_single_experiment(self, context):
        '''
        Runs a single experiment which parameters are determined by the context parameter and the self.parameters attribute
        '''
        for vn in ['stage_origin', 'screen_center', 'parallel_port']:
            if context.has_key(vn):
                setattr(self, vn, context[vn])
        message_to_screen = ''
        if self.config.PLATFORM == 'rc_cortical' and not self.connections['mes'].connected_to_remote_client(timeout = 3.0):
            message_to_screen = self.printl('No connection with MES, {0}'.format(self.connections['mes'].endpoint_name))
            return message_to_screen
        message = self._prepare_experiment(context)
        if message is not None:
            message_to_screen += message
            message = '{0} started at {1}' .format(self.name, utils.datetime_string())
            if context.has_key('experiment_count'):
                message = '{0} {1}'.format( context['experiment_count'],  message)
            message_to_screen += self.printl(message,  application_log = True) + '\n'
            if self.config.PLATFORM == 'rc_cortical':
                measurement_duration = numpy.round(numpy.array(self.fragment_durations).sum() + self.config.MES_RECORD_START_DELAY * len(self.fragment_durations), 1)
                self.printl('SOCmeasurement_startedEOC{0}EOP'.format(measurement_duration))
            self.finished_fragment_index = 0
            for fragment_id in range(self.number_of_fragments):
                if utils.is_abort_experiment_in_queue(self.queues['gui']['in'], False):
                    message_to_screen += self.printl('Experiment aborted',  application_log = True) + '\n'
                    self.abort = True
                    break
                elif utils.is_graceful_stop_in_queue(self.queues['gui']['in'], False):
                    message_to_screen += self.printl('Graceful stop requested',  application_log = True) + '\n'
                    break
                elif self._start_fragment(fragment_id):
                    if self.number_of_fragments == 1:
                        self.run()
                    else:
                        self.run(fragment_id)
                    if not self._finish_fragment(fragment_id):
                        self.abort = True
                        #close fragment files
                        self.fragment_files[fragment_id].close()
                        break #Do not record further fragments in case of error
                else:
                    self.abort = True
                    if not hasattr(self, 'analog_input') or not hasattr(self.analog_input, 'finish_daq_activity'):
                        break
                    elif self.analog_input.finish_daq_activity(abort = utils.is_abort_experiment_in_queue(self.queues['gui']['in'])):
                        self.printl('Analog acquisition finished')
                        break
                if self.abort:
                    break
        self._finish_experiment()
        #Send message to screen, log experiment completition
        message_to_screen += self.printl('Experiment finished at {0}' .format(utils.datetime_string()),  application_log = True) + '\n'
        if self.config.PLATFORM == 'rc_cortical':
            self.printl('SOCmeasurement_finishedEOC{0}EOP'.format(self.id))
        else:
            self.printl('SOCstim_finishedEOC{0}EOP'.format(self.id))
        self.application_log.flush()
        return message_to_screen

    def _load_experiment_parameters(self):
        if not self.parameters.has_key('id'):
            self.printl('Measurement ID is NOT provided')
            return False
        self.parameter_file = os.path.join(self.config.EXPERIMENT_DATA_PATH, self.parameters['id']+'.hdf5')
        if not os.path.exists(self.parameter_file):
            self.printl('Parameter file does NOT exists: {0}' .format(self.parameter_file))
            return False
        h = hdf5io.Hdf5io(self.parameter_file, filelocking=self.config.ENABLE_HDF5_FILELOCKING)
        mandatory_fields_to_load = ['parameters']
        fields_to_load = ['animal_parameters', 'anesthesia_history']
        if self.config.PLATFORM == 'rc_cortical':
            fields_to_load .append('xy_scan_parameters')
        fields_to_load.extend(mandatory_fields_to_load)
        for field in fields_to_load:
            value = h.findvar(field)
            if value is None:
                self.printl('{0} is NOT found in parameter file'.format(field))
                if field in mandatory_fields_to_load:
                    return False
            if field == 'parameters':
                self.parameters = dict(self.parameters.items() + value.items())
                if self.parameters.has_key('scan_mode'):
                    self.scan_mode = self.parameters['scan_mode']
                    if self.scan_mode == 'xz':
                        fields_to_load += ['xz_config', 'rois', 'roi_locations']
                self.id = self.parameters['id']
            else:
                setattr(self, field,  value)
        h.close()
        return True

    def _prepare_experiment(self, context):
        message_to_screen = ''
        self.frame_counter = 0
        self.stimulus_frame_info = []
        self.start_time = time.time()
        self.filenames = {}
        load_parameters_successful = self._load_experiment_parameters()
        if self.config.PLATFORM == 'rc_cortical':
           if not load_parameters_successful:
            self.abort = True
        elif not hasattr(self, 'id'):
            self.id = str(int(time.time()))
        if self.abort:
            return
        if self.config.PLATFORM == 'rc_cortical':
            if not self.parameters['enable_intrinsic']:
                #Check network connection before any interaction with mes
                if not self.connections['mes'].connected_to_remote_client():
                    self.printl('No connection with MES')
                    time.sleep(0.5)
                    return None
                result,  laser_intensity = self.mes_interface.read_laser_intensity()
                if result:
                    self.initial_laser_intensity = laser_intensity
                    self.laser_intensity = laser_intensity
                else:
                    self.printl('Laser intensity CANNOT be read')
                    return None
                parameters2set = ['laser_intensity', 'objective_position']
                for parameter_name2set in parameters2set:                
                    if self.parameters.has_key(parameter_name2set):
                        value = self.parameters[parameter_name2set]
                    elif context.has_key(parameter_name2set) :
                        value = context[parameter_name2set]
                    else:
                        value = None
                    if not value is None:
                        result, adjusted_value= getattr(self.mes_interface, 'set_'+parameter_name2set)(value)
                        if not result:
                            self.abort = True
                            self.printl('{0} is not set'.format(parameter_name2set.replace('_', ' ').capitalize()))
                        else:
                            self.printl('{0} is set to {1}'.format(parameter_name2set.replace('_', ' ').capitalize(), value))
                            setattr(self,  parameter_name2set,  value)
            #read stage and objective
            self.stage_position = self.stage.read_position() - self.stage_origin
            if not self.parameters['enable_intrinsic']:
                result, self.objective_position, self.objective_origin = self.mes_interface.read_objective_position(timeout = self.config.MES_TIMEOUT, with_origin = True)
                if not result:
                    time.sleep(0.4)#This message does not reach gui, perhaps a small delay will ensure it
                    self.printl('Objective position cannot be read, check STIM-MES connection')
                    return None
            else:
                self.objective_position = 0
                self.objective_origin = 0
        self._prepare_files()
        self._initialize_experiment_log()#TODO: needs to be merged with prepare_files
        self._initialize_devices()
        return message_to_screen 

    def _finish_experiment(self):
        self._finish_data_fragments()
        #Set back laser
        if hasattr(self, 'initial_laser_intensity') and self.parameters.has_key('laser_intensities'):
            result, adjusted_laser_intensity = self.mes_interface.set_laser_intensity(self.initial_laser_intensity)
            if not result:
                self.printl('Setting back laser did NOT succeed')
        self.printl('Closing devices')
        self._close_devices()
        utils.empty_queue(self.queues['gui']['out'])
        #Update logdata to files
        self.log.info('Experiment finished at {0}' .format(utils.datetime_string()))
        self.log.flush()

########## Fragment related ############
    def _start_fragment(self, fragment_id):
        self.printl('Start fragment {0}/{1} '. format(fragment_id+1,  self.number_of_fragments))
        self.stimulus_frame_info_pointer = 0
        self.frame_counter = 0
        self.stimulus_frame_info = []
        if self.config.PLATFORM == 'rc_cortical' and not self.parameters['enable_intrinsic']:
            if not self._pre_post_experiment_scan(is_pre=True):
                return False
        # Start ai recording
        if self.config.STIM_RECORDS_ANALOG_SIGNALS:
            self.analog_input = daq_instrument.AnalogIO(self.config, self.log, self.start_time,  id=0)
            if self.analog_input.start_daq_activity():
                self.printl('Analog signal recording started')
        if (self.config.PLATFORM == 'rc_cortical' or self.config.PLATFORM == 'ao_cortical'):
            self.mes_record_time = self.fragment_durations[fragment_id] + self.config.MES_RECORD_START_DELAY
            self.printl('Fragment duration is {0} s, expected end of recording {1}'.format(int(self.mes_record_time), utils.timestamp2hm(time.time() + self.mes_record_time)))
            if self.config.IMAGING_CHANNELS == 'both':
                channels = 'both'
            else :
                channels = None
            utils.empty_queue(self.queues['mes']['in'])
            if self.parameters.has_key('enable_intrinsic') and self.parameters['enable_intrinsic']:
                self.mes_interface.acquire_video(self.mes_record_time, self.config.CAMERA_MAX_FRAME_RATE, parameter_file = self.filenames['mes_fragments'][fragment_id])
                return True
        if self.config.PLATFORM == 'rc_cortical':
            #start two photon recording
            if self.scan_mode == 'xyz':
                scan_start_success, line_scan_path = self.mes_interface.start_rc_scan(self.roi_locations, 
                                                                                      parameter_file = self.filenames['mes_fragments'][fragment_id], 
                                                                                      scan_time = self.mes_record_time, 
                                                                                      channels = channels)
            else:
                if self.scan_mode == 'xz' and hasattr(self, 'roi_locations'):
                    #Before starting scan, set xz lines
                    if self.roi_locations is None:
                        self.printl('No ROIs found')
                        return False
                elif self.scan_mode == 'xy':
                    if hasattr(self, 'xy_scan_parameters') and not self.xy_scan_parameters is None:
                        self.xy_scan_parameters.tofile(self.filenames['mes_fragments'][fragment_id])
                scan_start_success, line_scan_path = self.mes_interface.start_line_scan(scan_time = self.mes_record_time, 
                    parameter_file = self.filenames['mes_fragments'][fragment_id], timeout = self.config.MES_TIMEOUT,  scan_mode = self.scan_mode, channels = channels)
            scan_start_success2 = False
            if not scan_start_success:
                self.printl('Scan did not start, retrying...')
                scan_start_success2, line_scan_path = self.mes_interface.start_line_scan(scan_time = self.mes_record_time, 
                    parameter_file = self.filenames['mes_fragments'][fragment_id], timeout = self.config.MES_TIMEOUT,  scan_mode = self.scan_mode)
            if scan_start_success2 or scan_start_success:
                time.sleep(1.0)
            else:
                self.printl('Scan start ERROR')
            return (scan_start_success2 or scan_start_success)
        elif self.config.PLATFORM == 'elphys_retinal_ca':
            #Set acquisition trigger pin to high
            self.parallel_port.set_data_bit(self.config.ACQUISITION_TRIGGER_PIN, 1)
            self.start_of_acquisition = self._get_elapsed_time()
            return True
        elif self.config.PLATFORM == 'epos':
            if self._wait_experiment_start_trigger():
                self.parallel_port.set_data_bit(self.config.ACQUISITION_TRIGGER_PIN, 1)
                return True
        elif self.config.PLATFORM == 'mc_mea':
            self.parallel_port.set_data_bit(self.config.ACQUISITION_START_PIN, 1)
            self.start_of_acquisition = self._get_elapsed_time()
            return True
        elif self.config.PLATFORM == 'elphys_retinal_ca':
            if self.parameters.has_key('enable_ca_recording') and self.parameters['enable_ca_recording']:
                command = 'SOCstart_experimentEOCid={0}EOP' .format(self.id)
                self.queues['imaging']['out'].put(command)
                utils.empty_queue(self.queues['imaging']['in'])
                result = False
                if utils.wait_data_appear_in_queue(self.queues['imaging']['in'], self.config.CA_IMAGING_START_TIMEOUT):
                    if 'imaging_started' in self.queues['imaging']['in'].get():
                        result = True
            else:
                result = True
            return result
        elif self.config.PLATFORM in ['standalone', 'ao_cortical']:
            return True
        return False

    def _stop_data_acquisition(self, fragment_id):
        '''
        Stops data acquisition processes:
        -analog input sampling
        -waits for mes data acquisition complete
        '''
        #Stop external measurements
        if self.config.PLATFORM == 'elphys_retinal_ca':
            #Clear acquisition trigger pin
            self.parallel_port.set_data_bit(self.config.ACQUISITION_TRIGGER_PIN, 0)
            data_acquisition_stop_success = True
        elif self.config.PLATFORM == 'epos':
            self.parallel_port.set_data_bit(self.config.ACQUISITION_TRIGGER_PIN, 0)
            data_acquisition_stop_success = True
        elif self.config.PLATFORM == 'mc_mea':
            self.parallel_port.pulse(self.config.ACQUISITION_STOP_PIN, 1e-3)
            data_acquisition_stop_success = True
        elif self.config.PLATFORM == 'rc_cortical' and not self.parameters['enable_intrinsic']:
            self.mes_timeout = 2.0 * self.fragment_durations[fragment_id]            
            if self.mes_timeout < self.config.MES_TIMEOUT:
                self.mes_timeout = self.config.MES_TIMEOUT
            if not utils.is_abort_experiment_in_queue(self.queues['gui']['in']):
                if self.scan_mode == 'xyz':
                    data_acquisition_stop_success =  self.mes_interface.wait_for_rc_scan_complete(self.mes_timeout)
                else:
                    data_acquisition_stop_success =  self.mes_interface.wait_for_line_scan_complete(self.mes_timeout)
                if not data_acquisition_stop_success:
                    self.printl('Line scan complete ERROR')
            else:
                data_acquisition_stop_success =  False
        elif self.config.PLATFORM == 'standalone':
            data_acquisition_stop_success =  True
        else:
            data_acquisition_stop_success =  True
        #Stop acquiring analog signals
        if hasattr(self.analog_input, 'finish_daq_activity') and self.analog_input.finish_daq_activity(abort = utils.is_abort_experiment_in_queue(self.queues['gui']['in'])):
            self.printl('Analog acquisition finished')
        return data_acquisition_stop_success

    def _finish_fragment(self, fragment_id):
        result = True
        aborted = False
        if self._stop_data_acquisition(fragment_id):
            if self.config.PLATFORM == 'rc_cortical' and not self.parameters['enable_intrinsic']:
                if not utils.is_abort_experiment_in_queue(self.queues['gui']['in']):
                    self.printl('Wait for data save complete')
                    if self.scan_mode == 'xyz':
                        scan_data_save_success = self.mes_interface.wait_for_rc_scan_save_complete(self.mes_timeout)
                    else:
                        scan_data_save_success = self.mes_interface.wait_for_line_scan_save_complete(self.mes_timeout)
                    self.printl('MES data save complete')
                    if not scan_data_save_success:
                        self.printl('Line scan data save error')
                else:
                    aborted = True
                    scan_data_save_success = False
                result = scan_data_save_success
            else:
                pass
            if not aborted and result:
                if self.config.PLATFORM == 'rc_cortical' and not self.parameters['enable_intrinsic']:
                    if self.mes_record_time > 30.0:
                        time.sleep(1.0)#Ensure that scanner starts???
                        try:
                            if not self._pre_post_experiment_scan(is_pre=False):
                                self.printl('Post experiment scan was NOT successful')
                        except:
                            self.printl(traceback.format_exc())
                self._save_fragment_data(fragment_id)
                if self.config.PLATFORM == 'rc_cortical':
                    for i in range(5):#Workaround for the temporary failure of queue.put().
                        time.sleep(0.1)
                        self.queues['gui']['out'].put('queue_put_problem_dummy_message')
                    time.sleep(0.1)
                    self.printl('SOCmeasurement_readyEOC{0}EOP'.format(self.id))#Notify gui about the new file
                    for i in range(5):
                        time.sleep(0.1)
                        self.queues['gui']['out'].put('queue_put_problem_dummy_message')
        else:
            result = False
            self.printl('Data acquisition stopped with error')
        if not aborted:
            self.finished_fragment_index = fragment_id
        return result

     ############### Devices ##################

    def _initialize_devices(self):
        '''
        All the devices are initialized here, that allow rerun like operations
        '''
        if hasattr(self.config, 'SERIAL_DIO_PORT') and self.config.PLATFORM != 'mc_mea':
            self.parallel_port = digital_io.SerialPortDigitalIO(self.config, self.log, self.start_time)
        elif self.config.PLATFORM == 'mc_mea':
            pass
        else:
            self.parallel_port = instrument.ParallelPort(self.config, self.log, self.start_time)
        self.filterwheels = []
        if hasattr(self.config, 'FILTERWHEEL_SERIAL_PORT'):
            self.number_of_filterwheels = len(self.config.FILTERWHEEL_SERIAL_PORT)
        else:
            #If filterwheels neither configured, nor enabled, two virtual ones are created, so that experiments calling filterwheel functions could be called
            self.number_of_filterwheels = 2
        if self.config.PLATFORM != 'elphys_retinal_ca':
            self.led_controller = daq_instrument.AnalogPulse(self.config, self.log, self.start_time, id = 1)#TODO: config shall be analog pulse specific, if daq enabled, this is always called
        self.analog_input = None #This is instantiated at the beginning of each fragment
        self.stage = stage_control.AllegraStage(self.config, self.log, self.start_time)
        if self.config.PLATFORM == 'rc_cortical' or self.config.PLATFORM == 'ao_cortical':
            self.mes_interface = mes_interface.MesInterface(self.config, self.queues, self.connections, log = self.log)

    def _close_devices(self):
        if self.config.PLATFORM != 'mc_mea':
            self.parallel_port.release_instrument()
        if self.config.OS == 'Windows':
            for filterwheel in self.filterwheels:
                filterwheel.release_instrument()
        if hasattr(self, 'led_controller'):
            self.led_controller.release_instrument()
        self.stage.release_instrument()


    ############### File handling ##################
    def _prepare_files(self):
        if hasattr(self,'scan_mode'):
            scan_mode = self.scan_mode
        else:
            scan_mode = ''
        if hasattr(self,'objective_position'):
            objective_position = self.objective_position
        else:
            objective_position = ''
        region_name = self.parameters.get('region_name', '')
        local_folder = 'd:\\tmp'
        if not os.path.exists(local_folder):
            local_folder = tempfile.mkdtemp()
            
        self.filenames = experiment_data.generate_filename(self.config, 
                                                                                self.id, 
                                                                                experiment_name = self.name_tag, 
                                                                                region_name = region_name, 
                                                                                scan_mode = scan_mode, 
                                                                                tmp_folder = local_folder,
                                                                                depth = objective_position)
        self._create_files()
        self.stimulus_frame_info_pointer = 0

    def _generate_filenames(self):
        ''''
        OBSOLETE
        -------------------------------
        Generates the necessary filenames for the experiment. The following files are generated during an experiment:
        experiment log file: 
        zipped:
            source code
            module versions
            experiment log

        Fragment file name formats:
        1) mes/hdf5: experiment_name_id_fragment_id
        2) elphys_retinal_ca/mat: experiment_name_fragment_id_index

        fragment file(s): measurement results, stimulus info, configs, zip
        '''
        self.filenames['fragments'] = []
        self.filenames['local_fragments'] = []#fragment files are first saved to a local, temporary file
        self.filenames['mes_fragments'] = []
        self.fragment_names = []
        for fragment_id in range(self.number_of_fragments):
            if hasattr(self.experiment_config, 'USER_FRAGMENT_NAME'):
                fragment_name = self.experiment_config.USER_FRAGMENT_NAME
            elif self.config.EXPERIMENT_FILE_FORMAT == 'mat':
                fragment_name = 'fragment_{0}' .format(self.name_tag)
            elif self.config.EXPERIMENT_FILE_FORMAT == 'hdf5':
                fragment_name = 'fragment_{0}_{1}_{2}' .format(self.name_tag, self.id, fragment_id)
            fragment_filename = os.path.join(self.config.EXPERIMENT_DATA_PATH, '{0}.{1}' .format(fragment_name, self.config.EXPERIMENT_FILE_FORMAT))
            if self.config.EXPERIMENT_FILE_FORMAT  == 'hdf5' and  (self.config.PLATFORM == 'rc_cortical' or self.config.PLATFORM == 'ao_cortical'):
                if hasattr(self, 'objective_position'):
                    if self.parameters.has_key('region_name'):
                        fragment_filename = fragment_filename.replace('fragment_', 
                        'fragment_{2}_{0:4}_{1}_'.format(self.parameters['region_name'], self.objective_position, self.scan_mode))
                    elif hasattr(self, 'stage_position'):
                        fragment_filename = fragment_filename.replace('fragment_', 
                        'fragment_{3}_{0:.1f}_{1:0=4.1f}_{2}_'.format(self.stage_position[0], self.stage_position[1], self.objective_position, self.scan_mode))
                self.filenames['mes_fragments'].append(fragment_filename.replace('hdf5', 'mat'))
            elif self.config.EXPERIMENT_FILE_FORMAT == 'mat':
                fragment_filename = fileop.generate_filename(fragment_filename, last_tag = str(fragment_id))
            local_folder = 'd:\\tmp'
            if not os.path.exists(local_folder):
                local_folder = tempfile.mkdtemp()
            local_fragment_file_name = os.path.join(local_folder, os.path.split(fragment_filename)[-1])
            self.filenames['local_fragments'].append(local_fragment_file_name)
            self.filenames['fragments'].append(fragment_filename)
            self.fragment_names.append(fragment_name.replace('fragment_', ''))

    def _create_files(self):
        self.fragment_files = []
        self.fragment_data = {}
        for fragment_file_name in self.filenames['local_datafile']:
            if self.config.EXPERIMENT_FILE_FORMAT  == 'hdf5':
                self.fragment_files.append(hdf5io.Hdf5io(fragment_file_name, filelocking=self.config.ENABLE_HDF5_FILELOCKING))
        if self.config.EXPERIMENT_FILE_FORMAT  == 'mat':
            pass

    def _initialize_experiment_log(self):
        date = utils.date_string()
        self.filenames['experiment_log'] = \
            fileop.generate_filename(os.path.join(self.config.EXPERIMENT_LOG_PATH, 'log_{0}_{1}.txt' .format(self.name_tag, date)))
        self.log = log.Log('experiment log' + uuid.uuid4().hex, self.filenames['experiment_log'], write_mode = 'user control', timestamp = 'elapsed_time')
        
    def _wait_experiment_start_trigger(self):
        '''
        Returns True if trigger occured
        '''
        utils.check_expected_parameter(self.config, 'EXPERIMENT_START_TRIGGER')
        result = False
        t0 = time.time()
        while True:
            if utils.is_abort_experiment_in_queue(self.queues['gui']['in'], False) or (hasattr(self, 'check_abort_pressed') and self.check_abort_pressed()):#abort command from keyboard or network 
                self.abort=True
                break
            if self.parallel_port.read_pin(self.config.EXPERIMENT_START_TRIGGER):#Check if trigger pin is high
                result = True
                break
            if hasattr(self.config, 'EXPERIMENT_START_TRIGGER_TIMEOUT') and time.time()-t0 > self.config.EXPERIMENT_START_TRIGGER_TIMEOUT: #If configured stop wait loop after a time
                self.printl('Experiment start trigger timeout')
                break
            time.sleep(1e-3)
        return result

    ########## Fragment data ############
    def _prepare_fragment_data(self, fragment_id):
        '''
        Collects and packs all the recorded and generated experiment data, depending on the platform but the following data is handled here:
        - stimulus-recording synchron signal
        - experiment log
        - electrophysiology data
        - user data from stimulation
        - stimulation function call info
        - source code of called software
        - roi data
        - animal parameters
        - anesthesia history
        - pre/post scan data
        '''
        if hasattr(self.analog_input, 'ai_data'):
            analog_input_data = self.analog_input.ai_data
        elif hasattr(self.config, 'SYSTEM_TEST') and self.config.SYSTEM_TEST:
            from visexpA.engine.datahandlers import matlabfile
            #Simulate analog data
            for f in fileop.filtered_file_list(os.path.join(self.config.TESTDATA_PATH, 'mes_simulator'), ['fragment', 'mat'], fullpath = True,filter_condition = 'and'):
                m = matlabfile.MatData(f)
                tduration = m.get_field(m.name2path('ts'))[0][0][0][0][-1]
                if tduration == self.mes_record_time:
                    break
            analog_input_data = hdf5io.read_item(f.replace('.mat', '.hdf5'), '_'.join(os.path.split(f.replace('.mat', ''))[1].split('_')[-3:]), filelocking=False)['sync_data']
        else:
            analog_input_data = numpy.zeros((2, 2))
            if self.config.PLATFORM != 'elphys_retinal_ca':
                self.printl('Analog input data is NOT available')
        stimulus_frame_info_with_data_series_index, rising_edges_indexes, pulses_detected =\
                            experiment_data.preprocess_stimulus_sync(\
                            analog_input_data[:, self.config.STIM_SYNC_CHANNEL_INDEX], 
                            stimulus_frame_info = self.stimulus_frame_info[self.stimulus_frame_info_pointer:], 
                            sync_signal_min_amplitude = self.config.SYNC_SIGNAL_MIN_AMPLITUDE)
        if not pulses_detected and self.config.PLATFORM != 'elphys_retinal_ca':
            self.printl('Stimulus sync signal is NOT detected')
        if self.config.PLATFORM == 'rc_cortical' and not self.parameters['enable_intrinsic']:
            a, b, pulses_detected =\
            experiment_data.preprocess_stimulus_sync(\
                            analog_input_data[:, self.config.MES_SYNC_CHANNEL_INDEX], sync_signal_min_amplitude = self.config.SYNC_SIGNAL_MIN_AMPLITUDE)
            if not pulses_detected:
                self.printl('MES sync signal is NOT detected')
        if not hasattr(self, 'experiment_specific_data'):
                self.experiment_specific_data = 0
        if hasattr(self, 'source_code'):
            experiment_source = self.source_code
        else:
            experiment_source = utils.file_to_binary_array(inspect.getfile(self.__class__).replace('.pyc', '.py'))
        software_environment = experiment_data.pack_software_environment(self.experiment_source_code)
        data_to_file = {
                                    'sync_data' : analog_input_data, 
                                    'current_fragment' : fragment_id, #deprecated
                                    'actual_fragment' : fragment_id,
                                    'rising_edges_indexes' : rising_edges_indexes, 
                                    'number_of_fragments' : self.number_of_fragments, 
                                    'generated_data' : self.experiment_specific_data, 
                                    'experiment_source' : experiment_source, 
                                    'software_environment' : software_environment, 
                                    'experiment_name': self.name, 
                                    }
        if len(self.parameters.keys()) > 0:#Empty dictionary not saved
            data_to_file['call_parameters'] = self.parameters
        if self.config.EXPERIMENT_FILE_FORMAT == 'hdf5':
            data_to_file['machine_config'] = experiment_data.pickle_config(self.config)
            data_to_file['experiment_config'] = experiment_data.pickle_config(self.experiment_config)
            data_to_file['experiment_log'] = numpy.fromstring(pickle.dumps(self.log.log_dict), numpy.uint8)
            stimulus_frame_info = {}
            if stimulus_frame_info_with_data_series_index != 0:
                stimulus_frame_info = self.stimulus_frame_info
            if hasattr(self, 'animal_parameters'):
                data_to_file['animal_parameters'] = self.animal_parameters
            else:
                self.printl('NO animal parameters saved')
            if self.config.PLATFORM == 'rc_cortical':
                data_to_file['mes_data_path'] = os.path.split(self.filenames['mes_fragments'][fragment_id])[-1]
                for attribute_name in ['rois', 'roi_locations', 'xz_config', 'prepost_scan_image', 'scanner_trajectory', 'anesthesia_history']:
                    if hasattr(self, attribute_name):
                        data_to_file[attribute_name] = getattr(self, attribute_name)
        elif self.config.EXPERIMENT_FILE_FORMAT == 'mat':
            stimulus_frame_info = stimulus_frame_info_with_data_series_index
            data_to_file['config'] = experiment_data.save_config(None, self.config, self.experiment_config)
            if self.config.PLATFORM == 'elphys_retinal_ca':
                data_to_file['start_of_acquisition'] = self.start_of_acquisition
        data_to_file['stimulus_frame_info'] = stimulus_frame_info
        self.stimulus_frame_info_pointer = len(self.stimulus_frame_info)
        if self.config.PLATFORM == 'rc_cortical':
            if hasattr(self, 'laser_intensity'):
                data_to_file['laser_intensity'] = self.laser_intensity
        return data_to_file

    def _save_fragment_data(self, fragment_id):
        data_to_file = self._prepare_fragment_data(fragment_id)
        if self.config.EXPERIMENT_FILE_FORMAT == 'hdf5':
            #Save stage and objective position
            if self.config.PLATFORM == 'rc_cortical':
                data_to_file['position'] = utils.pack_position(self.stage_position, self.objective_position)
            setattr(self.fragment_files[fragment_id], self.filenames['names'][fragment_id], data_to_file)
            self.fragment_files[fragment_id].save([self.filenames['names'][fragment_id]])
            self.fragment_files[fragment_id].close()
            if hasattr(self, 'fragment_durations'):
                time.sleep(1.0 + 0.01 * self.fragment_durations[fragment_id])#Wait till data is written to disk
            else:
                time.sleep(1.0)
            shutil.copy(self.filenames['local_datafile'][fragment_id], self.filenames['datafile'][fragment_id])
        elif self.config.EXPERIMENT_FILE_FORMAT == 'mat':
            self.fragment_data[self.filenames['local_datafile'][fragment_id]] = data_to_file
        self.printl('Measurement data saved to: {0}'.format(os.path.split(self.filenames['datafile'][fragment_id])[1]))

    def _finish_data_fragments(self):
        #Experiment log, source code, module versions
        experiment_log_dict = self.log.log_dict
        if self.config.EXPERIMENT_FILE_FORMAT == 'hdf5':
            pass
        elif self.config.EXPERIMENT_FILE_FORMAT == 'mat':
            fragment_id = 0
            for fragment_path, data_to_mat in self.fragment_data.items():
                data_to_mat['experiment_log_dict'] = experiment_log_dict
                data_to_mat['config'] = experiment_data.save_config(None, self.config, self.experiment_config)
                scipy.io.savemat(fragment_path, data_to_mat, oned_as = 'row', long_field_names=True)
                shutil.move(self.filenames['local_datafile'][fragment_id], self.filenames['datafile'][fragment_id])
                fragment_id += 1

    def _pre_post_experiment_scan(self, is_pre):
        '''
        Performs a short scans before and after experiment to save scanner signals and/or red channel static image
        '''
        initial_mes_line_scan_settings_filename = fileop.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'initial_mes_line_scan_settings.mat'))
        xy_static_scan_filename = fileop.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'measure_red_green_channel_xy.mat'))
        scanner_trajectory_filename = fileop.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'measure_scanner_signals.mat'))
        #Save initial line scan settings
        if hasattr(self, 'animal_parameters') and self.parameters.has_key('scan_mode') and self.parameters['scan_mode'] == 'xy':
            if (utils.safe_has_key(self.animal_parameters, 'red_labeling') and self.animal_parameters['red_labeling'] == 'no') or not utils.safe_has_key(self.animal_parameters, 'red_labeling'):
                return True
        result, line_scan_path, line_scan_path_on_mes = self.mes_interface.get_line_scan_parameters(parameter_file = initial_mes_line_scan_settings_filename)
        if not result:
            if os.path.exists(initial_mes_line_scan_settings_filename):
                os.remove(initial_mes_line_scan_settings_filename)
            self.printl('Saving initial line scan parameter was NOT successful. Please check MES-STIM connection')
            return False
        #Measure red channel
        self.printl('Recording red and green channel')
        if hasattr(self, 'xy_scan_parameters'):
            self.xy_scan_parameters.tofile(xy_static_scan_filename)
        if self.config.BLACK_SCREEN_DURING_PRE_SCAN:
            self.show_fullscreen(color=0.0, duration=0.0)
        if hasattr(self, 'scan_region'):
            self.scan_region['xy_scan_parameters'].tofile(xy_static_scan_filename)
        result, red_channel_data_filename = self.mes_interface.line_scan(parameter_file = xy_static_scan_filename, scan_time=4.0,
                                                                           scan_mode='xy', channels=['pmtUGraw','pmtURraw'])
        if self.config.BLACK_SCREEN_DURING_PRE_SCAN and hasattr(self.experiment_config, 'pre_runnable') and self.experiment_config.pre_runnable is not None:
            self.experiment_config.pre_runnable.run()
            self._flip()
        if not result:
            try:
                if os.path.exists(initial_mes_line_scan_settings_filename):
                    os.remove(initial_mes_line_scan_settings_filename)
                if os.path.exists(red_channel_data_filename):
                    os.remove(red_channel_data_filename)
                self.printl('Recording red and green channel was NOT successful')
                return False
            except TypeError:
                traceback_info = traceback.format_exc()
                self.printl('{0},  {1}\n{2}'.format(initial_mes_line_scan_settings_filename, red_channel_data_filename, traceback_info))
                return False
        if not hasattr(self, 'prepost_scan_image'):
            self.prepost_scan_image = {}
        if is_pre:
            self.prepost_scan_image['pre'] = utils.file_to_binary_array(red_channel_data_filename)
        else:
            self.prepost_scan_image['post'] = utils.file_to_binary_array(red_channel_data_filename)
        if self.parameters.has_key('scan_mode') and self.parameters['scan_mode'] == 'xz':
            #Measure scanner signal
            self.printl('Recording scanner signals')
            shutil.copy(initial_mes_line_scan_settings_filename, scanner_trajectory_filename)
            result, scanner_trajectory_filename = self.mes_interface.line_scan(parameter_file = scanner_trajectory_filename, scan_time=2.0,
                                                                               scan_mode='xz', channels=['pmtURraw','ScX', 'ScY'], autozigzag = False)
            if not result:
                try:
                    if os.path.exists(initial_mes_line_scan_settings_filename):
                        os.remove(initial_mes_line_scan_settings_filename)
                    if os.path.exists(red_channel_data_filename):
                        os.remove(red_channel_data_filename)
                    if os.path.exists(scanner_trajectory_filename):
                        os.remove(scanner_trajectory_filename)
                except:
                    self.printl(('removing unnecessary files failed:', initial_mes_line_scan_settings_filename, red_channel_data_filename, scanner_trajectory_filename))
                self.printl('Recording scanner signals was NOT successful')
                return False
            if not hasattr(self, 'scanner_trajectory'):
                self.scanner_trajectory = {}
            if is_pre:
                self.scanner_trajectory['pre'] = utils.file_to_binary_array(scanner_trajectory_filename)
            else:
                self.scanner_trajectory['post'] = utils.file_to_binary_array(scanner_trajectory_filename)
            os.remove(scanner_trajectory_filename)
            if not is_pre:
                self.printl('Setting back green channel')
                shutil.copy(initial_mes_line_scan_settings_filename, scanner_trajectory_filename)
                result, scanner_trajectory_filename = self.mes_interface.line_scan(parameter_file = scanner_trajectory_filename, scan_time=1.5,
                                                                               scan_mode='xz', channels=['pmtUGraw'], autozigzag = False)
            if not result:
                self.printl('Setting back green channel was NOT successful')
        os.remove(initial_mes_line_scan_settings_filename)
        os.remove(xy_static_scan_filename)
        return True

    ############### Helpers ##################
    def _get_elapsed_time(self):
        return time.time() - self.start_time

    def printl(self, message,  application_log = False, experiment_log = True):
        '''
        Helper function that can be called during experiment. The message is sent to:
        -standard output
        -gui
        -experiment log
        '''
        print message
        self.queues['gui']['out'].put(str(message))
        if application_log:
            self.application_log.info(message)
        if hasattr(self, 'log') and experiment_log:
            self.log.info(str(message))
        return message
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
