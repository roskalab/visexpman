import os,sys,time,threading,Queue,tempfile,random,shutil,multiprocessing,copy,logging
import numpy,scipy.io,visexpman, copy, traceback
import serial
from PIL import Image
import cv2
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import pyqtgraph,hdf5io,unittest
from visexpman.engine.generic import gui,utils,videofile,fileop,introspect
from visexpman.engine.hardware_interface import daq_instrument, digital_io
from visexpman.engine.vision_experiment import experiment_data, configuration
#TODO: protocol success rate summary
#TODO: valves will be controlled by arduino to ensure valve open time is precise

def object_parameters2dict(obj):
    return dict([(vn,getattr(obj, vn)) for vn in dir(obj) if vn.isupper()] )

class Protocol(object):
    def __init__(self,engine):
        self.engine=engine
        self.reset()
        
    def update(self):
        '''
        In subclass this method calculates if reward/punishment has to be given
        '''
        
    def stat(self):
        '''
        In a subclass this method calculates the actual success rate
        '''
    def reset(self):
        '''
        Resets state variables
        '''
        
        
def get_protocol_names():
    objects=[getattr(sys.modules[__name__], c) for c in dir(sys.modules[__name__])]
    pns=[o.__name__ for o in objects if 'Protocol' in introspect.class_ancestors(o)]
    return pns
    
class KeepRunningReward(Protocol):
    '''A reward is given if the animal was running for RUN_TIME '''
    RUN_TIME=5.0
    def reset(self):
        self.engine.run_time=self.RUN_TIME
        self.nrewards=0
    
    def update(self):
        indexes=[i for i in range(len(self.engine.events)) if not self.engine.events[i]['ack'] and self.engine.events[i]['type']=='run']
        self.last_update=time.time()
        if len(indexes)>0:
            for i in indexes:
                self.engine.events[i]['ack']=True
            self.engine.reward()
            self.nrewards+=1
        
    def stat(self):
        '''
        Success rate is the ratio of time while the animal was running
        '''
        if self.engine.speed_values.shape[0]>0:
            elapsed_time=self.last_update-self.engine.speed_values[0,0]
            success_rate=self.nrewards*self.RUN_TIME/elapsed_time
            success_rate = 1.0 if success_rate>=1 else success_rate
            return {'rewards':self.nrewards, 'Success Rate': success_rate}
        
class ForcedKeepRunningReward(KeepRunningReward):
    '''
    Animal gets a reward if it was running for RUN_TIME.
    If the animal is not moving for STOP_TIME it will be forced to move for RUN_FORCE_TIME seconds.
    '''
    RUN_TIME=5.0
    STOP_TIME=6.5
    RUN_FORCE_TIME = 3.0
    
    def reset(self):
        self.engine.run_time=self.RUN_TIME
        self.engine.stop_time=self.STOP_TIME
        self.nrewards=0
        self.nforcedruns=0
        
    def update(self):
        KeepRunningReward.update(self)
        indexes=[i for i in range(len(self.engine.events)) if not self.engine.events[i]['ack'] and self.engine.events[i]['type']=='stop']
        for i in indexes:
            self.engine.events[i]['ack']=True
        if len(indexes)>0:
            self.engine.airpuff()
            self.engine.forcerun(self.RUN_FORCE_TIME)
            self.nforcedruns+=1

    def stat(self):
        '''
        Number of rewards in session, number of forced runs
        '''
        stats=KeepRunningReward.stat(self)
        if stats==None:return
        stats['forcedruns']=self.nforcedruns
        return stats
                
        
class StopReward(Protocol):
    '''After running for RUN_TIME, the animal gets reward if stops for STOP_TIME
    '''
    RUN_TIME=10.0
    STOP_TIME=0.5
    
    def reset(self):
        self.engine.run_time=self.RUN_TIME
        self.engine.stop_time=self.STOP_TIME
        self.nrewards=0
        self.nruns=0
        self.run_complete=False
        
    def update(self):
        indexes=[i for i in range(len(self.engine.events)) if not self.engine.events[i]['ack'] and self.engine.events[i]['type'] in ['run', 'stop']]
        if len(indexes)>0:
            if self.engine.events[indexes[0]]['type']=='run':
                self.run_complete=True
                self.nruns+=1
            elif self.run_complete and self.engine.events[indexes[0]]['type']=='stop':
                self.run_complete=False
                self.engine.reward()
                self.nrewards+=1
            self.engine.events[indexes[0]]['ack']=True
        
    def stat(self):
        '''
        Success rate is the number of reward per the overall number of run events
        '''
        if self.nruns==0:
            success_rate=0
        else:
            success_rate=self.nrewards/float(self.nruns)
        return {'rewards':self.nrewards, 'runs': self.nruns, 'Success Rate': success_rate}
        


class StimStopReward(Protocol):
    '''
    If a run event occurs, turn on stimulus. Wait for stop event which should occur within DELAY_AFTER_RUN.
    If stop event does not happen, turn off stimulus and generate next randomized run time and wait for next run time
    If stop event takes place turn off stimulus, give reward and generate next randomized run time
    
    Randomized runtime :
    RUN_TME+a random number between 0 and RANDOM_TIME_RANGE in RANDOM_TIME_STEPs
    '''

    DELAY_AFTER_RUN=5.0
    RUN_TIME=5.0
    STOP_TIME=0.5
    RANDOM_TIME_RANGE=10.0
    RANDOM_TIME_STEP=0.5
    def reset(self):
        self.engine.run_time=self.generate_runtime()
        self.engine.stop_time=self.STOP_TIME
        self.nrewards=0
        self.nstimulus=0
        self.noreward=0
        self.run_complete=False
        
    def generate_runtime(self):
        nsteps=round(self.RANDOM_TIME_RANGE/self.RANDOM_TIME_STEP)
        new_runtime=self.RUN_TIME+round((random.random()*nsteps))*self.RANDOM_TIME_STEP
        logging.info('New runtime generated: {0} s'.format(new_runtime))
        return new_runtime
        
    def update(self):
        now=time.time()
        run_indexes=[i for i in range(len(self.engine.events)) if not self.engine.events[i]['ack'] and self.engine.events[i]['type'] =='run']
        if len(run_indexes)>0:
            self.run_complete=True
            self.run_complete_time=self.engine.events[run_indexes[0]]['t']
            self.engine.events[run_indexes[0]]['ack']=True
            self.engine.stimulate()
            self.nstimulus+=1
        elif self.run_complete:
            if now-self.run_complete_time>self.DELAY_AFTER_RUN:
                self.run_complete=False
                self.engine.run_time=self.generate_runtime()
                logging.info('No reward')
                self.noreward+=1
            else:
                stop_indexes=[i for i in range(len(self.engine.events)) if not self.engine.events[i]['ack'] and self.engine.events[i]['type'] =='stop' and self.engine.events[i]['t']>self.run_complete_time]
                if len(stop_indexes)>0:
                    for i in stop_indexes:
                        self.engine.events[i]['ack']=True
                    self.engine.reward()
                    self.nrewards+=1
                    self.run_complete=False
                    self.engine.run_time=self.generate_runtime()
        
    def stat(self):
        '''
        Success rate is nreward/nstimulus. nstimulus is the number when animal stopped and stimulus is presented. 
        nreward is the number when after stimulus the animal is stopped.
        '''
        if self.nstimulus==0:
            success_rate=0
        else:
            success_rate=self.nrewards/float(self.nstimulus)
        return {'rewards':self.nrewards, 'stimulus': self.nstimulus, 'No reward': self.noreward, 'Success Rate': success_rate}

class TreadmillSpeedReader(multiprocessing.Process):
    '''
    
    '''
    def __init__(self,queue, machine_config, emulate_speed=False):
        multiprocessing.Process.__init__(self)
        self.queue=queue
        self.speed_q=multiprocessing.Queue()
        self.machine_config=machine_config
        self.emulate_speed=emulate_speed
        
    def emulated_speed(self,t):
        if t<10:
            spd=5.0
        elif t>=10 and t<30:
            spd=20.0+t*1e-1
        elif t>=30:
            spd=2
        else:
            spd=10
        spd = 10*int(int(t/21)%2==0)
        spd+=numpy.random.random()-0.5
        return spd
        
    def run(self):
        self.last_run=time.time()
        self.start_time=time.time()
        logging.info('Speed reader started')
        while True:
            now=time.time()
            if now-self.last_run>self.machine_config.TREADMILL_SPEED_UPDATE_RATE:
                self.last_run=copy.deepcopy(now)
                if self.emulate_speed:
                    spd=self.emulated_speed(now-self.start_time)
                else:
                    pass
                self.speed_q.put([now,spd])
            
            if not self.queue.empty():
                msg=self.queue.get()
                if msg=='terminate':
                    break
            time.sleep(0.01)
        logging.info('Speed reader finished')

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
                self.camera = cv2.VideoCapture(0)#Initialize video capturing
                self.camera.set(3, self.machine_config.CAMERA_FRAME_WIDTH)#Set camera resolution
                self.camera.set(4, self.machine_config.CAMERA_FRAME_HEIGHT)
                logging.info('Camera initialized')
            except:
                logging.warning('no camera present')
            
    def start_video_recording(self,videofilename):
        if self.save_video and 0:
            numpy.save(self.videofilename.replace(os.path.splitext(self.videofilename)[1], '_frame_times.npy'),numpy.array(self.frame_times))
        self.video_saver= cv2.VideoWriter(videofilename,cv2.cv.CV_FOURCC(*'XVID'), 12,#self.machine_config.CAMERA_FRAME_RATE, 
                                                    (self.machine_config.CAMERA_FRAME_WIDTH,self.machine_config.CAMERA_FRAME_HEIGHT))
        self.save_video=True
        self.frame_counter=0
        self.frame_times=[]
        self.videofilename=videofilename
        logging.info('Recording video to {0} started'.format(videofilename))
        
    def stop_video_recording(self):
        self.save_video=False
        del self.video_saver
        logging.info('Recording video ended')
                
    def update_video_recorder(self):
        now=time.time()
        if now-self.last_runtime>=self.tperiod:
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
    def __init__(self,machine_config):
        self.machine_config=machine_config
        threading.Thread.__init__(self)
        CameraHandler.__init__(self,machine_config)
        self.from_gui = Queue.Queue()
        self.to_gui = Queue.Queue()
        self.context_filename = fileop.get_context_filename(self.machine_config,'npy')
        self.context_variables=['datafolder','parameters','current_animal']
        self.load_context()
        self.load_animal_file(switch2plot=True)
        self.speed_reader_q=multiprocessing.Queue()
        self.speed_reader=TreadmillSpeedReader(self.speed_reader_q,self.machine_config,emulate_speed=True)
        self.speed_reader.start()
        self.session_ongoing=False
        self.reset_data()
        self.enable_speed_update=True
        self.varnames=['speed_values','reward_values','airpuff_values','stimulus_values','forcerun_values', 'events','frame_times']
        
    def reset_data(self):
        self.speed_values=numpy.empty((0,2))
        self.reward_values=numpy.empty((0,2))
        self.airpuff_values=numpy.empty((0,2))
        self.stimulus_values=numpy.empty((0,2))
        self.forcerun_values=numpy.empty((0,2))
        self.events=[]
        logging.info('Data traces cleared')
        
    def load_context(self):
        if os.path.exists(self.context_filename):
            context_stream = numpy.load(self.context_filename)
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
        
    def add_animal(self,name):
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
            
    def forcerun(self,duration):
        logging.info('Force run for {0} s'.format(duration))
        now=time.time()
        self.forcerun_values=numpy.concatenate((self.forcerun_values,numpy.array([[now, 1]])))
            
    def reward(self):
        logging.info('Reward')
        now=time.time()
        self.reward_values=numpy.concatenate((self.reward_values,numpy.array([[now, 1]])))
        
    def airpuff(self):
        logging.info('Airpuff')
        now=time.time()
        self.airpuff_values=numpy.concatenate((self.airpuff_values,numpy.array([[now, 1]])))
        
    def set_valve(self,channel,state):
        pass
        
    def stimulate(self):
        logging.info('Stimulus')
        now=time.time()
        self.stimulus_values=numpy.concatenate((self.stimulus_values,numpy.array([[now-1e-3, 0],[now, 1],[now+self.parameters['Stimulus Pulse Duration'], 1],[now+self.parameters['Stimulus Pulse Duration']+1e-3, 0]])))

    def set_speed_update(self, state):
        self.enable_speed_update=state
        #Reset data buffer if no recording is ongoing and file was opened
        if state and not self.session_ongoing:#and hasattr(self, 'datafile_opened') and time.time()-self.datafile_opened<30:
            self.reset_data()
        
    def update_speed_values(self):
        new_value=[]
        if not self.speed_reader.speed_q.empty() and self.speed_reader.speed_q.qsize()>2:
            while not self.speed_reader.speed_q.empty():
                new_value.append(self.speed_reader.speed_q.get())
        if len(new_value)>0:
            self.speed_values=numpy.concatenate((self.speed_values,numpy.array(new_value)))
            return True
        else: return False

    def update_plot(self):
        if not self.speed_values.shape[0]>0:
            return
        xs,ys=self.values2trace(self.speed_values)
        now=xs[-1]
        t0=xs[0]
        x=[xs]
        y=[ys]
        trace_names=['speed']
        if sum([self.parameters[k] for k in ['Reward Trace', 'Airpuff Trace', 'Stimulus Trace', 'Run Events Trace', 'Stop Events Trace', 'Force Run Trace']])>3:
            return
        if self.reward_values.shape[0]>0 and self.parameters['Reward Trace']:
            xr,yr=self.values2trace(self.reward_values, now)
            if xr.shape[0]>0:
                t0=min(t0, xr[0])
                x.append(xr)
                y.append(yr*ys.max())
                trace_names.append('reward')
        if self.airpuff_values.shape[0]>0 and self.parameters['Airpuff Trace']:
            xa,ya=self.values2trace(self.airpuff_values, now)
            if xa.shape[0]>0:
                t0=min(t0, xa[0])
                x.append(xa)
                y.append(ya*ys.max())
                trace_names.append('airpuff')
        if self.stimulus_values.shape[0]>0 and self.parameters['Stimulus Trace']:
            xst,yst=self.values2trace(self.stimulus_values, now)
            if xst.shape[0]>0:
                t0=min(t0, xst[0])
                x.append(xst)
                y.append(yst*ys.max())
                trace_names.append('stimulus')
        if self.forcerun_values.shape[0]>0 and self.parameters['Force Run Trace']:
            xf,yf=self.values2trace(self.forcerun_values, now)
            if xf.shape[0]>0:
                t0=min(t0, xf[0])
                x.append(xf)
                y.append(yf*ys.max())
                trace_names.append('forcerun')
        for event_type in ['run', 'stop']:
            if self.parameters['{0} Events Trace'.format(event_type.capitalize())]:
                xe=numpy.array([event['t'] for event in self.events if event['type']==event_type])
                if xe.shape[0]>0:
                    ye=numpy.ones_like(xe)*ys.max()*0.5
                    xe,ye=self.values2trace(numpy.array([xe,ye]).T, now)
                    if xe.shape[0]>0:
                        x.append(xe)
                        y.append(ye)
                        trace_names.append(event_type)
                        t0=min(t0,x[-1][0])
        
        t0=numpy.concatenate(x).min()
        for xi in x:
            xi-=t0
        self.to_gui.put({'update_events_plot':{'x':x, 'y':y, 'trace_names': trace_names}})

    def values2trace(self, values, now=None):
        x=values[:,0].copy()
        xl= x[-1] if now==None else now
        indexes=numpy.nonzero(numpy.where(x>xl-self.parameters['Save Period'],1,0))[0]
        x=x[indexes]
        y=values[indexes,1]
        return x,y
        
    def run_stop_event_detector(self):
        '''
        Stop event: animal motion is below threshold for a certain amount of time. (Also a run event should happen right before that)
        Run event: animal was running for a certain amount of time
        Event time is when the condition is met
        
        At stim stop protocol there should be some tolerance between the run and stop event times
        Event structure:
        name:
        acknowledged:
        time:
        previous event: name, time
        '''
        #consider speed values since the last event        
        t=self.speed_values[:,0]
        spd=self.speed_values[:,1]
        if len(self.events)>0:
            indexes=numpy.nonzero(numpy.where(t>self.events[-1]['t'],1,0))[0]
            t=t[indexes]
            spd=spd[indexes]
        if t.shape[0]==0:
            return
        ismoving=numpy.where(spd>self.parameters['Move Threshold'],True,False)
        if hasattr(self, 'stop_time'):
            stop_indexes=numpy.nonzero(numpy.where(t>t.max()-self.stop_time,1,0))[0]
        else:
            stop_indexes=numpy.empty(0)            
        if hasattr(self, 'run_time'):
            running_indexes=numpy.nonzero(numpy.where(t>t.max()-self.run_time,1,0))[0]
        else:
            running_indexes=numpy.empty(0)
        last_event_time=self.events[-1]['t'] if len(self.events)>0 else 0#checking time elapsed since last event ensures that one event is counted once
        if last_event_time<t[0]:#When new session is started, earlier events are ignored as last event time
            last_event_time=t[0]
        if stop_indexes.shape[0]>0 and not ismoving[stop_indexes].any() and t[-1] - last_event_time> self.stop_time:
            event={}
            event['type']='stop'
            event['ack']=False
            event['t']=t[-1]
            self.events.append(event)
        elif running_indexes.shape[0]>0 and ismoving[running_indexes].sum()>ismoving[running_indexes].shape[0]*1e-2*self.parameters['Run Threshold']\
            and t[-1] - last_event_time> self.run_time:
            event={}
            event['type']='run'
            event['ack']=False
            event['t']=t[-1]
            self.events.append(event)
            
    def start_session(self):
        if self.session_ongoing:
            return
        self.reset_data()
        rootfolder=os.path.join(self.datafolder, self.current_animal)
        animal_file=os.path.join(rootfolder, 'animal_' + self.current_animal+'.hdf5')
        if not os.path.exists(rootfolder):
            self.notify('Warning', 'Animal folder does not exists')
            return
        if not os.path.exists(animal_file):
            self.notify('Warning', 'Animal file does not exists')
            return
        today=utils.timestamp2ymd(time.time(),'')
        last_entry_timestamp=utils.timestamp2ymd(self.weight[-1,0],'')
        if last_entry_timestamp<today and not self.ask4confirmation('No animal weight was added today. Do you want to continue?'):
            return
        self.recording_folder=os.path.join(rootfolder, today)
        if not os.path.exists(self.recording_folder):
            os.mkdir(self.recording_folder)
        self.show_day_success_rate(self.recording_folder)
        self.current_protocol = self.parameters['Protocol']
        #TODO give warning if suggested protocol is different
        self.protocol=getattr(sys.modules[__name__], self.current_protocol)(self)
        self.to_gui.put({'update_protocol_description':'Current protocol: '+ self.current_protocol+'\r\n'+self.protocol.__doc__+'\r\n'+str(object_parameters2dict(self.protocol))})
        self.session_ongoing=True
        self.start_recording()
        self.to_gui.put({'set_recording_state': 'recording'})
        self.to_gui.put({'switch2_event_plot': ''})
        logging.info('Session started using {0} protocol'.format(self.current_protocol))
        self.enable_speed_update=True
        
    def run_protocol(self):
        if self.session_ongoing:
            self.protocol.update()
            if int(time.time()*10)%10==0:
                stat=self.protocol.stat()
                if hasattr(stat,'has_key'):
                    stat['Success Rate']='{0:0.0f} %'.format(100*stat['Success Rate'])
                    self.to_gui.put({'statusbar':stat})

    def start_recording(self):
        self.recording_started_state={}
        for vn in self.varnames:
            if not hasattr(self, vn):
                self.recording_started_state[vn]=0
            else:
                var=getattr(self, vn)
                if isinstance(var,list):
                    self.recording_started_state[vn]=len(var)
                elif hasattr(var,'shape'):
                    self.recording_started_state[vn]=var.shape[0]
        self.id=int(time.time())
        self.filename=os.path.join(self.recording_folder, 'data_{0}_{1}'.format(self.current_protocol.replace(' ', '_'), self.id))
        videofilename=self.filename+'.avi'
        self.filename+='.hdf5'
        self.to_gui.put({'set_events_title': os.path.basename(self.filename)})
        self.start_video_recording(videofilename)
        
    def finish_recording(self):
        self.stop_video_recording()
        logging.info('Recorded {0:.0f} s'.format(self.speed_values[-1,0]-self.speed_values[self.recording_started_state['speed_values'],0]))
        self.save2file()
        
    def periodic_save(self):
        if self.parameters['Enable Periodic Save'] and self.session_ongoing and self.speed_values.shape[0]>self.recording_started_state['speed_values'] and self.speed_values[-1,0]-self.speed_values[self.recording_started_state['speed_values'],0]>self.parameters['Save Period']:
            self.finish_recording()
            self.start_recording()
        
    def stop_session(self):
        if not self.session_ongoing:
            return
        self.finish_recording()
        self.session_ongoing=False
        self.to_gui.put({'set_recording_state': 'idle'})
        logging.info('Session ended')
        
    def save2file(self):
        self.datafile=hdf5io.Hdf5io(self.filename)
        self.datafile.stat=self.protocol.stat()
        for nn in ['machine_config', 'protocol']:
            var=getattr(self, nn)
            setattr(self.datafile, nn, object_parameters2dict(var))
            #setattr(self.datafile, nn, dict([(vn,getattr(var, vn)) for vn in dir(var) if vn.isupper()] ))
        for vn in self.varnames:
            values=copy.deepcopy(getattr(self, vn))[self.recording_started_state[vn]:]
            setattr(self.datafile, vn, values)
        self.datafile.protocol_name=self.protocol.__class__.__name__#This for sure the correct value
        nodes=['machine_config', 'protocol', 'protocol_name', 'stat']
        nodes.extend(self.varnames)
        self.datafile.save(nodes)
        self.datafile.close()
        logging.info('Data saved to {0}'.format(self.filename))
        self.show_day_success_rate(self.filename)
        
    def open_file(self, filename):
        if self.session_ongoing:
            self.notify('Warning', 'Stop recording before opening a file')
            return
        self.filename=filename
        self.datafile_opened=time.time()
        self.datafile=hdf5io.Hdf5io(self.filename)
        for vn in self.varnames:
            self.datafile.load(vn)
            setattr(self, vn, getattr(self.datafile, vn))
        stat=self.datafile.findvar('stat')
        self.datafile.close()
        self.enable_speed_update=False
        self.to_gui.put({'set_live_state': 0})
        self.to_gui.put({'set_events_title': os.path.basename(filename)})
        if hasattr(stat,'has_key'):
            stat['Success Rate']='{0:0.0f} %'.format(100*stat['Success Rate'])
            self.to_gui.put({'statusbar':stat})
            
    def show_animal_success_rate(self):
        current_animal_folder=os.path.join(self.datafolder, self.current_animal)
        x=[]
        y=[]
        day_folders=[d for d in fileop.listdir_fullpath(current_animal_folder) if os.path.isdir(d)]
        day_folders.sort()
        top_protocols=[]
        for day_folder in day_folders:
            success_rate,top_protocol=self.day_summary(day_folder)
            top_protocols.append(top_protocol)
            y.append(success_rate)
            x.append(utils.datestring2timestamp(os.path.basename(day_folder),format="%Y%m%d"))
        x=numpy.array(x)
        x-=x.max()
        x/=86400
        self.animal_success_rate=numpy.array([x,y])
        y=numpy.array(y)
        self.to_gui.put({'update_success_rate_plot':{'x':[x], 'y':[y*100], 'trace_names': ['success_rate']}})
        self.to_gui.put({'set_success_rate_title': self.current_animal})
        logging.info('\r\n'.join(['{0}\t{1}'.format(x[i], top_protocols[i]) for i in range(len(top_protocols))]))
        
        
    def day_summary(self, folder):
        summary = [self.read_file_summary(f) for f in [os.path.join(folder,fn) for fn in os.listdir(folder) if os.path.splitext(fn)[1]=='.hdf5']]
        try:
            all_recording_time = sum([s['duration'] for s in summary])
            weighted_success_rates=[s['duration']/all_recording_time*s['Success Rate'] for s in summary]
            success_rate=sum(weighted_success_rates)
            #Most frequent protocol:
            protocols=[s['protocol'] for s in summary]
            protocol_names=list(set(protocols))
            top_protocol = protocol_names[numpy.array([len([p for p in protocols if pn in p]) for pn in protocol_names]).argmax()]
        except:
            success_rate=0
            top_protocol=''
        return success_rate,top_protocol
            
    def show_day_success_rate(self,folder):
        '''
        
        
        '''
        if os.path.isdir(folder):
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
                xp-=xi[0]
            xi-=xi[0]
            x=[numpy.array(xi)]
            y=[numpy.array(yi)*100]
            trace_names=['success_rate']
            self.to_gui.put({'update_success_rate_plot':{'x':x, 'y':y, 'trace_names': trace_names, 'vertical_lines': xp}})
            self.to_gui.put({'set_success_rate_title': os.path.basename(folder)})
            logging.info('Protocol order: {0}'.format(', '.join(protocol_order)))
            
    def read_file_summary(self,filename):
        '''
        Read time of recording, duration, protocol, success rate and other stat parameters
        '''
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
        
    def run(self):
        logging.info('Engine started')
        while True:
            try:
                self.last_run = time.time()#helps determining whether the engine still runs
                if not self.from_gui.empty():
                    msg = self.from_gui.get()
                    if msg == 'terminate':
                        break
                    if msg.has_key('function'):#Functions are simply forwarded
                        #Format: {'function: function name, 'args': [], 'kwargs': {}}
                        logging.info(msg)
                        getattr(self, msg['function'])(*msg['args'])
                self.update_video_recorder()
                if self.enable_speed_update:
                    self.run_stop_event_detector()
                    self.update_speed_values()
                self.update_plot()
                self.periodic_save()
                self.run_protocol()
            except:
                logging.error(traceback.format_exc())
                self.save_context()
            time.sleep(40e-3)
        self.close()
        
    def close(self):
        if self.session_ongoing:
            self.stop_session()
        self.close_video_recorder()
        self.speed_reader_q.put('terminate')
        self.speed_reader.join()
        self.save_context()
        logging.info('Engine terminated')
        
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
        self.engine=BehavioralEngine(self.machine_config)
        self.engine.start()
        self.to_engine=self.engine.from_gui
        self.from_engine=self.engine.to_gui
        self.maximized=False
        gui.SimpleAppWindow.__init__(self)
        
    def init_gui(self):
        self.setWindowTitle('Behavioral Experiment Control')
        self.setWindowIcon(gui.get_icon('behav'))
        self.setGeometry(4,21,1366,768)
        self.debugw.setMinimumHeight(300)
        self.debugw.setMaximumWidth(650)
        self.cw=CWidget(self)#Creating the central widget which contains the image, the plot and the control widgets
        self.setCentralWidget(self.cw)#Setting it as a central widget
        self.params_config=[
                            {'name': 'General', 'type': 'group', 'expanded' : True, 'children': [
                                {'name': 'Protocol', 'type': 'list', 'values': get_protocol_names(),'value':''},
                                {'name': 'Save Period', 'type': 'float', 'value': 100.0,'siPrefix': True, 'suffix': 's'},
                                {'name': 'Enable Periodic Save', 'type': 'bool', 'value': True},
                                {'name': 'Move Threshold', 'type': 'float', 'value': 1,'suffix': 'm/s'},
                                {'name': 'Run Threshold', 'type': 'float', 'value': 50.0, 'suffix': '%'},
                                {'name': 'Laser Intensity', 'type': 'float', 'value': 1.0,'siPrefix': True, 'suffix': 'V'},
                                {'name': 'Stimulus Pulse Duration', 'type': 'float', 'value': 1.0,'siPrefix': True, 'suffix': 's'},
                                {'name': 'Led Stim Voltage', 'type': 'float', 'value': 1.0,'siPrefix': True, 'suffix': 'V'},
                            ]},
                            {'name': 'Show...', 'type': 'group', 'expanded' : True, 'children': [
                                {'name': 'Run Events Trace', 'type': 'bool', 'value': True},
                                {'name': 'Stop Events Trace', 'type': 'bool', 'value': True},
                                {'name': 'Reward Trace', 'type': 'bool', 'value': False},
                                {'name': 'Airpuff Trace', 'type': 'bool', 'value': False},
                                {'name': 'Stimulus Trace', 'type': 'bool', 'value': False},
                                {'name': 'Force Run Trace', 'type': 'bool', 'value': False},
                                ]},
                            {'name': 'Advanced', 'type': 'group', 'expanded' : True, 'children': [
                                {'name': 'Water Open Time', 'type': 'float', 'value': 10e-3,'siPrefix': True, 'suffix': 's'},
                                {'name': 'Air Puff Duration', 'type': 'float', 'value': 10e-3,'siPrefix': True, 'suffix': 's'},
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
        self.paramw .setFixedWidth(400)
        self.paramw.params.sigTreeStateChanged.connect(self.parameter_changed)
        self.parameter_changed()
        self.add_dockwidget(self.paramw, 'Parameters', QtCore.Qt.RightDockWidgetArea, QtCore.Qt.RightDockWidgetArea)
        
        self.plotnames=['events', 'animal_weight', 'success_rate']
        self.plots=gui.TabbedPlots(self,self.plotnames)
        self.plots.animal_weight.plot.setLabels(left='weight [g]')
        self.plots.events.plot.setLabels(left='speed [m/s]', bottom='times [s]')
        self.plots.success_rate.setToolTip('''Displays success rate of days or a specific day depending on what is selected in Files tab.
        A day summary is shown if a specific recording day is selected. If animal is selected, a summary for each day is plotted
        ''')
        self.plots.success_rate.plot.setLabels(left='%')
        self.plots.tab.setMinimumWidth(700)
        self.plots.tab.setFixedHeight(300)
        for pn in self.plotnames:
            getattr(self.plots, pn).setMinimumWidth(self.plots.tab.width()-50)
        self.add_dockwidget(self.plots, 'Plots', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea)
        
        toolbar_buttons = ['record', 'stop', 'select_data_folder','add_animal', 'add_animal_weight', 'remove_last_animal_weight', 'exit']
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
        if msg.has_key('notify'):
            self.notify(msg['notify']['title'], msg['notify']['msg'])
        elif msg.has_key('statusbar'):
            self.update_statusbar(msg=msg['statusbar'])
        elif msg.has_key('update_weight_history'):
            x=msg['update_weight_history'][:,0]
            x/=86400
            x-=x[-1]
            utils.timestamp2ymd(self.engine.weight[-1,0])
            self.plots.animal_weight.update_curve(x,msg['update_weight_history'][:,1],plotparams={'symbol' : 'o', 'symbolSize': 8, 'symbolBrush' : (0, 0, 0)})
            self.plots.animal_weight.plot.setLabels(bottom='days, {0} = {1}, 0 = {2}'.format(int(numpy.round(x[0])), utils.timestamp2ymd(self.engine.weight[0,0]), utils.timestamp2ymd(self.engine.weight[-1,0])))
        elif msg.has_key('switch2_animal_weight_plot'):
            self.cw.main_tab.setCurrentIndex(0)
            self.plots.tab.setCurrentIndex(1)
        elif msg.has_key('update_main_image'):
            if not skip_main_image_display:
                self.cw.images.main.set_image(numpy.rot90(msg['update_main_image'],3),alpha=1.0)
        elif msg.has_key('update_events_plot'):
            plotparams=[]
            for tn in msg['update_events_plot']['trace_names']:
                if tn =='speed':
                    plotparams.append({'name': tn, 'pen':(0,0,0)})
                elif tn=='reward':
                    plotparams.append({'name': tn, 'pen':None, 'symbol':'t', 'symbolSize':12, 'symbolBrush': (0,255,0,150)})
                elif tn=='airpuff':
                    plotparams.append({'name': tn, 'pen':None, 'symbol':'t', 'symbolSize':12, 'symbolBrush': (255,0,0,150)})
                elif tn=='stimulus':
                    plotparams.append({'name': tn, 'pen':(0,0,255)})
                elif tn=='run':
                    plotparams.append({'name': tn, 'pen':None, 'symbol':'o', 'symbolSize':10, 'symbolBrush': (128,128,128,150)})
                elif tn=='stop':
                    plotparams.append({'name': tn, 'pen':None, 'symbol':'o', 'symbolSize':10, 'symbolBrush': (0,128,0,150)})
                elif tn=='forcerun':
                    plotparams.append({'name': tn, 'pen':None, 'symbol':'t', 'symbolSize':12, 'symbolBrush': (128,0,0,150)})
            self.plots.events.update_curves(msg['update_events_plot']['x'], msg['update_events_plot']['y'], plotparams=plotparams)
        elif msg.has_key('ask4confirmation'):
            reply = QtGui.QMessageBox.question(self, 'Confirm following action', msg['ask4confirmation'], QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
            self.to_engine.put(reply == QtGui.QMessageBox.Yes)
        elif msg.has_key('set_recording_state'):
            self.cw.set_state(msg['set_recording_state'])
        elif msg.has_key('switch2_event_plot'):
            self.plots.tab.setCurrentIndex(0)
        elif msg.has_key('set_live_state'):
            self.cw.live_speed.input.setCheckState(msg['set_live_state'])
        elif msg.has_key('set_events_title'):
            self.plots.events.plot.setTitle(msg['set_events_title'])
        elif msg.has_key('update_protocol_description'):
            self.cw.state.setToolTip(msg['update_protocol_description'])
        elif msg.has_key('update_success_rate_plot'):
            plotparams=[]
            for tn in msg['update_success_rate_plot']['trace_names']:
                if tn =='success_rate':
                    plotparams.append({'name': tn, 'pen':(0,0,0), 'symbol':'o', 'symbolSize':6, 'symbolBrush': (0,0,0)})
            self.plots.success_rate.update_curves(msg['update_success_rate_plot']['x'], msg['update_success_rate_plot']['y'], plotparams=plotparams)
            if msg['update_success_rate_plot'].has_key('vertical_lines') and msg['update_success_rate_plot']['vertical_lines'].shape[0]>0:
                self.plots.success_rate.add_linear_region(msg['update_success_rate_plot']['vertical_lines'],color=(0,0,0,20))
            else:
                self.plots.success_rate.add_linear_region([])
        elif msg.has_key('set_success_rate_title'):
            self.plots.success_rate.plot.setTitle(msg['set_success_rate_title'])
        
    def update_statusbar(self,msg=''):
        '''
        General text display
        '''
        ca=self.engine.current_animal if hasattr(self.engine, 'current_animal') else ''
        txt='Data folder: {0}, Current animal: {1} {2}'. format(self.engine.datafolder,ca,msg)
        self.statusbar.showMessage(txt)
        self.setWindowTitle('Behavioral Experiment Control\t{0}'.format(ca))
        
    def closeEvent(self, e):
        e.accept()
        self.exit_action()
        
    def record_action(self):
        self.to_engine.put({'function': 'start_session','args':[]})
    
    def stop_action(self):
        self.to_engine.put({'function': 'stop_session','args':[]})
        
    def select_data_folder_action(self):
        self.engine.datafolder = self.ask4foldername('Select Data Folder', self.engine.datafolder)
        self.cw.filebrowserw.set_root(self.engine.datafolder)
        self.update_statusbar()
        
    def add_animal_action(self):
        text, ok = QtGui.QInputDialog.getText(self, 'Add Animal', 
            'Enter animal name:')
        if ok:
            self.to_engine.put({'function': 'add_animal','args':[str(text)]})
            
    def add_animal_weight_action(self):
        self.aw=AddAnimalWeightDialog(self.to_engine)
        self.aw.show()
      
    def remove_last_animal_weight_action(self):
        if self.ask4confirmation('Do you want to remove last weight entry?'):
            self.to_engine.put({'function': 'remove_last_animal_weight','args':[]})
        
    def exit_action(self):
        self.to_engine.put('terminate')
        self.engine.join()
        self.close()
        
class CWidget(QtGui.QWidget):
    '''
    The central widget of the user interface which contains the image, the plot and the various controls for starting experiment or adjusting parameters
    '''
    def __init__(self,parent):
        QtGui.QWidget.__init__(self,parent)
        self.setFixedHeight(400)
        self.imagenames=['main', 'eye']
        self.images=gui.TabbedImages(self,self.imagenames)
        ar=float(parent.machine_config.CAMERA_FRAME_WIDTH)/parent.machine_config.CAMERA_FRAME_HEIGHT
        self.images.main.setFixedWidth(320*ar)
        self.images.main.setFixedHeight(320)
        self.main_tab = self.images.tab
        self.filebrowserw=FileBrowserW(self)
        self.main_tab.addTab(self.filebrowserw, 'Files')
        self.lowleveldebugw=LowLevelDebugW(self)
        self.main_tab.addTab(self.lowleveldebugw, 'Advanced')
        self.main_tab.setCurrentIndex(0)
        self.main_tab.setTabPosition(self.main_tab.South)
        self.main_tab.setMinimumHeight(330)
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
        self.parent().to_engine.put({'function':'set_speed_update','args':[state==2]})
        
class FileBrowserW(gui.FileTree):
    def __init__(self,parent):
        gui.FileTree.__init__(self,parent, parent.parent().engine.datafolder, ['mat','hdf5', 'avi'])
        self.doubleClicked.connect(self.open_file)
        self.clicked.connect(self.file_selected)
        
    def file_selected(self,index):
        self.selected_filename = gui.index2filename(index)
        if os.path.isdir(self.selected_filename) and os.path.dirname(self.selected_filename)==self.parent.parent().engine.datafolder:
            #Animal folder selected
            self.parent.parent().engine.current_animal=os.path.basename(self.selected_filename)
            logging.info('Animal selected: {0}'.format(self.parent.parent().engine.current_animal))
            self.parent.parent().update_statusbar()
            self.parent.parent().to_engine.put({'function':'load_animal_file','args':[]})
            self.parent.parent().to_engine.put({'function':'show_animal_success_rate','args':[]})
        elif os.path.isdir(self.selected_filename) and os.path.dirname(self.selected_filename)==os.path.join(self.parent.parent().engine.datafolder, self.parent.parent().engine.current_animal):
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
        self.connect(self.valves['water'].input, QtCore.SIGNAL('stateChanged(int)'),  self.water_valve_clicked)
        self.connect(self.valves['air'].input, QtCore.SIGNAL('stateChanged(int)'),  self.air_valve_clicked)
        self.airpuff=QtGui.QPushButton('Air Puff', parent=self)
        self.connect(self.airpuff, QtCore.SIGNAL('clicked()'), self.airpuff_clicked)
        self.reward=QtGui.QPushButton('Reward', parent=self)
        self.connect(self.reward, QtCore.SIGNAL('clicked()'), self.reward_clicked)
        self.stimulate=QtGui.QPushButton('Stimulate', parent=self)
        self.connect(self.stimulate, QtCore.SIGNAL('clicked()'), self.stimulate_clicked)
        self.forcerun=QtGui.QPushButton('Force Run', parent=self)
        self.connect(self.forcerun, QtCore.SIGNAL('clicked()'), self.forcerun_clicked)
        self.l = QtGui.QGridLayout()
        [self.l.addWidget(self.valves.values()[i], 0, i, 1, 1) for i in range(len(self.valves.values()))]
        self.l.addWidget(self.reward, 1, 0, 1, 1)
        self.l.addWidget(self.airpuff, 1, 1, 1, 1)
        self.l.addWidget(self.stimulate, 2, 0, 1, 1)
        self.l.addWidget(self.forcerun, 2, 1, 1, 1)
        self.setLayout(self.l)
        self.l.setColumnStretch(2,20)
        self.l.setRowStretch(3,20)
        
    def forcerun_clicked(self):
        self.parent.parent().to_engine.put({'function':'forcerun','args':[1]})
        
    def airpuff_clicked(self):
        self.parent.parent().to_engine.put({'function':'airpuff','args':[]})
        
    def reward_clicked(self):
        self.parent.parent().to_engine.put({'function':'reward','args':[]})
    
    def stimulate_clicked(self):
        self.parent.parent().to_engine.put({'function':'stimulate','args':[]})
    
    def air_valve_clicked(self,state):
        self.parent.parent().to_engine.put({'function':'set_valve','args':['air', state==2]})
        
    def water_valve_clicked(self,state):
        self.parent.parent().to_engine.put({'function':'set_valve','args':['water', state==2]})
        
    

        
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
        

class Config(object):
    '''
    This configuration class is for storing all the parameters
    '''
    def __init__(self):
        self.ENABLE_CAMERA=True
        self.STIM_CHANNELS=['Dev1/ao1','Dev1/ao0']#Physical channels of usb-daq device
        self.DIO_PORT = 'COM4' if os.name=='nt' else '/dev/ttyUSB0'#serial port which controls the valve
        self.VALVE_PIN=0
        self.ARDUINO_BASED_DIO=False
        self.DATA_FOLDER = 'c:\\temp' if os.name == 'nt' else tempfile.gettempdir()#Default data folder
        self.VALVE_OPEN_TIME=10e-3
        self.STIMULUS_DURATION=1.0
        self.CURSOR_RESET_POSITION=0.0#Reset position of the cursor, 0.01 means that the reet positions will be 0.01*screen_width and 0.99*screen_width
        self.CURSOR_POSITION_UPDATE_PERIOD = 50e-3#second, The period time for calling the cursor handler. Cursor position is sampled and speed is calculated when curor handler is called
        self.CAMERA_UPDATE_RATE=16#Hz, Frame rate of camera. This value will be used for the output video file too
        self.CAMERA_FRAME_WIDTH=640/2
        self.CAMERA_FRAME_HEIGHT=480/2
        self.POWER_VOLTAGE_RANGE=[0,10]#The minimum and maximum accepted values for controlling the stimulus
        self.RUN_DIRECTION=1#Polarity of speed signal

        self.RUN_THRESHOLD=0.5#The speed at 50% of the time when mouse is expected to run shall be above MOVE_THRESHOLD
        #7 cm: 803-5,988-21,1072-75,1172-270,1341-293,1338-466: 7 cm = 930 pixel -> 1 pixel = 0.0075214899713467055
        self.PIXEL2SPEED=0.0075214899713467055
        self.MOVE_THRESHOLD=1#Above this speed the mouse is considered to be moving
        self.STOP_TIME=0.5
        self.init_setup_specific_parameters()
        
    def init_setup_specific_parameters(self):
        pass
        
    def get_protocol_names(self):
        return [vn.replace('PROTOCOL_','') for vn in dir(self) if 'PROTOCOL_' in vn]
        
class FrameSaver(multiprocessing.Process):
    '''
    This process saves the images transmitted through the input queue. 
    It is running on a different processor core from the main thread to ensure higher video recording framerate.
    '''
    def __init__(self,queue):
        multiprocessing.Process.__init__(self)
        self.queue=queue
        self.exit=False
        
    def run(self):
        logging.info('Frame saver started')
        while True:
            while not self.queue.empty():
                msg=self.queue.get()
                if msg=='terminate':#If message contains this string, stop the process
                    self.exit=True
                else:
                    frame,filename=msg#A message shall contain the frame and the filename where the frame is to be saved
                    Image.fromarray(frame).save(filename)#Saving the image
            if self.exit: break
            time.sleep(1e-3)#Ensuring that this process does not consume all the time of the processor where it is running
        logging.info('Frame saver finished')
                
class FileSaver(multiprocessing.Process):
    '''
    
    '''
    def __init__(self,queue):
        multiprocessing.Process.__init__(self)
        self.queue=queue
        
    def run(self):
        while True:
            if not self.queue.empty():
                msg=self.queue.get()
                if msg=='terminate':#If message contains this string, stop the process
                    break
                else:
                    filename, data2save, frame_folder, fps=msg
                    self.save(filename, data2save, frame_folder, fps)
            else:
                time.sleep(1e-3)#Ensuring that this process does not consume all the time of the processor where it is running
                
    def save(self, filename, data2save, frame_folder, fps):
        scipy.io.savemat(filename, data2save,oned_as='row', do_compression=True)
        vfilename=filename.replace('.mat','.mp4')
        #frames saved to a temporary folder are used for generating an mpeg4 video file.
        if frame_folder is not None:
            videofile.images2mpeg4(frame_folder, vfilename,fps)
            shutil.rmtree(frame_folder)
        
class HardwareHandler(threading.Thread):
    '''
    Runs parallel with the main thread. Via queues it receives commands to open/close the valve or generate a stimulus
    '''
    def __init__(self,command,response,config):
        self.command=command
        self.response=response#Via queue the actual state of the stim and valve is signalled for the main thread
        self.config=config
        threading.Thread.__init__(self)
        
    def valve_on(self):
        self.s.set_pin(self.config.VALVE_PIN,1)
        
    def valve_off(self):
        self.s.set_pin(self.config.VALVE_PIN,0)
        
    def run(self):
        if self.config.ARDUINO_BASED_DIO:
            self.s=digital_io.AduinoIO(self.config.DIO_PORT)
        else:
            s=serial.Serial(self.config.DIO_PORT)#Opening the serial port
            s.setBreak(0)#Bringing the orange wire to a known state
            s.setRTS(1)#Same for the green one
        while True:
            if not self.command.empty():
                cmd=self.command.get()
                if cmd[0]=='terminate':#Terminate the command loop and stop thread
                    break
                elif cmd[0] == 'stimulate':
                    if os.name=='nt':
                        daq_instrument.set_voltage(cmd[2],cmd[1])#cmd[2] contains the physical channel name of the usb daq device, cmd[1] is the voltage
                    time.sleep(self.config.STIMULUS_DURATION)#Wait while the duration of the stimulus is over
                    if os.name=='nt':
                        daq_instrument.set_voltage(cmd[2],0)#Set the analog output to 0V
                    self.response.put('stim ready')#Signal the main thread that the stimulus is ready
                elif cmd[0] == 'stim on':
                    if os.name=='nt':
                        daq_instrument.set_voltage(cmd[2],cmd[1])
                elif cmd[0] == 'stim off':
                    if os.name=='nt':
                        daq_instrument.set_voltage(cmd[2],0)
                elif cmd[0] == 'reward':
                    if self.config.ARDUINO_BASED_DIO:
                        self.valve_on()
                    else:
                        s.setBreak(1)#Set the orange wire to 0 V which opens the valve (it has double inverted logic)
                    time.sleep(self.config.VALVE_OPEN_TIME)
                    if self.config.ARDUINO_BASED_DIO:
                        self.valve_off()
                    else:
                        s.setBreak(0)#Close the valve
                    self.response.put('reward ready')#signalling the main thread that delivering the reward is done
                elif cmd[0] == 'open_valve':
                    if self.config.ARDUINO_BASED_DIO:
                        self.valve_on()
                    else:
                        s.setBreak(1)#Opening the valve for debug purposes
                elif cmd[0] == 'close_valve':
                    if self.config.ARDUINO_BASED_DIO:
                        self.valve_off()
                    else:
                        s.setBreak(0)#Close tha valve 
            else:
                time.sleep(10e-3)
        if self.config.ARDUINO_BASED_DIO:
            self.s.close()
        else:
            s.setBreak(0)#Bring the orange and green wires to a safe state
            s.setRTS(1)
            s.close()#Close the serial port

HELP='''Start experiment: Ctrl+a
Stop experiment: Ctrl+s
Select next protocol: Space'''

class CWidget1(QtGui.QWidget):
    '''
    The central widget of the user interface which contains the image, the plot and the various controls for starting experiment or adjusting parameters
    '''
    def __init__(self,parent):
        QtGui.QWidget.__init__(self,parent)
        self.image=gui.Image(self)#Create image widget
        self.image.setFixedWidth(450)#Setting its width
        ar=float(parent.config.CAMERA_FRAME_WIDTH)/parent.config.CAMERA_FRAME_HEIGHT
        self.image.setFixedHeight(450/ar)#Setting image widget height while keeping the aspect ratio of camera resolution
        
        self.plotw=gui.Plot(self)
        self.plotw.setFixedHeight(250)
        self.plotw.plot.setLabels(left='speed [cm/s]', bottom='time [s]')#Adding labels to the plot
        #self.plotw.plot.addLegend(size=(120,60))
        
        self.setToolTip(HELP)
        self.select_protocol=gui.LabeledComboBox(self,'Select protocol', parent.config.get_protocol_names())#With this combobox the stimulus protocol can be selected
        self.select_folder = QtGui.QPushButton('Data Save Folder', parent=self)#Clicking this button the data save folder can be selected
        self.selected_folder = QtGui.QLabel(parent.config.DATA_FOLDER, self)#Displays the data folder
        
        self.stim_power = gui.LabeledInput(self, 'Stimulus Intensity [V]')#The voltages controlling the stimulus devices can be set here
        self.stim_power.input.setText('7,5')#The default value is 4 V for both channels
        self.stim_power.input.setFixedWidth(40)
        
        self.open_valve=gui.LabeledCheckBox(self,'Open Valve')#This checkbox is for controlling the valve manually
        self.open_valve.setToolTip('When checked, the valve is open')
        self.save_data=gui.LabeledCheckBox(self,'Save Data')#Checking this checkbox enables saving the video and the speed signal of a session
        self.save_data.input.setCheckState(2)
        
        self.start = QtGui.QPushButton('Start', parent=self)#Start recording/experiment session
        self.start.setMaximumWidth(100)
        self.stop = QtGui.QPushButton('Stop', parent=self)#Stop recording/experiment session
        self.stop.setMaximumWidth(100)
        
        self.enable_periodic_data_save=gui.LabeledCheckBox(self,'Enable Periodic Save')
        self.enable_periodic_data_save.input.setCheckState(2)
        
        self.counter = QtGui.QLabel('', self)
        
        self.save_period = gui.LabeledInput(self, 'Data Save Period [s]')
        self.save_period.input.setText('60')
        self.save_period.input.setFixedWidth(40)
        
        self.l = QtGui.QGridLayout()#Organize the above created widgets into a layout
        self.l.addWidget(self.image, 0, 0, 5, 2)
        self.l.addWidget(self.plotw, 0, 2, 1, 5)
        self.l.addWidget(self.select_protocol, 1, 2, 1, 2)
        self.l.addWidget(self.stim_power, 2, 5, 1, 1)
        self.l.addWidget(self.counter, 3, 6, 1, 1)
        self.l.addWidget(self.enable_periodic_data_save, 3, 4, 1, 1)
        self.l.addWidget(self.save_period, 3, 5, 1, 1)
        self.l.addWidget(self.select_folder, 1, 4, 1, 1)
        self.l.addWidget(self.selected_folder, 1, 5, 1, 1)
        self.l.addWidget(self.open_valve, 1, 6, 1, 1)
        self.l.addWidget(self.save_data, 2, 4, 1, 1)
        self.l.addWidget(self.start, 2, 2, 1, 1)
        self.l.addWidget(self.stop, 2, 3, 1, 1)
        self.setLayout(self.l)

class Behavioral1(gui.SimpleAppWindow):
    '''
    Main application class and main thread of the behavioral control software.
    '''
    def init_gui(self):
        self.config=getattr(sys.modules[__name__],sys.argv[1])()#The Config class is created which holds the configuration values
        self.setWindowTitle('Behavioral Experiment Control')
        self.cw=CWidget(self)#Creating the central widget which contains the image, the plot and the control widgets
        self.cw.setMinimumHeight(500)#Adjusting its geometry
        self.cw.setMinimumWidth(1100)
        self.setCentralWidget(self.cw)#Setting it as a central widget
        self.debugw.setMinimumWidth(800)#Setting the sizes of the debug widget. The debug widget is created by gui.SimpleAppWindow class which is 
        self.debugw.setMinimumHeight(250)#the superclass of Behavioral. The debug widget displays the logfile and provides a python console
        self.setMinimumWidth(1200)#Setting the minimum size of the main user interface
        self.setMinimumHeight(750)
        self.camera=None
        if self.config.ENABLE_CAMERA:
            try:
                self.camera = cv2.VideoCapture(0)#Initialize video capturing
                self.camera.set(3, self.config.CAMERA_FRAME_WIDTH)#Set camera resolution
                self.camera.set(4, self.config.CAMERA_FRAME_HEIGHT)
            except:
                print 'no camera present'
                
        self.camera_reader = QtCore.QTimer()#Timer for periodically reading out the camera
        self.camera_reader.timeout.connect(self.read_camera)#Assigning the function which reads out the camera to this timer
        self.camera_reader.start(int(1000./self.config.CAMERA_UPDATE_RATE))#Setting the update rate of the timer
        #Assign the keyboard hortcuts to functions, more details check the value of HELP variable
        self.connect(QtGui.QShortcut(QtGui.QKeySequence('Ctrl+a'), self), QtCore.SIGNAL('activated()'), self.start_experiment)
        self.connect(QtGui.QShortcut(QtGui.QKeySequence('Ctrl+s'), self), QtCore.SIGNAL('activated()'), self.stop_experiment)
        self.connect(QtGui.QShortcut(QtGui.QKeySequence('Space'), self), QtCore.SIGNAL('activated()'), self.next_protocol)
        #Assigning the folder selection button to the function which pops up the dialog box
        self.connect(self.cw.select_folder, QtCore.SIGNAL('clicked()'), self.select_folder)
        #When the open valve checkbox is toggled, the toggle_value function is called
        self.connect(self.cw.open_valve.input, QtCore.SIGNAL('stateChanged(int)'),  self.toggle_valve)
        #Assigning start and stop buttons with the corresponding functions
        self.connect(self.cw.start, QtCore.SIGNAL('clicked()'), self.start_experiment)
        self.connect(self.cw.stop, QtCore.SIGNAL('clicked()'), self.stop_experiment)
        self.output_folder = self.config.DATA_FOLDER
        self.cursor_t = QtCore.QTimer()#Timer for periodically checking mouse cursor position
        self.cursor_t.timeout.connect(self.cursor_handler)#Assign it to cursor_handler function
        self.cursor_t.start(int(1000.*self.config.CURSOR_POSITION_UPDATE_PERIOD))#Start timer with the right period time
        self.screen_width = self.qt_app.desktop().screenGeometry().width()#Read the screens's size. This will be used for resetting cursor position
        self.screen_height = self.qt_app.desktop().screenGeometry().height()
        self.screen_left=int(self.screen_width*self.config.CURSOR_RESET_POSITION)#When the cursor is left from this position it is set to the right side
        self.screen_right=int((1-self.config.CURSOR_RESET_POSITION)*self.screen_width)-1#When the cursor is right from this position it is set to the left side
        nparams=5#time, position, speed, reward, stim
        self.empty=numpy.empty((nparams,0))#Empty array for resetting other arrays
        self.hwcommand=Queue.Queue()#creating queue for controlling and reading the hardware handler thread
        self.hwresponse=Queue.Queue()
        self.hwh=HardwareHandler(self.hwcommand,self.hwresponse, self.config)#Initialize hardware handler thread (controls valve and stimulus)
        self.hwh.start()#Starting the thread
        self.framequeue=multiprocessing.Queue()#Queue for sending video frames for the frame saver
        self.framesaver=FrameSaver(self.framequeue)#Create frame saver process
        self.framesaver.start()#Start the process
        self.video_counter=0
        self.frame_counter=0
        self.filesaver_q=multiprocessing.Queue()
        self.filesaver=FileSaver(self.filesaver_q)
        self.filesaver.start()
        #Initialize state variables:
        self.stim_state=0#0 when no stimulus is presented, 1 when LED1 and 2 when LED2 is on
        self.valve_state=False#True when valve is open
        self.running=False#True when session is running
        
    def toggle_valve(self,state):
        '''
        Opens/closes the valve depending on the state of the checkbox
        '''
        if state==2:
            self.hwcommand.put(['open_valve'])#Sending the "open_valve" command via the command queue to the hardware handler thread
        elif state == 0:
            self.hwcommand.put(['close_valve'])
        
    def read_camera(self):
        '''
        Reads the camera periiodically, displays the image and sends it to the frame saver process when a session is running
        '''
        if self.camera is None:
            return
        ret, frame = self.camera.read()#Reading the raw frame from the camera
        if frame is None:
            return
        frame_color_corrected=numpy.zeros_like(frame)#For some reason we need to rearrange the color channels
        frame_color_corrected[:,:,0]=frame[:,:,2]
        frame_color_corrected[:,:,1]=frame[:,:,1]
        frame_color_corrected[:,:,2]=frame[:,:,0]
        
        if hasattr(frame_color_corrected, 'shape'):
            self.image.set_image(numpy.rot90(frame_color_corrected,3),alpha=1.0)#Setting the image with correct colors on the user interface. A 90 degree rotation is necessary
            if self.running:#If the experiment is running...
                self.frame_times.append(time.time())#... the time of image acquisition is saved
                #self.frames.append(frame_color_corrected)#Saving the frame to the memory (might not be necessary)
                if self.cw.save_data.input.checkState()==2:#If the data save checkbox is checked...
                    #... The image and the filename of the image file is sent via a queue to the frame saver. The images are saved to a temporary folder
                    self.framequeue.put([copy.deepcopy(frame_color_corrected), os.path.join(self.frame_folder, 'f{0:0=5}.png'.format(self.frame_counter))])
                    self.frame_counter+=1
            
    def _get_new_frame_folder(self):
        self.frame_folder=os.path.join(tempfile.gettempdir(), 'vf_{0}_{1}'.format(self.video_counter,time.time()))#Create temporary folder for video frames
        self.video_counter+=1
        if os.path.exists(self.frame_folder):#If already exists, delete it with its content
            shutil.rmtree(self.frame_folder)
        os.mkdir(self.frame_folder)
        
    def update_counter(self):
        self.cw.counter.setText('rewards {0}, stimuli {1}, stop {2}, punishment {3}'.format(self.reward_counter, self.stimulus_counter, self.stop_counter,self.punishment_counter))
                    
    def start_experiment(self):
        if self.running: return#Do nothing when already running
        self.running=True
        self.checkdata=numpy.copy(self.empty)#checkdata contains the speed values for checking whether the mouse reached run for x seconds or stop for y seconds condition
        self.data=numpy.copy(self.empty)#self.data stores the all the speed, valve state, stimulus state data
        self.frame_times=[]
        self.save_period=float(self.cw.save_period.input.text())
        self.enable_periodic_data_save=self.cw.enable_periodic_data_save.input.checkState()==2
        self.recording_start_time=time.time()
        self.last_save_time=time.time()
        self.data_index=0
        self.frame_counter=0
        self.log('start experiment')
        self._get_new_frame_folder()
        #Protocol specific
        self.run_complete=False
        self.stimulus_fired=False
        self.stop_complete=False
        self.generate_run_time()#Generate the randomized expected runtime for start stop stim protocol
        self.last_reward = 0
        self.punishment=False
        self.punishment_counter =0
        self.reward_counter=0
        self.stimulus_counter=0
        self.stop_counter=0
        self.is_stop=True
        
    def check_recording_save(self):
        if not self.enable_periodic_data_save:return
        now=time.time()
        #Restart is enabled if last reward was within a second or it was a long time ago (20 sec).
        dt=now-self.last_reward
        if now-self.last_save_time>self.save_period and dt>1:# and ((dt<2.0 and dt>0.5) or dt>20):
            self.save_data()
            self._get_new_frame_folder()
            self.last_save_time=now
            self.frame_counter=0
            self.data=numpy.copy(self.empty)
#            if self.data[0,-1]-self.data[0,0]>2*60:
#                index=numpy.where(self.data[0]>self.data[0,-1]-60.0)[0].min()
#                self.data=self.data[:,index:]
#            self.data_index=self.data.shape[1]
            self.reward_counter=0
            self.stimulus_counter=0
            self.stop_counter=0
            #self.stop_experiment()
            #self.start_experiment()
            
        
    def stop_experiment(self):
        if not self.running: return
        self.running=False
        self.log('stop experiment')
        if self.cw.save_data.input.checkState()==2:#If save data checked...
            self.save_data() #... Save all the speeed, valve state, timing, stimulus state and video data to file
        
    def next_protocol(self):
        '''
        When space is pressed, the actual item in the protocol selector combobox is changed
        '''
        if self.running: return#If space is accidentially pressed during experiment, do not change protocol
        next_index = self.cw.select_protocol.input.currentIndex()+1
        if next_index == self.cw.select_protocol.input.count():
            next_index = 0
        self.cw.select_protocol.input.setCurrentIndex(next_index)
        
    def cursor_handler(self):
        '''
        Cursor handler, reads mouse cursor position, calculates speed and calls protocol specific logic
        '''
        if not self.running:
            return
        self.check_recording_save()
        self.cursor_position = QtGui.QCursor.pos().x()#Reading the mouse position (x)
        self.now=time.time()#Save the current time for timestamping later the data
        reset_position=None
        jump=0
        if self.cursor_position<=self.screen_left:#If cursor position is left from the left edge...
            reset_position = self.screen_right# ... set the reset position to the other side
            jump=self.screen_width#this is for  eliminating the effect of the position resetting at the speed calculation
        if self.cursor_position>=self.screen_right:
            reset_position = self.screen_left
            jump=-self.screen_width
        if reset_position is not None:#If reet_position is valid...
            QtGui.QCursor.setPos(reset_position,int(self.screen_height*0.5))#...Setting the cursor to reset position
        if self.data.shape[1]>0:
            ds=self.cursor_position-self.data[1, -1]#movement of x position since the last call of cursor handler
            self.cursor_position+=jump#correct cursor position with jump
            #calculate speed using the pixel2speed conversion factor and the time elapsed since the last call of cursor handler
            speed=self.config.RUN_DIRECTION*ds/(self.now-self.data[0,-1])*self.config.PIXEL2SPEED
        else:
            speed=0#At the first call of cursor handler the previous cursor position is not known
        #collect all the data to one array: time, cursor position, speed, valve state, stimulus state
        newdata=numpy.array([[self.now, self.cursor_position,speed,int(self.valve_state),int(self.stim_state)]]).T
        self.data = numpy.append(self.data, newdata,axis=1)#Append it to data
        self.checkdata = numpy.append(self.checkdata, newdata,axis=1)#Append newdata to the checkdata where the protocol handlers will look for srun/stop events
        t=self.data[0]-self.data[0,0]#Relative time values for the x axis of the plot
        #Plot speed, valve state and stimulus state on the user interface
        self.cw.plotw.update_curves([t,t,t], [self.data[2],self.data[3]*self.data[2].max(),self.data[4]*self.data[2].max()], colors=[(0,0,0),(0,255,0),(0,0,255)])
        self.cw.plotw.plot.setXRange(min(t), max(t))#Set the x range of plot
        #Call the protocol handler which value is taken from protocol selection combox
        getattr(self, str(self.cw.select_protocol.input.currentText()).lower())()
        #Check stim and valve states:
        if not self.hwresponse.empty():
            resp=self.hwresponse.get()#If there is a stim ready message...
            if resp=='stim ready':
                self.stim_state=0#...set the stim_state to 0
            elif resp == 'reward ready':#Same for valve state
                self.valve_state=False
        self.is_stopped()
        self.update_counter()
        
    def is_stopped(self):
        if self.checkdata.shape[1]==0: return
        if self.checkdata[0,-1]-self.checkdata[0,0]>self.config.STOP_TIME:
            speed=numpy.where(self.checkdata[2]>self.config.MOVE_THRESHOLD,1,0)#speed mask 1s: above threshold
            t=self.checkdata[0]-self.checkdata[0,0]#Time is shifted to 0
            #Calculate index for last 2*stoptime duration
            t0index=numpy.where(t>t.max()-(self.config.STOP_TIME))[0].min()
            #Calculate index for last stoptime duration
            index=numpy.where(t>t.max()-self.config.STOP_TIME)[0].min()
            stop_speed=speed[index:]#...and the stop part
            stop=stop_speed.sum()==0#All elements of the stop part shall be below threshold
            if self.is_stop!=stop:
                self.is_stop=stop
                if stop:
                    self.stop_counter+=1
        
    def stop_reward(self):
        '''
        Stop reward protocol handler
        '''
        #If time recorded into checkdata is bigger than run time and stop time ...
        if self.checkdata[0,-1]-self.checkdata[0,0]>self.config.PROTOCOL_STOP_REWARD['run time']+self.config.PROTOCOL_STOP_REWARD['stop time']:
            speed=numpy.where(self.checkdata[2]>self.config.MOVE_THRESHOLD,1,0)#speed mask 1s: above threshold
            t=self.checkdata[0]-self.checkdata[0,0]#Time is shifted to 0
            #Calculate index for last runtime +stoptime duration
            t0index=numpy.where(t>t.max()-(self.config.PROTOCOL_STOP_REWARD['run time']+self.config.PROTOCOL_STOP_REWARD['stop time']))[0].min()
            #Calculate index for last stoptime duration
            index=numpy.where(t>t.max()-self.config.PROTOCOL_STOP_REWARD['stop time'])[0].min()
            run_speed=speed[t0index:index]#using these indexes, take out running part ...
            stop_speed=speed[index:]#...and the stop part
            run=run_speed.sum()>self.config.RUN_THRESHOLD*run_speed.shape[0]#Decide wheather at the run part was the speed above thershold
            stop=stop_speed.sum()==0#All elements of the stop part shall be below threshold
            if run and stop:#If both conditions are met ...
                self.reward()#... give reward and...
                self.checkdata=numpy.copy(self.empty)#Reset checkdata
    
    def stim_stop_reward(self):
        '''
        Stim stop protocol handler
        '''
        #Run the protocol handler is checkdata has at least self.actual_runtime duration
        if self.checkdata[0,-1]-self.checkdata[0,0]>self.actual_runtime:
            speed=numpy.where(self.checkdata[2]>self.config.MOVE_THRESHOLD,1,0)#speeds above threshold are marked with 1s
            t=self.checkdata[0]-self.checkdata[0,0]
            index=numpy.where(t>t.max()-self.actual_runtime)[0].min()#calculate index of last actual_runtime duration
            run_speed=speed[index:]#cut this section out of speed vector
            run=run_speed.sum()>self.config.RUN_THRESHOLD*run_speed.shape[0]#decide if the mouse was really running
            if run and not self.run_complete:#If mouse was really running and we consider the run part uncompleted...
                self.run_complete=True#... then mark this with completed. This is necessary for firing the stimulus only once and detect if the mouse stops running afterwards
            if self.run_complete:
                if not self.stimulus_fired:#If stimulus not yet fired but run part is completed by mouse...
                    self.mouse_run_complete=self.now
                    if self.config.PROTOCOL_STIM_STOP_REWARD['stimulus till stop']:
                        self.stim_on()
                    else:
                        self.stimulate()#... present stimulus
                    self.stimulus_fired=True
                else:#If stimulus was fired, ...
                    index=numpy.where(t>t.max()-self.config.PROTOCOL_STIM_STOP_REWARD['stop time'])[0].min()#... we look back for the last "stop time" duration
                    stop_speed=speed[index:]#Cut out this part from the speed vector
                    self.stop_complete = stop_speed.sum()==0#Check if the mouse was really stopped
                    if self.now-self.mouse_run_complete>self.config.PROTOCOL_STIM_STOP_REWARD['delay after run']+self.config.PROTOCOL_STIM_STOP_REWARD['stop time'] and not self.stop_complete:
                        #Timeout, start from the beginning if time elapsed since the run complete event is bigger than "delay after run" and "stop time" (expected time to stay stopped"
                        self.log('no reward')
                        if self.config.PROTOCOL_STIM_STOP_REWARD['stimulus till stop']:
                            self.stim_off()
                        self.run_complete=False#Reset all the state variables
                        self.stimulus_fired=False
                        self.checkdata=numpy.copy(self.empty)
                        self.generate_run_time()#generate a new randomized runtime 
                    elif self.stop_complete:
                        self.reward()#If mouse stopped afterthe run complete for a certain amount of time, reward is given
                        if self.config.PROTOCOL_STIM_STOP_REWARD['stimulus till stop']:
                            self.stim_off()
                        self.run_complete=False#Reset state variables
                        self.stimulus_fired=False
                        self.checkdata=numpy.copy(self.empty)
                        self.generate_run_time()#generate a new randomized runtime 
                        
    def keep_running_reward(self):
        '''
        If mouse is running for at least 10 seconds and the last reward was given 10 sec ago
        '''
        if self.checkdata[0,-1]-self.checkdata[0,0]>self.config.PROTOCOL_KEEP_RUNNING_REWARD['run time']:
            t=self.checkdata[0]-self.checkdata[0,0]#Time is shifted to 0
            t0index=numpy.where(t>t.max()-self.config.PROTOCOL_KEEP_RUNNING_REWARD['run time'])[0].min()
            ismoving=numpy.where(self.checkdata[2]>self.config.MOVE_THRESHOLD,1,0)[t0index:]
            run=ismoving.sum()>self.config.RUN_THRESHOLD*ismoving.shape[0]#Decide wheather at the run part was the speed above thershold
            if run and self.checkdata[0,-1]-self.last_reward>=self.config.PROTOCOL_KEEP_RUNNING_REWARD['run time']:
                self.reward()#... give reward and...
                self.checkdata=numpy.copy(self.empty)#Reset checkdata
                
    def keep_stop_reward(self):
        if not hasattr(self, 'keep_stop_time'):
            self.reward_period=self.config.PROTOCOL_KEEP_STOP_REWARD['reward period']
        speed=numpy.where(abs(self.checkdata[2])>self.config.MOVE_THRESHOLD,1,0)#speed mask 1s: above threshold
        if speed.sum()>0:
            if self.punishment:
                self.punishment_start_time=time.time()
                self.checkdata=numpy.copy(self.empty)    
            else:
                self.log('Start of water deprivation');
                self.punishment = True
                self.punishment_counter+=1
                self.punishment_start_time=time.time()
                self.checkdata=numpy.copy(self.empty)  
        else:
            if self.punishment:
                if time.time()-self.punishment_start_time>self.config.PROTOCOL_KEEP_STOP_REWARD['punishment time']:
                    self.punishment = False
                    self.log('End of water deprivation')
            else:
                if self.checkdata[0,-1]-self.checkdata[0,0]>self.reward_period:
                    speed=numpy.where(self.checkdata[2]>self.config.MOVE_THRESHOLD,1,0)#speed mask 1s: above threshold
                    t=self.checkdata[0]-self.checkdata[0,0]#Time is shifted to 0
                    #Calculate index for last stoptime duration
                    index=numpy.where(t>t.max()-self.reward_period)[0].min()
                    stop_speed=speed[index:]#...and the stop part
                    stop=stop_speed.sum()==0#All elements of the stop part shall be below threshold
                    if stop:
                        self.reward()#... give reward and...
                        self.checkdata=numpy.copy(self.empty)#Reset checkdata
        
#        if not self.punishment:#punishment is a certain period of time while no reward is given
#            if self.checkdata[0,-1]-self.checkdata[0,0]>self.reward_period:
#                speed=numpy.where(self.checkdata[2]>self.config.MOVE_THRESHOLD,1,0)#speed mask 1s: above threshold
#                t=self.checkdata[0]-self.checkdata[0,0]#Time is shifted to 0
#                #Calculate index for last stoptime duration
#                index=numpy.where(t>t.max()-self.reward_period)[0].min()
#                stop_speed=speed[index:]#...and the stop part
#                stop=stop_speed.sum()==0#All elements of the stop part shall be below threshold
#                if stop:
#                    self.reward()#... give reward and...
#                    self.checkdata=numpy.copy(self.empty)#Reset checkdata
#                else:
#                    self.log('Start of water deprivation');
#                    self.punishment = True
#                    self.punishment_counter+=1
#                    self.punishment_start_time=time.time()
#                    self.checkdata=numpy.copy(self.empty)    
#        else:
#            speed=numpy.where(self.checkdata[2]>self.config.MOVE_THRESHOLD,1,0)#speed mask 1s: above threshold
#            if speed.sum()>0:
#                self.punishment_start_time=time.time()
#                self.checkdata=numpy.copy(self.empty)    
#            if time.time()-self.punishment_start_time>self.config.PROTOCOL_KEEP_STOP_REWARD['punishment time']:
#                self.punishment = False
#                self.log('End of water deprivation');
        
                        
    def generate_run_time(self):
        '''
        Stim stop protocol expected runtime has a random part that needs to be recalculated
        
        The random part is between 0...'stimulus time range' and has its values are generated in 'stimulus time resolution' steps
        The random part i added to the "run time"
        '''
        if str(self.cw.select_protocol.input.currentText()).upper()=='STIM_STOP_REWARD':
            random_time=self.config.PROTOCOL_STIM_STOP_REWARD['stimulus time resolution']*int(random.random()*self.config.PROTOCOL_STIM_STOP_REWARD['stimulus time range']/self.config.PROTOCOL_STIM_STOP_REWARD['stimulus time resolution'])
            self.actual_runtime = self.config.PROTOCOL_STIM_STOP_REWARD['run time']+random_time
        
    def _parse_stim_power_and_channel(self):
        try:
            power=map(float, str(self.cw.stim_power.input.text()).split(','))#read power intensity values from user interface
        except:
            import traceback
            self.log(traceback.format_exc())
        if self.config.POWER_VOLTAGE_RANGE[0]>power[0] and self.config.POWER_VOLTAGE_RANGE[1]<power[0]\
            or self.config.POWER_VOLTAGE_RANGE[0]>power[1] and self.config.POWER_VOLTAGE_RANGE[1]<power[1]:
            #Check if the provided value falls into the expected range, otherwise give warning
            self.log('stimulus intensity shall be within this range: {0}'.format(self.config.POWER_VOLTAGE_RANGE))
            power=[0,0]
        channel = random.choice(range(self.config.PROTOCOL_STIM_STOP_REWARD['n stimulus channels']))#Make a random choice from the two stimulus channels
        return power, channel
        
    def stimulate(self):
        power, channel = self._parse_stim_power_and_channel()
        self.hwcommand.put(['stimulate', power[channel], self.config.STIM_CHANNELS[channel]])#Send command to hardware handler to generate stimulation
        self.stim_state=channel+1#Stim state is 0 when no stimulus is shown, otherwise the id of the stimulus channel
        self.log('stim at channel {0}'.format(self.stim_state))
        self.stimulus_counter+=1
        
    def stim_on(self):
        power, channel = self._parse_stim_power_and_channel()
        self.hwcommand.put(['stim on', power[channel], self.config.STIM_CHANNELS[channel]])#Send command to hardware handler to generate stimulation
        self.stim_state=channel+1#Stim state is 0 when no stimulus is shown, otherwise the id of the stimulus channel
        self.log('stim on at channel {0}'.format(self.stim_state))
        self.stimulus_counter+=1
        
    def stim_off(self):
        power, channel = self._parse_stim_power_and_channel()
        self.hwcommand.put(['stim off', 0, self.config.STIM_CHANNELS[self.stim_state-1]])
        self.stim_state=0
        self.log('stim off at channel {0}'.format(self.stim_state))
        
    def reward(self):
        self.hwcommand.put(['reward'])#hardware handler is notified to generate reward 
        self.valve_state=True
        self.log('reward')
        self.last_reward=time.time()
        self.reward_counter+=1
        
    def save_data(self):
        '''
        Save all the recorded data to a mat file and generate a video file from the captured frames
        '''
        #Filename containts the protocol name and the date
        filename=os.path.join(self.output_folder, '{1}_{0}.mat'.format(utils.timestamp2ymdhms(time.time()).replace(':', '-').replace(' ', '_'),str(self.cw.select_protocol.input.currentText()).lower()))
        #Aggregating the data to be saved
        data2save={}
        self.data_index=0
        data2save['time']=self.data[0,self.data_index:]
        data2save['position']=self.data[1,self.data_index:]
        data2save['speed']=self.data[2,self.data_index:]
        data2save['reward']=self.data[3,self.data_index:]
        data2save['stim']=self.data[4,self.data_index:]
        #configuration values are also saved
        data2save['config']=[(vn, getattr(self.config,vn)) for vn in dir(self.config) if vn.isupper()]
        data2save['frametime']=self.frame_times[self.data_index:]
        data2save['reward_counter']=self.reward_counter
        data2save['stimulus_counter']=self.stimulus_counter
        data2save['stop_counter']=self.stop_counter
        self.log('Video capture frame rate was {0}'.format(1/numpy.diff(self.frame_times).mean()))
        self.log('Saving data to {0}, saving video to {1}'.format(filename,filename.replace('.mat','.mp4')))
        self.filesaver_q.put((filename, data2save, self.frame_folder if self.config.ENABLE_CAMERA else None,  self.config.CAMERA_UPDATE_RATE))
        
    def select_folder(self):
        #Pop up a dialog asking the user for folder selection
        self.output_folder=self.ask4foldername('Select output folder', self.output_folder)
        self.cw.selected_folder.setText(self.output_folder)

    def closeEvent(self, e):
        #When the user interface is closed the following procedure is preformed
        if hasattr(self.camera,'release'):
            self.camera.release()#Stop camera operation
        self.hwcommand.put(['terminate'])#Terminate hardware handler thread
        e.accept()
        self.hwh.join()#Wait till thread ends
        self.framequeue.put('terminate')#Terminate frame saver process and ...
        self.framesaver.join()#Wait until it terminates
        self.filesaver_q.put('terminate')
        self.filesaver.join()

class UltrasoundSetup(Config):
    def init_setup_specific_parameters(self):
        self.VALVE_PIN=7
        self.ARDUINO_BASED_DIO=True
        self.PROTOCOL_KEEP_STOP_REWARD={}
        self.PROTOCOL_KEEP_STOP_REWARD['reward period']=20#sec
        self.PROTOCOL_KEEP_STOP_REWARD['punishment time']=30#sec
        self.PROTOCOL_KEEP_STOP_REWARD['reward period increment']=0#sec
        self.PROTOCOL_KEEP_STOP_REWARD['max reward perdion']=3600.0#sec
        self.ENABLE_CAMERA=False

class BehavioralSetup(Config):
    def init_setup_specific_parameters(self):
        self.PROTOCOL_STOP_REWARD={}
        self.PROTOCOL_STOP_REWARD['run time']=10#sec
        self.PROTOCOL_STOP_REWARD['stop time']=self.STOP_TIME#sec
        
        self.PROTOCOL_STIM_STOP_REWARD={}
        self.PROTOCOL_STIM_STOP_REWARD['run time']=5#sec
        self.PROTOCOL_STIM_STOP_REWARD['stop time']=self.STOP_TIME#sec
        self.PROTOCOL_STIM_STOP_REWARD['stimulus time range']=10#sec
        self.PROTOCOL_STIM_STOP_REWARD['stimulus time resolution']=0.5#sec
        self.PROTOCOL_STIM_STOP_REWARD['delay after run']=5#sec equivalent to flash time. After run condition is fulfilled and led is turned on, the mouse is expected to stop...
        #...If it does not happen in this time (5sec) stim is turned off and the software generates a new random duration and the mouse is expected to run for this duration ...
        self.PROTOCOL_STIM_STOP_REWARD['n stimulus channels'] = 1
        self.PROTOCOL_STIM_STOP_REWARD['stimulus till stop'] = True
        
        self.PROTOCOL_KEEP_RUNNING_REWARD={}
        self.PROTOCOL_KEEP_RUNNING_REWARD['run time']=15.0


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
        tsr=TreadmillSpeedReader(q,self.machine_config,emulate_speed=True)
        tsr.start()
        time.sleep(rectime)
        q.put('terminate')
        tsr.join()
        samples=[]
        while not tsr.speed_q.empty():
            samples.append(tsr.speed_q.get())
        self.assertEqual(numpy.array(samples).shape[0], rectime/self.machine_config.TREADMILL_SPEED_UPDATE_RATE-1)
        

if __name__ == '__main__':
    if len(sys.argv)>1:
        gui = Behavioral()
    else:
        unittest.main()
