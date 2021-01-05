import time,pdb
import os.path
import tempfile
import scipy.io
import numpy
import traceback
import shutil
import copy
import tables
import zmq
try:
    import PyDAQmx
    import PyDAQmx.DAQmxConstants as DAQmxConstants
    import PyDAQmx.DAQmxTypes as DAQmxTypes
except:
    print ('No PyDAQmx')
from visexpman.engine.vision_experiment import experiment_data
import visexpman.engine
from visexpman.engine.generic import utils,fileop,introspect,signal
from visexpman.engine.generic.graphics import is_key_pressed,check_keyboard
from visexpman.engine.hardware_interface import mes_interface,daq_instrument,stage_control,digital_io,queued_socket
from visexpman.engine.vision_experiment.screen import CaImagingScreen
try:
    import hdf5io
except ImportError:
    print('hdf5io not installed')

from visexpman.engine.generic.command_parser import ServerLoop
try:
    from visexpman.users.test import unittest_aggregator
    test_mode=True
except IOError:
    test_mode=False
import unittest

ENABLE_16_BIT = True

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
        elif self.digital_io.type=='ioboard':
            while True:
                if self.digital_io.read_pin(self.machine_config.STIM_START_TRIGGER_PIN, inverted=self.machine_config.PLATFORM=='epos'):
                    result = True
                    break
                self.check_abort()
                if self.abort:
                    break
        elif self.digital_io.type=='arduino':
            #All data in serial port buffer is  flushed.
            if self.digital_io.hwhandler.inWaiting()>0:
                print(self.read(100))
                self.digital_io.hwhandler.flushInput()
            #Check if trigger is fired too early
            time.sleep(1.5)
            if self.digital_io.hwhandler.inWaiting()>0:
                raise RuntimeError('Trigger missed!')
            #Trigger is fired when new bytes show up in serial port buffer
            while True:                
                self.check_abort()
                if self.abort:
                    break
                if self.digital_io.hwhandler.inWaiting()>0:
                    self.first_imaging_frame_timepoint=time.time()
                    result = True
                    self.digital_io.read()
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
        if hasattr(self.machine_config, 'DIGITAL_IO_PORT_TYPE') and self.machine_config.user_interface_name!='main_ui':
            skip_hw_init= hasattr(self, 'kwargs') and 'create_runnable' in self.kwargs and not self.kwargs['create_runnable']
            if skip_hw_init:
                return
            self.digital_io=digital_io.DigitalIO(self.machine_config.DIGITAL_IO_PORT_TYPE,self.machine_config.DIGITAL_IO_PORT, timeout=1e-3)
            Trigger.__init__(self, machine_config, queues, self.digital_io)
            if 0 and self.digital_io!=None:#Digital output is available
                self.clear_trigger(self.config.BLOCK_TIMING_PIN)
                self.clear_trigger(self.config.FRAME_TIMING_PIN)
        #Helper functions for getting messages from socket queues
        queued_socket.QueuedSocketHelpers.__init__(self, queues)
        self.user_data = {}
        self.abort = False
        self.check_frame_rate=True
        
    def start_sync_recording(self):
        class Conf(object):
            DAQ_CONFIG = [
                    {
                    'ANALOG_CONFIG' : 'ai', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 30 if self.sync_recording_duration>800 else 3.0,
                    'SAMPLE_RATE'  :self.machine_config.SYNC_RECORDER_SAMPLE_RATE,
                    'AI_CHANNEL' : self.machine_config.SYNC_RECORDER_CHANNELS,
                    'MAX_VOLTAGE' : 10.0,
                    'MIN_VOLTAGE' : -10.0,
                    'DURATION_OF_AI_READ' : 2*self.sync_recording_duration,
                    'ENABLE' : True
                    },]
        if self.sync_recording_duration==0:
            raise ValueError('Sync buffer is set to 0 because recording duration is 0. Please correct stimulus duration calculation')
        config=Conf()
        self.analog_input = daq_instrument.AnalogIO(config)
        self.sync_recorder_started=time.time()
        self.abort=not self.analog_input.start_daq_activity()
        self.printl('Sync signal recording started')
        
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
            if self.machine_config.CAMERA_TRIGGER_ENABLE:
                self.camera_trigger=digital_io.IOBoard(self.machine_config.CAMERA_IO_PORT_STIM)
            prefix='data' if self.machine_config.PLATFORM in  ['ao_cortical','resonant'] else 'stim'
            if self.machine_config.PLATFORM in ['standalone',  'intrinsic']:#TODO: this is just a hack. Standalone platform has to be designed
                self.parameters['outfolder']=self.machine_config.EXPERIMENT_DATA_PATH#parameters dict has to be created since there is no main_ui
                if hasattr(self, 'calculate_stimulus_duration'):
                    self.parameters['stimclass']=self.__class__.__name__
                else:
                    self.parameters['stimclass']=self.experiment_config.__class__.__name__
                self.parameters['outfilename']=experiment_data.get_recording_path(self.machine_config, self.parameters,prefix = 'data')
                from visexpman.engine.vision_experiment.experiment import get_experiment_duration
                self.parameters['duration']=get_experiment_duration(self.parameters['stimclass'], self.config)                    
            #Check if main_ui user and machine config class matches with stim's
            if 'user' in self.parameters and (self.parameters['user']!=self.machine_config.user or \
                self.parameters['machine_config']!=self.machine_config.__class__.__name__):
                    self.send({'trigger':'stim error'})
                    raise RuntimeError('Stim and Visexpman GUI user or machine config does not match: {0},{1},{2},{3}'\
                        .format(self.parameters['user'], self.machine_config.user, self.parameters['machine_config'], self.machine_config.__class__.__name__))
            self.outputfilename=self.parameters['outfilename']
            self.partial_save=self.parameters.get('Partial Save', False)
            #Computational intensive precalculations for stimulus
            self.prepare()
            #Control/synchronization with platform specific recording devices
            time.sleep(0.1)
            if hasattr(self,  'digital_io'):
                self.digital_io.set_pin(self.config.BLOCK_TIMING_PIN, 0)#Reset pin
            try:
                if self.machine_config.ENABLE_SYNC=='stim':
                    self.sync_recording_duration=self.parameters['duration']
                    if self.sync_recording_duration<0:
                        self.sync_recording_duration=self.machine_config.EXPERIMENT_MAXIMUM_DURATION*60
                    self.start_sync_recording()
#                    self.send({'trigger':'sync recording started'})
                if self.machine_config.PLATFORM=='ao_cortical':
                    self.sync_recording_duration=self.parameters['mes_record_time']/1000+1#little overhead making sure that the last sync pulses from MES are recorded
                    self.start_sync_recording()
                    self.start_ao()
                elif self.machine_config.PLATFORM=='hi_mea':
                    #send start signal
                    self._send_himea_cmd("start")
                elif self.machine_config.PLATFORM in ['retinal', 'elphys_retinal_ca']:
                    if self.machine_config.PLATFORM == 'retinal':
                        self.sync_recording_duration=self.parameters['duration']
                        self.start_sync_recording()
                    cmd='sec {0} filename {1}'.format(self.parameters['duration']+self.machine_config.CA_IMAGING_START_DELAY, self.parameters['outfolder'])
                    self.printl(cmd)
                    utils.send_udp(self.machine_config.CONNECTIONS['ca_imaging']['ip']['ca_imaging'],446,cmd)
                    time.sleep(self.machine_config.CA_IMAGING_START_DELAY)
                    self.send({'trigger':'stim started'})
                elif self.machine_config.PLATFORM=='mc_mea':
                    time.sleep(0.5)
                    self.digital_io.set_pin(self.machine_config.TRIAL_START_END_PIN,1)
                    time.sleep(0.5)
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
                elif self.machine_config.PLATFORM in ['standalone','epos', 'generic']:
                    if self.machine_config.WAIT4TRIGGER_ENABLED:
                        self.printl('Waiting for external trigger')
                    if hasattr(self.machine_config,'INJECT_START_TRIGGER'):
                        import threading
                        t=threading.Thread(target=inject_trigger, args=('/dev/ttyACM1',5,2))
                        t.start()
                    if self.machine_config.WAIT4TRIGGER_ENABLED and not self.wait4digital_input_trigger(self.machine_config.STIM_START_TRIGGER_PIN):
                        self.abort=True
                        self.send({'trigger':'stim error'})
                elif self.machine_config.PLATFORM == 'resonant':
                    if not self.parameters.get('Stimulus Only', False):
                        self.send({'mesc':'start'})
                        time.sleep(1.5)
                        response=self.recv()
                        self.mesc_error=True
                        #Sometimes message is sent over in  {u'mesc start command result': True} format and this is not detected
                        if hasattr(response, 'keys') and (('mesc start command result' in response and response['mesc start command result']) or (u'mesc start command result' in response and response[u'mesc start command result'])):
                            self.mesc_error=False
                        if self.mesc_error:
                            self.abort=True
                            self.mesc_error=True
                            self.printl('MESc did not start, aborting stimulus')
                            self.send({'trigger':'stim error'})
                        time.sleep(2)#ensure that imaging hass started. MESc start takes some time.
                elif self.machine_config.PLATFORM == '2p':
                    if not self.parameters.get('Stimulus Only', False):
                        self.send({'2p': 'start'})
                        t0=time.time()
                        while True:
                            if time.time()-t0>5:
                                break
                            response=self.recv()
                            if response!=None:
                                break
                            time.sleep(0.5)
                        if not hasattr(response, 'keys') or not response['start command result']:
                            self.abort=True
                            self.printl('Two photon recording did not start, aborting stimulus')
                            self.send({'trigger':'stim error'})
                            self.send({'2p': 'stop'})
                if self.machine_config.CAMERA_TRIGGER_ENABLE:
                    self.camera_trigger.set_waveform(self.machine_config.CAMERA_TRIGGER_FRAME_RATE,0,0)
                    time.sleep(self.machine_config.CAMERA_PRE_STIM_WAIT)
                    self.printl('Camera trigger enabled')
            except:
                self.abort=True
                self.send({'trigger':'stim error'})
                self.printl(traceback.format_exc())
                self.partial_save=False#if failed before starting stimulus, no partial data is saved
            self.log.suspend()#Log entries are stored in memory and flushed to file when stimulation is over ensuring more reliable frame rate
            self.experiment_start_timestamp=time.time()
            self._start_frame_capture()
            try:
                self.printl('Starting stimulation {0}/{1}'.format(self.name,self.parameters['id']))
                self.run()
            except:
                self.abort=True
                self.send({'trigger':'stim error'})
                self.printl(traceback.format_exc())
            self._stop_frame_capture()
            self.log.resume()
            #Terminate recording devices
            if self.machine_config.PLATFORM in ['retinal', 'elphys_retinal_ca', 'mc_mea', 'us_cortical', 'ao_cortical', 'resonant', 'behav', '2p', 'elphys', 'generic']:
                self.printl('Stimulation ended')
                self.send({'trigger':'stim done'})#Notify main_ui about the end of stimulus. sync signal and ca signal recording needs to be terminated
            if self.machine_config.CAMERA_TRIGGER_ENABLE:
                time.sleep(self.machine_config.CAMERA_POST_STIM_WAIT)
                self.camera_trigger.stop_waveform()
                self.printl('Camera trigger stopped')
            if self.machine_config.PLATFORM=='hi_mea':
                #send stop signal
                self._send_himea_cmd("stop")
            elif self.machine_config.PLATFORM=='intrinsic':
                self.camera.trigger.clear()
                self.camera.join()
            elif self.machine_config.PLATFORM=='ao_cortical':
                self.wait4ao()
            elif self.machine_config.PLATFORM == 'resonant':
                if not self.parameters.get('Stimulus Only', False) and not self.mesc_error:
                    self.send({'mesc':'stop'})
            elif self.machine_config.PLATFORM == '2p':
                if not self.parameters.get('Stimulus Only', False):
                    self.send({'2p': 'stop'})
            elif self.machine_config.PLATFORM == 'mc_mea':
                self.digital_io.set_pin(self.machine_config.TRIAL_START_END_PIN,0)
                if self.parameters.get('stop_trigger',False) or self.parameters['Repeats']==1 or self.abort:
                    self.printl("Stop MC Mea recording")
                    self.digital_io.set_pin(self.machine_config.MCMEA_STOP_PIN,1)
                    self.digital_io.set_pin(self.machine_config.MCMEA_STOP_PIN,0)
            if self.machine_config.PLATFORM in [ 'retinal']:
                #Make sure that imaging recording finishes before terminating sync recording
                time.sleep(self.machine_config.CA_IMAGING_START_DELAY)
            if self.machine_config.ENABLE_SYNC=='stim':
                self.analog_input.finish_daq_activity(abort = self.abort and not self.partial_save)
                self.printl('Sync signal recording finished')
            #Saving data
            if not self.abort or self.partial_save:
                self._save2file()
                self.printl('Stimulus info saved to {0}'.format(self.datafilename))
                if self.machine_config.PLATFORM in ['behav','retinal', 'elphys_retinal_ca', 'us_cortical', 'ao_cortical','resonant', '2p', 'mc_mea', 'elphys', 'generic']:
                    self.send({'trigger':'stim data ready'})
#                if self.machine_config.PLATFORM in ['retinal', 'ao_cortical',  'resonant']:
#                    self._backup(self.datafilename)
#                    self.printl('{0} backed up'.format(self.datafilename))
            else:
                self.printl('Stimulation stopped')
            if self.machine_config.PLATFORM=='mc_mea':
                self.printl('Warning: why is this pulse generated?')
                if 0:
                    self.timing_pulse(self.machine_config.ACQUISITION_TRIGGER_PIN, self.machine_config.START_STOP_TRIGGER_WIDTH,polarity=self.machine_config.ACQUISITION_TRIGGER_POLARITY)
            self.frame_rates = numpy.array(self.frame_rates)
            if len(self.frame_rates)>0 and self.check_frame_rate:
                fri = 'mean: {0}, std {1}, max {2}, min {3}, values: {4}'.format(self.frame_rates.mean(), self.frame_rates.std(), self.frame_rates.max(), self.frame_rates.min(), numpy.round(self.frame_rates,0))
                self.log.info(fri, source = 'stim')
                expfr=self.machine_config.SCREEN_EXPECTED_FRAME_RATE
                self.enable_frame_rate_error=not (self.machine_config.PLATFORM=='behav' and float(self.frame_counter)/expfr<30)
                if abs((expfr-self.frame_rates.mean())/expfr)>self.machine_config.FRAME_RATE_ERROR_THRESHOLD and not self.abort and self.enable_frame_rate_error:
                    raise RuntimeError('Mean frame rate {0} does not match with expected frame {1}'.format(self.frame_rates.mean(), expfr))
        except:
            self.send({'trigger':'stim error'})
            raise RuntimeError(traceback.format_exc())
        finally:
            self.close()#If something goes wrong, close serial port

    def close(self):
        if hasattr(self, 'digital_io') and hasattr(self.digital_io, 'close'):
                self.digital_io.set_pin(self.config.BLOCK_TIMING_PIN, 0)
                self.digital_io.set_pin(self.config.FRAME_TIMING_PIN, 0)
                self.printl('Frame and block timing pins cleared.')
                self.digital_io.close()
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
        block_info=[sfi for sfi in self.stimulus_frame_info if 'block_name' in sfi]
        if len(block_info)==0: return
        if len(block_info)%2==1: return
        #convert block names to column headers
        signatures=[b['block_name'] for b in block_info]
        if not isinstance(signatures[0],tuple):
            self.printl('Block info cannot be converted to table, block names must be tuples')
            return
        if any(numpy.array(list(map(len, signatures)))-len(signatures[0])):
            self.printl('Block info cannot be converted to a table')
            return
        if isinstance(signatures[0][0],str):
            #Assume, that first item in signature is always an enumerated string
            #none, all and both are reserved keywords
            enum_values=list(set([s[0] for s in signatures if s[0] not in ['none', 'all','both']]))
            enum_values.sort()
            nblocks=int(len(block_info)/2)
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
#        if self.machine_config.EXPERIMENT_FILE_FORMAT == 'hdf5':
        setattr(self.datafile, 'software_environment',experiment_data.pack_software_environment())
        setattr(self.datafile, 'configs', experiment_data.pack_configs(self))
        self.datafile.frame_times=self.frame_times if self.machine_config.SCREEN_MODE=='psychopy' else self.screen.frame_times
#        elif self.machine_config.EXPERIMENT_FILE_FORMAT == 'mat':
#            self.datafile['software_environment'] = experiment_data.pack_software_environment()
#            self.datafile['configs'] = experiment_data.pack_configs(self)
#            self.datafile['frame_times']=self.screen.frame_times
        if 'trigger_timestamp' in self.parameters:
            t0=self.parameters['trigger_timestamp']
            self.datafile.block_timestamps=[sfi['time']-t0 for sfi in self.stimulus_frame_info  if 'block_name' in sfi]
        
    def _save2file(self):
        '''
        Certain variables are saved to hdf5 file
        '''
        self.parameters['partial_data']=self.abort
        self._read_sync()
        self._blocks2table()
        variables2save = ['parameters', 'stimulus_frame_info', 'configs', 'user_data', 'software_environment', 'block', 'experiment_start_timestamp', 'arduino_sync',  'arduino_timestamps']#['experiment_name', 'experiment_config_name', 'frame_times']
#        if self.machine_config.EXPERIMENT_FILE_FORMAT == 'hdf5':
        self.datafile = experiment_data.CaImagingData(self.outputfilename)
        self._prepare_data2save()
        if hasattr(self.datafile, 'block_timestamps'):
            variables2save.append('block_timestamps')
        [setattr(self.datafile, v, getattr(self,v)) for v in variables2save if hasattr(self, v) and v not in ['configs', 'software_environment']]
        for v in variables2save :
            if hasattr(self.datafile, v):
                self.printl(v)
                if hasattr(self.machine_config, 'PICKLE_NODES'):
                    if v in self.machine_config.PICKLE_NODES:
                        setattr(self.datafile, v, utils.object2array(getattr(self.datafile, v)))
                self.datafile.save(v)
        #[self.datafile.save(v) for v in variables2save if hasattr(self.datafile, v)]
        if hasattr(self, 'analog_input'):#Sync signals are recorded by stim
            self.datafile.sync, self.datafile.sync_scaling=signal.to_16bit(self.analog_input.ai_data)
            self.datafile.save(['sync', 'sync_scaling'])
            try:
                if not self.parameters.get('Stimulus Only', False) and not self.parameters['partial_data']:
                    self.datafile.sync2time()
                    if hasattr(self, 'enable_frame_rate_error') and self.enable_frame_rate_error:
                        self.datafile.check_timing(check_frame_rate=self.check_frame_rate)
                else:
                    self.printl("Timing signal check is skipped at partial data")
            except:
                self.datafile.corrupt_timing=True
                self.datafile.save('corrupt_timing')
                self.printl(traceback.format_exc())
                self.printl('{0} saved but timing signal is corrupt'.format(self.datafile.filename))
        if 0 and 'Record Eyecamera' in self.parameters and self.parameters['Record Eyecamera']:
            fps_values, fpsmean,  fpsstd=self.datafile.sync_frame_rate(self.machine_config.TBEHAV_SYNC_INDEX)
            bins=[min(fps_values), fpsmean-fpsstd/2,  fpsmean+fpsstd/2,  max(fps_values)]
            self.printl('Eye camera mean frame rate: {0} Hz,  std: {1} Hz,  number of frames {2}, Hist: {3}, {4}'.format(fpsmean, fpsstd, len(fps_values), *numpy.histogram(fps_values, bins)))
        if 'Runwheel attached' in self.parameters and self.parameters['Runwheel attached']:
            self.printl('Check runwheel signals')
            high_low_levels, powered, signals_connected=self.datafile.check_runwheel_signals()
            self.printl('Runwheel signal checked: high low transitions: {0}, powered: {1}, signals connected: {2}'.format(high_low_levels, powered, signals_connected))
            if not high_low_levels or not signals_connected:
                self.send({'notify':['Warning', 'No runwheel signal detected, check connections and runwheel power supply!']})
            if not powered:
                self.send({'notify':['Warning', '50 Hz in runwheel signal, check runwheel power']})
        self.datafile.close()
        self._sfi2txt()
        #Convert to mat file except for Dani
        if self.machine_config.EXPERIMENT_FILE_FORMAT=='mat' and self.machine_config.PLATFORM not in ['elphys']:
            experiment_data.hdf52mat(self.outputfilename)
            self.printl('{0} converted to mat'.format(self.outputfilename))
        self.datafilename=self.datafile.filename
#        elif self.machine_config.EXPERIMENT_FILE_FORMAT == 'mat':
#            self.datafile = {}
#            self._prepare_data2save()
#            for v in variables2save:
#                if hasattr(self, v):
#                    self.datafile[v] = getattr(self,v)
#            self._data2matfile_compatible()
#            if self.machine_config.PLATFORM == 'hi_mea' and self.machine_config.USE_MEADATAFILE_PREFIX:
#                #the latest file's name with a specific format
#                latest_file = fileop.find_latest(os.path.split(experiment_data.get_user_experiment_data_folder(self.parameters))[0],extension=None)#TODO: extension tbd
#                if latest_file is None:
#                    filename_prefix = ''
#                else:
#                    filename_prefix = str(os.path.split(latest_file)[1].replace(os.path.splitext(latest_file)[1],'')[:-1])
#                fn = experiment_data.get_recording_path(self.machine_config, self.parameters, prefix = filename_prefix)
#                fn = os.path.join(os.path.split(os.path.split(fn)[0])[0], os.path.split(fn)[1])
#            else:
#                if self.machine_config.PLATFORM == 'epos':
#                    filename_prefix = ''
#                else:
#                    filename_prefix = 'stim'
#                fn = experiment_data.get_recording_path(self.machine_config, self.parameters, prefix = filename_prefix)
#            self.datafilename=fn
#            scipy.io.savemat(fn, self.datafile, oned_as = 'column',do_compression=True) 

    def _sfi2txt(self):
        #Convert stimulus frame info to pickled text:
        try:
            import cPickle as pickle
        except ImportError:
            import pickle
        import tables
        h=tables.open_file(self.datafile.filename,'a')
        stimulus_frame_info_text=pickle.dumps(self.stimulus_frame_info)
        sfi=numpy.fromstring(stimulus_frame_info_text,dtype=numpy.uint8)
        ca=h.create_carray(h.root, 'stimulus_frame_info_text', tables.UInt8Atom(), sfi.shape)
        ca[:]=sfi[:]
        h.flush()
        h.close()
        self.printl('Stimulus frame info saved as pickled')
        
    def _read_sync(self):
        if hasattr(self.machine_config, 'READ_VIDEO_TIMING_SIGNALS') and self.machine_config.READ_VIDEO_TIMING_SIGNALS:
            self.digital_io.read()
            self.arduino_sync=self.digital_io.read_all()
            self.arduino_timestamps=[self.arduino_sync[0,numpy.nonzero(self.arduino_sync[i])[0]]*1e-3 for i in [1, 2]]
            self.printl(1/numpy.diff(self.arduino_timestamps[1]).mean())
            stim_block_timestamps=numpy.array([sfi['time'] for sfi in self.stimulus_frame_info if 'block_name' in sfi])
            stim_block_timestamps-=self.first_imaging_frame_timepoint
            video_timestamps=self.arduino_timestamps[1]-self.arduino_timestamps[1][0]
            self.arduino_timestamps={'t0':self.first_imaging_frame_timepoint, 'video_timestamps':video_timestamps, 'stim_block_timestamps': stim_block_timestamps}
            
    def _backup(self, filename):#Maybe obsolete?
        bupaths=[self.machine_config.BACKUP_PATH]
        for bupath in bupaths:
            dst=os.path.join(bupath, 'raw',  os.path.join(*str(self.parameters['outfolder']).split(os.sep)[-2:]))
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
       if self.machine_config.ENABLE_MEA_START_COMMAND:
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.connect(self.machine_config.MEA_COMPUTER_ADDRESS)
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
            if hasattr(self, 'context'):
                visexpman.engine.stop_application(self.context)
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
                print(datafile)
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
