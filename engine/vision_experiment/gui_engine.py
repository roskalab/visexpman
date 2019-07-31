import time,tempfile,datetime
import scipy.io
import copy
try:
    import Queue
    import cPickle as pickle
except ImportError:
    import queue as Queue
    import pickle
import os,platform
import threading,multiprocessing
import unittest,traceback
import numpy
import shutil
import itertools
import tables
try:
    import PyQt4.Qt as Qt
    import PyQt4.QtGui as QtGui
    import PyQt4.QtCore as QtCore
except ImportError:
    import PyQt5.Qt as Qt
    import PyQt5.QtGui as QtGui
    import PyQt5.QtCore as QtCore
try:
    import hdf5io
except ImportError:
    pass
from visexpman.engine.vision_experiment import experiment_data, experiment
from visexpman.engine.analysis import cone_data,aod,elphys
from visexpman.engine.hardware_interface import queued_socket,daq_instrument,scanner_control,camera_interface,digital_io,instrument
from visexpman.engine.generic import fileop, signal,stringop,utils,introspect,videofile,colors
from visexpman.applications.visexpman_main import stimulation_tester

class GUIDataItem(object):
    def __init__(self,name,value,path):
        self.name = name
        self.n = name
        self.value = value
        self.v=value
        self.path = path
        self.p=path
        
class GUIData(object):
    def add(self, name, value, path):
        setattr(self,stringop.to_variable_name(name),GUIDataItem(name,value,path))#Overwritten if already exists

    def read(self, name = None, path = None, **kwargs):
        if name is not None and hasattr(self,stringop.to_variable_name(name)):
            return getattr(self,stringop.to_variable_name(name)).value
        elif path is not None:
            for v in dir(self):
                v = getattr(self,v)
                if isinstance(v, GUIDataItem) and (v.path == path or path in v.path):
                    return v.value
                    
    def to_dict(self):
        return [{'name': getattr(self, vn).n, 'value': getattr(self, vn).v, 'path': getattr(self, vn).p} for vn in dir(self) if isinstance(getattr(self, vn), GUIDataItem)]
        
    def from_dict(self, data):
        for item in data:
            setattr(self, stringop.to_variable_name(item['name']), GUIDataItem(stringop.to_title(item['name']), item['value'], item['path']))

class ExperimentHandler(object):
    '''
    Takes care of all microscope, hardware related tasks
    Handles stimulus files, initiates recording and stimulation, 
    '''
    def __init__(self):
        if self.machine_config.PLATFORM!='mc_mea' and platform.system()=='Windows':
            self.queues = {'command': multiprocessing.Queue(), 
                            'response': multiprocessing.Queue(), 
                            'data': multiprocessing.Queue()}
            if hasattr(self.machine_config, 'SYNC_RECORDER_CHANNELS') and self.machine_config.ENABLE_SYNC=='main':
                if self.machine_config.PLATFORM=='elphys':
                    limits = {}
                    limits['min_ao_voltage'] = -5.0
                    limits['max_ao_voltage'] = 5.0
                    limits['min_ai_voltage'] = -5.0
                    limits['max_ai_voltage'] = 5.0
                    limits['timeout'] = self.machine_config.DAQ_TIMEOUT
                else:
                    limits=None
                dev=self.machine_config.SYNC_RECORDER_CHANNELS.split('/')[0]
                res=daq_instrument.is_device_present(dev)
                if not res:
                    raise IOError('{0} device is not present in system. Make sure that it is configured properly.'.format(dev))
                self.sync_recorder=daq_instrument.AnalogIOProcess('daq', self.queues, self.log, ai_channels=self.machine_config.SYNC_RECORDER_CHANNELS,limits=limits)
                self.sync_recorder.start()
            self.sync_recording_started=False
            self.experiment_running=False
            self.experiment_finish_time=time.time()
            self.batch_running=False
        else:
            self.experiment_running=False
            self.sync_recording_started=False
            self.batch_running=False
        self.santiago_setup='santiago' in self.machine_config.__class__.__name__.lower()
        if self.machine_config.user=='common':
            self.dataroot=self.machine_config.EXPERIMENT_DATA_PATH
        else:#Multiple users
            self.dataroot=os.path.join(self.machine_config.EXPERIMENT_DATA_PATH, self.machine_config.user)
        if hasattr(self.machine_config, 'GUI_ENGINE_COPIER') and self.machine_config.GUI_ENGINE_COPIER:
            self.copier=experiment_data.Copier(self.dataroot, os.path.join(self.machine_config.BACKUP_PATH, self.machine_config.user))
            self.copier.start()
    
    def open_stimulus_file(self, filename, classname):
        if not os.path.exists(filename):
            self.printc('{0} does not exists'.format(filename))
            return
        if os.path.basename(os.path.dirname(filename))=='common' and self.machine_config.user!='common':#Stimulus edit is not allowed at multiuser setups
            self.notify('Warning', 'Common stimulus files cannot be opened for editing')
            return
        lines=fileop.read_text_file(filename).split('\n')
        line=[i for i in range(len(lines)) if 'class '+classname in lines[i]][0]+1+0*20#+20: beginning of class is on the middle of the screen
        self.printc('Opening {0}{3}{1} in gedit at line {2}'.format(filename, classname,line,os.sep))
        import subprocess
        process = subprocess.Popen(['gedit', filename, '+{0}'.format(line)], shell=self.machine_config.OS != 'Linux')
        
    def check_parameter_changes(self, parameter_name):
        '''
        parameter_name: name of parameter changed
        Depending on which parameter changed certain things has to be recalculated
        '''
        if parameter_name == 'Bullseye On':
            self.send({'function': 'set_variable','args':['bullseye_size',self.guidata.read('Bullseye Size')]},'stim')
            self.send({'function': 'toggle_bullseye','args':[self.guidata.read('Bullseye On')]},'stim')
        elif parameter_name == 'Bullseye Size':
            self.send({'function': 'set_variable','args':['bullseye_size',self.guidata.read('Bullseye Size')]},'stim')
        elif parameter_name == 'Bullseye Shape':
            self.send({'function': 'set_variable','args':['bullseye_type',self.guidata.read('Bullseye Shape')]},'stim')
        elif parameter_name == 'Grey Level':
            if self.santiago_setup:
                cmd='SOCcolorEOC{0}EOP'.format(int(self.guidata.read('Grey Level')*1e-2*255))
                utils.send_udp(self.machine_config.CONNECTIONS['stim']['ip']['stim'],446,cmd)
                self.printc(cmd)
            else:
                self.send({'function': 'set_context_variable','args':['background_color',self.guidata.read('Grey Level')*1e-2]},'stim')            
        elif parameter_name == 'Stimulus Center X' or parameter_name == 'Stimulus Center Y':
            v=[self.guidata.read('Stimulus Center X'), self.guidata.read('Stimulus Center Y')]
            self.send({'function': 'set_context_variable','args':['screen_center',v]},'stim')
        elif parameter_name=='Filterwheel':
            f=self.guidata.read('Filterwheel')
            if isinstance(self.machine_config.FILTERWHEEL_FILTERS,  list):
                v=self.machine_config.FILTERWHEEL_FILTERS[0][f]
                port=self.machine_config.FILTERHWEEL_PORT[0]
            else:
                v=self.machine_config.FILTERWHEEL_FILTERS[f]
                port=self.machine_config.FILTERHWEEL_PORT
            self.printc('Set filterwheel to {0}/{1}'.format(f,v))
            res=instrument.set_filterwheel(v, port, self.machine_config.FILTERHWEEL_BAUDRATE)
            self.printc(res)
        elif parameter_name=='Filterwheel 2':
            f=self.guidata.read('Filterwheel 2')
            v=self.machine_config.FILTERWHEEL_FILTERS[1][f]
            self.printc('Set filterwheel to {0}/{1}'.format(f,v))
            res=instrument.set_filterwheel(v, self.machine_config.FILTERHWEEL_PORT[1], self.machine_config.FILTERHWEEL_BAUDRATE)
            self.printc(res)
            
    def _get_experiment_parameters(self):
        '''
        Parse parameters, user interface inputs for generating experiment parameters
        '''
        cf=self.guidata.read('Selected experiment class')
        if cf == None:
            self.notify('Warning', 'Select stimulus')
            return
        classname=cf.split(os.sep)[-1]
        filename=os.sep.join(cf.split(os.sep)[:-1])
        stimulus_source_code = fileop.read_text_file(filename)
        #Find out duration
        experiment_duration = experiment.get_experiment_duration(classname, self.machine_config, source = stimulus_source_code)
        if self.santiago_setup and experiment_duration>240:
            if not self.ask4confirmation('Longer recordings than 240 s may result memory error. Do you want to continue? {0}'.format(experiment_duration)):
                return
        #Collect experiment parameters
        experiment_parameters = {}
        experiment_parameters['stimfile']=filename
        experiment_parameters['name']=self.guidata.read('Name')
        if self.guidata.read('Name')!='':
            experiment_parameters['region_name']=self.guidata.read('Name')
        experiment_parameters['animal']=self.guidata.read('Animal')
        experiment_parameters['comment']=self.guidata.read('Comment')
        source_code_type='stimulus_source_code' if len(experiment.parse_stimulation_file(filename)[classname])==0 else 'experiment_config_source_code'
        experiment_parameters[source_code_type]=stimulus_source_code
        experiment_parameters['stimclass']=classname
        experiment_parameters['duration']=experiment_duration
        experiment_parameters['status']='waiting'
        experiment_parameters['id']=experiment_data.get_id()
        experiment_parameters['user']=self.machine_config.user
        experiment_parameters['machine_config']=self.machine_config.__class__.__name__
        #Outfolder is date+id. Later all the files will be merged from id this folder
        experiment_parameters['outfolder']=os.path.join(self.dataroot, utils.timestamp2ymd(time.time(), separator=''))
        if not os.path.exists(experiment_parameters['outfolder']):
            os.makedirs(experiment_parameters['outfolder'])
        experiment_parameters['outfilename']=experiment_data.get_recording_path(self.machine_config, experiment_parameters,prefix = 'data')
        if self.machine_config.PLATFORM=='us_cortical':
            for pn in ['Protocol', 'Number of Trials', 'Motor Positions']:
                experiment_parameters[pn]=self.guidata.read(pn)
            experiment_parameters['motor position']=0
        elif self.machine_config.PLATFORM=='elphys_retinal_ca':
            if not self.santiago_setup:
                self.send({'function': 'start_imaging','args':[experiment_parameters]},'ca_imaging')
        elif self.machine_config.PLATFORM=='ao_cortical':
            if experiment_parameters['duration']<self.machine_config.MES_LONG_RECORDING:
                wt=self.machine_config.MES_RECORD_START_WAITTIME
            else:
                wt=self.machine_config.MES_RECORD_START_WAITTIME_LONG_RECORDING
            oh=wt+self.machine_config.MES_RECORD_OVERHEAD
            experiment_parameters['mes_record_time']=int(1000*(experiment_parameters['duration']+oh))
        elif self.machine_config.PLATFORM=='elphys':
            mode=self.guidata.read('Clamp Mode')
            if 'Electrical' in mode:
                raise NotImplementedError()
#            sensitivity=self.guidata.read(mode.split()[0]+' Command Sensitivity')
#            command=self.guidata.read('Clamp '+mode.split()[0])
#            experiment_parameters['Command Voltage']=command/sensitivity
            experiment_parameters['Recording Sample Rate']=self.guidata.read('Recording Sample Rate')
            experiment_parameters['Current Gain']=self.guidata.read('Current Gain')
            experiment_parameters['Voltage Gain']=self.guidata.read('Voltage Gain')
            experiment_parameters['Current Command Sensitivity']=self.guidata.read('Current Command Sensitivity')
            experiment_parameters['Voltage Command Sensitivity']=self.guidata.read('Voltage Command Sensitivity')
            
        elif self.machine_config.PLATFORM=='mc_mea' and hasattr(self,'latest_mcd_file'):
            experiment_parameters['mcd_file']=self.latest_mcd_file
            self.printc('MEA data is being saved to {0}'.format(self.latest_mcd_file))
        #parameter_names=['Runwheel attached',  'Record Eyecamera',  'Partial Save', 'Stimulus Only', 'Filterwheel', 'Filterwheel 2']
        parameter_names=[i['name'] for i in self.guidata.to_dict()]#Take all values from Settings
#        if hasattr(self.machine_config,  "GUI_SETTINGS_TO_STIM"):
#            parameter_names.extend(self.machine_config.GUI_SETTINGS_TO_STIM)
        for pn in parameter_names:
            v=self.guidata.read(pn)
            if v!=None:
                experiment_parameters[pn]=v
        experiment_parameters['eyecamfilename']=experiment_data.get_recording_path(self.machine_config, experiment_parameters, prefix = 'eyecam')
        return experiment_parameters
            
    def start_batch_experiment(self):
        if self.batch_running:
            self.notify('Warning', 'Batch is already running')
            return
        self.printc('Generating batch, please wait')
        experiment_parameters=self._get_experiment_parameters()
        if experiment_parameters==None:
            return
        if self.machine_config.PLATFORM == 'us_cortical':
            if not (experiment_parameters['Number of Trials']>1 or ',' in experiment_parameters['Motor Positions']):
                self.notify('Warning', 'Batch cannot be generated. Motor Positions shall be configured or Number of Trials shall be greater than 1!')
                return
            if ',' in experiment_parameters['Motor Positions']:
                motor_positions=map(float,experiment_parameters['Motor Positions'].split(','))
                start=motor_positions[0]
                end=motor_positions[1]
                step=motor_positions[2] if start<end else -motor_positions[2]
                motor_positions=numpy.arange(start,end,step)
                motor_positions_repeats=numpy.repeat(motor_positions, experiment_parameters['Number of Trials'])
                self.batch=[]
                for i in range(motor_positions_repeats.shape[0]):
                    par=copy.deepcopy(experiment_parameters)
                    par['motor position']=motor_positions_repeats[i]
                    par['is batch']=True
                    par['id']=experiment_data.get_id()
                    if len(self.batch)>0 and par['id']==self.batch[-1]['id']:
                        time.sleep(0.11)
                        par['id']=experiment_data.get_id()
                    par['outfolder']=os.path.join(self.machine_config.EXPERIMENT_DATA_PATH,  utils.timestamp2ymd(time.time(), separator=''),par['id'])
                    self.batch.append(par)
            else:
                experiment_parameters['is batch']=True
                self.batch=[]
                for i in range(experiment_parameters['Number of Trials']):
                    par=copy.deepcopy(experiment_parameters)
                    par['id']=experiment_data.get_id()
                    if len(self.batch)>0 and par['id']==self.batch[-1]['id']:
                        time.sleep(0.11)
                        par['id']=experiment_data.get_id()
                    par['outfolder']=os.path.join(self.machine_config.EXPERIMENT_DATA_PATH,  utils.timestamp2ymd(time.time(), separator=''),par['id'])
                    self.batch.append(par)
            [self.printc('Batch generated: {0}/{1} um' .format(b['id'], b['motor position'])) for b in self.batch]
        elif self.machine_config.ENABLE_BATCH_EXPERIMENT:
            if self.guidata.read('Enable tile scan'):
                raise NotImplementedError()
            if self.guidata.read('Z start')<self.guidata.read('Z end'):
                raise ValueError('Z start shall be bigger than Z end')
            elif self.guidata.read('Z step')<0:
                raise ValueError('Z step shall be greater than 0')
            zs=self.guidata.read('Z start')
            ze=self.guidata.read('Z end')
            zst=self.guidata.read('Z step')
            depths=numpy.linspace(zs,ze,(zs-ze)/zst+1)
            self.batch=[]
            for d in depths:
                for r in range(self.guidata.read('Repeats')):
                    par=copy.deepcopy(experiment_parameters)
                    time.sleep(0.2)
                    par['id']=experiment_data.get_id()
                    par['depth']=d
                    par['outfilename']=experiment_data.get_recording_path(self.machine_config, par ,prefix = 'data')
                    par['eyecamfilename']=experiment_data.get_recording_path(self.machine_config, par, prefix = 'eyecam')
                    self.batch.append(par)
            self.printc('Batch generated:'+'\r\n'.join(['{0}/{1} um' .format(b['id'], b['depth']) for b in self.batch]))
        elif self.machine_config.PLATFORM == 'rc_cortical':
            raise NotImplementedError('Batch experiment on rc_cortical platform is not yet available')
        self.fullbatch=copy.deepcopy(self.batch)
        self.batch_running=True
        
    def check_batch(self):
        if self.batch_running:
            if not self.experiment_running and time.time()-self.experiment_finish_time>self.machine_config.WAIT_BETWEEN_BATCH_JOBS and \
                 'stim' in self.connected_nodes and (hasattr(self,  'microscope') and self.microscope.name in self.connected_nodes):
                if len(self.batch)==0:
                    self.batch_running=False
                    self.notify('Info', 'Batch finished')
                    return
                self.printc('Starting next batch item, {0} left'.format(len(self.batch)))
                self.start_experiment(experiment_parameters=self.batch[0], manually_started=False)
                self.batch=self.batch[1:]
                
    def mc_mea_trigger(self):
        '''
        If a new file (max 5 second age) is found in MC_DATA_FOLDER folder, an experiment is initiated, checked in every 5 second
        '''
        if self.guidata.read('MC Rack New File Trigger Enable') and not self.experiment_running:
            self.mcd_check_period=5
            now=time.time()
            if not hasattr(self, 'last_mcd_check'):
                self.last_mcd_check=now
            dt=now-self.last_mcd_check
            if dt>self.mcd_check_period:
                self.last_mcd_check=now
                self.latest_mcd_file=fileop.find_latest(self.machine_config.MC_DATA_FOLDER,'.mcd')
                if self.latest_mcd_file==None:
                    return
                dt=now-os.path.getmtime(self.latest_mcd_file)
                if dt<2*self.mcd_check_period:
                    self.start_experiment(manually_started=False)
                
    def connect(self):
        self.microscope_handler('init')
        
    def start_experiment(self, experiment_parameters=None, manually_started=True):
        self.aborted=False
        if self.machine_config.PLATFORM in 'mc_mea':
            if manually_started:
                if self.guidata.read('MC Rack New File Trigger Enable')==True:
                    self.notify('Warning', 'MC Rack new file trigger enabled, cannot start experiment manually')
                    return
                else:
                    pass#raise NotImplementedError('MC MEA platform manual experiment start is not yet supported')
        if self.machine_config.PLATFORM in ['2p',  'resonant']:
            if not hasattr(self, 'connected_nodes') or 'stim' not in self.connected_nodes or (hasattr(self,  'microscope') and self.microscope.name not in self.connected_nodes):
                scope_name=self.microscope.name if hasattr(self,  'microscope') else ''
                missing_connections=[conn for conn in [scope_name, 'stim'] if conn not in self.connected_nodes]
                self.notify('Warning', '{0} connection(s) required.'.format(','.join(missing_connections)))
                return
            #Set z
            if hasattr(experiment_parameters, 'keys') and 'depth' in experiment_parameters and hasattr(self.microscope, 'set_z'):
                self.microscope.set_z(experiment_parameters['depth'])
                self.printc('Set z to {0} um'.format(experiment_parameters['depth']))
        if self.sync_recording_started or self.experiment_running:
            self.notify('Warning', 'Experiment already running')
            return
        if experiment_parameters==None:
            experiment_parameters=self._get_experiment_parameters()
            if experiment_parameters==None:
                return
        if self.machine_config.PLATFORM=='ao_cortical':
            if not self.ask4confirmation('Is AO line scan selected on MES user interface?'):
                return
        if hasattr(self, 'sync_recorder'):
            nchannels=map(int,self.machine_config.SYNC_RECORDER_CHANNELS.split('ai')[1].split(':'))
            nchannels=nchannels[1]-nchannels[0]+1
            self.daqdatafile=fileop.DataAcquisitionFile(nchannels,'sync',None if self.machine_config.PLATFORM=="elphys" else [-5,5])
            #Start sync signal recording
            sample_rate=self.machine_config.SYNC_RECORDER_SAMPLE_RATE
            d=self.sync_recorder.read_ai()#Empty ai buffer
            self.sync_recorder.start_daq(ai_sample_rate = sample_rate,
                                ai_record_time=self.machine_config.SYNC_RECORDING_BUFFER_TIME, timeout = 10) 
            self.sync_recording_started=True
            self.printc('Signal recording started')
#        if self.machine_config.PLATFORM in ['elphys']:
#            daq_instrument.set_voltage(self.machine_config.ELPHYS_COMMAND_CHANNEL, experiment_parameters['Command Voltage'])
#            self.printc('Set clamp signal to {0:.1f} V'.format(experiment_parameters['Command Voltage']))
        if self.machine_config.PLATFORM in ['elphys']:
            if not self.guidata.read('Infinite Recording') or not hasattr(self, 'live_data'):
                self.live_data=numpy.empty((0,self.machine_config.N_AI_CHANNELS))
            if self.guidata.read('Block Projector'):
                self.printc('Open projector lightpath')
                res=instrument.set_filterwheel(self.machine_config.FILTERWHEEL_FILTERS[1]['empty'], self.machine_config.FILTERHWEEL_PORT[1], self.machine_config.FILTERHWEEL_BAUDRATE)
                self.printc(res)
        if self.machine_config.PLATFORM in ['erg']:
            experiment_parameters=self.user_gui_engine.start_experiment(experiment_parameters)
            self.live_data=numpy.empty((0,self.machine_config.N_AI_CHANNELS))
        if self.santiago_setup:
            time.sleep(1)
            #UDP command for sending duration and path to imaging
            cmd='sec {0} filename {1}'.format(experiment_parameters['duration']+self.machine_config.CA_IMAGING_START_DELAY, experiment_parameters['outfolder'])
            utils.send_udp(self.machine_config.CONNECTIONS['ca_imaging']['ip']['ca_imaging'],446,cmd)
            time.sleep(1)
            #UDP command for stim including path and stimulus source code
            stimulus_source_code=[v for k, v in experiment_parameters.items() if 'experiment_config_source_code' in k][0]
            cmd='SOCexecute_experimentEOC{0}EOP'.format(stimulus_source_code.replace('\n', '<newline>').replace('=', '<equal>').replace(',', '<comma>').replace('#OUTPATH', experiment_parameters['outfolder'].replace('\\', '\\\\')))
            utils.send_udp(self.machine_config.CONNECTIONS['stim']['ip']['stim'],446,cmd)
        else:
            if 'Record Eyecamera' in experiment_parameters and experiment_parameters['Record Eyecamera']:
                self.send({'function': 'start_recording','args':[experiment_parameters]},'cam')
                time.sleep(self.machine_config.CAMERA_PRETRIGGER_TIME)
            if self.machine_config.PLATFORM not in ['erg']:
                self.send({'function': 'start_stimulus','args':[experiment_parameters]},'stim')
        if hasattr(self, 'copier'):
            self.copier.suspend()
            self.printc('Suspend copier')
        self.start_time=time.time()
        if self.machine_config.PLATFORM=='ao_cortical':
            self.printc('{1} experiment is starting, mes recording length is {2:.0f} ms, stimulus duration is {0:.0f} s'.format(experiment_parameters['duration'], experiment_parameters['stimclass'], experiment_parameters['mes_record_time']))
        else:
            self.printc('{1} experiment is starting, expected duration is {0:.0f} s'.format(experiment_parameters['duration'], experiment_parameters['stimclass']))
        self.enable_check_network_status=False
        self.current_experiment_parameters=experiment_parameters
        self.experiment_running=True
        self.experiment_start_time=time.time()
        if experiment_parameters.get('Stimulus Only', False):
            self.to_gui.put({'update_status':'stimulus only'})
        else:
            self.to_gui.put({'update_status':'recording'})
        
    def finish_experiment(self):
        if not self.experiment_running:
            return
        self.to_gui.put({'update_status':'busy'})   
        self.printc('Finishing experiment...')
        if self.machine_config.PLATFORM=='mc_mea':
            #Copy mcd file to outfolder:
            time.sleep(3)
            if not self.aborted and 'mcd_file' in self.current_experiment_parameters:
                dst=fileop.replace_extension(self.current_experiment_parameters['outfilename'], '.mcd')
                self.printc('Move {0} to {1}'.format(self.current_experiment_parameters['mcd_file'],dst))
                shutil.move(self.current_experiment_parameters['mcd_file'], dst)
            
#            if hasattr(self.machine_config, 'MC_DATA_FOLDER'):
#                #Find latest mcd file and save experiment metadata to the same folder
#                self.latest_mcd_file=fileop.find_latest(self.machine_config.MC_DATA_FOLDER,'.mcd')
#                txt='Experiment name\t{0}\rBandpass filter\t{1}\rND filter\t{2}\rComments\t{3}\r'\
#                        .format(\
#                        self.guidata.read('name'),
#                        self.guidata.read('Bandpass filter'),
#                        self.guidata.read('ND filter'),
#                        self.guidata.read('Comment'))
#                for k,v in self.current_experiment_parameters.items():
#                    if k !='stimulus_source_code' or k!='status':
#                        txt+='{0}\t{1}\r'.format(k,v)
#                txt+=self.current_experiment_parameters['stimulus_source_code']
#                outfile=self.latest_mcd_file.replace('.mcd','_metadata.txt')
#                if os.path.exists(outfile):
#                    if not self.ask4confirmation('Experiment info file already exists.\r\nDo you want to overwrite {0}'.format(outfile)):
#                        return
#                fileop.write_text_file(outfile,txt)
#                self.printc('Experiment info saved to {0}'.format(outfile))
        else:
            if self.santiago_setup:
                t0=time.time()
                while True:
                    if len([True for d in os.listdir(self.current_experiment_parameters['outfolder']) if os.path.isdir(os.path.join(self.current_experiment_parameters['outfolder'],d))])>0:
                        break
                    if time.time()-t0>10:
                        self.printc('Timeout')
                        break
                    time.sleep(1)
            time.sleep(1)
            self._stop_sync_recorder()
#            self.experiment_running=False
            #self.experiment_finish_time=time.time()
        if hasattr(self, 'copier'):
            self.printc('Resume copier')
            self.copier.resume()
        self.experiment_finish_time=time.time()
        if self.machine_config.PLATFORM in ['elphys']:
            if self.guidata.read('Block Projector'):
                self.printc('Block projector lightpath')
                res=instrument.set_filterwheel(self.machine_config.FILTERWHEEL_FILTERS[1]['block'], self.machine_config.FILTERHWEEL_PORT[1], self.machine_config.FILTERHWEEL_BAUDRATE)
                self.printc(res)

#            self.printc('Set clamp signal to 0V')
#            daq_instrument.set_voltage(self.machine_config.ELPHYS_COMMAND_CHANNEL, 0.0)

            
    def save_experiment_files(self, aborted=False):
        self.to_gui.put({'update_status':'busy'})   
        fn=experiment_data.get_recording_path(self.machine_config, self.current_experiment_parameters, prefix = "sync")
        if aborted:
            if hasattr(self, 'daqdatafile') and os.path.exists(self.daqdatafile.filename):
                os.remove(self.daqdatafile.filename)
        else:
            if hasattr(self, 'daqdatafile'):
                #shutil.copy(self.daqdatafile.filename, os.path.join(tempfile.gettempdir(), os.path.basename(fn)))
                if not os.path.exists(os.path.dirname(fn)):
                    time.sleep(0.1)
                #Here comes merging datafiles if stim computer is available
                if 'stim' in self.machine_config.CONNECTIONS:
                    outfile=self.current_experiment_parameters['outfilename']
                    fileop.merge_hdf5_files(self.daqdatafile.filename, outfile)
                    self.printc('Sync data merged to {0}'.format(outfile))
                    experiment_data.hdf52mat(outfile, scale_sync=True)
                    self.printc('{0} converted to mat'.format(outfile))
                else:
                    shutil.copy(self.daqdatafile.filename,fn)
                    self.printc('Sync data saved to {0}'.format(fn))
                if self.santiago_setup:
                    #Make a local copy of sync file
                    localfn=os.path.join('c:\\Data\\santiago-setup', os.path.basename(fn))
                    shutil.copy(self.daqdatafile.filename, localfn)
                    self.printc('Local copy saved to {0}'.format(localfn))
                try:
                    os.remove(self.daqdatafile.filename)
                except:
                    self.printc('Tempfile cannot be removed')
            if self.santiago_setup:
                from visexpman.users.zoltan import legacy
                self.printc('Merging datafiles, please wait...')
                filename=legacy.merge_ca_data(self.current_experiment_parameters['outfolder'],**self.current_experiment_parameters)
                fn=filename
                self.printc('Data saved to {0}'.format(filename))
                #Check for dropped frames
                dropped_frames=legacy.get_dropped_frames(filename)
                if dropped_frames>2:
                    self.notify('Error', '{0} dropped frames were detected, close unused applications on Imaging computer or reboot it'.format(dropped_frames))
                elif dropped_frames==2:
                    self.printc('No dropped frames detected')
                else:
                    self.printc('Warning: more frames than timing pulses were detected.')
                dst=os.path.join(os.path.dirname(self.machine_config.EXPERIMENT_DATA_PATH),'raw', filename.split(os.sep)[-2], os.path.basename(filename.replace('.hdf5','.zip')))
                fileop.move2zip(self.current_experiment_parameters['outfolder'],dst,delete=True)
                current_folder=os.path.dirname(self.current_experiment_parameters['outfolder'])
                folders=[os.path.join(current_folder, fi) for fi in os.listdir(current_folder) if fi != 'output' and os.path.isdir(os.path.join(current_folder, fi))]
                try:
                    [shutil.rmtree(f) for f in folders]
                except:
                    pass
                self.printc('Rawdata archived')
            elif self.machine_config.PLATFORM=='ao_cortical':
                raise RuntimeError("Is it used at all?")
                fn=experiment_data.get_recording_path(self.machine_config, self.current_experiment_parameters, prefix = 'data')
            if not (self.machine_config.PLATFORM in ['behav', '2p', 'retinal', 'ao_cortical', 'resonant', "elphys", '2p','mc_mea']):#On ao_cortical sync signal calculation and check is done by stim
                raise RuntimeError('On which platform it is really needed?')
                self.printc(fn)
                h = experiment_data.CaImagingData(fn)
                h.sync2time()
                if self.santiago_setup:
                    self._remove_dropped_frame_timestamps(h)
                    h.crop_timg()
                self.tstim=h.tstim
                self.timg=h.timg
                h.check_timing(check_frame_rate=not self.santiago_setup)
                h.close()
            if self.santiago_setup:
                #Export timing to csv file
                self._timing2csv(filename)
            if self.machine_config.PLATFORM=='elphys' and not aborted:
                hh=experiment_data.CaImagingData(outfile)
                hh.load()
                self.to_gui.put({'plot_title': os.path.dirname(outfile)+'<br>'+os.path.basename(outfile)})
#                if self.guidata.read('Displayed signal length')==0:
#                    self._plot_elphys(hh.sync)
                try:
                    hh.sync2time()
                    hh.check_timing(check_frame_rate=True)
                except:
                    self.printc(traceback.format_exc())
                hh.close()
        self.to_gui.put({'update_status':'idle'})
        
    def enable_plot_signals(self,enable):
        self.plot_signal_enable=enable
        if hasattr(self, 'live_data'):
            self._plot_elphys(self.live_data)
            
    def _remerge_files(self,folder,hdf5fold):
        if not self.santiago_setup:
            return
        from visexpman.users.zoltan import legacy
        self.printc('Warning, not tested')
        for fold in fileop.listdir_fullpath(folder):
            import tempfile,zipfile
            zip_ref = zipfile.ZipFile(fold, 'r')
            
            dst=os.path.join(tempfile.gettempdir(),'z')
            if os.path.exists(dst):
                shutil.rmtree(dst)
            os.mkdir(dst)
            zip_ref.extractall(dst)
            zip_ref.close()
    
            self.printc(fold)
            fn=[f for f in fileop.listdir_fullpath(hdf5fold) if os.path.splitext(os.path.basename(fold))[0] in f][0]
            pars=hdf5io.read_item(fn, 'parameters')
            filename=legacy.merge_ca_data(dst,**pars)
            shutil.copy(filename,folder)
            self._timing2csv(os.path.join(folder, os.path.basename(filename)))
            
    def fix_timg(self,folder):
        for fn in fileop.listdir_fullpath(folder):
            h=hdf5io.Hdf5io(fn)
            h.load('timg')
            h.timg+=numpy.diff(h.timg)[0]
            h.save('timg')
            h.close()
            self._timing2csv(fn)
            
    def indexofsmallestpositive(self,a):
        m=numpy.where(a<0, 0, a)
        return numpy.where(a==a[numpy.nonzero(m)[0]].min())[0][0]
        
    def _folder2csv(self,folder):
        for f in fileop.listdir_fullpath(folder):
            if os.path.splitext(f)[1]=='.hdf5':
                try:
                    self._timing2csv(f)
                except:
                    import traceback
                    self.printc(traceback.format_exc())
                    
    def _timing2csv(self,filename):
        h = experiment_data.CaImagingData(filename)
        output_folder=os.path.join(os.path.dirname(filename), 'output', os.path.basename(filename))
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        from PIL import Image
        h.load('raw_data')
        h.load('parameters')
        self.printc(h.parameters['imaging_filename'])
        self.printc('Export rawdata to pngs')
        #Fn: 1_0__rect_64.00_64.00_0.00_0.00_2.00_top_0000000.png
        for framei in range(h.raw_data.shape[0]):
            for chi in range(h.raw_data.shape[1]):
                base=os.path.splitext(os.path.basename(h.parameters['imaging_filename']))[0]
                base='frame_'+h.parameters['channels'][chi]+'_{0:0=5}'.format(framei)
                fn=os.path.join(output_folder, base+'.png')
                Image.fromarray(h.raw_data[framei,chi]).rotate(90).save(fn)
        h.load('tstim')
        h.load('timg')
        h.load('dropped_frames')
        if hasattr(h, 'dropped_frames'):
            h.dropped_frames=numpy.array(h.dropped_frames)
            if h.dropped_frames.sum()>0:
                self.printc('dropped frames in file')
                h.timg=h.timg[numpy.where(h.dropped_frames==False)[0]]
                h.timg=h.timg[:h.raw_data.shape[0]]
        if 'Led2' in filename:
            h.load('generated_data')
            channels = utils.array2object(h.generated_data)#,len(utils.array2object(h.generated_data))
            real_events=h.tstim[numpy.where(numpy.diff(h.tstim)>2e-3)[0]]
            real_events=numpy.append(real_events, h.tstim[-1])
            tstim_sep={}
            for ch in ['stim','led']:
                tstim_sep[ch]=real_events[[i for i in range(len(channels)) if channels[i]==ch or channels[i]=='both']]
        h.close()
        if 'Led2' in filename:
            self.printc(['led stim', numpy.round(tstim_sep['led'])])
            self.printc(['stim', numpy.round(tstim_sep['stim'])])
            txtlines1=','.join(map(str,numpy.round(tstim_sep['stim'],3)))
            txtlines2=','.join(map(str,numpy.round(tstim_sep['led'],3)))
            #Calculate image index for stim events
            stim_indexes=[self.indexofsmallestpositive(h.timg-s) for s in tstim_sep['stim']]
            led_indexes=[self.indexofsmallestpositive(h.timg-s) for s in tstim_sep['led']]
            txtlines1a=','.join(map(str,stim_indexes))+'\n'+txtlines1
            txtlines2a=','.join(map(str,led_indexes))+'\n'+txtlines2
        else:
            txtlines2=','.join(map(str,numpy.round(h.tstim,3)))
            led_indexes=[self.indexofsmallestpositive(h.timg-s) for s in h.tstim]
            txtlines2a=','.join(map(str,led_indexes))+'\n'+txtlines2
        txtlines3 =','.join(map(str,numpy.round(h.timg,3)))
        csvfn3=os.path.join(output_folder,'_img.csv')
        csvfn2=os.path.join(output_folder, '_lgnled.csv')
        csvfn2a=os.path.join(output_folder, '_lgnled_index.csv')
        csvfn1=os.path.join(output_folder,  '_stim.csv')
        csvfn1a=os.path.join(output_folder,  '_stim_index.csv')
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        if 'Led2' in filename:
            fileop.write_text_file(csvfn1, txtlines1)
            fileop.write_text_file(csvfn1a, txtlines1a)
        fileop.write_text_file(csvfn2a, txtlines2a)
        fileop.write_text_file(csvfn2, txtlines2)
        fileop.write_text_file(csvfn3, txtlines3)
        self.printc('Timing information exported to {0} and {1}'.format(csvfn1, csvfn2, csvfn3))
        
    def pulse(self, n):
        self.send({'function': 'pulse','args':[n]},'stim')
        
    def read_position(self):
        self.send({'function': 'position','args':[]},'stim')
        
    def read_sync_recorder(self):
        self.syncreadout=self.sync_recorder.read_ai()
        if hasattr(self.syncreadout,  "dtype"):
            maxnsamples=int(self.machine_config.SYNC_RECORDER_SAMPLE_RATE*self.machine_config.LIVE_SIGNAL_LENGTH*2)#max 5 minutes
            if self.live_data.shape[0]>maxnsamples:
                self.live_data=self.live_data[-maxnsamples:,:]
            self.live_data=numpy.concatenate((self.live_data,self.syncreadout))
            self.last_ai_read=self.syncreadout
            if self.live_data.shape[0]>0:
                self._plot_elphys(self.live_data)
            self.daqdatafile.add(self.syncreadout)
            
    def _stop_sync_recorder(self):
        if self.sync_recording_started:
            self.sync_recording_started=False
            res=self.sync_recorder.stop_daq()
            try:
                d, n=res
            except:
                raise RuntimeError("daq data cannot be read: {0}".format(res))
            self.printc('Sync signal recording stopped')
            if len(d.shape)==3:
                self.printc('Warning: 3 d data, 2 d expected')
                d=d[0]
            elif d.shape[0]!=0:
                self.daqdatafile.add(d)
            else:
                pass
            self.daqdatafile.close()
            
    def run_always_experiment_handler(self):
        now=time.time()
        self.check_batch()
        self.mc_mea_trigger()
        if self.sync_recording_started:
            self.read_sync_recorder()
            if self.santiago_setup:
                if time.time()-self.start_time>self.current_experiment_parameters['duration']+1.5*self.machine_config.CA_IMAGING_START_DELAY:
                    [self.trigger_handler(trigname) for trigname in ['stim done', 'stim data ready']]
        if hasattr(self, 'copier'):
            for l in self.copier.printl():
                self.printc(l)

    def stop_experiment(self):
        self.aborted=True
        if self.batch_running:
            self.batch_running=False
            self.batch=[]
            if self.ask4confirmation('Batch terminated, do you want to keep current recording running?'):
                self.printc('Batch terminated, current recording is left running')
                return
        self.printc('Aborting experiment, please wait...')
        if hasattr(self, 'current_experiment_parameters') and self.current_experiment_parameters.get('Partial Save', False):
            self.printc('Saving partial data')
        if self.machine_config.PLATFORM=='retinal':
            self.send({'function': 'stop_all','args':[]},'ca_imaging')
        self.send({'function': 'stop_all','args':[]},'stim')
        if 'Record Eyecamera' in self.current_experiment_parameters and self.current_experiment_parameters['Record Eyecamera']:
            self.send({'function': 'stop_recording','args':[]},'cam')
        self.enable_check_network_status=True
        if hasattr(self, 'sync_recorder'):
            self._stop_sync_recorder()
        if self.machine_config.PLATFORM=='elphys':
            if 'stim' not in self.machine_config.CONNECTIONS:
                self.finish_experiment()
            self.experiment_running=False
            self.save_experiment_files(self.aborted)
            #When infinite recording stopped, live_data erased
            self.live_data=numpy.empty((0,self.machine_config.N_AI_CHANNELS))
        if self.machine_config.PLATFORM in ['erg']:
            self.to_gui.put({'update_status':'busy'})   
            self.printc('Finishing experiment...')
            experiment_parameters=self.user_gui_engine.stop_experiment()
            self.to_gui.put({'update_status':'idle'})
        self.experiment_running=False
        self.printc('Experiment stopped')
                   
    def trigger_handler(self,trigger_name):
        if trigger_name == 'stim started':
            self.printc('WARNING: no stim started trigger timeout implemented')
        elif trigger_name == 'stim done':
            if self.machine_config.PLATFORM in ['mc_mea', 'elphys_retinal_ca', 'ao_cortical', 'retinal', '2p',  'resonant']:
                self.enable_check_network_status=True
            if 'Record Eyecamera' in self.current_experiment_parameters and self.current_experiment_parameters['Record Eyecamera']:
                self.send({'function': 'stop_recording','args':[]},'cam')
            self.finish_experiment()
#        elif trigger_name=='sync recording started':
#            if self.experiment_running and 'Enable Eye Camera' in self.current_experiment_parameters and self.current_experiment_parameters['Enable Eye Camera']:
#                self.stop_eye_camera()
#                self.printc('Saving eye video')
#                self.cam=camera_interface.CameraRecorderProcess(self.guidata.read('Eye Camera Frame Rate'),  self.machine_config)
#                self.printc('Starting eye camera recording')
#                self.cam.start()
#                if not self.cam.wait():
#                    errormsg=self.cam.error.get() if not self.cam.error.empty() else ''
#                    raise RuntimeError('Camera did not start: {0}'.format(errormsg))
#                self.to_gui.put({'update_camera_status':'camera recording'})
        elif trigger_name=='stim data ready':
            self.save_experiment_files()
            self.printc('Experiment ready')
            if self.machine_config.PLATFORM=='ao_cortical':
                msg='Go to Matlab window and make sure that "RECORDING FINISHED" message has shown up.'
                self.notify('Info', 'Experiment ready'+'\r\n'+msg)
            elif self.machine_config.PLATFORM=='resonant':
                if self.machine_config.ENABLE_MESC_SAVE and not self.current_experiment_parameters.get('Stimulus Only', False):
                    self.printc('MESc saves data to {0}'.format(self.current_experiment_parameters['outfilename']))
                    self.mesc.save(fileop.replace_extension(self.current_experiment_parameters['outfilename'],  '.mesc'))
                else:
                    self.printc('Go to MESc processing window and add " {0} " to comment'.format(os.path.basename(self.current_experiment_parameters['outfilename'])))
#                self.printc('Sync data folder to rldata')
#                import dirsync
#                dirsync.sync(self.machine_config.EXPERIMENT_DATA_PATH, self.machine_config.BACKUP_PATH, 'sync', only=['.*hdf5$', '.*mesc$'])
            elif self.machine_config.PLATFORM=='2p':
                fn=fileop.replace_extension(self.current_experiment_parameters['outfilename'], self.microscope.fileformat)
                self.printc('Save 2p data to {0}'.format(fn))
                self.microscope.save(fn)
            self.experiment_running=False
            self.to_gui.put({'update_status':'idle'})
            self.experiment_finish_time=time.time()
            if self.machine_config.PLATFORM in ['elphys']:
                self.spikes2polar(self.current_experiment_parameters['outfilename'])
        elif trigger_name=='stim error' or trigger_name=='cam error':
            if self.machine_config.PLATFORM in ['mc_mea', 'elphys_retinal_ca',  'retinal']:
                self.enable_check_network_status=True
            elif self.machine_config.PLATFORM=='resonant':
                self.printc('Stop mesc recording, might still running')
                try:
                    self.microscope_handler('stop')
                except:
                    pass#Ignore errors
            elif self.machine_config.PLATFORM=='2p':
                self.printc('Stop two photon microscope recording, might still running')
                try:
                    if self.experiment_running:
                        self.microscope.stop()
                except:
                    pass#Ignore errors
            if trigger_name=='cam error':
                self.send({'function': 'stop_all','args':[]},'stim')
            elif trigger_name=='stim error':
                if 'cam' in self.machine_config.CONNECTIONS.keys():
                    self.send({'function': 'stop_recording','args':[]},'cam')
            self.finish_experiment()
            self.experiment_running=False
            self.to_gui.put({'update_status':'idle'})
            self.experiment_finish_time=time.time()
            self.save_experiment_files(aborted=True)
            self.printc('Experiment finished with error')
            
    def microscope_handler(self,command):
        if self.machine_config.PLATFORM=='resonant':#This is temporary, should be eliminated
            self.mesc_handler(command)
        elif self.machine_config.PLATFORM=='2p':
            if command=='init':
                for u in ['common', self.machine_config.user]:
                    import visexpman
                    microscope_class = utils.fetch_classes(visexpman.USER_MODULE+'.'+ u, classname = self.machine_config.MICROSCOPE_INTERFACE,  
                                                    required_ancestors = visexpman.engine.hardware_interface.microscope.TwoPhotonMicroscopeInterface, direct=False)
                    if len(microscope_class) == 1:
                        microscope_class = microscope_class[0][1]
                        break
                self.microscope=microscope_class()
            else:
                if hasattr(self,  'current_experiment_parameters'):
                    self.microscope.experiment_parameters=self.current_experiment_parameters
                self.microscope.machine_config=self.machine_config
                self.microscope.guiengine=self
                res=getattr(self.microscope, command)()
                self.send({'{0} command result'.format(command):res}, 'stim')
            
    def mesc_handler(self, command):
        if command=='init':
            if self.machine_config.PLATFORM=='resonant':
                from visexpman.engine.hardware_interface import mesc_interface
                self.mesc=mesc_interface.MescapiInterface()
                self.microscope=self.mesc
                self.microscope.name='mesc'
                self.printc('mesc init {0} successful'.format('not' if not self.mesc.connected else ''))
        elif command=='close':
            if hasattr(self, 'mesc'):
                self.mesc.close()
                self.printc('mesc closed')
        elif hasattr(self, 'mesc'):
            if not self.mesc.connected:
                self.printc('No connection to MESc')
                return
            self.mesc.galvo=self.guidata.read('Enable Galvo')
            res=getattr(self.mesc,  command)()
            self.printc('mesc command: {0}, {1}'.format(command,  res))
            self.send({'mesc {0} command result'.format(command):res}, 'stim')
            if not res:
                self.stop_experiment()
                    
    def convert_stimulus_to_video(self):
        if hasattr(self.machine_config, 'SCREEN_MODE') and self.machine_config.SCREEN_MODE == 'psychopy':
            self.notify('Warning', 'This function is not supported in SCREEN_MODE = psychopy')
            return
        self.printc('Converting stimulus to video started, please wait')
        cf=self.guidata.read('Selected experiment class')
        classname=cf.split(os.sep)[-1]
        c=stimulation_tester(self.machine_config.user, self.machine_config.__class__.__name__, classname,ENABLE_FRAME_CAPTURE = True,FULLSCREEN=False)
        videofilename=os.path.join(self.machine_config.EXPERIMENT_DATA_PATH, os.path.basename(os.path.dirname(cf))+'-'+os.path.basename(cf)+'.mp4')
        #Remove first frame because it is the menu
        ff=os.listdir(c['machine_config'].CAPTURE_PATH)
        ff.sort()
        os.remove(os.path.join(c['machine_config'].CAPTURE_PATH,ff[0]))
        #Convert png files to video
        self.printc('Merging frames to video file')
        videofile.images2mpeg4(c['machine_config'].CAPTURE_PATH, videofilename,self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
        self.printc('Stimulus exported to {0}, raw frames in {1}'.format(videofilename,c['machine_config'].CAPTURE_PATH))
        
    def on_exit(self):
        if hasattr(self, 'sync_recorder'):
            self._stop_sync_recorder()
            #Stop sync recorder
            self.log.info(self.log.pid)
            self.log.info(os.getpid())
            self.sync_recorder.queues['command'].put('terminate')
            self.sync_recorder.join()
            self.log.info('Sync recorder terminated')

    def init_experiment_handler(self):
        self.microscope_handler('init')

    def close_experiment_handler(self):
        self.microscope_handler('close')
        if hasattr(self, 'copier'):
            self.copier.close()

class Analysis(object):
    def __init__(self,machine_config):
        self.machine_config = machine_config
        import multiprocessing
        self.pool=multiprocessing.Pool(introspect.get_available_process_cores())
        
    def keep_rois(self, keep):
        if keep:
            if hasattr(self, 'rois'):
                self.reference_rois = [{'rectangle': r['rectangle'], 'area' :r.get('area',None)} for r in self.rois]
                for r in self.reference_rois:
                    if r['area'] is None:
                        del r['area']
                self.reference_roi_filename = copy.deepcopy(self.filename)
        else:
            if hasattr(self, 'reference_rois'):
                del self.reference_rois
            if hasattr(self, 'reference_roi_filename'):
                del self.reference_roi_filename

    def open_datafile(self,filename, ask=True):
        if hasattr(self, 'bouton_stat_text'):
            del self.bouton_stat_text
        if self.experiment_running:
            self.printc('Try again after recording')
            return
        self._check_unsaved_rois(warning_only=not ask)
        if experiment_data.parse_recording_filename(filename)['type'] != 'data':
            self.notify('Warning', 'This file cannot be displayed')
            return
        if self.machine_config.PLATFORM=='ao_cortical' and not os.path.exists(fileop.replace_extension(experiment_data.add_mat_tag(filename), '.mat')):
            self.notify('Warning', 'File is not yet completely processed by jobhandler. Try opening it a bit later')
            return
        if hasattr(self, 'reference_roi_filename') and experiment_data.parse_recording_filename(self.reference_roi_filename)['id'] == experiment_data.parse_recording_filename(filename)['id']:
            self.notify('Warning', 'ROIS cannot be copied to a file itself')
            del self.reference_roi_filename
            del self.reference_rois
        self.filename = filename
        self.printc('Opening {0}'.format(filename))
        self.datafile = experiment_data.CaImagingData(filename)
        if self.machine_config.PLATFORM not in ["elphys"]:
            self.datafile.sync2time(recreate=self.santiago_setup)
            self.to_gui.put({'image_title': os.path.dirname(self.filename)+'<br>'+os.path.basename(self.filename)})
        else:
            self.to_gui.put({'plot_title': os.path.dirname(self.filename)+'<br>'+os.path.basename(self.filename)})
            sync=self.datafile.findvar("sync")
            self._plot_elphys(sync,  full_view=True)
        if self.machine_config.PLATFORM not in  ['resonant',  "elphys"]:#Do not load imaging data
            self.datafile.get_image(image_type=self.guidata.read('3d to 2d Image Function'),motion_correction=self.guidata.read('Motion Correction'))
            self.image_scale=self.datafile.scale
            self.meanimage=self.datafile.image
            self.raw_data=self.datafile.raw_data
            self.printc(self.raw_data.shape)
            self.to_gui.put({'send_image_data' :[self.meanimage, self.image_scale, None]})
        if self.santiago_setup and 0:
            self._remove_dropped_frame_timestamps()
        if self.machine_config.PLATFORM not in ["elphys"]:
            self.tstim=self.datafile.tstim
            self.timg=self.datafile.timg
            if self.santiago_setup:
                self.timg=self.timg[:self.datafile.raw_data.shape[0]]
            self.printc(self.timg.shape)
            self.printc(self.tstim.shape)
            if self.tstim.shape[0]==0 or  self.timg.shape[0]==0:
                msg='In {0} stimulus sync signal or imaging sync signal was not recorded'.format(self.filename)
                self.notify('Error', msg)
                raise RuntimeError(msg)
        self.experiment_name= self.datafile.findvar('parameters')['stimclass']
        if self.machine_config.PLATFORM not in ['resonant',  "elphys"]:
            if self.machine_config.PLATFORM != 'ao_cortical':
                self._recalculate_background()
            try:
                self._red_channel_statistics()
            except:
                self.printc('No red stat')
            self.rois = self.datafile.findvar('rois')
            if hasattr(self, 'reference_rois'):
                if self.rois is not None and len(self.rois)>0:
                    if not self.ask4confirmation('{0} already contains Rois. These will be overwritten with Rois from previous file. Is that OK?'.format(os.path.basename(self.filename))):
                        self.datafile.close()
                        return
                #Calculate roi curves
                self.rois = copy.deepcopy(self.reference_rois)
                self._extract_roi_curves()
                self._normalize_roi_curves()
                self.current_roi_index = 0
                self.selected_roi_indexes=[]
                self.display_roi_rectangles()
                self.display_roi_curve()
                self._roi_area2image()
            elif self.rois is None:#No reference rois, nothing is loaded from file
                self.rois=[]
                self.selected_roi_indexes=[]
                self._init_meanimge_w_rois()
            else:
                self.current_roi_index = 0
                self.selected_roi_indexes=[]
                self.display_roi_rectangles()
                self.display_roi_curve()
                self._roi_area2image()
        self.datafile.close()
        self._bouton_analysis()
        if self.machine_config.PLATFORM in ['elphys']:
            self.spikes2polar(filename)

    def _remove_dropped_frame_timestamps(self,h=None):
        if h == None:
            h=self.datafile
        h.load('dropped_frames')
        if hasattr(h, 'dropped_frames'):
            h.dropped_frames=numpy.array(h.dropped_frames)
            if h.dropped_frames.sum()>0:
                self.printc('dropped frames in file')
                h.load('timg')
                #self.printc(h.timg.shape)
                #self.printc(h.dropped_frames.shape)
                h.timg=h.timg[numpy.where(h.dropped_frames==False)[0]]
                h.timg=h.timg[:h.raw_data.shape[0]]
                #self.printc(h.timg.shape)
                h.save('timg')
        
    def _init_meanimge_w_rois(self):
        self.image_w_rois = numpy.ones((self.meanimage.shape[0], self.meanimage.shape[1], 3))*self.meanimage.min()
        self.image_w_rois[:,:,1] = self.meanimage
        
    def _recalculate_background(self):
        if self.guidata.read('Background threshold')==None: return
        background_threshold = self.guidata.read('Background threshold')*1e-2
        self.background = cone_data.calculate_background(self.raw_data[:,0],threshold=background_threshold)
        if any(numpy.isnan(self.background)):
            self.printc('Background cannot be calculated')
        self.background_threshold=background_threshold
        
    def find_cells(self, pixel_range=None, ask_confirmation=True):
        if not hasattr(self, 'meanimage') or not hasattr(self, 'image_scale'):
            self.notify('Warning', 'Open datafile first')
            return
        if len(self.rois)>0:
            if ask_confirmation and not self.ask4confirmation('Automatic cell detection will remove current rois. Are you sure?'):
                return
        self.rois = []
        self.printc('Searching for cells, please wait...')
        min_ = int(self.guidata.read('Minimum cell radius')/self.image_scale)
        max_ = int(self.guidata.read('Maximum cell radius')/self.image_scale)
        sigma = self.guidata.read('Sigma')/self.image_scale
        threshold_factor = self.guidata.read('Threshold factor')
        if sigma*self.image_scale<0.2 or max_-min_>3:
            if ask_confirmation and not self.ask4confirmation('Automatic cell detection will take long with these parameters, do you want to continue?'):
                return
        img2process=numpy.copy(self.meanimage)
        if pixel_range != None:
            image_range = self.meanimage.max()-self.meanimage.min()
            low = float(pixel_range[0])/100*image_range
            high = float(pixel_range[1])/100*image_range
            img2process=numpy.where(img2process<low,low,img2process)
            img2process=numpy.where(img2process>high,high,img2process)
        if self.santiago_setup:
       #     try:
                from visexpman.users.santiago import bouton_analysis
                K=self.guidata.read('Expected cell number')
                tau=self.guidata.read('Gaussian fit std')
                p=int(self.guidata.read('Expected response type').split()[-1][1:-1])
                merge_thr=self.guidata.read('Merge threshold')
                self.suggested_rois = bouton_analysis.find_boutons(self.raw_data, K, tau, p, merge_thr)
#            except:
 #               raise RuntimeError('''
  #              1) Make sure that MATLAB python API is installed:
   #                         cd "matlabroot\extern\engines\python"
    #                        python setup.py install
     #           2) Make sure that MATLAB path is set to <visexpmanroot>\users\santiago
      #          3) Make sure that MATLAB path is set to CaImAn-Matlab folder and subfolders
        #                    ''')
        else:
            self.suggested_rois = cone_data.find_rois(numpy.cast['uint16'](signal.scale(img2process, 0,2**16-1)), min_,max_,sigma,threshold_factor)
        self._filter_rois()
        #Calculate roi bounding box
        self.roi_bounding_boxes = [[rc[:,0].min(), rc[:,0].max(), rc[:,1].min(), rc[:,1].max()] for rc in self.suggested_rois]
        self.roi_rectangles = [[sum(r[:2])*0.5, sum(r[2:])*0.5, (r[1]-r[0]), (r[3]-r[2])] for r in self.roi_bounding_boxes]
        self.rois = [{'rectangle': self.roi_rectangles[i], 'area': self.suggested_rois[i], 'manual':False} for i in range(len(self.roi_rectangles))]
        self._extract_roi_curves()
        self._normalize_roi_curves()
        self._roi_area2image()
        self.current_roi_index = 0
        self.display_roi_rectangles()
        self.display_roi_curve()
        self._bouton_analysis()
        
    def _roi_area2image(self, recalculate_contours = True, shiftx = 0, shifty = 0):
        areas = [self._clip_area(copy.deepcopy(r['area'])) for r in self.rois if r.has_key('area') and hasattr(r['area'], 'dtype')]
        if recalculate_contours:
            contours=self.pool.map(cone_data.area2edges, areas)
            self._init_meanimge_w_rois()
            for coo in contours:
                self.image_w_rois[coo[:,0],coo[:,1],2]=self.meanimage.max()*0.8
        else:
            self.image_w_rois[:,:,2] = numpy.roll(self.image_w_rois[:,:,2], shiftx, 0)
            self.image_w_rois[:,:,2] = numpy.roll(self.image_w_rois[:,:,2], shifty, 1)
        self.to_gui.put({'show_suggested_rois' :self.image_w_rois})
        
    def _filter_rois(self):
        self.suggested_rois = [r for r in self.suggested_rois if min(r[:,0].max()-r[:,0].min(), r[:,1].max()-r[:,1].min())>2]#Roi bounding rectangle's sides are greater than 2 pixel
        #remove overlapping rois
        removeable_rois = []
        for roi1, roi2 in itertools.combinations(self.suggested_rois,2):
            mask1=numpy.zeros(self.meanimage.shape)
            mask1[roi1[:,0], roi1[:,1]]=1
            mask2=numpy.zeros(self.meanimage.shape)
            mask2[roi2[:,0], roi2[:,1]]=1
            mask=mask1+mask2
            overlapping_pixels = numpy.where(mask==2)[0].shape[0]
            maximal_acceptable_overlap = min(roi1.shape[0], roi2.shape[0])*0.05#5% overlap is allowed
            if overlapping_pixels>maximal_acceptable_overlap:
                removeable_rois.extend([roi1, roi2])
        self.suggested_rois = [sr for sr in self.suggested_rois if len([rr for rr in removeable_rois if numpy.array_equal(rr, sr)])==0]
        
    def _extract_roi_curves(self):
        for r in self.rois:
            if r.has_key('area') and hasattr(r['area'], 'dtype'):
                area = self._clip_area(copy.deepcopy(r['area']))
                r['raw'] = self.raw_data[:,0,area[:,0], area[:,1]].mean(axis=1)
            elif r.has_key('rectangle'):
                r['raw'] = self.raw_data[:,0,r['rectangle'][0]-0.5*r['rectangle'][2]: r['rectangle'][0]+0.5*r['rectangle'][2], r['rectangle'][1]-0.5*r['rectangle'][3]: r['rectangle'][1]+0.5*r['rectangle'][3]].mean(axis=1).mean(axis=1)
                
    def _clip_area(self,area):
        for i in range(2):#Make sure that indexing is correct even if area falls outside the image
            area[:,i] = numpy.where(area[:,i]>=self.raw_data.shape[i+2]-1,self.raw_data.shape[i+2]-1,area[:,i])
            area[:,i] = numpy.where(area[:,i]<0,0,area[:,i])
        return area
        
    def _red_channel_statistics(self):
        self.red_stat={}
        if self.raw_data.shape[1]==1:
            self.red_stat=0
            return
        red=self.raw_data[:,1]
        x,y = cone_data.pixels_below_threshold(red,self.guidata.read('Background threshold')*1e-2)
        lowest_pixels=red[:,x,y]
        nostim_indexes=[]
        for i in range(self.tstim.shape[0]/2):
            start=self.tstim[2*i]
            end=self.tstim[2*i+1]
            nostim_indexes.extend(list(numpy.where(self.timg<start)[0]))
            nostim_indexes.extend(list(numpy.where(self.timg>end)[0]))
        self.red_stat['roi_pixels']={}
        self.red_stat['roi_pixels']['nostim']=red[nostim_indexes]
        self.red_stat['roi_pixels']['withstim']=red
        self.red_stat['lowest_green_pixels']={}
        self.red_stat['lowest_green_pixels']['nostim']=lowest_pixels[nostim_indexes].mean()
        self.red_stat['lowest_green_pixels']['withstim']=lowest_pixels.mean()
        
    def _normalize_roi_curves(self):
        if not hasattr(self, 'rois'):
            return
        baseline_length = self.guidata.read('Baseline lenght')
        for r in self.rois:
            if not hasattr(self, 'background') or any(numpy.isnan(self.background)):
                r['normalized'] = numpy.copy(r['raw'])
            else:
                r['normalized'] = signal.df_over_f(self.timg, r['raw']-self.background, self.tstim[0], baseline_length)
            r['baseline_length'] = baseline_length
            if hasattr(self, 'background'):
                r['background'] = self.background
                r['background_threshold']=self.background_threshold
            r['timg']=self.timg
            r['tstim']=self.tstim
            r['stimulus_name']=self.experiment_name
            r['meanimage']=self.meanimage
            r['image_scale']=self.image_scale
            if not self.santiago_setup:
                r['red']=copy.deepcopy(self.red_stat)
                if self.red_stat!=0:
                    area=copy.deepcopy(r['area'])
                    area=numpy.array([area[i] for i in range(area.shape[0]) if area[i][0]<r['red']['roi_pixels']['nostim'].shape[1] and area[i][1]<r['red']['roi_pixels']['nostim'].shape[2]])
                    r['red']['roi_pixels']['nostim']=r['red']['roi_pixels']['nostim'][:,area[:,0],area[:,1]].mean()
                    r['red']['roi_pixels']['withstim']=r['red']['roi_pixels']['withstim'][:,area[:,0],area[:,1]].mean()
            if r.has_key('matches'):
                for fn in r['matches'].keys():
                    raw = r['matches'][fn]['raw']
                    timg = r['matches'][fn]['timg']
                    t0=r['matches'][fn]['tstim'][0]
                    r['matches'][fn]['normalized'] = signal.df_over_f(timg, raw, t0, baseline_length)
        
    def _bouton_analysis(self):
        if self.santiago_setup:
            from visexpman.users.santiago import bouton_analysis
            if self.datafile.h5f.isopen==0:
                rois=self.rois
                raw_data=self.raw_data
                stimulus_parameters=hdf5io.read_item(self.datafile.filename, 'stimulus_parameters')
                if not hasattr(stimulus_parameters, 'keys') or 'NUMBER_OF_FLASHES' not in stimulus_parameters:
                    stimulus_parameters={}
                    stimulus_parameters['NUMBER_OF_FLASHES']=self.tstim.shape[0]/2
            else:
                raise NotImplementedError('')
            res=bouton_analysis.extract_bouton_increase(raw_data, rois, stimulus_parameters, self.guidata.read('Baseline'),
                                                                                            self.guidata.read('Preflash'),
                                                                                            self.guidata.read('Postflash'),
                                                                                            self.guidata.read('Significance Threshold'),
                                                                                            self.guidata.read('Mean Method'))
            if res!=None:
                self.rois=res[0]
                vns=['preflash','postflash','increase','is_significant','preflash_std', 'postflash_std', 'preflash_start','preflash_end','postflash_start','postflash_end']
                self.bouton_stat_text='roi index,{0}\n'.format(','.join(vns))
                roi_index=0
                for roi in self.rois:
                    if not 'bouton_analysis' in roi:
                        break
                    self.bouton_stat_text+='{0},'.format(roi_index)
                    for k in vns:
                        if isinstance(roi['bouton_analysis'][k], float):
                            self.bouton_stat_text+='{0:0.3f},'.format(roi['bouton_analysis'][k])
                        else:
                            self.bouton_stat_text+='{0},'.format(roi['bouton_analysis'][k])
                    self.bouton_stat_text=self.bouton_stat_text[:-1]
                    self.bouton_stat_text+='\n'
                    roi_index+=1
                self.printc(res[1])
                if hasattr(self, 'aggregated'):
                    self.aggregated.append([os.path.basename(self.filename), res[1]['increase'], res[1]['decrease'], len(self.rois)])
                
    def display_roi_rectangles(self):
        self.to_gui.put({'display_roi_rectangles' :[list(numpy.array(r['rectangle'])*self.image_scale) for r in self.rois]})
        
    def display_roi_curve(self):
        show_repetitions = self.guidata.show_repetitions.v if hasattr(self.guidata, 'show_repetitions') else False
        if hasattr(self, 'rois') and len(self.rois)>0:
            x_, y_, x, y, parameters = self._extract_repetition_data(self.rois[self.current_roi_index])
            if not show_repetitions or len(x) == 1:
                x=x[0]
                y=y[0]
            self.to_gui.put({'display_roi_curve': [x, y, self.current_roi_index, self.tstim, {}]})
            if self.santiago_setup and self.rois[self.current_roi_index].has_key('bouton_analysis'):
                ba=self.rois[self.current_roi_index]['bouton_analysis']
                self.printc('Preflash [df/F]: {0}, postflash: {1}, std: {3}, significant change: {2}'
                                .format(ba['preflash'], ba['postflash'], ba['is_significant'], ba['preflash_std']))
#            self.to_gui.put({'display_trace_parameters':parameters[0]})
        
    def remove_roi_rectangle(self):
        if len(self.rois)>0:
            self.to_gui.put({'remove_roi_rectangle' : numpy.array(self.rois[self.current_roi_index]['rectangle'][:2])*self.image_scale})
        
    def roi_mouse_selected(self,x,y, multiple_selection):
        if len(self.rois)==0:
            return
        roi_centers = numpy.array([r['rectangle'][:2] for r in self.rois])
        p=numpy.array([x,y])
        prev=self.current_roi_index
        self.current_roi_index = ((roi_centers-p)**2).sum(axis=1).argmin()
        if multiple_selection:
            if self.current_roi_index in self.selected_roi_indexes:
                self.selected_roi_indexes.remove(self.current_roi_index)
            else:
                if prev!=self.current_roi_index and prev not in self.selected_roi_indexes:
                    self.selected_roi_indexes.append(prev)
                self.selected_roi_indexes.append(self.current_roi_index)
            self.to_gui.put({'highlight_multiple_rois': [self.selected_roi_indexes]})
        else:
            self.selected_roi_indexes=[]
            self.display_roi_curve()
        
    def previous_roi(self):
        if not hasattr(self, 'current_roi_index'):
            return
        self.current_roi_index -= 1
        if self.current_roi_index==-1:
            self.current_roi_index=len(self.rois)-1
        self.display_roi_curve()
        
    def next_roi(self):
        if not hasattr(self, 'current_roi_index'):
            return
        self.current_roi_index += 1
        if self.current_roi_index==len(self.rois):
            self.current_roi_index=0
        self.display_roi_curve()
        
    def delete_roi(self):
        if not hasattr(self, 'current_roi_index'):
            return
        if len(self.selected_roi_indexes)==0:
            if not self.unittest and not self.ask4confirmation('Removing this ROI. Are you sure?'):
                return
            self.remove_roi_rectangle()
            self.printc('Removing roi: {0}'.format(self.rois[self.current_roi_index]['rectangle']))
            del self.rois[self.current_roi_index]
        else:
            if not self.unittest and not self.ask4confirmation('Removing all the highlighted ROIs. Are you sure?'):
                return
            for index in self.selected_roi_indexes:
                self.to_gui.put({'remove_roi_rectangle' : numpy.array(self.rois[index]['rectangle'][:2])*self.image_scale})
            self.rois=[self.rois[roi_i] for roi_i in range(len(self.rois)) if roi_i not in self.selected_roi_indexes]
        self.selected_roi_indexes=[]
        if len(self.rois)==0:
            self.current_roi_index = 0
        elif len(self.rois)<=self.current_roi_index:
            self.current_roi_index = len(self.rois)-1
        self.display_roi_curve()
        self._roi_area2image()
        self._bouton_analysis()
        
    def reset_datafile(self):
        if not hasattr(self, 'current_roi_index'):
            return
        if not self.unittest and not self.ask4confirmation('Reset file: removing all rois and exported mat file. Are you sure?'):
            return
        self.rois = []
        del self.current_roi_index
        self.to_gui.put({'reset_datafile': None})
        self._roi_area2image()
        file_info = os.stat(self.filename)
        self.datafile = experiment_data.CaImagingData(self.filename)
        self.datafile.load('rois')
        self.datafile.rois = None
        self.datafile.repetition_link = None
        self.datafile.save(['rois', 'repetition_link'], overwrite=True)
        self.datafile.close()
        fileop.set_file_dates(self.filename, file_info)
        self.printc('{0} datafile reset, rois and repetition links are removed'.format(self.filename))
        outfile=self.filename.replace('.hdf5','.'+self.guidata.read('Save File Format'))
        if os.path.exists(outfile):
            os.remove(outfile)
            self.printc('{0} removed'.format(outfile))
        
    def add_manual_roi(self, rectangle,pixel_range=None):
        rectangle = numpy.array(rectangle)/self.image_scale
        rectangle[0] +=0.5*rectangle[2]
        rectangle[1] +=0.5*rectangle[3]
        self.printc('Roi {0}, {1}'.format(rectangle, self.raw_data.shape))
        raw = self.raw_data[:,0,rectangle[0]-0.5*rectangle[2]: rectangle[0]+0.5*rectangle[2], rectangle[1]-0.5*rectangle[3]: rectangle[1]+0.5*rectangle[3]].mean(axis=1).mean(axis=1)
        img2process=numpy.copy(self.meanimage)
        if pixel_range != None:
            image_range = self.meanimage.max()-self.meanimage.min()
            low = float(pixel_range[0])/100*image_range
            high = float(pixel_range[1])/100*image_range
            img2process=numpy.where(img2process<low,low,img2process)
            img2process=numpy.where(img2process>high,high,img2process)
        if self.guidata.read('Manual Roi')=='cell shape':
            area=cone_data.roi_redetect(rectangle, img2process, subimage_size=3)
        elif self.guidata.read('Manual Roi')=='rectangle':
            areax,areay=numpy.meshgrid(numpy.arange(rectangle[0]-0.5*rectangle[2],rectangle[0]+0.5*rectangle[2]),numpy.arange(rectangle[1]-0.5*rectangle[3],rectangle[1]+0.5*rectangle[3]))
            area= numpy.cast['int'](numpy.round(numpy.array([areax.flatten(), areay.flatten()]).T))
        self.rois.append({'rectangle': rectangle.tolist(), 'raw': raw, 'area': area, 'manual':True})
        self.current_roi_index = len(self.rois)-1
        self._normalize_roi_curves()
        self.to_gui.put({'fix_roi' : None})
        self.display_roi_curve()
        self._roi_area2image()
        self.printc('Roi added, {0}'.format(rectangle))
        self.printc(len(self.rois))
        self._bouton_analysis()
        self.printc(len(self.rois))
        
    def readd_rois(self, filename):
        rois=hdf5io.read_item(filename,'rois',filelocking=False)
        h=experiment_data.CaImagingData(self.filename)
        h.repetition_link=hdf5io.read_item(filename,'repetition_link',filelocking=False)
        h.save('repetition_link')
        h.close()
        rectangles=[r['rectangle'] for r in rois]
        areas=[r['area'] for r in rois]
        
        self.rois=[]
        for i in range(len(rectangles)):
            self.rois.append({'area':areas[i], 'rectangle':rectangles[i]})
        
        self._extract_roi_curves()
        self._normalize_roi_curves()
        self._roi_area2image()
        self.current_roi_index = 0
        self.display_roi_rectangles()
        self.display_roi_curve()
        
    def _check_unsaved_rois(self, warning_only=False):
        if not hasattr(self,'filename'):
            return
        if self._any_unsaved_roi():
            if warning_only:
                print('Rois are not saved')
            elif self.ask4confirmation('Do you want to save unsaved rois in {0}?'.format(os.path.basename(self.filename))):
                self.save_rois_and_export()
                
    def _any_unsaved_roi(self):
        rois = hdf5io.read_item(self.filename, 'rois', filelocking=False)
        return (hasattr(self, 'rois') and rois is not None and len(rois)!=len(self.rois)) or (rois is None and hasattr(self, 'rois') and len(self.rois)>0)
        
    def save_rois_and_export(self,ask_overwrite=True):
        if not hasattr(self, 'filename'):
            return
        file_info = os.stat(self.filename)
        self.datafile = experiment_data.CaImagingData(self.filename)
        self.datafile.load('rois')
        if hasattr(self.datafile, 'rois'):
            if ask_overwrite and not self.ask4confirmation('{0} already contains Rois. These will be overwritten. Is that OK?'.format(os.path.basename(self.filename))):
                self.datafile.close()
                return
        self.datafile.rois = copy.deepcopy(self.rois)
        if hasattr(self, 'reference_roi_filename'):
            self.datafile.repetition_link = [experiment_data.parse_recording_filename(self.reference_roi_filename)['id']]
            self.datafile.save(['repetition_link'], overwrite=True)
        if 0:
            self.printc('Calculating and saving trace parameters')
            self.datafile.trace_parameters = [self._extract_repetition_data(roi)[-1] for roi in self.rois]
            self.datafile.save(['rois', 'trace_parameters'], overwrite=True)
        else:
            self.datafile.save(['rois'], overwrite=True)
        self.printc('Converting, please wait...')
        self.datafile.convert(self.guidata.read('Save File Format'))
        if self.santiago_setup:
            self.datafile.convert('rois')
            self.printc('Roi plots are exported to {0}'.format(self.datafile.rois_output_folder))
            if hasattr(self, 'bouton_stat_text'):
                fn=os.path.join(self.datafile.rois_output_folder, 'bouton_stat.csv')
                fileop.write_text_file(fn, self.bouton_stat_text)
                self.printc('Bouton stats are exported to {0}'.format(fn))
        self.datafile.close()
        fileop.set_file_dates(self.filename, file_info)
        self.printc('ROIs are saved to {0}'.format(self.filename))
        self.printc('Data exported to  {0}'.format(self.datafile.outfile))
        if not self.santiago_setup:
            #Copy to BACKUP_PATH/user/date/filename
            if self.machine_config.PLATFORM=='ao_cortical':
                bupath=os.path.join(self.machine_config.BACKUP_PATH , 'processed')
            else:
                bupath=self.machine_config.BACKUP_PATH 
            dst=self.datafile.backup(bupath, 2)
            self.printc('Data backed up to  {0}'.format(dst))
        
    def backup(self):
        if self.experiment_running:
            self.printc('No backup during recording')
            return
        self.printc('Backing up logfiles')
        from visexpman.engine import backup_manager
        logbuconf=backup_manager.Config()
        logbuconf.last_file_access_timeout=1
        logbuconf.COPY= [{'src':self.machine_config.LOG_PATH, 'dst':[os.path.join(self.machine_config.BACKUP_PATH, os.path.basename(self.machine_config.LOG_PATH))],'extensions':['.txt']},]
        self.logfilebackup=backup_manager.BackupManager(logbuconf,simple=True)
        self.logfilebackup.run()
        self.printc('Backing up data files')
        for folder in [self.machine_config.EXPERIMENT_DATA_PATH, os.path.join(os.path.dirname(self.machine_config.EXPERIMENT_DATA_PATH), 'raw')]:
            databuconf=backup_manager.Config()
            databuconf.last_file_access_timeout=1
            databuconf.COPY= [{'src':folder, 'dst':[os.path.join(self.machine_config.BACKUP_PATH, os.path.basename(folder))],'extensions':['.hdf5','.mat', '.zip', '.csv', '.eps', '.tif','.png']},]
            self.datafilebackup=backup_manager.BackupManager(databuconf,simple=True)
            self.datafilebackup.run()
        self.printc('Done')
        
    def run_always_analysis(self):
        t=datetime.datetime.fromtimestamp(self.last_run)
        if not self.experiment_running and (t.hour==self.machine_config.BACKUPTIME and t.minute==0):
            if self.last_run-self.experiment_finish_time>self.machine_config.BACKUP_NO_EXPERIMENT_TIMEOUT*60:
                self.backup()
        
    def roi_shift(self, h, v):
        if not hasattr(self, 'rois'):
            return
        for r in self.rois:
            r['rectangle'][0] += h
            r['rectangle'][1] += v
            if r.has_key('area') and hasattr(r['area'], 'dtype'):
                r['area'] += numpy.array([h,v])
        self._extract_roi_curves()
        self._normalize_roi_curves()
        self._roi_area2image(recalculate_contours = False, shiftx = h, shifty = v)
        self.display_roi_rectangles()
        self.display_roi_curve()
        
    def find_repetitions(self):
        if not hasattr(self,'filename'):
            return
        if self._any_unsaved_roi():
            self.save_rois_and_export()
        self.printc('Searching for repetitions, please wait...')
        aggregated_rois = cone_data.find_repetitions(self.filename, os.path.dirname(self.filename))#self.machine_config.EXPERIMENT_DATA_PATH)
        self.aggregated_rois = aggregated_rois
        files = []
        for i in range(len(self.rois)):
            if aggregated_rois[i].has_key('matches'):
                self.rois[i]['matches'] = aggregated_rois[i]['matches']
                files.extend(self.rois[i]['matches'].keys())
        if len(files)>0:
            self.printc('Repetitions found in {0} other file(s): {1}'.format(len(list(set(files))), ', ' .join(list(set(files)))))
        else:
            self.printc('No repetitions found')
        self._normalize_roi_curves()
        self.display_roi_curve()
        
    def aggregate(self, folder):
        if self.santiago_setup:
            save=self.ask4confirmation('Shall we save ROIs to files (will take longer)?')
            files=fileop.listdir(folder)
            self.files=files
            self.folder=folder
            main_folder=len([f for f in files if f[-5:]=='.hdf5'])==0
            if main_folder:
                subfolders=[f for f in files if os.path.isdir(f)]
            else:
                subfolders=[folder]
            self.abort=False
            self.printc('Batch processing files in {0}, please wait...'.format(subfolders))
            for subfolder in subfolders:
                files=fileop.listdir(subfolder)
                self.aggregated=[['filename', 'number of increase', 'number of decrease', 'number of cells']]
                for datafile in files:
                    if datafile[-5:]!='.hdf5': continue
                    self.open_datafile(datafile, ask=False)
                    try:
                        #self._bouton_analysis()
                        self.find_cells(ask_confirmation=False)
                    except:
                        continue
                    if save:
                        self.save_rois_and_export(ask_overwrite=False)
#                    if files.index(datafile)==20:
#                        break
                    self.printc('Batch progress: {0}/{1}'.format(files.index(datafile)+1,len(files)))
                    if self.abort:
                        break
                filename=subfolder+'.xls'
                if os.path.exists(filename):
                    os.remove(filename)
                self.printc('Saving aggregated data to {0}'.format(filename))
                import xlwt
                book = xlwt.Workbook()
                sh = book.add_sheet('Bouton summary')
                self.printc(self.aggregated)
                self.aggregated=self.aggregated[0::2]
                for line in range(len(self.aggregated)):#bouton analysis is run twice: at file open and cell detection
                    for c in range(4):
                        sh.write(line+1, c, self.aggregated[line][c])
                book.save(filename)
                #Extract samre regions:
                animals=list(set(['-'.join(row[0].split('-')[:2]) for row in self.aggregated[1:]]))
                self.aggregated_animals=[self.aggregated[0]]
                self.aggregated_animals[0][0]='animal'
                book = xlwt.Workbook()
                sh = book.add_sheet('Bouton summary')
                [sh.write(0, i, self.aggregated[0][i]) for i in range(0,4)]
                line=1
                for a in animals:
                    stats=numpy.array([row[1:] for row in self.aggregated[1:] if a in row[0]]).sum(axis=0)
                    self.printc((line,a,stats))
                    sh.write(line, 0, a)
                    [sh.write(line, col, stats[col-1]) for col in range(1,4)]
                    line+=1
                filename_compiled=filename.replace('.xls', '_compiled.xls')
                book.save(filename_compiled)
                self.printc('Saving aggregated data to {0}'.format(filename_compiled))
                self.printc('Done')

        else:
            self.printc('Aggregating cell data from files in {0}, please wait...'.format(folder))
            self.cells = cone_data.aggregate_cells(folder)
            self.printc('Calculating parameter distributions')
            self.parameter_distributions = cone_data.quantify_cells(self.cells)
            self.stage_coordinates = cone_data.aggregate_stage_coordinates(folder)
            if len(self.cells)==0:
                self.notify('Warning', '0 cells aggregated, check if selected folder contains any measurement file')
                return
            self.printc('Aggregated {0} cells. Saving to file...'.format(len(self.cells)))
            aggregate_filename = os.path.join(folder, 'aggregated_cells_{0}.'.format(os.path.basename(folder)))
            h=hdf5io.Hdf5io(aggregate_filename+'hdf5', filelocking=False)
            h.cells=self.cells
            h.stage_coordinates=self.stage_coordinates
            h.parameter_distributions=self.parameter_distributions
            h.save(['stage_coordinates','cells', 'parameter_distributions'])
            h.close()
            scipy.io.savemat(aggregate_filename+'mat', {'cells':self.cells, 'parameter_distributions': self.parameter_distributions, 'stage_coordinates': 'not found' if self.stage_coordinates=={} else self.stage_coordinates}, oned_as = 'row', long_field_names=True,do_compression=True)
            self.printc('Aggregated cells are saved to {0}mat and {0}hdf5'.format(aggregate_filename))
            self.to_gui.put({'display_cell_tree':self.cells})
            self.display_trace_parameter_distribution()
        
    def display_trace_parameter_distribution(self):
        if not hasattr(self, 'parameter_distributions'):
            return
        self.to_gui.put({'display_trace_parameter_distributions':self.parameter_distributions})
        
    def _extract_repetition_data(self,roi):
        '''
        Extracts the following from a roi:
        1) parameters for each repetition
        2) ca signal and time series for each repetition
        3) Mean of ca signals
        '''
        mean_of_repetitions = self.guidata.mean_of_repetitions.v if hasattr(self.guidata, 'mean_of_repetitions') else False
        baseline_length = self.guidata.read('Baseline lenght')
        x=[self.timg]
        key='raw' if (self.santiago_setup or self.machine_config.PLATFORM=='ao_cortical') else 'normalized'
        y=[roi[key]]
        parameters = []
        if roi.has_key('matches'):
            for fn in roi['matches'].keys():
                #collect matches, shift matched curve's timing such that sync events fall into the same time
                tdiff = self.tstim[0]-self.rois[self.current_roi_index]['matches'][fn]['tstim'][0]
                x.append(self.rois[self.current_roi_index]['matches'][fn]['timg']+tdiff)
                y.append(self.rois[self.current_roi_index]['matches'][fn]['normalized'])
        try:
            for i in range(len(x)):
                baseline_mean, amplitude, rise, fall, drop, fitted  = cone_data.calculate_trace_parameters(y[i], self.tstim, x[i], baseline_length)
                parameters.append({'amplitude':amplitude, 'rise': rise, 'fall': fall, 'drop':drop})
        except:
                self.printc('Trace parameters cannot be calculated')
        x_,y_ = signal.average_of_traces(x,y)
        parameters_ = {}
        if mean_of_repetitions:
            for pn in parameters[0].keys():
                parameters_[pn] = numpy.array([par[pn] for par in parameters]).mean()
            parameters = [parameters_]
        return x_, y_, x, y, parameters
        
    def display_cell(self, path):
        index=int(path[0].split('_')[-1])
        self.to_gui.put({'image_title' :'/'.join(path)})
        if len(path)==1:#Display all stimulus and all repetitions
            #Collect all roi curves and meanimage
            roi=self.cells[index]
            first_roi = roi[[k for k in roi.keys() if k!='scan_region'][0]].values()[0]
            rois = []
            for k,r in roi.items():
                if k == 'scan_region': continue
                rois.extend(r.values())
            self._display_single_roi(first_roi)
            possible_colors = [(0,0,0),(0,0,200),(0,200,0)]
            stimnames = [stimname for stimname in roi.keys() if stimname != 'scan_region']
            colors = []
            for i in range(len(stimnames)):
                colors.extend(len(roi[stimnames[i]].keys())*[possible_colors[i]])
            timgs, tstim, normalized = self._align_curves(rois)
            options = {'plot_average':False, 'colors' : colors}
            self.to_gui.put({'display_roi_curve': [timgs, normalized, 0, tstim, options]})
        elif len(path)==2:
            roi=self.cells[index][path[1]].values()
            first_roi = roi[0]
            self._display_single_roi(first_roi)
            timgs, tstim, normalized = self._align_curves(roi)
            self.to_gui.put({'display_roi_curve': [timgs, normalized, 0, tstim, {}]})
        elif len(path)==3:
            roi=self.cells[index][path[1]][path[2]]
            self._display_single_roi(roi)
            self.to_gui.put({'display_roi_curve': [roi['timg'], roi['normalized'], 0, roi['tstim'], {}]})
            
    def _align_curves(self, rois):
        tdiffs = numpy.array([r['tstim'][0] for r in rois])
        tdiffs -= tdiffs.min()
        timgs=numpy.array([r['timg'] for r in rois])
        transposed=False
        if len(timgs.shape)==2 and timgs.shape[0]<timgs.shape[1]:#For some weird reoson timgs can come transposed
            timgs=timgs.T
            transposed=True
        timgs = list(timgs-tdiffs)
        if transposed:
            timgs = list(numpy.array(timgs).T)
        normalized=[r['normalized'] for r in rois]
        tstim = rois[tdiffs.argmin()]['tstim']
        return timgs, tstim, normalized
            
    def _display_single_roi(self,roi):
        self.to_gui.put({'send_image_data' :[roi['meanimage'], roi['image_scale']]})
        self.to_gui.put({'display_roi_rectangles' :[list(numpy.array(roi['rectangle'])*roi['image_scale']) ]})
        
    def remove_recording(self,filename):
        if not experiment_data.is_recording_filename(filename) or os.path.splitext(filename)[1]!='.hdf5':
            self.notify('Info', '{0} is not a recording file'.format(filename))
            return
        #Figure out which files will be removed
        measurement_folder=os.path.dirname(filename)
        h=hdf5io.Hdf5io(filename,filelocking=False)
        nodes=['ftiff','fphys']
        files2remove = [filename]
        for n in nodes:
            h.load(n)
            if hasattr(h,n):
                path=str(getattr(h,n)).lstrip()
                path = path[0].lower()+path[1:]#In windows the drive letter mightr come lowercase and uppercase. 
                if n=='ftiff':
                    path=os.path.dirname(path)
                if os.path.exists(path) and measurement_folder in path:
                    files2remove.append(path)
        h.close()
        id=experiment_data.parse_recording_filename(filename)['id']
        files2remove.extend([fn for fn in fileop.listdir_fullpath(measurement_folder) if id in fn and fn != filename])
        if not self.ask4confirmation('The following files will be removed:\r\n{0}. Is that OK?'.format('\r\n'.join(files2remove))):
            return
        self.printc('Removing {0}, please wait...'.format(', '.join(files2remove)))
        for fn in files2remove:
            if hasattr(self.machine_config, 'DELETED_FILES_PATH'):
                shutil.move(fn,self.machine_config.DELETED_FILES_PATH)
            else:
                os.remove(fn)
        self.printc('Done')
        
    def plot_sync(self,filename):
        if self.machine_config.PLATFORM in ['ao_cortical', 'resonant',  'retinal',  "elphys", '2p', 'behav'] or self.santiago_setup:
            if os.path.splitext(filename)[1]!='.hdf5':
                self.notify('Warning', 'Only hdf5 files can be opened!')
                return
            if not os.path.exists(fileop.replace_extension(experiment_data.add_mat_tag(filename), '.mat')) and not self.santiago_setup:
                if not self.ask4confirmation('File might be opened by other applications. Opening it might lead to file corruption. Continue?'):
                    return
            self.fn=filename
            self.printc('Opening {0}'.format(filename))
            h=hdf5io.Hdf5io(filename)
            scale=h.findvar('sync_scaling')
            self.printc(scale)
            sync=h.findvar('sync')
            if sync.dtype.name=='uint16':
                sync=signal.from_16bit(sync,scale)
            elif sync.dtype.name=='uint8':
                sync=signal.from_16bit(sync*256,scale)
            elif sync.dtype.name=='float32':
                pass
            else:
                raise NotImplementedError(sync.dtype.name)
            fs=h.findvar('configs')['machine_config']['SYNC_RECORDER_SAMPLE_RATE']
            x=[]
            y=[]
            t=numpy.arange(sync.shape[0])*(1.0/fs)
            for ch in range(sync.shape[1]):
                x.append(t)
                spacing=sync.max() if sync.max()>10 else 10
                y.append(sync[:,ch]+numpy.ceil(ch*spacing))
            self.sync=sync
            self.to_gui.put({'plot_sync':[x,y]})
            h.load('parameters')
            if 'Runwheel attached' in h.parameters and h.parameters['Runwheel attached']==True:
                mc=h.findvar('configs')['machine_config']
                channels=mc['RUNWHEEL_SIGNAL_CHANNELS'] if 'RUNWHEEL_SIGNAL_CHANNELS' in mc else [3, 4]
                chab=self.sync[:,channels]
#                cha=numpy.nonzero(numpy.diff(numpy.where(chab[:, 0]>2.5), 1, 0))[0][0::2]
                cha=signal.trigger_indexes(numpy.where(chab[:, 0]>2.5, 5, 0))[0::2]
                signs=numpy.where(chab[cha+2, 0]>2.5, 1, -1)[1:]
                dfi=2*numpy.pi/360
                self.speed=dfi/numpy.diff(cha/float(fs))*signs
                t=(cha/float(fs))[1:]
                if self.speed.shape[0]>0:
                    self.to_gui.put({'plot_speed':[[t],[self.speed]]})
            self.timg=h.findvar('timg')
            self.tstim=h.findvar('tstim')
            self.tcam=h.findvar('tcam')
            h.close()
        else:
            raise NotImplementedError()
            
    def add_comment(self,filename):
        if os.path.splitext(filename)[1]!='.hdf5':
            self.notify('Warning', 'Only hdf5 files can be opened!')
            return
        self.hcomment=hdf5io.Hdf5io(filename)
        self.hcomment.load('comment')
        if not hasattr(self.hcomment,'comment'):
            self.hcomment.comment=''
        self.to_gui.put({'add_comment':[self.hcomment.comment]})
        
    def save_comment(self,comment):
        if hasattr(self, 'hcomment') and self.hcomment.h5f.isopen:
            self.hcomment.comment=comment+'\r\nSaved on '+utils.timestamp2ymdhm(time.time())+'\r\n'
            self.hcomment.save('comment')
            self.printc('{0} comment saved to {1}'.format(comment, self.hcomment.filename))
            self.hcomment.close()
            
    def spikes2polar(self,filename):
        self.printc("Display polar plot")
        self.to_gui.put({'polar_plot':[elphys.spikes2polar(filename)]})
        
        
        
        
    def fix_files(self,folder):
        self.printc('Fixing '+folder)
        files=fileop.listdir_fullpath(folder)
        files.sort()
        self.abort=False
        for f in files:
            if 'hdf5' not in f: continue
            self.open_datafile(f)
            self._normalize_roi_curves()
            self.save_rois_and_export(ask_overwrite=False)
            if self.abort:break
        self.printc('DONE')
        self.notify('Info', 'ROI fixing is ready')
        
    def check_files(self,folder):
        self.printc('Checking '+folder)
        files=fileop.listdir_fullpath(folder)
        files.sort()
        self.abort=False
        self.broken_files=[]
        for f in files:
            if 'hdf5' not in f: continue
            try:
                self.open_datafile(f)
            except:
                self.broken_files.append(f)
            if self.abort:break
        self.printc('Broken files:')
        [self.printc('{0}'.format(bf)) for bf in self.broken_files]
        self.printc('DONE')
        self.notify('Info', 'Checking files is ready')
        
    def check_stim_timing(self,folder):
        files=fileop.listdir_fullpath(folder)
        files.sort()
        self.abort=False
        problematic_files=[]
        for f in files:
            if 'hdf5' not in f: continue
            try:
                self.open_datafile(f)
                if self.tstim[0]>11:
                    problematic_files.append(f)
            except:
                import traceback
                self.printc(traceback.format_exc())
                problematic_files.append(f)
                self.datafile.close()
            if self.abort:break
        self.printc('Problematic files')
        [os.remove(f) for f in problematic_files]
        problematic_files=[os.path.basename(f).split('_')[1] for f in problematic_files]
        problematic_files.sort()
        for f in problematic_files:
            self.printc(f)
        self.printc('DONE')
        
    def meanimage2tiff(self,fn):
        import tifffile
        tifffile.imsave(fn, numpy.cast['uint16'](signal.scale(self.meanimage)*(2**16-1)))
        
    def close_analysis(self):
        self._check_unsaved_rois(warning_only=True)
        
class UserGUIEngine(object):
    def __init__(self,parent):
        self.printc=parent.printc
        self.machine_config=parent.machine_config
        self.parent = parent
        self.init()
        
    def init(self):
        pass
        
    def run(self):
        '''
        Users should subclass from this to define user gui engine
        '''
    
class GUIEngine(threading.Thread, queued_socket.QueuedSocketHelpers):
    '''
    GUI engine: receives commands via queue interface from gui and performs the following actions:
     - stores data internally
     - initiates actions on gui or in engine
     
     Command format:
     {'command_name': [parameters]}
    '''

    def __init__(self, machine_config, log, socket_queues, unittest=False,enable_network=True):
        self.socket_queues=socket_queues
        self.unittest=unittest
        self.log=log
        self.machine_config = machine_config
        threading.Thread.__init__(self)
        self.from_gui = Queue.Queue()
        self.to_gui = Queue.Queue()
        self.context_filename = fileop.get_context_filename(self.machine_config,'npy')
        self.load_context()
        self.check_software_hash()
        self.widget_status = {}
        self.last_network_check=time.time()
        self.enable_check_network_status=enable_network
        self.enable_network=enable_network
        self.mes_connection_status=False
        if hasattr(self.machine_config, 'USER_GUI_ENGINE'):
            for u in ['common', self.machine_config.user]:
                import visexpman
                user_gui_engine_class = utils.fetch_classes(visexpman.USER_MODULE+'.'+ u, classname = self.machine_config.USER_GUI_ENGINE,  
                                                    required_ancestors = UserGUIEngine, direct=False)
                if len(user_gui_engine_class ) == 1:
                    user_gui_engine_class  = user_gui_engine_class [0][1]
                    break
            self.user_gui_engine=user_gui_engine_class (self)
            
        
    def load_context(self):
        self.guidata = GUIData()
        if os.path.exists(self.context_filename):
            context_stream = numpy.load(self.context_filename)
            self.guidata.from_dict(utils.array2object(context_stream))
        else:
            self.printc('Warning: Restart gui because parameters are not in guidata')#TODO: fix it!!!

    def dump(self, filename=None):
        #TODO: include logfile and context file content
        variables = ['rois', 'reference_rois', 'reference_roi_filename', 'filename', 'tstim', 'timg', 'meanimage', 'image_scale'
                    'raw_data', 'background', 'current_roi_index', 'suggested_rois', 'roi_bounding_boxes', 'roi_rectangles', 'image_w_rois',
                    'aggregated_rois', 'context_filename', 'cells']
        dump_data = {}
        for v in variables:
            if hasattr(self, v):
                dump_data[v] = getattr(self,v)
        dump_data['machine_config'] = self.machine_config.serialize()
        dump_data['guidata'] = self.guidata.to_dict()
        if filename is None:
            filename = os.path.join(self.machine_config.LOG_PATH, 'dump_{0}.{1}'.format(utils.timestamp2ymdhms(time.time()).replace(':','-').replace(' ', '-'),'npy'))
        dump_stream=utils.object2array(dump_data)
        numpy.save(filename,dump_stream)
        self.printc('GUI engine dumped to {0}'.format(filename))
        
    def save_software_hash(self):
        hash=introspect.visexpman2hash()
        if hasattr(self.guidata.read('software_hash'),  'dtype'):
            self.guidata.software_hash.v=hash
        else:
            self.guidata.add('software_hash', hash, 'hash/software_hash')
        if self.machine_config.PLATFORM=='ao_cortical':
            meshash=introspect.mes2hash()
            if self.guidata.read('mes_hash')==None:
                self.guidata.add('mes_hash', hash, 'hash/mes_hash')
            else:
                self.guidata.mes_hash.v=meshash
        self.printc('Software hash saved: {0}'.format(hash))
        self.save_context()
    
    def check_software_hash(self):
        current_hash=introspect.visexpman2hash()
        saved_hash=self.guidata.read('software_hash')
        if not numpy.array_equal(saved_hash, current_hash):
            self.to_gui.put({'permanent_warning':'Software hashes do not match, make sure that the correct software version is used!'})
            self.printc('Software hashes do not match, make sure that the correct software version is used!')
        if self.machine_config.PLATFORM=='ao_cortical':
            meshash=introspect.mes2hash()
            saved_hash=self.guidata.read('mes_hash')
            if not numpy.array_equal(saved_hash, meshash):
                print(saved_hash, meshash)
                self.to_gui.put({'permanent_warning':'MES has changed, hashes do not match.'})
                self.printc('MES has changed, hashes do not match.')

    def save_context(self):
        context_stream=utils.object2array(self.guidata.to_dict())
        numpy.save(self.context_filename,context_stream)
        
    def get_queues(self):
        return self.from_gui, self.to_gui

    def printc(self,txt):
        self.to_gui.put({'printc':str(txt)})
        
    def ask4confirmation(self,message):
        self.to_gui.put({'ask4confirmation':message})
        while True:
            if not self.from_gui.empty():
                break
            time.sleep(0.05)
        result=self.from_gui.get()
        self.log.info('Ask for confirmation: {0}, {1}'.format(message, result), 'engine')
        return result
        
    def notify(self,title,message):
        self.printc('Notify: {0}, {1}'.format(title, message))
        self.to_gui.put({'notify':{'title': title, 'msg':message}})
        
    def update_widget_status(self, status):
        '''
        Update widget status
        
        Engine shall know whether a pop up window is open or not
        '''
        for k,v in status.items():
            self.widget_status[k]=v
            
    def check_network_status(self):
        now=time.time()
        if now-self.last_network_check<4:
            return
        self.last_network_check=now
        self.connected_nodes = ''
        n_connected = 0
        n_connections = len(self.socket_queues.keys())
        for remote_node_name, socket in self.socket_queues.items():
            if self.ping(timeout=0.5, connection=remote_node_name):
                self.connected_nodes += remote_node_name + ' '
                n_connected += 1
        if self.machine_config.PLATFORM=='ao_cortical' and 0:#Disabled now
            #Initiate stim to check mes connection but don't wait for result
            self.send({'function': 'check_mes_connection','args':[]},'stim')
            n_connections+=1
            if self.mes_connection_status:
                n_connected += 1
                self.connected_nodes+='stim-mes '
        elif self.machine_config.PLATFORM in ['2p', 'resonant']:
            n_connections+=1
            if hasattr(self, 'mesc'):
                if self.mesc.ping():
                    n_connected += 1
                    self.connected_nodes+='mesc '
            elif hasattr(self, 'microscope'):
                if self.microscope.ping():
                    n_connected += 1
                    self.connected_nodes+=self.microscope.name+' '
        self.to_gui.put({'update_network_status':'Network connections: {2} {0}/{1}'.format(n_connected, n_connections, self.connected_nodes)})
        
    def check_network_messages(self):
        for connname in self.socket_queues.keys():
            msg=self.recv(connname)
            if msg is not None and 'ping' not in msg  and 'pong' not in msg:
                if isinstance(msg,str):
                    self.printc('{0} {1}'.format(connname.upper(),msg))
                elif 'trigger' in msg:
                    if hasattr(self,'trigger_handler'):
                        self.trigger_handler(msg['trigger'])
                elif 'notify' in msg:
                    self.notify(msg['notify'][0],msg['notify'][1])
                elif 'mes_connection_status' in msg:
                    self.mes_connection_status=msg['mes_connection_status']
                elif 'mesc' in msg and hasattr(self,  'mesc_handler'):
                    self.microscope_handler(msg['mesc'])#TODO: eliminate this
                elif '2p' in msg and hasattr(self, 'microscope_handler'):
                    self.microscope_handler(msg['2p'])
                    
        
    def run(self):
        self.loop_wait=20e-3
        run_always=[fn for fn in dir(self) if 'run_always' in fn and callable(getattr(self, fn))]
        for fn in dir(self):
            if 'init_'==fn[:5] and callable(getattr(self, fn)):
                getattr(self, fn)()
        while True:
            try:                
                self.last_run = time.time()#helps determining whether the engine still runs
                for fn in run_always:
                    getattr(self, fn)()
                if hasattr(self, 'user_gui_engine'):
                    self.user_gui_engine.run()
                if self.enable_check_network_status:
                    self.check_network_status()
                if self.enable_network:
                    self.check_network_messages()
                if not self.from_gui.empty():
                    msg = self.from_gui.get()
                    if msg == 'terminate':
                        break
                else:
                    time.sleep(self.loop_wait)
                    continue
                #parse message
                if 'data' in msg:#expected format: {'data': value, 'path': gui path, 'name': name}
                    self.guidata.add(msg['name'], msg['data'], msg['path'])#Storing gui data
                    [getattr(c,'check_parameter_changes')(self,msg['name']) for c in self.__class__.__bases__ if hasattr(c,'check_parameter_changes')]
                elif 'read' in msg:#gui might need to read guidata database
                    value = self.guidata.read(**msg)
                    getattr(self, 'to_gui').put(value)
                elif 'function' in msg:#Functions are simply forwarded
                    #Format: {'function: function name, 'args': [], 'kwargs': {}}
#                    with introspect.Timer(str(msg)):
                    getattr(self, msg['function'])(*msg['args'])
                    if hasattr(self, 'log') and hasattr(self.log, 'info'):
                        self.log.info(msg, 'engine')
            except:
                import traceback
                self.printc(traceback.format_exc())
                self.dump()
                self.close_open_files()
            time.sleep(self.loop_wait)
        self.close()
        
    def close_open_files(self):
        if hasattr(self, 'datafile') and self.datafile.h5f.isopen==1:
            self.datafile.close()
            self.printc('{0} file is closed'.format(self.datafile.filename))
        
    def close(self):
        self.save_context()
       
class ElphysEngine():
    '''
    Elphys platform specific methods separated from gui engine
    '''
    def run_always_elphys_engine(self):
        if self.machine_config.PLATFORM!='elphys':
            return
        if not hasattr(self, 'last_mem_check'):
            self.last_mem_check=time.time()
        if time.time()-self.last_mem_check>60 and 0:
            import os
            import psutil
            process = psutil.Process(os.getpid())
            self.printc((process.get_memory_info()[0]/1024/1024))
            self.last_mem_check=time.time()
            
    
    def read_flowmeter(self):
        if not hasattr(self, 'flowmeter'):
            from visexpman.engine.hardware_interface.flowmeter import SLI_2000Flowmeter
            self.flowmeter=SLI_2000Flowmeter(self.machine_config.FLOWMETER_PORT)
            self.flow_rates=[]
            self.flow_rate_times=[]
            self.live_data.shape[0]
        fr=self.flowmeter.get_flow_rate()
        if fr!=None:
            self.flow_rates.append(fr)
            self.flow_rate_times.append(time.time())
        return fr
    
    
    def _plot_elphys(self, sync, full_view=False):
        if self.machine_config.PLATFORM in ['erg']:
            return
        #Filter rawdata
        if self.guidata.read('Enable Filter')==True:
            order=self.guidata.filter_order.v
            frq=float(self.guidata.cut_frequency.v)
            sample_rate=self.machine_config.SYNC_RECORDER_SAMPLE_RATE
            if self.guidata.filter_type.v=='lowpass':
                self.filter=scipy.signal.butter(order,frq/sample_rate,'low')
            else:
                self.filter=scipy.signal.butter(order,frq/sample_rate,'high')
            self.filtered=scipy.signal.filtfilt(self.filter[0],self.filter[1], sync[:,self.machine_config.ELPHYS_INDEX]).real
        else:
            self.filtered=sync[:,self.machine_config.ELPHYS_INDEX]
        if self.guidata.read('Displayed signal length')>0 and not full_view:
            index=-int(self.guidata.read('Displayed signal length')*self.machine_config.SYNC_RECORDER_SAMPLE_RATE)
        else:
            index=0
        self.iindex=index
        t=numpy.arange(sync.shape[0])/float(self.machine_config.SYNC_RECORDER_SAMPLE_RATE)
        t=t[index:]
        if self.machine_config.PLATFORM=='elphys':
            mode=self.guidata.read('Clamp Mode')
            #Scale elphys
            if 'Voltage' in mode:
                unit='nA'
                scale=self.guidata.read('Current Gain')
                command_scale=self.guidata.read("Voltage Command Sensitivity")
            elif 'Current' in mode:
                unit='mV'
                scale=self.guidata.read('Voltage Gain')
                command_scale=self.guidata.read("Current Command Sensitivity")
            fn= self.filename if hasattr(self, 'filename') else str(self.current_experiment_parameters['stimclass'])
            scale*=1e-3
            if self.guidata.read('Show raw voltage'):
                scale=1.0
                command_scale=1.0
            unit='Red / Green: '+unit
            cmd_disp_ena=False#self.guidata.read('Show Command Trace')
            stim_disp_ena=True#self.guidata.read('Show Stimulus Trace')
            n=1+int(cmd_disp_ena)
            x=n*[t]
            y=[self.filtered[index:]/scale]
            cc=[[255, 0, 0]]
            if cmd_disp_ena:
                y.append(sync[index:, self.machine_config.ELPHYSCOMMAND_INDEX]*command_scale)
                cc.append([0, 255, 0])
#            y.append(sync[index:,  self.machine_config.TSTIM_SYNC_INDEX])
#            cc.append([0, 0, 255])
            self.y=y
            self.sync=sync
            labels={"left": unit,  "bottom": "time [s]"}
            self.yrange=[self.guidata.read('Y min'),  self.guidata.read('Y max')] if not self.guidata.read('Y axis autoscale') else None
            thr=2.5
            sig=sync[index:, self.machine_config.TSTIM_SYNC_INDEX]
            tsync=signal.detect_edges(sig,thr)/float(self.machine_config.SYNC_RECORDER_SAMPLE_RATE)
            if sig[0]>thr:
                tsync=numpy.insert(tsync, 0, 0)
            if tsync.shape[0]%2==1:
                tsync=numpy.append(tsync,  (sig.shape[0])/float(self.machine_config.SYNC_RECORDER_SAMPLE_RATE))
            tsync+=t[0]
            self.to_gui.put({'plot_title': ''})
            self.to_gui.put({'display_roi_curve': [x, y, None, tsync, {'plot_average':False, "colors":cc,  "labels": labels, 'range': self.yrange}]})
#        elif self.machine_config.AMPLIFIER_TYPE=='differential' :
#            n=sync.shape[1]
#            x=n*[t]
#            y=[sync[index:,i] for i in range(n)]
#            if hasattr(self.machine_config, 'CHANNEL_SCALE'):
#                y=[(y[i]-self.machine_config.CHANNEL_OFFSET[i])*self.machine_config.CHANNEL_SCALE[i] for i in range(n)]
#            cc=[colors.get_color(i,unit=False) for i in range(n)]
#            cc_html=[('#%02x%02x%02x' % (cci[0], cci[1], cci[2])).upper() for cci in cc]
#            labels={"left": '',  "bottom": "time [s]"}
#            xleft=[]
#            yleft=[]
#            ccleft=[]
#            xright=[]
#            yright=[]
#            ccright=[]
#            left_title=''
#            right_title=''
#            self.t=t
#            flow_rate_times=[f-self.flow_rate_times[0] for f in self.flow_rate_times]
#            fr=numpy.array([[flow_rate_times[i], self.flow_rates[i]] for i in range(len(self.flow_rates)) if max(t)>flow_rate_times[i] and min(t)<flow_rate_times[i]])
#            for i in range(len(self.plot_signal_enable['left'])):
#                if self.plot_signal_enable['left'][i]:
#                    if self.machine_config.CHANNEL_NAMES[i]=='Flowrate':
#                        if fr.shape[0]>0:
#                            xleft.append(fr[:,0])
#                            yleft.append(fr[:,1])
#                            ccleft.append(('#%02x%02x%02x' % (255, 200, 100)).upper())
#                            last_value='<font color="{2}">{0:0.1f} {1}</font>, '.format(yleft[-1][-1], self.machine_config.CHANNEL_UNITS[i], ccleft[-1])
#                            
#                    else:
#                        xleft.append(x[i])
#                        yleft.append(y[i])
#                        ccleft.append(cc[i])
#                        last_value='<font color="{2}">{0:0.1f} {1}</font>, '.format(y[i][-1], self.machine_config.CHANNEL_UNITS[i], cc_html[i])
#                    if len(self.machine_config.CHANNEL_UNITS[i])>0:
#                        left_title+=last_value
#                if self.plot_signal_enable['right'][i]:
#                    if self.machine_config.CHANNEL_NAMES[i]=='Flowrate':
#                        pass
#                    else:
#                        xright.append(x[i])
#                        yright.append(y[i])
#                        ccright.append(cc[i])
#                        last_value='<font color="{2}">{0:0.1f} {1}</font>, '.format(y[i][-1], self.machine_config.CHANNEL_UNITS[i], cc_html[i])
#                        if len(self.machine_config.CHANNEL_UNITS[i])>0:
#                            right_title+=last_value
#            self.to_gui.put({'display_roi_curve': [xright, yright, None, None, {'plot_average':False, "colors":ccright,  "labels": labels}]})
#            self.to_gui.put({'curves2plot2': [xleft, yleft, None, None, {'plot_average':False, "colors":ccleft,  "labels": labels}]})
#            self.to_gui.put({'plot_title': right_title})
#            self.to_gui.put({'plot2_title': left_title})   
           
class MainUIEngine(GUIEngine,Analysis,ExperimentHandler, ElphysEngine):
    def __init__(self, machine_config, log, socket_queues, unittest=False):
        GUIEngine.__init__(self, machine_config,log, socket_queues, unittest)
        Analysis.__init__(self, machine_config)
        ExperimentHandler.__init__(self)

    def close(self):
        self.on_exit()
        self.close_analysis()
        print('analysis closed')
        self.close_experiment_handler()
        print('exphandler closed')
        GUIEngine.close(self)

class CaImagingEngine(GUIEngine):
    def __init__(self, machine_config, log, socket_queues, unittest=False):
        GUIEngine.__init__(self, machine_config,log, socket_queues, unittest)
        self.isrunning=False
        self.limits = {}
        self.limits['min_ao_voltage'] = -self.machine_config.MAX_SCANNER_VOLTAGE
        self.limits['max_ao_voltage'] = self.machine_config.MAX_SCANNER_VOLTAGE
        self.limits['min_ai_voltage'] = -self.machine_config.MAX_PMT_VOLTAGE
        self.limits['max_ai_voltage'] = self.machine_config.MAX_PMT_VOLTAGE
        self.limits['timeout'] = self.machine_config.TWO_PHOTON_DAQ_TIMEOUT
        self.instrument_name = 'daq'
        self.laser_on = False
        self.projector_state = False
        self.frame_ct=0
        self.ENABLE_16_BIT=True
        self.images={}
        self.daq_logger_queue = self.log.get_queues()[self.instrument_name]
        self.daq_queues = daq_instrument.init_daq_queues()
        
    def one_second_periodic(self):
        '''
        Periodically checks if any command has arrived via zmq
        '''
        message = self.recv()
        if message is None:
            return
        if not utils.safe_has_key(message, 'function'):
            return False
        if not hasattr(self, message['function']):
            return False
        args = message.get('args', [])
        kwargs = message.get('kwargs', {})
        try:
            getattr(self, message['function'])(*args, **kwargs)
            return True
        except:
            import traceback
            self.printc(traceback.format_exc())
            
    def generate_imaging_parameters(self):
        params={}
        size=utils.rc((self.guidata.read('scan height'),self.guidata.read('scan width')))
        resolution=self.guidata.read('pixel size')
        channels = []
        if self.guidata.read('enable top'):
            channels.append('TOP')
        if self.guidata.read('enable side'):
            channels.append('SIDE')
        if len(channels)==0:
            self.printc('No channels selected')
            return
        psu=self.guidata.read('pixel size unit')
        if psu=='um/pixel':
            resolution=1.0/resolution
        elif psu=='us':
            raise NotImplementedError('')
        self.image_scale=1.0/resolution
        center = utils.rc((self.guidata.read('scan center y'),self.guidata.read('scan center x')))
        constraints = {}
        constraints['x_flyback_time']=self.guidata.read('x scanner flyback time')*1e-6
        constraints['y_flyback_time']=self.guidata.read('y scanner flyback time')*1e-6
        constraints['x_max_frq']=1400
        constraints['f_sample']=self.guidata.read('analog output sampling rate')*1e3
        constraints['movement2voltage']=self.guidata.read('scanner movement to voltage factor')
        self.printc('Generating scanner signals')
        x,y,frame_sync,stim_sync,valid_data_mask,signal_attributes = scanner_control.generate_scanner_signals(size,resolution,center,constraints)
        params['channels']=channels
        params['size']=size
        params['resolution']=resolution
        params['analog_input_sampling_rate']=self.guidata.read('analog input sampling rate')*1e3
        params['analog_output_sampling_rate']=self.guidata.read('analog output sampling rate')*1e3
        params.update({'x':x,'y':y,'frame_sync':frame_sync,'stim_sync': stim_sync,'valid_data_mask':valid_data_mask})
        params.update(signal_attributes)
        params.update(constraints)
        return params
        
    def start_imaging(self, experiment_parameters):
        experiment_parameters.update(self.generate_imaging_parameters())
        experiment_parameters['save2file']=True
        self.imaging_parameters=experiment_parameters
        self._start2p()
        
    def live_2p(self):
        self.imaging_parameters=self.generate_imaging_parameters()
        self.imaging_parameters['save2file']=False
        self._start2p()
        
    def stop_2p(self):
        self._finish2p()
        
    def _shutter(self,state):
        daq_instrument.set_digital_line(self.machine_config.TWO_PHOTON['LASER_SHUTTER_PORT'], int(state))
        self.laser_on = state
        
    def _2pnap(self):
        pass
        
    def _start2p(self):
        if self.isrunning:
            self.printc('Restarting imaging')
            self._finish2p()
        parameters = self.imaging_parameters
        self.record_ai_channels = daq_instrument.ai_channels2daq_channel_string(*self._pmtchannels2indexes(parameters['channels']))
        self._prepare_datafile()
        self.daq_process = daq_instrument.AnalogIOProcess(self.instrument_name, self.daq_queues, self.daq_logger_queue,
                                ai_channels = self.record_ai_channels,
                                ao_channels= self.machine_config.TWO_PHOTON['CA_IMAGING_CONTROL_SIGNAL_CHANNELS'],limits=self.limits)
        self.daq_process.start()
        self._shutter(True)
        self.frame_ct=0
        imaging_started_result = self.daq_process.start_daq(ai_sample_rate = parameters['analog_input_sampling_rate'], 
                                                            ao_sample_rate = parameters['analog_output_sampling_rate'], 
                                                            ao_waveform = self._pack_waveform(parameters), 
                                                            timeout = 30)
        self.t0=time.time()
        if parameters.has_key('experiment_name'):
            self.send({'trigger': 'imaging started',  'arg': imaging_started_result})#notifying main_ui that imaging started and stimulus can be launched
        self.printc('Imaging started {0} at {1:.2f} Hz'.format('' if imaging_started_result else imaging_started_result,parameters['frame_rate']))
        self.isrunning = False if imaging_started_result == 'timeout' else imaging_started_result
        self.to_gui.put({'set_isrunning':self.isrunning})
        
    def _finish2p(self):
        if not self.isrunning:
            self.printc('No scanning is running')
            return
        self.t2=time.time()
        #Closing shutter before terminating scanning
        self._shutter(False)
        try:
            parameters = self.imaging_parameters
            unread_data = self.daq_process.stop_daq()
            if isinstance(unread_data ,str):
                self.printc(unread_data)
            else:
                self.printc('acquired frames {0} read frames {1}, expected number of frames {2}'.format(
                                unread_data[1],
                                self.frame_ct, 
                                (self.t2-self.t0) * parameters['frame_rate']))
                #Check if all frames have been acquired
                if unread_data[0].shape[0] + self.frame_ct != unread_data[1] or\
                    unread_data[1] < (self.t2-self.t0) * parameters['frame_rate']:
                    self.printc('WARNING: Some frames are lost')
                self._close_datafile(unread_data)
        except:
            self.printc(traceback.format_exc())
        finally:
            self.isrunning = False
            self.to_gui.put({'set_isrunning':self.isrunning})
            self.daq_process.terminate()
            #Wait till process terminates
            while self.daq_process.is_alive():
                time.sleep(0.2)
                print('daq alive')
            #Set scanner voltages to 0V
            daq_instrument.set_voltage(self.machine_config.TWO_PHOTON['CA_IMAGING_CONTROL_SIGNAL_CHANNELS'], 0.0)
            self.printc('Imaging stopped')
            
    def read_2p(self):
        '''
        Read imaging data when live imaging is ongoing
        '''
        if hasattr(self, 'daq_process') and self.isrunning is not False and hasattr(self, 'imaging_parameters'):
            while True:
                frame = self.daq_process.read_ai()
                if frame is None:
                    break
                else:
                    #Transform frame to image
                    self.frame=frame
                    self.images['display'], self.images['save'] = scanner_control.signal2image(frame, self.imaging_parameters, self.machine_config.PMTS)
                    self.images['display']/=self.machine_config.MAX_PMT_VOLTAGE
                    self.frame_ct+=1
                    if self.ENABLE_16_BIT:
                        self.images['save'] = self._pmt_voltage2_16bit(self.images['save'])
                    self._save_data(self.images['save'])
                    self.to_gui.put({'send_image_data' :[self.images['display'], self.image_scale]})
                    
    def _pmtchannels2indexes(self, recording_channels):
        daq_device = self.machine_config.TWO_PHOTON['PMT_ANALOG_INPUT_CHANNELS'].split('/')[0]
        channel_indexes = [self.machine_config.PMTS[ch]['CHANNEL'] for ch in recording_channels]
        channel_indexes.sort()
        return channel_indexes, daq_device
        
    def _pack_waveform(self,parameters,xy_scanner_only=False):
        waveforms = numpy.array([parameters['x'], 
                                parameters['y'],
                                parameters['stim_sync']*self.machine_config.STIMULATION_TRIGGER_AMPLITUDE,
                                parameters['frame_sync']*self.machine_config.FRAME_TIMING_AMPLITUDE])
        if xy_scanner_only:
            waveforms *= numpy.array([[1,1,0,0]]).T
        return waveforms
            
    def _prepare_datafile(self):
        if self.imaging_parameters['save2file']:
            raise RuntimeError('Fix filename generation')
            self.datafile = hdf5io.Hdf5io(experiment_data.get_recording_path(self.imaging_parameters, self.machine_config, prefix = 'ca'),filelocking=False)
            self.datafile.imaging_parameters = copy.deepcopy(self.imaging_parameters)
            self.image_size = (len(self.imaging_parameters['channels']), self.imaging_parameters['size']['row'] * self.imaging_parameters['resolution'],self.imaging_parameters['size']['col'] * self.imaging_parameters['resolution'])
            datacompressor = tables.Filters(complevel=self.machine_config.DATAFILE_COMPRESSION_LEVEL, complib='blosc', shuffle = 1)
            if self.ENABLE_16_BIT:
                datatype = tables.UInt16Atom(self.image_size)
            else:
                datatype = tables.Float32Atom(self.image_size)
            self.raw_data = self.datafile.h5f.create_earray(self.datafile.h5f.root, 'raw_data', datatype, 
                    (0,),filters=datacompressor)
        
    def _close_datafile(self, data=None):
        if self.imaging_parameters['save2file']:
            self.printc('Saved frames at the end of imaging: {0}'.format(data[0].shape[0]))
            if data is not None:
                for frame in data[0]:
                    frame_converted = scanner_control.signal2image(frame, self.imaging_parameters, self.machine_config.PMTS)[1]
                    if self.ENABLE_16_BIT:
                        frame_converted = self._pmt_voltage2_16bit(frame_converted)
                    self._save_data(frame_converted)
                    self.frame_ct += 1
            self.datafile.imaging_run_info = {'acquired_frames': self.frame_ct, 'start': self.t0, 'end':self.t2, 'duration':self.t2-self.t0 }
            setattr(self.datafile, 'software_environment_{0}'.format(self.machine_config.user_interface_name), experiment_data.pack_software_environment())
            setattr(self.datafile, 'configs_{0}'.format(self.machine_config.user_interface_name), experiment_data.pack_configs(self))
            nodes2save = ['imaging_parameters', 'imaging_run_info', 'software_environment_{0}'.format(self.machine_config.user_interface_name), 'configs_{0}'.format(self.machine_config.user_interface_name)]
            self.datafile.save(nodes2save)
            self.printc('Data saved to {0}'.format(self.datafile.filename))
            self.datafile.close()
        
    def _save_data(self,frame):
        if self.imaging_parameters['save2file']:
            self.raw_data.append(numpy.array([frame]))
            
    def _pmt_voltage2_16bit(self,image):
        '''
        Limit PMT voltage between -MAX_PMT_NOISE_LEVEL...self.machine_config.MAX_PMT_VOLTAGE+MAX_PMT_NOISE_LEVEL range. 
        The MAX_PMT_NOISE_LEVEL extension to both extremes ensures that noise is not distorted with limiting PMT voltage values,
        but ensures that no invalid value is generated by scale and converting image data to 0...2**16-1 range
        '''
        #Subzero PMT voltages are coming from noise. Voltages below MAX_PMT_NOISE_LEVEL are ignored. 
        image_cut = numpy.where(image<-self.machine_config.MAX_PMT_NOISE_LEVEL,-self.machine_config.MAX_PMT_NOISE_LEVEL,image)
        #Voltages above MAX_PMT_VOLTAGE+max_noise_level are considered to be saturated
        image_cut = numpy.where(image>self.machine_config.MAX_PMT_VOLTAGE+self.machine_config.MAX_PMT_NOISE_LEVEL,self.machine_config.MAX_PMT_VOLTAGE+self.machine_config.MAX_PMT_NOISE_LEVEL,image_cut)
        return numpy.cast['uint16'](((image_cut+self.machine_config.MAX_PMT_NOISE_LEVEL)/(2*self.machine_config.MAX_PMT_NOISE_LEVEL+self.machine_config.MAX_PMT_VOLTAGE))*(2**16-1))

class TestMainUIEngineIF(unittest.TestCase):
    def setUp(self):
        self.wait = 100e-3
        from visexpman.users.test.test_configurations import GUITestConfig
        self.machine_config = GUITestConfig()
        self.machine_config.user_interface_name = 'main_ui'
        self.machine_config.user = 'test'
        self.cf=fileop.get_context_filename(self.machine_config)
        fileop.remove_if_exists(self.cf)
        if '_03_' in self._testMethodName:
            guidata = GUIData()
            guidata.add('Sigma 1', 0.5, 'path/sigma')
            hdf5io.save_item(self.cf, 'guidata', utils.object2array(guidata.to_dict()), filelocking=False)
        import visexpman.engine
        self.appcontext = visexpman.engine.application_init(user = 'test', config = 'GUITestConfig', user_interface_name = 'main_ui', log_sources = ['engine'])
        self.appcontext['logger'].start()
        self.engine = MainUIEngine(self.machine_config, self.appcontext['logger'], self.appcontext['socket_queues'], unittest=True)
        
        self.engine.save_context()
        self.from_gui, self.to_gui = self.engine.get_queues()
        self.engine.start()
        utils.empty_queue(self.to_gui)
        
    def test_01_add_and_read_data(self):
        v = 100
        self.from_gui.put({'data': v, 'name': 'dummy', 'path': 'test.dummy'})
        time.sleep(self.wait)
        self.assertEqual(self.engine.guidata.dummy.v, v)
        self.assertEqual(self.engine.guidata.dummy.n, 'dummy')
        self.from_gui.put({'read':None, 'name':'dummy'})
        time.sleep(self.wait)
        self.assertFalse(self.to_gui.empty())
        self.assertEqual(self.to_gui.get(), v)
        #access by path
        self.from_gui.put({'read':None, 'path':'dummy'})
        time.sleep(self.wait)
        self.assertFalse(self.to_gui.empty())
        self.assertEqual(self.to_gui.get(), v)
        #access by invalid path
        self.from_gui.put({'read':None, 'path':'dummy.'})
        time.sleep(self.wait)
        self.assertFalse(self.to_gui.empty())
        self.assertEqual(self.to_gui.get(), None)
        
    def test_02_function(self):
        function_call={'function': 'test', 'args': []}
        self.from_gui.put(function_call)
        time.sleep(self.wait)
        self.assertFalse(self.to_gui.empty())
        self.assertEqual(self.to_gui.get(), function_call)
        
    def test_03_context(self):
        self.from_gui.put({'read':None, 'name':'Sigma 1'})
        time.sleep(self.wait)
        self.assertFalse(self.to_gui.empty())
        self.assertEqual(self.to_gui.get(), 0.5)
        
    def test_04_online_analysis_procedure(self):
        from visexpman.users.test import unittest_aggregator
        import tempfile
        self._init_guidata()
        ref_folder = os.path.join(fileop.select_folder_exists(unittest_aggregator.TEST_test_data_folder), 'cone_gui')
        self.working_folder = os.path.join(tempfile.gettempdir(), 'guienginetest')
        if os.path.exists(self.working_folder):
            shutil.rmtree(self.working_folder)
        self.engine.machine_config.EXPERIMENT_DATA_PATH = self.working_folder
        shutil.copytree(ref_folder, self.working_folder)
        files = fileop.listdir_fullpath(self.working_folder)
        protocol_files = [f for f in files if os.path.splitext(f)[1] == '.txt']
        protocols = dict(map(self._parse_protocol_files, protocol_files))
        for n in protocols.keys():
            protocol = protocols[n]
            [self.from_gui.put(p) for p in protocol]
            resp = []
            tlast = time.time()
            while True:
                if not self.to_gui.empty():
                    resp.append(self.to_gui.get())
                    tlast = time.time()
                if time.time()-tlast>60:#assuming that the execution of any function does not take longer than 30 sec
                    break
            printc_messages = [r['printc'] for r in resp if r.has_key('printc')]
            print(n)
            for p in printc_messages:
                print(p)
            self.assertEqual([p for p in printc_messages if 'error' in p], [])#No error in printc messages
            files = [p.split(' ')[-1] for p in printc_messages if 'ROIs are saved to ' in p]
            #Check if mat files are available
            self.assertTrue(all([os.path.exists(f.replace('.hdf5', '.mat')) for f in files]))
            replink_occurences=0
            for file in files:
                h=hdf5io.Hdf5io(file,filelocking=False)
                rois = h.findvar('rois')
                if 'data_C20_unknownstim_1423227193_0.hdf5' in file and n == 'manual_rois.txt':#Test for all rois removed
                    self.assertEqual(len(rois), 0)
                else:
                    self.assertGreater(len(rois), 0)
                    #Area key is available when manual rois are used
                    self.assertEqual(len([r for r in rois if 'area' in r.keys()]), len(rois))
                repetition_link = h.findvar('repetition_link')
                if repetition_link is not None:
                    replink_occurences+=len(repetition_link)
                h.close()
            if n == 'manual_rois.txt':
                #self.assertTrue(hasattr(self.engine, 'parameter_distributions'))
                #self.assertEqual(len(list(set(numpy.array([k.split('@') for k in self.engine.parameter_distributions.keys()]).flatten().tolist()))), 4)#Distribution of 4 parameters are created
                #Each distribution contains two column data
                #numpy.testing.assert_equal(numpy.array([d.shape[0] for d in self.engine.parameter_distributions.values()]),2)
                notlinkedfiles=1
            elif n == 'automated_roi_detection.txt':
                self.assertTrue('All rois removed' in printc_messages)
                self.assertEqual(self.engine.rois, [])
                notlinkedfiles=2
            self.assertEqual(replink_occurences,len(files)-notlinkedfiles)
            #Check roi matches, all aggregated_rois have one match. It is important that finding repetitions shall take place at the end of the protocol
            try:
                self.assertEqual(abs(numpy.array([len(r['matches']) for r in self.engine.aggregated_rois])-1).sum(),0)
            except:
                import traceback
                print(traceback.format_exc())
                import pdb
                pdb.set_trace()
        
    def _parse_protocol_files(self,filename):
        protocol = [line.split('\t')[1] for line in fileop.read_text_file(filename).split('\n') if 'INFO/engine' in line]
        protocol_cmds = []
        for i in range(len(protocol)):
            if '/mnt/rzws/experiment_data/test/' in protocol[i]:
                path=protocol[i].split('[\'')[1].split('\']')[0]
                new_path = path.replace('/mnt/rzws/experiment_data/test',self.working_folder).replace('/',os.sep)
                protocol[i] = protocol[i].replace(path, new_path)
            exec('cmd='+protocol[i])
            protocol_cmds.append(cmd)
        return os.path.split(filename)[1], protocol_cmds
        
    def _init_guidata(self):
        self.engine.guidata.from_dict(
            [{'path': 'params/Advanced/Scanner/Analog Input Sampling Rate', 'name': 'Analog Input Sampling Rate', 'value': 400.0}, 
            {'path': 'params/Advanced/Scanner/Analog Output Sampling Rate', 'name': 'Analog Output Sampling Rate', 'value': 400.0}, 
            {'path': 'params/Analysis/Background Threshold', 'name': 'Background Threshold', 'value': 10}, 
            {'path': 'params/Analysis/Baseline Lenght', 'name': 'Baseline Lenght', 'value': 1.0}, 
            {'path': 'params/Stimulus/Bullseye On', 'name': 'Bullseye On', 'value': False}, 
            {'path': 'params/Stimulus/Bullseye Shape', 'name': 'Bullseye Shape', 'value': 'bullseye'}, 
            {'path': 'params/Stimulus/Bullseye Size', 'name': 'Bullseye Size', 'value': 100.0}, 
            {'path': 'params/Imaging/Cell Name', 'name': 'Cell Name', 'value': ''}, 
            {'path': 'params/Electrophysiology/Electrophysiology Channel', 'name': 'Electrophysiology Channel', 'value': 'None'}, 
            {'path': 'params/Electrophysiology/Electrophysiology Sampling Rate', 'name': 'Electrophysiology Sampling Rate', 'value': 10000.0}, 
            {'path': 'params/Advanced/Scanner/Enable Flyback Scan', 'name': 'Enable Flyback Scan', 'value': False}, 
            {'path': 'params/Advanced/Scanner/Enable Phase Characteristics', 'name': 'Enable Phase Characteristics', 'value': False}, 
            {'path': 'params/Stimulus/Filterwheel 1', 'name': 'Filterwheel 1', 'value': 'IR'}, 
            {'path': 'params/Stimulus/Filterwheel 2', 'name': 'Filterwheel 2', 'value': 'ND10'}, 
            {'path': 'params/Stimulus/Grey Level', 'name': 'Grey Level', 'value': 100.0}, 
            {'path': 'params/Imaging/Imaging Channel', 'name': 'Imaging Channel', 'value': 'TOP'}, 
            {'path': 'params/Analysis/Trace Statistics/Include All Files', 'name': 'Include All Files', 'value': False}, 
            {'path': 'main_tab', 'name': 'Main Tab', 'value': 1}, 
            {'path': 'params/Analysis/Cell Detection/Maximum Cell Radius', 'name': 'Maximum Cell Radius', 'value': 3.0}, 
            {'path': 'params/Analysis/Trace Statistics/Mean of Repetitions', 'name': 'Mean Of Repetitions', 'value': False}, 
            {'path': 'params/Analysis/Cell Detection/Minimum Cell Radius', 'name': 'Minimum Cell Radius', 'value': 2.0}, 
            {'path': 'params/Imaging/Pixel Size', 'name': 'Pixel Size', 'value': 1.0}, 
            {'path': 'params/Imaging/Pixel Size Unit', 'name': 'Pixel Size Unit', 'value': 'pixel/um'}, 
            {'path': 'params/Stimulus/Projector On', 'name': 'Projector On', 'value': False}, 
            {'path': 'params/Analysis/Save File Format', 'name': 'Save File Format', 'value': 'mat'}, 
            {'path': 'params/Advanced/Scanner/Scan Center X', 'name': 'Scan Center X', 'value': 0.0}, 
            {'path': 'params/Advanced/Scanner/Scan Center Y', 'name': 'Scan Center Y', 'value': 0.0}, 
            {'path': 'params/Imaging/Scan Height', 'name': 'Scan Height', 'value': 100.0}, 
            {'path': 'params/Imaging/Scan Width', 'name': 'Scan Width', 'value': 100.0}, 
            {'path': 'params/Advanced/Scanner/Scanner Position to Voltage Factor', 'name': 'Scanner Position To Voltage Factor', 'value': 0.013}, 
            {'path': 'stimulusbrowser/Selected experiment class', 'name': 'Selected experiment class', 'value': '/mnt/rzws/codes/visexpman/users/zoltan/experiment_tests.py/NaturalBarsConfig1'}, 
            {'path': 'analysis_helper/show_repetitions/input', 'name': 'Show Repetitions', 'value': True}, 
            {'path': 'params/Analysis/Cell Detection/Sigma', 'name': 'Sigma', 'value': 1.0}, 
            {'path': 'params/Stimulus/Stimulus Center X', 'name': 'Stimulus Center X', 'value': 0.0}, 
            {'path': 'params/Stimulus/Stimulus Center Y', 'name': 'Stimulus Center Y', 'value': 0.0}, 
            {'path': 'params/Advanced/Scanner/Stimulus Flash Delay', 'name': 'Stimulus Flash Delay', 'value': 0.0}, 
            {'path': 'params/Advanced/Scanner/Stimulus Flash Duty Cycle', 'name': 'Stimulus Flash Duty Cycle', 'value': 100.0}, 
            {'path': 'params/Analysis/Cell Detection/Threshold Factor', 'name': 'Threshold Factor', 'value': 1.0}])
        
    def tearDown(self):
        self.from_gui.put('terminate')
        self.engine.join()
        import visexpman.engine
        visexpman.engine.stop_application(self.appcontext)
        self.assertTrue(os.path.exists(self.cf))
        if hasattr(self, 'working_folder') and os.path.exists(self.working_folder):
            shutil.rmtree(self.working_folder)
        


if __name__=='__main__':
    unittest.main()
