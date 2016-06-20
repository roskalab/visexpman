import random,logging,time,numpy
from visexpman.engine.vision_experiment.experiment import Protocol
    
class FearResponse(Protocol):
    '''
    Superclass for training for and measuring fear response
    
    Trigger timing is defined relative to the start of the save period
    
    file = "samples/sample.wav"

        winsound.PlaySound(
            file,
            winsound.SND_FILENAME|winsound.SND_NOWAIT,
    )
    
    '''
    ENABLE_AIRPUFF=True
    ENABLE_AUDITORY_STIMULUS=False
    ENABLE_VISUAL_STIMULUS=False
    STIMULUS_REPETITIONS=20
    STIMULUS_DURATION=1.0
    PAUSE_BETWEEN_STIMULUS_REPETITIONS=1.0
    TRIGGER_TIME_MIN=15
    TRIGGER_TIME_MAX=25
    NTRIGGERS=5
    ENABLE_IMAGING_SOURCE_CAMERA=True
    def reset(self):
        #self.trigger_times=numpy.arange(self.NTRIGGERS)*self.PAUSE_BETWEEN_TRIGGERS+self.FIRST_TRIGGER_TIME
        self.trigger_times=numpy.round(numpy.random.random(self.NTRIGGERS)*(self.TRIGGER_TIME_MAX-self.TRIGGER_TIME_MIN)+self.TRIGGER_TIME_MIN,0).cumsum()
        logging.info('Trigger times: {0}'.format(self.trigger_times))
        self.trigger_index=0
        
    def update(self):
        index=self.engine.recording_started_state['speed_values']
        if self.engine.speed_values.shape[0]>index:
            elapsed_time=time.time()-self.engine.speed_values[index,0]
            if self.trigger_times.shape[0]>self.trigger_index and elapsed_time>=self.trigger_times[self.trigger_index]:
                self.trigger_index+=1
                if self.ENABLE_AIRPUFF:
                    self.engine.airpuff()
                if self.ENABLE_AUDITORY_STIMULUS:
                    self.engine.auditory_stimulus(self.STIMULUS_REPETITIONS)
                if self.ENABLE_VISUAL_STIMULUS:
                    fsample=self.engine.machine_config.STIM_SAMPLE_RATE
                    waveform=numpy.tile(numpy.concatenate(
                            (numpy.zeros(0.5*self.PAUSE_BETWEEN_STIMULUS_REPETITIONS*fsample), 
                            numpy.ones(self.STIMULUS_DURATION*fsample), 
                            numpy.zeros(0.5*self.PAUSE_BETWEEN_STIMULUS_REPETITIONS*fsample)
                            )),self.STIMULUS_REPETITIONS)
                    self.engine.stimulate(waveform)
                    
class FearAirpuffLaser(FearResponse):
    __doc__=FearResponse.__doc__
    ENABLE_AIRPUFF=True
    ENABLE_AUDITORY_STIMULUS=False
    ENABLE_VISUAL_STIMULUS=True
    STIMULUS_REPETITIONS=20
    STIMULUS_DURATION=1.0
    PAUSE_BETWEEN_STIMULUS_REPETITIONS=1.0
    
class FearLaserOnly(FearResponse):
    __doc__=FearResponse.__doc__
    ENABLE_AIRPUFF=False
    ENABLE_AUDITORY_STIMULUS=False
    ENABLE_VISUAL_STIMULUS=True
    STIMULUS_REPETITIONS=20
    STIMULUS_DURATION=1.0
    PAUSE_BETWEEN_STIMULUS_REPETITIONS=1.0
    
class FearAuditoryOnly(FearResponse):
    __doc__=FearResponse.__doc__
    ENABLE_AIRPUFF=True
    ENABLE_AUDITORY_STIMULUS=False
    ENABLE_VISUAL_STIMULUS=False
    
    def reset(self):
        FearResponse.reset(self)
        logging.warning('!!! Make sure that compressed air is closed !!!')

    
class KeepStopReward(Protocol):
    '''
        self.PROTOCOL_KEEP_STOP_REWARD['reward period']=20#sec
        self.PROTOCOL_KEEP_STOP_REWARD['punishment time']=30#sec
        self.PROTOCOL_KEEP_STOP_REWARD['reward period increment']=0#sec
        self.PROTOCOL_KEEP_STOP_REWARD['max reward perdion']=3600.0#sec
        
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

    '''

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
            if not hasattr(self.engine, 'recording_started_state'):
                index=0
            else:
                index=self.engine.recording_started_state['speed_values']
                index = index-1 if index>0 else index
            tlast=self.last_update if hasattr(self, 'last_update') else self.engine.speed_values[-1,0]
            elapsed_time=tlast-self.engine.speed_values[index,0]
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
        
class ForcedKeepRunningRewardLevel1(ForcedKeepRunningReward):
    __doc__=ForcedKeepRunningReward.__doc__
    RUN_TIME=3.0
    STOP_TIME=6.5
    RUN_FORCE_TIME = 3.0
    
class ForcedKeepRunningRewardLevel2(ForcedKeepRunningReward):
    __doc__=ForcedKeepRunningReward.__doc__
    RUN_TIME=6.0
    STOP_TIME=6.5
    RUN_FORCE_TIME = 6.0
                
class ForcedKeepRunningRewardLevel3(ForcedKeepRunningReward):
    __doc__=ForcedKeepRunningReward.__doc__
    RUN_TIME=10.0
    STOP_TIME=6.5
    RUN_FORCE_TIME = 5.0

        
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
        
class StopRewardLevel2(StopReward):
    __doc__=StopReward.__doc__
    STOP_TIME=1.0

class StimStopReward(Protocol):
    '''
    If a run event occurs, turn on stimulus. Wait for stop event which should occur within DELAY_AFTER_RUN.
    If stop event does not happen, turn off stimulus and generate next randomized run time and wait for next run time
    If stop event takes place turn off stimulus, give reward and generate next randomized run time
    
    Randomized runtime:
    RUN_TIME+a random number between 0 and RANDOM_TIME_RANGE in RANDOM_TIME_STEPs
    '''
    DELAY_AFTER_RUN=2.0
    RUN_TIME=10.0
    STOP_TIME=1.0
    RANDOM_TIME_RANGE=10.0
    RANDOM_TIME_STEP=0.5
    def reset(self):
        self.engine.run_time=self.generate_runtime()
        self.engine.run_times.append(self.engine.run_time)
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
        
