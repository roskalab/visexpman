import os,sys,time,threading,Queue,shutil,multiprocessing,copy,logging,datetime
import numpy,visexpman, traceback,serial,re,subprocess,platform
import cv2
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import hdf5io,unittest
from visexpman.engine.generic import gui,utils,fileop,introspect
from visexpman.engine.analysis import behavioral_data
from visexpman.engine.hardware_interface import daq_instrument,camera_interface, lick_detector
from visexpman.engine.vision_experiment import experiment,experiment_data
DEBUG=False
NREWARD_VOLUME=100
SPEED_BUFFER_SIZE=10000
EVENT_BUFFER_SIZE=1000
FRAME_TIME_BUFFER_SIZE=10000
EMULATE_SPEED= False

#from memory_profiler import profile

def object_parameters2dict(obj):
    return dict([(vn,getattr(obj, vn)) for vn in dir(obj) if vn.isupper()] )

def get_protocol_names():
    pns = [m[1].__name__ for m in utils.fetch_classes('visexpman.users.common', required_ancestors = experiment.BehavioralProtocol,direct = False)]
    if 0:
        objects=[getattr(sys.modules[__name__], c) for c in dir(sys.modules[__name__])]
        pns=[o.__name__ for o in objects if 'Protocol' in introspect.class_ancestors(o)]
    return pns

class CameraHandler(object):
    '''
    Reads image from camera, transmits via queue and saves frames to file
    '''
    def __init__(self,machine_config):
        self.machine_config=machine_config
        self.save_video=False
        self.camera=None
        self.tperiod=int(1.0/self.machine_config.CAMERA_FRAME_RATE)
        self.frame_counter=0
        self.last_runtime=time.time()
        if self.machine_config.ENABLE_CAMERA:
            try:
                self.camera = cv2.VideoCapture(self.machine_config.CAMERA_ID)#Initialize video capturing
                self.camera.set(3, self.machine_config.CAMERA_FRAME_WIDTH)#Set camera resolution
                self.camera.set(4, self.machine_config.CAMERA_FRAME_HEIGHT)
                logging.info('Camera initialized')
            except:
                logging.warning('no camera present')
            
    def start_video_recording(self,videofilename):
        self.video_saver= cv2.VideoWriter(videofilename,cv2.cv.CV_FOURCC(*'XVID'), 12,#self.machine_config.CAMERA_FRAME_RATE, 
                                                    (self.machine_config.CAMERA_FRAME_WIDTH,self.machine_config.CAMERA_FRAME_HEIGHT))
        self.save_video=True
        self.frame_counter=0
        self.frame_times=[]
        self.videofilename=videofilename
        logging.info('Recording video to {0} started'.format(videofilename))
        
    def stop_video_recording(self):
        self.save_video=False
        if hasattr(self, 'video_saver'):
            del self.video_saver
        logging.info('Recording video ended')
                
    def update_video_recorder(self):
        now=time.time()
        if now-self.last_runtime>=self.tperiod and self.machine_config.ENABLE_CAMERA:
            now1=time.time()
            self.fps=1.0/(now1-self.last_runtime)
            self.last_runtime=now1
            frame = self.read_frame()
            self.to_gui.put({'update_main_image' :frame})
        
    def close_video_recorder(self):
        if hasattr(self.camera,'release'):
            self.camera.release()#Stop camera operation
                
    def read_frame(self):
        if self.camera is None:
            return
        ret, frame = self.camera.read()#Reading the raw frame from the camera
        if frame is None or not ret:
            return
        if self.save_video:
                self.video_saver.write(frame)
                self.frame_times.append(time.time())
        frame_color_corrected=numpy.zeros_like(frame)#For some reason we need to rearrange the color channels
        frame_color_corrected[:,:,0]=frame[:,:,2]
        frame_color_corrected[:,:,1]=frame[:,:,1]
        frame_color_corrected[:,:,2]=frame[:,:,0]
        self.frame_counter+=1
        return frame_color_corrected

class BehavioralEngine(threading.Thread,CameraHandler):
    def __init__(self,machine_config,logfile_path=''):
        self.machine_config=machine_config
        self.logfile_path=logfile_path
        threading.Thread.__init__(self)
        CameraHandler.__init__(self,machine_config)
        self.from_gui = Queue.Queue()
        self.to_gui = Queue.Queue()
        self.context_filename = fileop.get_context_filename(self.machine_config,'npy')
        self.context_variables=['datafolder','parameters','current_animal']
        self.load_context()
        free_space=round(fileop.free_space(self.datafolder)/1e9,1)
        if free_space<self.machine_config.MINIMUM_FREE_SPACE:
            self.notify('Warning', 'Only {0} GB free space is left'.format(free_space))
        logging.info('Pack source code')
        self.software_env = experiment_data.pack_software_environment()
        self.start_time=time.time()
        self.stim_number=0
        self.session_ongoing=False
        
    def load_context(self):
        if os.path.exists(self.context_filename):
            try:
                context_stream = numpy.load(self.context_filename)
            except:
                raise IOError('{0} context file may be corrupt. Delete it and start software again'.format(self.context_filename))
            context=utils.array2object(context_stream)
            for k,v in context.items():
                setattr(self,k,v)
        if not hasattr(self,'datafolder'):
            self.datafolder=self.machine_config.EXPERIMENT_DATA_PATH
            
    def save_context(self):
        context={}
        for vn in self.context_variables:
            if hasattr(self,vn):
                context[vn]=getattr(self,vn)
        context_stream=utils.object2array(context)
        numpy.save(self.context_filename,context_stream)
        
    def ask4confirmation(self,message):
        self.to_gui.put({'ask4confirmation':message})
        while True:
            if not self.from_gui.empty():
                break
            time.sleep(0.15)
        result=self.from_gui.get()
        logging.info('Ask for confirmation: {0}, {1}'.format(message, result))
        return result
        
    def notify(self,title,message):
        logging.info('{0}, {1}'.format(title, message))
        self.to_gui.put({'notify':{'title': title, 'msg':message}})
        
    def set_animal_id(self,current_animal):
        self.current_animal=current_animal
        self.load_animal_file(switch2plot=True)
        
    def new_animal(self,name):
        if self.session_ongoing:
            return
        foldername=os.path.join(self.datafolder,name)
        if os.path.exists(foldername):
            self.notify('Warning', '{0} folder already exists'.format(foldername))
            return
        os.mkdir(foldername)
        logging.info('{0} animal created'.format(name))
        self.set_animal_id(name)
        self.to_gui.put({'statusbar':''})
        
    def add_animal_weight(self,date,weight):
        if self.session_ongoing:
            return
        self.load_animal_file(date=date,weight=weight, switch2plot=True)
        logging.info('Animal weight added ({0}g/{1})'.format(weight,date))
        
    def remove_last_animal_weight(self):
        if self.session_ongoing:
            return
        self.load_animal_file(remove_last=True, switch2plot=True)
        
    def load_animal_file(self, date=None,weight=None,remove_last=False, switch2plot=False):
        if not hasattr(self,'current_animal'):
            return
        self.current_animal_file=os.path.join(self.datafolder,self.current_animal,'animal_'+self.current_animal+'.hdf5')
        if not os.path.exists(os.path.dirname(self.current_animal_file)):
            return
        h=hdf5io.Hdf5io(self.current_animal_file)
        h.load('weight')
        save=False
        if not hasattr(h,'weight') or h.weight.shape[0]==0:
            h.weight=numpy.empty((0,2))
            save=True
        if remove_last:
            save=True
            if h.weight.shape[0]>0:
                h.weight=h.weight[:-1]
                if h.weight.shape[0]==0:
                    h.weight=numpy.empty((0,2))
        if date !=None and weight!=None:
            if h.weight.shape[0]>0 and date in h.weight[:,0]:
                logging.warning('This day is already added')
            else:
                h.weight=numpy.concatenate((h.weight,numpy.array([[date,weight]])))
                save=True
        if save:
            if h.weight.shape[0]>1:
                h.weight=h.weight[h.weight.argsort(axis=0)[:,0]]#Sort by timestamp
            h.save('weight')
        self.weight=h.weight
        h.close()
        if self.weight.shape[0]==0:
            self.weight=numpy.zeros((1,2))
        self.to_gui.put({'update_weight_history':self.weight.copy()})
        if switch2plot:
            self.to_gui.put({'switch2_animal_weight_plot':[]})
            
    def edit_protocol(self):
        fn=utils.fetch_classes('visexpman.users.common', classname=self.parameters['Protocol'],required_ancestors = experiment.BehavioralProtocol,direct = False)[0][0].__file__
        if fn[-3:]=='pyc':
            fn=fn[:-1]
        lines=fileop.read_text_file(fn).split('\n')
        line=[i for i in range(len(lines)) if 'class '+self.parameters['Protocol'] in lines[i]][0]+1
        logging.info('Opening {0} at line {1}'.format(fn,line))
        process = subprocess.Popen(['gedit', fn, '+{0}'.format(line)], shell= platform.system()!= 'Linux')
            
    def reward(self):
        logging.info('NOT IMPLEMENTED')
        logging.info('Reward')
        
    def rewardx100(self):
        for i in range(NREWARD_VOLUME):
            self.reward()
            time.sleep(0.2)
        logging.info('Done')
        
    def airpuff(self):
        if not self.parameters['Enable Air Puff']: return
        waveform=numpy.ones((1,1000*self.parameters['Air Puff Duration']+2))*5
        waveform[0,0]=0
        waveform[0,-1]=0
        daq_instrument.set_waveform('Dev1/ao1',waveform,sample_rate = 1000)
        logging.info('Airpuff')
        
    def set_valve(self,channel,state):
        if channel=='air':
            waveform=numpy.ones((1,1000*0.1))*5*state
            #daq_instrument.set_waveform('Dev1/ao1',waveform,sample_rate = 1000)
        elif channel=='water':
            #daq_instrument.set_digital_line('Dev1/port0/line0', state)
            self.serialport=serial.Serial(self.machine_config.ARDUINO_SERIAL_PORT, 115200, timeout=1)
            self.serialport.write('reward,{0}\r\n'.format(state))
            logging.info(self.serialport.readline())
            self.serialport.close()
            
    def stimulate(self,waveform=None):
        now=time.time()
        self.serialport=serial.Serial(self.machine_config.ARDUINO_SERIAL_PORT, 115200, timeout=1)
        self.serialport.write('stim,{0},{1}\r\n'.format(self.parameters['Laser Intensity'], self.parameters['Pulse Duration']))
        logging.info(self.serialport.readline())
        self.serialport.close()
        return
        fsample=self.machine_config.STIM_SAMPLE_RATE
        if waveform is None:
            self.stimulus_waveform=numpy.ones(int(self.parameters['Pulse Duration']*fsample))
            self.stimulus_waveform[0]=0
            self.stimulus_waveform[-1]=0
            logging.info('Stimulate with {0} for {1} s'.format(self.parameters['Laser Intensity'], self.parameters['Pulse Duration']))
        else:
            self.stimulus_waveform=waveform
            logging.info('Stimulating for {0} s'.format(waveform.shape[0]/fsample))
        self.stimulus_waveform*=self.parameters['Laser Intensity']
        stimulus_duration=self.stimulus_waveform.shape[0]/float(fsample)
        self.stimulus_waveform = self.stimulus_waveform.reshape((1,self.stimulus_waveform.shape[0]))
        daq_instrument.set_waveform('Dev1/ao0',self.stimulus_waveform,sample_rate = fsample)
        
    def convert_folder(self,folder):
        files=fileop.find_files_and_folders(folder)[1]
        hdf5files=[f for f in files if os.path.splitext(f)[1]=='.hdf5']
        logging.info('Converting hdf5 files to mat')
        for f in hdf5files:
            experiment_data.hdf52mat(f)
            logging.info(f)
    
    def update_plot(self):
        t=numpy.arange(self.sync.shape[0])/float(self.machine_config.AI_SAMPLE_RATE)
        x=(self.sync.shape[1])*[t]
        y=[self.sync[:,i] for i in range(self.sync.shape[1])]
        trace_names=['licks', 'lick raw',  'stimulus', 'reward',  'protocol/debug']
        if hasattr(self,'protocol_state_change_times') and self.protocol_state_change_times.shape[0]>0:
            x[4]=self.protocol_state_change_times
            y[4]=numpy.ones_like(self.protocol_state_change_times)
        else:
            y=y[:-1]
            x=x[:-1]
            trace_names=trace_names[:-1]
        if hasattr(self,'lick_times') and self.lick_times.shape[0]>0:
            x[0]=self.lick_times
            y[0]=numpy.ones_like(self.lick_times)*2
        else:
            del x[0]
            del y[0]
            del trace_names[0]
        
        self.to_gui.put({'set_events_title': os.path.basename(self.filename)})
        self.to_gui.put({'update_events_plot':{'x':x, 'y':y, 'trace_names': trace_names}})
        
    def _load_protocol(self):
        logging.info('Loading protocol')
        self.current_protocol = str(self.parameters['Protocol'])
        modulename=utils.fetch_classes('visexpman.users.common', classname=self.current_protocol,required_ancestors = experiment.BehavioralProtocol,direct = False)[0][0].__name__
        __import__(modulename)
        reload(sys.modules[modulename])
        self.software_env['protocol_source']=fileop.read_text_file(sys.modules[modulename].__file__.replace('.pyc','.py'))
        self.protocol= getattr(sys.modules[modulename], self.current_protocol)(self)
        
    def _start_protocol(self):
        self._load_protocol()
        param_str=str(object_parameters2dict(self.protocol)).replace(',',',\r\n')
        self.to_gui.put({'update_protocol_description':'Current protocol: '+ self.current_protocol+'\r\n'+self.protocol.__doc__+'\r\n'+param_str})
        self.protocol.start()
        logging.info('Protocol started')
            
    def start_session(self):
        if self.session_ongoing:
            return
        if not hasattr(self, 'current_animal'):
            self.notify('Warning', 'Create or select animal')
            return
        self.filecounter=0
        rootfolder=os.path.join(self.datafolder, self.current_animal)
        animal_file=os.path.join(rootfolder, 'animal_' + self.current_animal+'.hdf5')
        if not os.path.exists(rootfolder):
            self.notify('Warning', 'Animal folder does not exists')
            return
        if not os.path.exists(animal_file):
            self.notify('Warning', 'Animal file does not exists')
            return
        today=utils.timestamp2ymd(time.time(),'')
        if hasattr(self, 'weight'):
            last_entry_timestamp=utils.timestamp2ymd(self.weight[-1,0],'')
            if last_entry_timestamp<today and not self.ask4confirmation('No animal weight was added today. Do you want to continue?'):
                return
        self.recording_folder=os.path.join(rootfolder, today)
        if not os.path.exists(self.recording_folder):
            os.mkdir(self.recording_folder)
        #self.show_day_success_rate(self.recording_folder)
        self.day_analysis=behavioral_data.HitmissAnalysis(self.recording_folder)
        self.session_ongoing=True
        self.serialport=serial.Serial(self.machine_config.ARDUINO_SERIAL_PORT, 115200, timeout=1)
        self.start_recording()
        self.to_gui.put({'set_recording_state': 'recording'})
        self.to_gui.put({'switch2_event_plot': ''})
        logging.info('Session started with {0} protocol'.format(self.current_protocol))

    def start_recording(self):
        #logging.info(introspect.python_memory_usage())
        self.ai=daq_instrument.AnalogRecorder(self.machine_config.AI_CHANNELS, self.machine_config.AI_SAMPLE_RATE)
        self.ai.start()
        t0=time.time()
        while self.ai.responseq.empty():
            time.sleep(0.1)
            if time.time()-t0>10:
                break
        time.sleep(1)#This value is experimental!!!
        self._start_protocol()
        self.id=experiment_data.get_id()
        self.filename=os.path.join(self.recording_folder, 'data_{0}_{1}'.format(self.current_protocol.replace(' ', '_'), self.id))
        videofilename=self.filename+'.avi'
        self.filename+='.hdf5'
        if self.protocol.ENABLE_IMAGING_SOURCE_CAMERA:
            self.iscamera=camera_interface.ImagingSourceCameraSaver(self.filename)
        self.start_video_recording(videofilename)
        if self.protocol.ENABLE_IMAGING_SOURCE_CAMERA:
            self.iscamera.start()
        self.actual_recording_started=time.time()
    
    def finish_recording(self):
        self.protocol.join()
        logging.info('Protocol finished')
        self.ai.commandq.put('stop')
        time.sleep(0.5)
        t0=time.time()
        while True:
            self.sync=self.ai.read()
            logging.info('ai data shape: '+str(self.sync.shape[0]))
            if self.sync.shape[0]>0: 
                #self.ai.read()
                break
            if time.time()-t0>10:
                logging.error('Not enough AI samples?')
                logging.info(self.ai.dataq.qsize())
                break
            time.sleep(0.1)
        logging.info('Recorded {0} s'.format(self.sync.shape[0]/float(self.machine_config.AI_SAMPLE_RATE)))
        self.stop_video_recording()
        if hasattr(self, 'iscamera'):
            self.iscamera.stop()
            self.iscamera.close()
            del self.iscamera
        try:
            self.stat, self.lick_times, self.protocol_state_change_times =lick_detector.detect_events(self.sync, self.machine_config.AI_SAMPLE_RATE)
            self.update_plot()
            self.save2file()
            behavioral_data.check_hitmiss_files(self.filename)
            self.day_analysis.add2day_analysis(self.filename)
            self.stat2gui()
        except:
            logging.info(traceback.format_exc())
#        self.show_day_success_rate(self.recording_folder)

    def stat2gui(self):
        timingstr='Protocol timing: {0}'.format([(k, v) for k, v in self.stat.items() if k!='result' and k!='lick_numbers' and k!='lick_times'])
        stat_str='Result: {1}, lick numbers: {0}'.format(self.stat['lick_numbers'],  'Hit' if self.stat['result'] else 'Miss')
        today_stat='Flashes: {0}, Hits: {1}, Success rate: {2} %'.format(self.day_analysis.nflashes, self.day_analysis.nhits, int(100*self.day_analysis.success_rate))
        logging.info(stat_str)
        logging.info(timingstr)
        logging.info(today_stat)
        self.to_gui.put({'statusbar':stat_str+' '+today_stat})

    def save_during_session(self):
        if self.session_ongoing and not self.protocol.is_alive():
            self.finish_recording()
            self.start_recording()
        
    def stop_session(self):
        if not self.session_ongoing:
            return
        logging.info('Wait until protocol finishes')
        self.finish_recording()
        self.serialport.close()
        self.session_ongoing=False
        self.to_gui.put({'set_recording_state': 'idle'})
        logging.info('Session ended')
    
    def save2file(self):
        #print introspect.python_memory_usage()
        #logging.info(introspect.python_memory_usage())
        self.datafile=hdf5io.Hdf5io(self.filename)
        for nn in ['machine_config', 'protocol']:
            var=getattr(self, nn)
            setattr(self.datafile, nn, object_parameters2dict(var))
            setattr(self.datafile, nn, dict([(vn,getattr(var, vn)) for vn in dir(var) if vn.isupper()] ))
        self.datafile.sync=self.sync
        self.datafile.stat=copy.deepcopy(self.stat)
        self.datafile.frame_times=self.frame_times
        self.datafile.protocol_name=self.protocol.__class__.__name__#This for sure the correct value
        self.datafile.machine_config_name=self.machine_config.__class__.__name__#This for sure the correct value
        self.datafile.parameters=copy.deepcopy(self.parameters)
        self.datafile.software=self.software_env
        self.datafile.animal=self.current_animal
        nodes=['stat','frame_times', 'sync', 'animal', 'machine_config', 'protocol', 'protocol_name', 'machine_config_name', 'parameters', 'software']
        self.datafile.save(nodes)
        self.datafile.close()
        del self.datafile
        logging.info('Data saved to {0}'.format(self.filename))
        self.filecounter+=1
        #self.show_day_success_rate(self.filename)
        
    def open_file(self, filename):
        if self.session_ongoing:
            self.notify('Warning', 'Stop recording before opening a file')
            return
        self.filename=filename
        self.datafile_opened=time.time()
        self.datafile=hdf5io.Hdf5io(self.filename)
        self.sync=self.datafile.findvar('sync')
        self.stat, self.lick_times, self.protocol_state_change_times =lick_detector.detect_events(self.sync, self.machine_config.AI_SAMPLE_RATE)
        self.stat2gui()
        self.datafile.close()
        self.to_gui.put({'set_events_title': os.path.basename(filename)})
        logging.info('Opened {0}'.format(filename))
        self.update_plot()
            
    def show_animal_statistics(self):
        logging.info('Generating success rate and lick histograms, please wait')
        current_animal_folder=os.path.join(self.datafolder, self.current_animal)
        self.analysis=behavioral_data.HitmissAnalysis(current_animal_folder,self.parameters['Histogram bin size'])
        logging.info('Done')
        self.to_gui.put({'show_animal_statistics':self.analysis})
        
    def show_global_analysis(self):
        logging.info('Generating success rate for each animal')
        self.global_analysis=behavioral_data.HitmissAnalysis(self.datafolder)
        logging.info('Done')
        self.to_gui.put({'show_global_statistics':self.global_analysis})
    
    def show_animal_success_rate(self):
        return
        #self.animal_analysis=behavioral_data.HitmissAnalysis(os.path.join(self.datafolder, self.current_animal))
        
        
        
    def day_summary(self, folder):
        summary = [self.read_file_summary(f) for f in [os.path.join(folder,fn) for fn in os.listdir(folder) if os.path.splitext(fn)[1]=='.hdf5']]
        protocols=[s['protocol'] for s in summary if s.has_key('protocol')]
        protocol_names=list(set(protocols))
        success_rates = {}
        for pn in protocol_names:
            success_rates[pn]=[si['Success Rate'] for si in summary if si.has_key('protocol') and si['protocol']==pn]
        return success_rates
            
    def show_day_success_rate(self,folder):
        '''
        
        '''  
        logging.info('Aggregating statistics on {0}, please wait'.format(folder))
        self._load_protocol()
        self.summary=behavioral_data.lick_detection_folder(folder,self.machine_config.AI_SAMPLE_RATE,self.protocol.LICK_WAIT_TIME,
                                self.parameters['Voltage Threshold'],
                                self.parameters['Max Lick Duration'],
                                self.parameters['Min Lick Duration'],
                                self.parameters['Mean Voltage Threshold'])
        logging.info('Summary ready')
        #Put summary on success rate plot
        x=timestamp2hhmmfp(numpy.array([s[0] for s in self.summary]))
        nlicks=numpy.array([s[2].shape[0] for s in self.summary])
        successfull_licks=numpy.array([s[3].shape[0] for s in self.summary])
        success_rate=numpy.where(successfull_licks>0,1,0)
        y=[nlicks,successfull_licks,success_rate]
        x=len(y)*[x]
        trace_names=['nlicks', 'successful_licks', 'success_rate']
        self.to_gui.put({'update_success_rate_plot':{'x':x, 'y':y, 'trace_names': trace_names}})
        return
        logging.info('Generating today\'s success rate plot')
        if os.path.isdir(folder):
            if len(os.listdir(folder))>500:
                logging.info('Too many recording, success rate plot is not updated')
                return
            self.summary = [self.read_file_summary(f) for f in [os.path.join(folder,fn) for fn in os.listdir(folder) if os.path.splitext(fn)[1]=='.hdf5']]
        elif hasattr(self, 'summary'):
            self.summary.append(self.read_file_summary(folder))
        else:
            return
        #Sort
        ts=[item['t'] for item in self.summary if item.has_key('t')]
        ts.sort()
        sorted=[]
        for ti in ts:
            sorted.append([item for item in self.summary if item.has_key('t') and ti==item['t']][0])
        self.summary=sorted
        xi=[]
        yi=[]
        for si in self.summary:
            xi.append(si['t'])
            yi.append(si['Success Rate'])
        xp=[]
        xp=numpy.array([self.summary[i]['t'] for i in range(len(self.summary)) if i>0 and self.summary[i]['protocol']!=self.summary[i-1]['protocol']])
        protocol_order=[self.summary[i]['protocol'] for i in range(len(self.summary)) if i>0 and self.summary[i]['protocol']!=self.summary[i-1]['protocol']]
        if len(self.summary)>0:
            protocol_order.insert(0,self.summary[0]['protocol'])
        if len(xi)>0:
            if xp.shape[0]>0:
                if xp.shape[0]%2==1:
                    xp=numpy.append(xp, xi[-1])
                #xp-=xi[0]
            #xi-=xi[0]
            xp=timestamp2hhmmfp(xp)
            x=[timestamp2hhmmfp(numpy.array(xi))]
            y=[numpy.array(yi)*100]
            trace_names=['success_rate']
            self.to_gui.put({'update_success_rate_plot':{'x':x, 'y':y, 'trace_names': trace_names, 'vertical_lines': xp}})
            self.to_gui.put({'set_success_rate_title': os.path.basename(folder)})
            logging.info('Protocol order: {0}'.format(', '.join(protocol_order)))
        self.stim_number=sum([s['stimulus counter'] for s in self.summary if s.has_key('stimulus counter')])
            
    def read_file_summary(self,filename):
        '''
        Read time of recording, duration, protocol, success rate and other stat parameters
        '''
        try:
            h=hdf5io.Hdf5io(filename)
            for vn in ['protocol_name', 'speed_values', 'stat']:
                h.load(vn)
                if not hasattr(h, vn):
                    h.close()
                    return {}
            duration=h.speed_values[-1,0]-h.speed_values[0,0]
            t=h.speed_values[0,0]
            data_item ={'t':t, 'duration':duration, 'protocol': h.protocol_name}
            data_item.update(h.stat)
            h.close()
            return data_item
        except:
            return {}
        
    def run(self):
        logging.info('Engine started')
        while True:
            if self.periodic():break
        self.close()
    
    def periodic(self):
            try:
                self.last_run = time.time()#helps determining whether the engine still runs
                if not self.from_gui.empty():
                    msg = self.from_gui.get()
                    if msg == 'terminate':
                        return True#break
                    if msg.has_key('function'):#Functions are simply forwarded
                        #Format: {'function: function name, 'args': [], 'kwargs': {}}
                        if DEBUG:
                            logging.debug(msg)
                        getattr(self, msg['function'])(*msg['args'])
                self.update_video_recorder()
                self.save_during_session()
                if hasattr(self, 'iscamera') and self.iscamera.isrunning:
                    self.iscamera.save()
                    if len(self.iscamera.frames)>0 and len(self.iscamera.frames)%4==0:
                        self.to_gui.put({'update_closeup_image' :self.iscamera.frames[-1][::3,::3]})
                #Run backup
                t=datetime.datetime.fromtimestamp(self.last_run)
                if (t.hour==self.machine_config.BACKUPTIME and t.minute==0):
                    if os.path.exists(self.logfile_path) and os.path.getmtime(self.last_run-self.logfile_path)>self.machine_configBACKUP_LOG_TIMEOUT*60:
                        logging.info('Backing up logfiles')
                        logfilecomparer=fileop.FileComparer(os.dirname(self.logfile_path),self.machine_config.BACKUP_PATH,['.txt'])
                        logfilecomparer.compare()
                        logfilecomparer.sync()
                        logging.info('Backing up data files')
                        datafilecomparer=fileop.FileComparer(self.datafolder,self.machine_config.BACKUP_PATH,['.hdf5','.avi'])
                        datafilecomparer.compare()
                        datafilecomparer.sync()
                        logging.info('Done')
            except:
                logging.error(traceback.format_exc())
                self.save_context()
            time.sleep(40e-3)
        
    def close(self):
        if hasattr(self, 'stimulus_daq_handle'):
            daq_instrument.set_waveform_finish(self.stimulus_daq_handle, self.stimulus_timeout)
        if self.session_ongoing:
            self.stop_session()
        self.close_video_recorder()
        self.save_context()
        logging.info('Engine terminated')
        
    def recalculate_stat(self,folder):
        '''
        self.engine.recalculate_stat('c:\\Data\\nelidash\\rd1 only\\')
        '''
        for fn in fileop.find_files_and_folders(folder)[1]:
            if fn[-4:] == 'hdf5' and 'ForcedKeepRunningRewardLevel' in fn:
                try:
                    self.open_file(fn)
                    self.datafile=hdf5io.Hdf5io(self.filename)
                    self.datafile.load('reward_values')
                    self.datafile.load('protocol_name')
                    self.datafile.load('stat')
                    logging.info('old: ' +str(self.datafile.stat))
                    pn=str(self.datafile.protocol_name)
                    modulename=utils.fetch_classes('visexpman.users.common', classname=pn,required_ancestors = experiment.Protocol,direct = False)[0][0].__name__
                    __import__(modulename)
                    reload(sys.modules[modulename])
                    protocol= getattr(sys.modules[modulename], pn)(self)
                    protocol.nrewards=self.datafile.reward_values.shape[0]
                    if hasattr(self, 'recording_started_state'):
                        del self.recording_started_state
                    self.datafile.stat=protocol.stat()
                    logging.info('new: '+str(self.datafile.stat))
                    self.datafile.save('stat')
                    self.datafile.close()
                except:
                    logging.error(traceback.format_exc())
        logging.info('Done')
        
        
class Behavioral(gui.SimpleAppWindow):
    '''
    command line parameters expected:
    '''
    def __init__(self):
        #Figure out machine config
        self.machine_config = utils.fetch_classes('visexpman.users.common', classname = sys.argv[1], required_ancestors = visexpman.engine.vision_experiment.configuration.BehavioralConfig,direct = False)[0][1]()
        self.logfile=fileop.get_log_filename(self.machine_config)
        logging.basicConfig(filename= self.logfile,
                    format='%(asctime)s %(levelname)s\t%(message)s',
                    level=logging.INFO)
        self.engine=BehavioralEngine(self.machine_config,logfile_path=self.logfile)
        self.engine.start()
        self.to_engine=self.engine.from_gui
        self.from_engine=self.engine.to_gui
        self.maximized=False
        gui.SimpleAppWindow.__init__(self)
        
    def init_gui(self):
        self.setWindowTitle('Behavioral Experiment Control')
        self.setWindowIcon(gui.get_icon('behav'))
        gui.set_win_icon()
        self.setGeometry(self.machine_config.SCREEN_OFFSET[0],self.machine_config.SCREEN_OFFSET[1],self.machine_config.SCREEN_SIZE[0],self.machine_config.SCREEN_SIZE[1])
        self.debugw.setFixedHeight(self.machine_config.BOTTOM_WIDGET_HEIGHT)
        self.debugw.setMaximumWidth(650)
        self.cw=CWidget(self)#Creating the central widget which contains the image, the plot and the control widgets
        self.setCentralWidget(self.cw)#Setting it as a central widget
        protocol_names=get_protocol_names()
        protocol_names_sorted=[pn for pn in self.machine_config.PROTOCOL_ORDER if pn in protocol_names]
        self.params_config=[
                            {'name': 'Experiment', 'type': 'group', 'expanded' : True, 'children': [
                                {'name': 'Protocol', 'type': 'list', 'values': protocol_names_sorted,'value':''},
                                {'name': 'Laser Intensity', 'type': 'float', 'value': 1.0,'siPrefix': True, 'suffix': 'V'},
                                {'name': 'Pulse Duration', 'type': 'float', 'value': 10e-3,'siPrefix': True, 'suffix': 's'},
                                ]},
#                            {'name': 'Lick Detection', 'type': 'group', 'expanded' : True, 'children': [
#                                {'name': 'Voltage Threshold', 'type': 'float', 'value': 0.25,'siPrefix': True, 'suffix': 'V'},
#                                {'name': 'Min Lick Duration', 'type': 'float', 'value': 10e-3,'siPrefix': True, 'suffix': 's'},
#                                {'name': 'Max Lick Duration', 'type': 'float', 'value': 100e-3,'siPrefix': True, 'suffix': 's'},
#                                {'name': 'Mean Voltage Threshold', 'type': 'float', 'value': 0.07,'siPrefix': True, 'suffix': 'V'},
#                                ]},
                            {'name': 'Advanced', 'type': 'group', 'expanded' : True, 'children': [
                                {'name': 'Water Open Time', 'type': 'float', 'value': 10e-3,'siPrefix': True, 'suffix': 's'},
                                {'name': 'Air Puff Duration', 'type': 'float', 'value': 10e-3,'siPrefix': True, 'suffix': 's'},
                                {'name': '100 Reward Volume', 'type': 'float', 'value': 10e-3,'siPrefix': True, 'suffix': 'l'},
                                {'name': 'Enable Air Puff', 'type': 'bool', 'value': False},
                                {'name': 'Enable Lick Simulation', 'type': 'bool', 'value': False},
                                {'name': 'Best N', 'type': 'float', 'value': 10},
                                {'name': 'Histogram bin size', 'type': 'float', 'value': 50e-3, 'siPrefix': True, 'suffix': 's'},
                                ]},
                    ]
        if hasattr(self.engine, 'parameters'):
            for k,v in self.engine.parameters.items():
                for p in self.params_config:
                    for pi in p['children']:
                        if pi['name']==k:
                            pi['value']=v
                            break
        self.paramw = gui.ParameterTable(self, self.params_config)
        self.paramw.setFixedWidth(550)
        self.paramw.params.sigTreeStateChanged.connect(self.parameter_changed)
        self.parameter_changed()
        self.add_dockwidget(self.paramw, 'Parameters', QtCore.Qt.RightDockWidgetArea, QtCore.Qt.RightDockWidgetArea)
        
        self.plotnames=['events', 'animal_weight']
        self.plots=gui.TabbedPlots(self,self.plotnames)
        self.plots.animal_weight.plot.setLabels(left='weight [g]')
        self.plots.events.plot.setLabels(left='speed [m/s]', bottom='times [s]')
        self.plots.tab.setMinimumWidth(self.machine_config.PLOT_WIDGET_WIDTH)
        self.plots.tab.setFixedHeight(self.machine_config.BOTTOM_WIDGET_HEIGHT)
        for pn in self.plotnames:
            getattr(self.plots, pn).setMinimumWidth(self.plots.tab.width()-50)
        self.add_dockwidget(self.plots, 'Plots', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea)
        
        toolbar_buttons = ['record', 'stop', 'select_data_folder','new_animal', 'add_animal_weight', 'remove_last_animal_weight', 'edit_protocol', 'show_animal_statistics', 'show_global_analysis', 'convert_folder', 'exit']
        self.toolbar = gui.ToolBar(self, toolbar_buttons)
        self.addToolBar(self.toolbar)
        self.statusbar=self.statusBar()
        self.update_statusbar()
        
        self.cq_timer=QtCore.QTimer()
        self.cq_timer.start(20)#ms
        self.connect(self.cq_timer, QtCore.SIGNAL('timeout()'), self.check_queue)
        
    def parameter_changed(self):
        self.engine.parameters=self.paramw.get_parameter_tree(return_dict=True)
        
    def check_queue(self):
        if not self.from_engine.empty():
            if self.from_engine.qsize()>5:
                while not self.from_engine.empty():
                    self.process_msg(self.from_engine.get(), skip_main_image_display=True)
            else:
                self.process_msg(self.from_engine.get())
            
    def process_msg(self,msg,skip_main_image_display=False):
        self.msg=msg
        if msg.has_key('notify'):
            self.notify(msg['notify']['title'], msg['notify']['msg'])
        elif msg.has_key('statusbar'):
            self.update_statusbar(msg=msg['statusbar'])
        elif msg.has_key('update_weight_history'):
            x=msg['update_weight_history'][:,0]
            x/=86400
            x-=x[0]
            self.plots.animal_weight.update_curve(x,msg['update_weight_history'][:,1],plotparams={'symbol' : 'o', 'symbolSize': 8, 'symbolBrush' : (0, 0, 0)})
            self.plots.animal_weight.plot.setLabels(bottom='days, {0} = {1}, {3} = {2}'.format(int(numpy.round(x[0])), utils.timestamp2ymd(self.engine.weight[0,0]), utils.timestamp2ymd(self.engine.weight[-1,0]), int(numpy.round(x[-1]))))
            self.plots.animal_weight.plot.setYRange(min(msg['update_weight_history'][:,1]), max(msg['update_weight_history'][:,1]))
            self.plots.animal_weight.plot.setXRange(min(x), max(x))
        elif msg.has_key('switch2_animal_weight_plot'):
            self.plots.tab.setCurrentIndex(1)
        elif msg.has_key('update_main_image'):
            if not skip_main_image_display:
                self.cw.images.main.set_image(numpy.rot90(msg['update_main_image'],3),alpha=1.0)
        elif msg.has_key('update_closeup_image'):
            self.cw.images.closeup.set_image(numpy.rot90(numpy.dstack(tuple(3*[msg['update_closeup_image']])),3),alpha=1.0)
        elif msg.has_key('update_events_plot'):
            plotparams=[]
            for tn in msg['update_events_plot']['trace_names']:
                if tn =='lick raw':
                    plotparams.append({'name': tn, 'pen':(0, 255,0)})
                elif tn=='reward':
                    plotparams.append({'name': tn, 'pen':(0,0,255)})
                elif tn=='licks':
                    plotparams.append({'name': tn, 'pen':None, 'symbol':'t', 'symbolSize':8, 'symbolBrush': (0, 255,0,150)})
                elif tn=='stimulus':
                    plotparams.append({'name': tn, 'pen':(255,0,0)})
                elif tn=='protocol/debug':
                    plotparams.append({'name': tn, 'pen':None, 'symbol':'t', 'symbolSize':8, 'symbolBrush': (0,0,0,150)})
            self.plots.events.update_curves(msg['update_events_plot']['x'], msg['update_events_plot']['y'], plotparams=plotparams)
            tmax=max([x.max() for x in msg['update_events_plot']['x']])
            self.plots.events.plot.setXRange(0,tmax)
        elif msg.has_key('ask4confirmation'):
            reply = QtGui.QMessageBox.question(self, 'Confirm following action', msg['ask4confirmation'], QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
            self.to_engine.put(reply == QtGui.QMessageBox.Yes)
        elif msg.has_key('set_recording_state'):
            self.cw.set_state(msg['set_recording_state'])
        elif msg.has_key('switch2_event_plot'):
            self.plots.tab.setCurrentIndex(0)
        elif msg.has_key('set_events_title'):
            self.plots.events.plot.setTitle(msg['set_events_title'])
        elif msg.has_key('update_protocol_description'):
            self.cw.state.setToolTip(msg['update_protocol_description'])
        elif msg.has_key('update_success_rate_plot'):
            plotparams=[]
            if msg['update_success_rate_plot'].has_key('scatter') and msg['update_success_rate_plot']['scatter']:
                alpha=100
                colors=[(0,0,0,alpha), (255,0,0,alpha), (0,255,0,alpha),(0,0,255,alpha), (255,255,0,alpha), (0,255,255,alpha), (255,255,0,alpha),(128,255,255,alpha)]
                color_i=0
                for tn in msg['update_success_rate_plot']['trace_names']:
                    plotparams.append({'name': tn, 'pen':None, 'symbol':'o', 'symbolSize':7, 'symbolBrush': colors[color_i]})
                    color_i+=1
            else:
                for tn in msg['update_success_rate_plot']['trace_names']:
                    if tn =='success_rate':
                        plotparams.append({'name': tn, 'pen':(255,0,0), 'symbol':'o', 'symbolSize':3, 'symbolBrush': (200,0,0)})
                    elif tn=='nlicks':
                        plotparams.append({'name': tn, 'pen':(0,0,0)})
                    elif tn=='successful_licks':
                        plotparams.append({'name': tn, 'pen':(0,255,0)})
                        
            self.plots.success_rate.update_curves(msg['update_success_rate_plot']['x'], msg['update_success_rate_plot']['y'], plotparams=plotparams)
            if msg['update_success_rate_plot'].has_key('vertical_lines') and msg['update_success_rate_plot']['vertical_lines'].shape[0]>0:
                self.plots.success_rate.add_linear_region(msg['update_success_rate_plot']['vertical_lines'],color=(0,0,0,20))
            else:
                self.plots.success_rate.add_linear_region([])
        elif msg.has_key('set_success_rate_title'):
            self.plots.success_rate.plot.setTitle(msg['set_success_rate_title'])
        elif msg.has_key('show_animal_statistics'):
            if hasattr(self, 'asp'):
                del self.asp
            self.asp = AnimalStatisticsPlots(self, msg['show_animal_statistics'])
        elif msg.has_key('update_reward_volume_plot'):
            pass
        elif msg.has_key('show_global_statistics'):
            gs=msg['show_global_statistics']
            t0=min([min(v[0]) for v in gs.animal_success_rate.values()])
            axis=gui.TimeAxisItemYYMMDD(orientation='bottom')
            axis.year=int(t0[:4])
            axis.month=int(t0[4:6])
            axis.day=int(t0[6:])
            self.w=QtGui.QWidget()
            self.w.setWindowIcon(gui.get_icon('behav'))
            self.w.setGeometry(self.machine_config.SCREEN_OFFSET[0],self.machine_config.SCREEN_OFFSET[1],self.machine_config.SCREEN_SIZE[0],self.machine_config.SCREEN_SIZE[1])
            self.w.setWindowTitle('Summary of '+gs.folder)
            self.w.p=gui.Plot(self.w,axisItems={'bottom': axis})
            pp={ 'symbol':'o', 'symbolSize':8, 'symbolBrush': (50,255,0,128), 'pen': (50,255,0,128)}
            pps=[]
            logging.info('TODO: generate trace colors')
            for ln in gs.animal_success_rate.keys():
                pps.append(copy.deepcopy(pp))
                pps[-1]['name']=ln
                pps[-1]['pen']=(50,255,0,128)
            x=[tr[0] for tr in gs.animal_success_rate.values()]
            xconverted=[]
            t0ts=utils.datestring2timestamp(t0,format='%Y%m%d')/86400 
            for xi in x:
                xconverted.append([utils.datestring2timestamp(xii,format='%Y%m%d')/86400-t0ts for xii in xi])
            y=[tr[1]*100 for tr in gs.animal_success_rate.values()]
            print xconverted,y
            self.w.p.update_curves(xconverted,y,plotparams=pps)
            self.w.p.plot.setLabels(left='success rate [%]')
            
            self.w.l = QtGui.QGridLayout()
            self.w.l.addWidget(self.w.p, 0,0, 1, 1)
            self.w.setLayout(self.w.l)
            
            self.w.show()
            
        
    def update_statusbar(self,msg=''):
        '''
        General text display
        '''
        ca=self.engine.current_animal if hasattr(self.engine, 'current_animal') else ''
        txt='Data folder: {0}, Current animal: {1} {2}'. format(self.engine.datafolder,ca,msg)
        self.statusbar.showMessage(txt)
        self.setWindowTitle('Behavioral\t {0}'.format(ca))
        
    def closeEvent(self, e):
        e.accept()
        self.exit_action()
        
    def record_action(self):
        self.to_engine.put({'function': 'start_session','args':[]})
    
    def stop_action(self):
        self.to_engine.put({'function': 'stop_session','args':[]})
        
    def select_data_folder_action(self):
        folder = self.ask4foldername('Select Data Folder', self.engine.datafolder)
        if folder=='':return
        self.engine.datafolder=folder
        free_space=round(fileop.free_space(self.engine.datafolder)/1e9,1)
        if free_space<self.machine_config.MINIMUM_FREE_SPACE:
            self.notify('Warning', 'Only {0} GB free space is left'.format(free_space))
        self.cw.filebrowserw.set_root(self.engine.datafolder)
        self.update_statusbar()
        
    def new_animal_action(self):
        text, ok = QtGui.QInputDialog.getText(self, 'Add Animal', 
            'Enter animal name:')
        if ok:
            self.to_engine.put({'function': 'new_animal','args':[str(text)]})
            
    def add_animal_weight_action(self):
        self.aw=AddAnimalWeightDialog(self.to_engine)
        self.aw.show()
      
    def remove_last_animal_weight_action(self):
        if self.ask4confirmation('Do you want to remove last weight entry?'):
            self.to_engine.put({'function': 'remove_last_animal_weight','args':[]})
            
    def show_animal_statistics_action(self):
        self.to_engine.put({'function': 'show_animal_statistics','args':[]})
        
    def show_global_analysis_action(self):
        self.to_engine.put({'function': 'show_global_analysis','args':[]})
        
    def edit_protocol_action(self):
        self.to_engine.put({'function': 'edit_protocol','args':[]})
        
    def convert_folder_action(self):
        folder = self.ask4foldername('Select Data Folder', self.engine.datafolder)
        self.to_engine.put({'function': 'convert_folder','args':[folder]})

        
    def exit_action(self):
        if hasattr(self,'asp'):
            self.asp.close()
        self.to_engine.put('terminate')
        self.engine.join()
        self.close()
        
class CWidget(QtGui.QWidget):
    '''
    The central widget of the user interface which contains the image, the plot and the various controls for starting experiment or adjusting parameters
    '''
    def __init__(self,parent):
        QtGui.QWidget.__init__(self,parent)
        self.setFixedHeight(390)
        self.imagenames=['main', 'closeup']
        self.images=gui.TabbedImages(self,self.imagenames)
        ar=float(parent.machine_config.CAMERA_FRAME_WIDTH)/parent.machine_config.CAMERA_FRAME_HEIGHT
        self.images.main.setFixedWidth(280*ar)
        self.images.main.setFixedHeight(280)
        self.images.closeup.setFixedWidth(280*ar)
        self.images.closeup.setFixedHeight(280)
        self.main_tab = self.images.tab
        self.filebrowserw=FileBrowserW(self)
        self.main_tab.addTab(self.filebrowserw, 'Files')
        self.lowleveldebugw=LowLevelDebugW(self)
        self.main_tab.addTab(self.lowleveldebugw, 'Advanced')
        self.main_tab.setCurrentIndex(0)
        self.main_tab.setTabPosition(self.main_tab.South)
        self.main_tab.setMinimumHeight(290)
        self.main_tab.setMinimumWidth(700)
        self.live_speed=gui.LabeledCheckBox(self,'Live Speed')
        self.live_speed.input.setCheckState(2)
        self.connect(self.live_speed.input, QtCore.SIGNAL('stateChanged(int)'),  self.live_event_udpate_clicked)
        self.state=QtGui.QPushButton('Idle', parent=self)
        self.state.setMinimumWidth(100)
        self.state.setEnabled(False)
        self.set_state('idle')
        self.l = QtGui.QGridLayout()
        self.l.addWidget(self.main_tab, 0, 0, 2, 4)
        self.l.addWidget(self.state, 2, 0, 1, 1)
        self.l.addWidget(self.live_speed, 2, 1, 1, 1)
        self.setLayout(self.l)
        self.l.setColumnStretch(3,20)
        self.l.setRowStretch(3,20)
        
    def set_state(self,state):
        self.state.setText(state)
        if state=='recording':
            self.state.setStyleSheet('QPushButton {background-color: red; color: black;}')
        elif state=='idle':
            self.state.setStyleSheet('QPushButton {background-color: gray; color: black;}')
        
        
    def live_event_udpate_clicked(self,state):
        pass
        
class FileBrowserW(gui.FileTree):
    def __init__(self,parent):
        gui.FileTree.__init__(self,parent, parent.parent().engine.datafolder, ['*.mat','*.hdf5', '*.avi'])
        self.doubleClicked.connect(self.open_file)
        self.clicked.connect(self.file_selected)
        
    def file_selected(self,index):
        self.selected_filename = gui.index2filename(index)
        datafolder=self.parent.parent().engine.datafolder
        if os.path.isdir(self.selected_filename) and os.path.dirname(self.selected_filename).lower()==datafolder.lower():
            #Animal folder selected
            self.parent.parent().engine.current_animal=os.path.basename(self.selected_filename)
            logging.info('Animal selected: {0}'.format(self.parent.parent().engine.current_animal))
            self.parent.parent().update_statusbar()
            self.parent.parent().to_engine.put({'function':'load_animal_file','args':[]})
            self.parent.parent().to_engine.put({'function':'show_animal_success_rate','args':[]})
        elif os.path.isdir(self.selected_filename) and hasattr(self.parent.parent().engine, 'current_animal') and os.path.dirname(self.selected_filename).lower()==os.path.join(self.parent.parent().engine.datafolder, self.parent.parent().engine.current_animal).lower():
            self.parent.parent().to_engine.put({'function':'show_day_success_rate','args':[self.selected_filename]})
            
    def open_file(self,index):
        self.double_clicked_filename = gui.index2filename(index)
        if os.path.splitext(self.double_clicked_filename)[1]=='.hdf5' and os.path.basename(self.double_clicked_filename)[:4]=='data':
            self.parent.parent().to_engine.put({'function':'open_file','args':[self.double_clicked_filename]})
            
class LowLevelDebugW(QtGui.QWidget):
    '''
    
    '''
    def __init__(self,parent):
        QtGui.QWidget.__init__(self,parent)
        self.parent=parent
        valve_names=['water', 'air']
        self.valves={}
        for vn in valve_names:
            self.valves[vn]=gui.LabeledCheckBox(self,'Open {0} Valve'.format(vn.capitalize()))
            self.valves[vn].setToolTip('When checked, the valve is open')
        self.fan=gui.LabeledCheckBox(self,'Fan on/off')
        self.connect(self.valves['water'].input, QtCore.SIGNAL('stateChanged(int)'),  self.water_valve_clicked)
        self.connect(self.valves['air'].input, QtCore.SIGNAL('stateChanged(int)'),  self.air_valve_clicked)
        self.connect(self.fan.input, QtCore.SIGNAL('stateChanged(int)'),  self.fan_clicked)
        self.airpuff=QtGui.QPushButton('Air Puff', parent=self)
        self.connect(self.airpuff, QtCore.SIGNAL('clicked()'), self.airpuff_clicked)
        self.reward=QtGui.QPushButton('Reward', parent=self)
        self.connect(self.reward, QtCore.SIGNAL('clicked()'), self.reward_clicked)
        self.stimulate=QtGui.QPushButton('Stimulate', parent=self)
        self.connect(self.stimulate, QtCore.SIGNAL('clicked()'), self.stimulate_clicked)
        self.forcerun=QtGui.QPushButton('Force Run', parent=self)
        self.connect(self.forcerun, QtCore.SIGNAL('clicked()'), self.forcerun_clicked)
        self.rewardx100=QtGui.QPushButton('100 x Reward', parent=self)
        self.connect(self.rewardx100, QtCore.SIGNAL('clicked()'), self.rewardx100_clicked)
        self.l = QtGui.QGridLayout()
        [self.l.addWidget(self.valves.values()[i], 0, i, 1, 1) for i in range(len(self.valves.values()))]
        self.l.addWidget(self.fan, 0, i+1, 1, 1)
        self.l.addWidget(self.reward, 1, 0, 1, 1)
        self.l.addWidget(self.airpuff, 1, 1, 1, 1)
        self.l.addWidget(self.stimulate, 2, 0, 1, 1)
        self.l.addWidget(self.forcerun, 2, 1, 1, 1)
        self.l.addWidget(self.rewardx100, 3, 0, 1, 1)
        self.setLayout(self.l)
        self.l.setColumnStretch(2,20)
        self.l.setRowStretch(3,20)
        
    def forcerun_clicked(self):
        self.parent.parent().to_engine.put({'function':'forcerun','args':[1]})
    
    def airpuff_clicked(self):
        self.parent.parent().to_engine.put({'function':'airpuff','args':[]})
        
    def reward_clicked(self):
        self.parent.parent().to_engine.put({'function':'reward','args':[]})
        
    def rewardx100_clicked(self):
        self.parent.parent().to_engine.put({'function':'rewardx100','args':[]})
            
    
    def stimulate_clicked(self):
        self.parent.parent().to_engine.put({'function':'stimulate','args':[]})
    
    def air_valve_clicked(self,state):
        self.parent.parent().to_engine.put({'function':'set_valve','args':['air', state==2]})
        
    def water_valve_clicked(self,state):
        self.parent.parent().to_engine.put({'function':'set_valve','args':['water', state==2]})
        
    def fan_clicked(self,state):
        self.parent.parent().to_engine.put({'function':'set_fan','args':[state==2]})
        
class AddAnimalWeightDialog(QtGui.QWidget):
    '''
    Dialog window for date and animal weight
    '''
    def __init__(self,q):
        self.q=q
        QtGui.QWidget.__init__(self)
        self.move(200,200)
        date_format = QtCore.QString('yyyy-MM-dd')
        self.date = QtGui.QDateTimeEdit(self)
        self.date.setDisplayFormat(date_format)
        now = time.localtime()
        self.date.setDateTime(QtCore.QDateTime(QtCore.QDate(now.tm_year, now.tm_mon, now.tm_mday), QtCore.QTime(now.tm_hour, now.tm_min)))
        self.date.setFixedWidth(150)
        self.weight_input=QtGui.QLineEdit(self)
        self.weight_input.setFixedWidth(100)
        self.weight_input.setFocus()
        self.weight_input_l = QtGui.QLabel('Animal weight [g]', self)
        self.weight_input_l.setFixedWidth(120)
        self.ok=QtGui.QPushButton('OK' ,parent=self)
        self.connect(self.ok, QtCore.SIGNAL('clicked()'), self.ok_clicked)
        self.cancel=QtGui.QPushButton('Cancel' ,parent=self)
        self.connect(self.cancel, QtCore.SIGNAL('clicked()'), self.cancel_clicked)
        
        self.l = QtGui.QGridLayout()
        self.l.addWidget(self.date, 0, 0, 1, 1)
        self.l.addWidget(self.weight_input_l, 0, 1, 1, 1)
        self.l.addWidget(self.weight_input, 0, 2, 1, 1)
        self.l.addWidget(self.ok, 1, 0, 1, 1)
        self.l.addWidget(self.cancel, 1, 1, 1, 1)
        self.l.setColumnStretch(3,20)
        self.l.setRowStretch(0,1)
        self.l.setRowStretch(1,1)
        self.setLayout(self.l)
        
    def ok_clicked(self):
        weight=float(str(self.weight_input.text()))
        date=self.date.date()
        datets=time.mktime(time.struct_time((date.year(),date.month(),date.day(),0,0,0,0,0,-1)))
        self.q.put({'function': 'add_animal_weight','args':[datets,weight]})
        self.close()
        
    def cancel_clicked(self):
        self.close()

class AnimalStatisticsPlots(QtGui.QTabWidget):
    def __init__(self, parent, analysis):
        QtGui.QTabWidget.__init__(self)
        self.setWindowIcon(gui.get_icon('behav'))
        gui.set_win_icon()
        self.machine_config=parent.machine_config
        self.setGeometry(self.machine_config.SCREEN_OFFSET[0],self.machine_config.SCREEN_OFFSET[1],parent.machine_config.SCREEN_SIZE[0],parent.machine_config.SCREEN_SIZE[1])
        self.setWindowTitle('Summary of '+os.path.basename(analysis.folder))
        self.setTabPosition(self.North)
        pp=[{'symbol':'o', 'symbolSize':12, 'symbolBrush': (50,255,0,128), 'pen': (50,255,0,128)}]
        days=numpy.array([utils.datestring2timestamp(d,format='%Y%m%d')/86400 for d in analysis.days])
        days-=days[0]
        axis=gui.TimeAxisItemYYMMDD(orientation='bottom')
        axis.year=int(analysis.days[0][:4])
        axis.month=int(analysis.days[0][4:6])
        axis.day=int(analysis.days[0][6:])
        success_rate_plot=gui.Plot(self,axisItems={'bottom': axis})
        success_rate_plot.update_curves([days],[analysis.success_rates*100],plotparams=pp)
        success_rate_plot.plot.setLabels(left='success rate [%]')
        self.addTab(success_rate_plot,'Success rate')
        lick_latency_histogram_plot=self.histograms(analysis.lick_latency_histogram)
        lick_times_histogram_plot=self.histograms(analysis.lick_times_histogram)
        self.addTab(lick_latency_histogram_plot,'Lick latencies')
        self.addTab(lick_times_histogram_plot,'Lick times')
        self.show()
        
    def histograms(self,hist):
        histw=QtGui.QWidget()
        histw.plots=[]
        histw.l = QtGui.QGridLayout()
        bins=hist[0]
        days=hist[1].keys()
        days.sort()
        ct=0
        ymax=max(map(max,hist[1].values()))
        for d in days:
            histw.plots.append(gui.Plot(histw))
            histw.plots[-1].plot.setTitle(d)
            histw.plots[-1].update_curve(bins,hist[1][d], plotparams={'fillLevel':-0.3, 'brush': (50,50,128,100)})
            histw.plots[-1].plot.setLabels(left='occurence', bottom='dt [ms]')
            histw.plots[-1].plot.setYRange(0, ymax)
            histw.l.addWidget(histw.plots[-1], ct/2, ct%2, 1, 1)
            ct+=1
        histw.setLayout(histw.l)
        return histw
        
        
class PlotPage(QtGui.QWidget):
    '''
    Dialog window for date and animal weight
    '''
    def __init__(self,data,parent):
        QtGui.QWidget.__init__(self)
        self.tp=[]
        self.l = QtGui.QGridLayout()
        days=data.keys()
        days.sort()
        ct=0
        for d in days:
            self.tp.append(gui.TabbedPlots(self, data[d].keys()))
            for pn in data[d].keys():
                ref=getattr(self.tp[-1],pn)
                ref.plot.setTitle(d)
                t=data[d][pn][0]
                t=timestamp2hhmmfp(t)
                ref.update_curve(t,data[d][pn][1]*100,plotparams={'symbol':'o', 'symbolSize':6, 'symbolBrush': (0,0,0)})
                ref.plot.setLabels(left='success rate [%]', bottom='time [hour]')
            self.tp[-1].tab.setFixedWidth(parent.machine_config.SCREEN_SIZE[0]/3-50)
            self.tp[-1].tab.setFixedHeight(parent.machine_config.SCREEN_SIZE[1]/2-50)
            self.l.addWidget(self.tp[-1], ct/3, ct%3, 1, 1)
            ct+=1
        self.setLayout(self.l)
        
def timestamp2hhmmfp(t):
    '''
    Converts timestamp to hour.minute format where . is a decimal point
    '''
    t=numpy.array(map(utils.timestamp2secondsofday,t.tolist()))/3600.0
    #minutes=(t-numpy.floor(t))*0.6
    #t-=t-numpy.floor(t)
    #t+=minutes
    return t
        

class TestBehavEngine(unittest.TestCase):
    
    def setUp(self):
        self.machine_config = utils.fetch_classes('visexpman.users.common', classname = 'BehavioralSetup', required_ancestors = visexpman.engine.vision_experiment.configuration.BehavioralConfig,direct = False)[0][1]()
        if not hasattr(self, 'log_initialized'):
            self.logfile=fileop.generate_filename('/tmp/behav_engine_test.txt')
            logging.basicConfig(filename= self.logfile,
                        format='%(asctime)s %(levelname)s\t%(message)s',
                        level=logging.INFO)
            self.log_initialized=True
        self.context_filename = fileop.get_context_filename(self.machine_config,'npy')
        if os.path.exists(self.context_filename):
            os.remove(self.context_filename)
        
    def test_01_add_remove_weight(self):
        self.animal_name='ta001'
        self.engine=BehavioralEngine(self.machine_config)
        af=os.path.join(self.engine.datafolder,self.animal_name)
        if os.path.exists(af):
            shutil.rmtree(af)
        self.engine.add_animal(self.animal_name)
        for i in range(10):
            self.engine.add_animal_weight(time.time()+i*86400,i)
        for i in range(11):
            self.engine.remove_last_animal_weight()
        for i in range(5):
            self.engine.add_animal_weight(time.time()+i*86400,i)
        self.assertEqual(5,self.engine.weight.shape[0])
        self.engine.close()
        
    def test_02_video_recorder(self):
        frame_folder=fileop.generate_foldername('/tmp/frames')
        capture_duration=3
        videofilename1='/tmp/{0}.avi'.format(int(time.time()))
        self.engine=BehavioralEngine(self.machine_config)
        t0=time.time()
        while True:
            self.engine.update_video_recorder()
            if time.time()-t0>capture_duration:
                break
        self.engine.start_video_recording(videofilename1)
        t0=time.time()
        while True:
            self.engine.update_video_recorder()
            if time.time()-t0>capture_duration:
                break
        videofilename2='/tmp/{0}.avi'.format(int(time.time()))
        self.engine.start_video_recording(videofilename2)
        self.assertEqual(os.path.exists(videofilename1), True)
        t0=time.time()
        while True:
            self.engine.update_video_recorder()
            if time.time()-t0>capture_duration:
                break
        self.engine.stop_video_recording()
        self.engine.close()
        self.assertEqual(os.path.exists(videofilename2), True)
        
    def test_03_speed_emulator(self):
        q=multiprocessing.Queue()
        rectime=3
        tsr=TreadmillSpeedReader(q,self.machine_config,emulate_speed=False)
        tsr.start()
        time.sleep(rectime)
        q.put('terminate')
        tsr.join()
        samples=[]
        while not tsr.speed_q.empty():
            samples.append(tsr.speed_q.get())
        self.assertEqual(numpy.array(samples).shape[0], rectime/self.machine_config.TREADMILL_SPEED_UPDATE_RATE-1)
        
    def test_04_speed_read(self):
        q=multiprocessing.Queue()
        rectime=3
        tsr=TreadmillSpeedReader(q,self.machine_config)
        tsr.start()
        time.sleep(rectime)
        q.put('terminate')
        tsr.join()
        samples=[]
        while not tsr.speed_q.empty():
            samples.append(tsr.speed_q.get())
        pass
        
    def test_05_animal_summary(self):
        self.engine=BehavioralEngine(self.machine_config)
        self.engine.session_ongoing=False
        self.engine.current_animal='test1'
        self.engine.datafolder='/tmp/animal'
        self.engine.parameters={'Best Success Rate Over Number Of Stimulus':2}
        self.engine.show_animal_statistics()
        self.engine.show_animal_success_rate()
        #self.engine.show_day_success_rate('/tmp/animal/eger1/20160412')
        self.engine.close()
        

if __name__ == '__main__':
    if len(sys.argv)>1:
        if ('BehavioralSetup' in sys.argv[1]):
            introspect.kill_other_python_processes()
            #Check number of python processes
            if len(introspect.get_python_processes())>1:
                raise RuntimeError('Kill all python prcesses from task manager')
        gui = Behavioral()
    else:
        unittest.main()
