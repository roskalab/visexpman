#TODO: low volt/high/mid voltage?? volt instead of all voltage values
#TODO: color assignment
from pylab import *
import hdf5io,unittest,numpy,os,multiprocessing,pdb
from visexpman.engine.vision_experiment import experiment_data
from visexpman.engine.generic import introspect,fileop,utils,signal
from scipy.ndimage.filters import gaussian_filter
import skvideo.io,skimage.transform
import scipy.ndimage


def read_frame(filename,index):
    if 0:
        ct=0
        reader= skvideo.io.vreader(filename)
        for frame in reader:
            if ct==index:
                captured=numpy.copy(frame)
                break
            ct+=1
        reader.close()
        return captured
    else:
        import cv2
        video=cv2.VideoCapture(filename)
        video.set(cv2.CAP_PROP_POS_FRAMES,index)
        ret,frame=video.read()
        video.release()
        capt=numpy.copy(frame)
        return capt

def align_videos(video1_fn,video2_fn,sync_fn):
    h=hdf5io.Hdf5io(sync_fn)
    fsample=h.findvar('machine_config')['SYNC_RECORDER_SAMPLE_RATE']
    try:
        teyeindex= h.findvar('machine_config')['TEYECAM_SYNC_INDEX']
    except KeyError:
        teyeindex=3
    sync=h.findvar('sync')
    inscopix_timestamps=signal.trigger_indexes(sync[:,h.findvar('machine_config')['TNVISTA_SYNC_INDEX']])[1::2]/fsample
    behavioral_timestamps=signal.trigger_indexes(sync[:,h.findvar('machine_config')['TBEHAV_SYNC_INDEX']])[1::2]/fsample
    eyecam_timestamps=signal.trigger_indexes(sync[:,teyeindex])[1::2]/fsample
    #Align eye camera and behavioral timestamps with inscopix timestamps
    indexes=[]
    for i in range(inscopix_timestamps.shape[0]-1):
        ts=inscopix_timestamps[i]
        te=inscopix_timestamps[i+1]
        behav_indexes=[ii for ii in range(behavioral_timestamps.shape[0]) if ts<behavioral_timestamps[ii]<te]
        eyecam_indexes=[ii for ii in range(eyecam_timestamps.shape[0]) if ts<eyecam_timestamps[ii]<te]
        indexes.append([behav_indexes,eyecam_indexes])
        pass
    #Resample videos:
    fns=[[video1_fn,video1_fn.replace('.mp4', '_resampled.mp4')], [video2_fn,video2_fn.replace('.mp4', '_resampled.mp4')]]
    for videoi in [0,1]:
        if os.path.exists(fns[videoi][1]):
            os.remove(fns[videoi][1])
        video_writer= skvideo.io.FFmpegWriter(fns[videoi][1])
        prev_frame=numpy.zeros(skvideo.io.vread(fns[videoi][0],num_frames=1).shape[1:])
        for i in indexes:
            print(videoi,i[videoi])
            if len(i[videoi])>0:
                prev_frame=read_frame(fns[videoi][0],i[videoi][0])
            video_writer.writeFrame(prev_frame)
        video_writer.close()
        
        
    h.close()

def align_videos_wrapper(fn):
    fnid=fn.split('_')[-1].split('.')[0]
    files=fileop.listdir(os.path.dirname(fn))
    vfn1=[f for f in files if fnid in f and 'behav' in os.path.basename(f) and '.mp4' in f][0]
    vfn2=[f for f in files if fnid in f and 'eye' in os.path.basename(f) and '.mp4' in f][0]
    align_videos(vfn1,vfn2,fn)
    return vfn1, vfn2

def extract_eyeblink(filename, baseline_length=0.5,blink_duration=0.5,threshold=0.01, debug=False, annotation=None):
    '''
    Ceiling light is reflected on mice eyeball which results a significantly bright area. When eyes are
    closed, this area turns to dark, this is used for detecting if eyeblink happened after an airpuff
    '''
    h=hdf5io.Hdf5io(filename)
    h.load('ic_frames')
    h.load('ic_timestamps')
    h.load('airpuff_values')
    frames=h.ic_frames
    h.close()
    std=frames.std(axis=0)
    std_range=std.max()-std.min()
    activity=(numpy.where(std>std_range*0.75,1,0)*frames).mean(axis=1).mean(axis=1)
    activity=gaussian_filter(activity,2)
    activity_t=h.ic_timestamps[:,0]
    if h.airpuff_values.shape[0]==0:
        return
    airpuff_t=h.airpuff_values[:,0]
    airpuff= h.airpuff_values[:,1]
    is_blinked=[]
    for rep in range(airpuff.shape[0]):
        t0=airpuff_t[rep]
        baseline=activity[numpy.where(numpy.logical_and(activity_t<t0,activity_t>t0-baseline_length))[0]].mean()
        eye_closed=activity[numpy.where(numpy.logical_and(activity_t>t0,activity_t<t0+blink_duration))[0]].mean()
        is_blinked.append(True if baseline-eye_closed>threshold else False)
        if debug:
            outfolder='/tmp/out'
            tmin=t0-1
            tmax=t0+5
            indexes1=numpy.where(numpy.logical_and(activity_t>tmin, activity_t<tmax))[0]
            indexes2=numpy.where(numpy.logical_and(airpuff_t>tmin, airpuff_t<tmax))[0]
            clf()
            cla()
            plot(activity_t[indexes1]-t0, activity[indexes1])
            plot(airpuff_t[indexes2]-t0, airpuff[indexes2]*0.05,'o')
            if annotation!=None:
                annot=annotation[os.path.basename(filename)]
                indexes3=numpy.where(numpy.logical_and(activity_t[annot]>tmin, activity_t[annot]<tmax))[0]
                if indexes3.shape[0]>0:
                    indexes3=numpy.array(annot)[indexes3]
                    plot(activity_t[indexes3]-t0, numpy.ones_like(activity_t[indexes3])*0.06, 'o')
            ylim([0,0.1])
            title(is_blinked[-1])
            savefig(os.path.join(outfolder, '{0}_{1}.png'.format(os.path.basename(filename),rep)),dpi=200)
    return airpuff_t, airpuff, numpy.array(is_blinked), activity_t, activity
    
class ProcessBehavioralData(object):
    '''
    Expects a folder where same day recordings reside. Stim
    '''
    def __init__(self,folder,protocol):
        self.protocol=protocol
        self.experiment_date=os.path.basename(folder)
        self.animal_id=os.path.basename(os.path.dirname(folder))
        self.files=[os.path.join(folder,f) for f in os.listdir(folder) if os.path.splitext(f)[1]=='.hdf5' and protocol in f]
        ids=[os.path.splitext(os.path.basename(f))[0].split('_')[-1] for f in self.files]
        ids.sort()
        self.files=[[f for f in self.files if i in os.path.basename(f)][0] for i in ids]        
        self.process()
        
    def concatenate(self):
        h=hdf5io.Hdf5io(self.files[0])
        varnames=[v for v in dir(h.h5f.root) if v[0]!='_' and v[-7:] == '_values']
        for vn in varnames:
            setattr(self, vn, numpy.empty((0,2)))
        self.laser_values=numpy.empty((0,2))
        h.close()
        for f in self.files:
            h=hdf5io.Hdf5io(f)
            for vn in varnames:
                h.load(vn)
                if getattr(h,vn).shape[0]>0:
                    #Check if timeseries is continous
                    old=getattr(self,vn)
                    new=getattr(h,vn)
                    if old.shape[0]>0 and new.shape[0]>0:
                        if old[-1,0]>new[0,0]:
                            raise RuntimeError('{0} is improperly concatenated'.format(vn))
                    setattr(self, vn, numpy.concatenate((old, new)))
            h.load('parameters')
            laser_values=numpy.copy(h.stimulus_values)
            if laser_values.shape[0]!=0:
                laser_values[:,1]=h.parameters['Laser Intensity']
                self.laser_values=numpy.concatenate((self.laser_values,laser_values))
            h.close()
        
    def process(self):
        self.concatenate()
        getattr(self, 'process_' + self.protocol)()
            
    def process_StimStopReward(self):
        speed_window=1.0
        first_n_stims=3
        stimonoff_times=self.stimulus_values[numpy.where(self.stimulus_values[:,1]==1)[0],0]
        if stimonoff_times.shape[0]==0:
            return
        stimon=stimonoff_times[::2]
        stimoff=stimonoff_times[1::2]
        t=self.speed_values[:,0]
        speed=self.speed_values[:,1]
        speed_pre_post=[]
        laser_volt_prev=0
        stim_counter=0
        for stim_i in range(stimon.shape[0]):
            pre=numpy.where(numpy.logical_and(t<stimon[stim_i],t>stimon[stim_i]-speed_window))[0]
            post=numpy.where(numpy.logical_and(t>stimoff[stim_i],t<stimoff[stim_i]+speed_window))[0]
            speed_pre=speed[pre].mean()
            speed_post=speed[post].mean()
            speed_post= speed_post if speed_post>0 else 0
            speed_pre= speed_pre if speed_pre>0 else 0
            if speed_pre==0:
                print(speed_pre)
                speed_change=0
            else:
                speed_change=(speed_post-speed_pre)/speed_pre
            if numpy.isnan(speed_change) or numpy.isinf(speed_change):
                continue
            #Columns: time, pre, post, change, voltage
            laser_volt=self.laser_values[numpy.where(self.laser_values[:,0]==stimon[stim_i])[0]][0,1]
            if laser_volt_prev!=laser_volt and laser_volt_prev!=0:
                stim_counter=0
            else:
                stim_counter+=1
            import copy
            laser_volt_prev=copy.deepcopy(laser_volt)
            if stim_counter<first_n_stims:
                speed_pre_post.append([(stimon[stim_i]+stimoff[stim_i])/2, speed_pre,speed_post,speed_change, laser_volt])
        self.speed_change_pre_post=numpy.array(speed_pre_post)
        fs=7
        rcParams['font.size']=fs
        cla()
        clf()
        subplot(2,2,1)
        ms=3
        plot(self.speed_change_pre_post[:,0]-self.speed_values[0,0],self.speed_change_pre_post[:,1], '-o',markersize=ms)
        plot(self.speed_change_pre_post[:,0]-self.speed_values[0,0],self.speed_change_pre_post[:,2], '-o',markersize=ms)
        legend(['pre stim', 'post stim'], loc=0,fontsize='xx-small')
        xlabel('time [s]')
        ylabel('speed [m/s]')
        subplot(2,2,2)
        plot(self.speed_change_pre_post[:,0]-self.speed_values[0,0],self.speed_change_pre_post[:,4], '-o',markersize=ms)
        xlabel('time [s]')
        ylabel('laser [V]')
        #group speeds by voltage
        voltages=list(set(self.speed_change_pre_post[:,4]))
        voltages.sort()
        subplot(2,2,3)
        plot(self.speed_change_pre_post[:,4],self.speed_change_pre_post[:,1], '.')
        plot(self.speed_change_pre_post[:,4],self.speed_change_pre_post[:,2], '.')
        ylabel('speed [m/s]')
        xlabel('laser [V]')
        xlim([min(voltages)-0.1, max(voltages)+0.1])
        legend(['pre stim', 'post stim'], loc=0,fontsize='xx-small')
        subplot(2,2,4)
        changes=self.speed_change_pre_post[:,3]
        plot(self.speed_change_pre_post[:,4],self.speed_change_pre_post[:,3], '.')
        means=[self.speed_change_pre_post[numpy.where(self.speed_change_pre_post[:,4]==v)[0],3].mean() for v in voltages]
        n=[self.speed_change_pre_post[numpy.where(self.speed_change_pre_post[:,4]==v)[0],3].shape[0] for v in voltages]
        plot(voltages,means, 'r_',markersize=20)
        ylabel('speed change [PU]')
        xlabel('laser [V]')
        xlim([min(voltages)-0.1, max(voltages)+0.1])
        ylim([min(changes)-0.1,max(changes)+0.1])
        title('n={0}'.format(n),fontdict={'fontsize':fs})
        suptitle('{0}  {1}  speed window {2:0.0f} s'.format(self.animal_id, self.experiment_date, speed_window))
        savefig('/tmp/{0}_{1}.png'.format(self.animal_id, self.experiment_date), dpi=300)
        self.speed_change_vs_voltage=self.speed_change_pre_post[:,-2:]
        
def process_all(folder):
    #Generate experiment day/mouse id pairs with corresponding folder
    animal_folders=[os.path.dirname(f) for f in fileop.find_files_and_folders(folder)[1] if 'animal' in os.path.basename(f)]
    animal_folders.sort()
    animals={}    
    bp=[('m1_noP', 'LE', '20160803')]
    for animal_folder in animal_folders:
        animal_name=os.path.basename(animal_folder)
        if 'LE' in animal_name or 'RE' in animal_name:
            allfiles=fileop.find_files_and_folders(animal_folder)[1]
            days=list(set([os.path.dirname(f) for f in allfiles if os.path.splitext(f)[1]=='.hdf5' and 'StimStopReward' in os.path.basename(f)]))
            days.sort()
            eye='LE' if 'LE' in animal_name else 'RE'
            sig=(animal_name.replace('_LE','').replace('_RE',''),eye)
            if len(days)>0:
                animals[sig]=days
    aggregated={}
    aggregated_mean={}
    for sig in animals.keys():
        for day in animals[sig]:
            signew=(sig[0], sig[1], os.path.basename(day))
            print(signew)
            #if signew not in bp:continue
            p=ProcessBehavioralData(day,'StimStopReward')
            if hasattr(p, 'speed_change_vs_voltage'):
                aggregated[signew]=p.speed_change_vs_voltage
                aggregated_mean[signew]=numpy.array([[v, aggregated[signew][numpy.where(aggregated[signew]==v)[0],0].mean()] for v in list(set(aggregated[signew][:,1]))])
            else:
                print('ignored')
    numpy.save('/tmp/aggregated.npy', utils.object2array(aggregated))
    numpy.save('/tmp/aggregated_mean.npy', utils.object2array(aggregated_mean))
#TODO: nan in mean, ignore raw speed change value if it is nan
def plot_aggregated():
    aggregated_raw=utils.array2object(numpy.load('/tmp/aggregated.npy'))
    aggregated_mean=utils.array2object(numpy.load('/tmp/aggregated_mean.npy'))
    #Select best animal
    #1. select last two days
    animals = list(set([a[0] for a in aggregated_mean.keys()]))
    ranks={}
    for aref in animals:
        values=numpy.concatenate(tuple([val for sig, val in aggregated_mean.items() if sig[0]==aref]))
        values=numpy.array([v for v in values if not any(numpy.isnan(v))])
        ranks[values[numpy.where(values[:,0]==values[:,0].min())[0],1].min()]=aref
    #Select the 10 lowest ranks
    r=ranks.keys()
    r.sort()
    selected_ranks=r[:10]
    best_animals=[ranks[s] for s in selected_ranks]
        
    
    aggregated=aggregated_raw
    fs=10
    rcParams['font.size']=fs
    cla()
    clf()
    
    sides=['LE', 'RE']
    
    datatype_ct=0
    
        
    ct=1
    avg=True
    aggregate_per_voltage={}
    selected_sigs=[]
    for e in sides:
        figure(1)
        #Find out maximal number of days
        ndays=0#process only last 2 days
        animals=list(set([a[0] for a in aggregated.keys()]))
        #animals=best_animals
        for a in animals:
            [sig for sig in aggregated.keys() if sig[0]==a and sig[1]==e]
            ndays=max(ndays, len([sig[2] for sig in aggregated.keys() if sig[0]==a and sig[1]==e]))
        ndays=2
        for d in range(ndays):
            #identify last dth day's signature
            sigs=[]
            subplot(2,ndays,ct)
            ct+=1
            sigagg=(e,-d)
            aggregate_per_voltage[sigagg]=[]
            for a in animals:
                days=[sig[2] for sig in aggregated.keys() if sig[0]==a and sig[1]==e]
                days.sort()
                if len(days)==0 or len(days)<=d: continue
                current_day=days[-(d+1)]
                current_sig=(a,e,current_day)
                voltages=list(set(aggregated[current_sig][:,1]))
                if avg:
                    speed_changes=aggregated[current_sig][:,0]
                    voltage_trace=aggregated[current_sig][:,1]
                    means=[speed_changes[numpy.where(voltage_trace==v)[0]].mean() for v in voltages]
                    plot(voltages,means, '.')
                else:
                    plot(aggregated[current_sig][:,1],aggregated[current_sig][:,0], '.')
#                    v=aggregated[current_sig][:,1]
#                    sc=aggregated[current_sig][:,0]
#                    aggregate_per_voltage[sigagg].extend([[v[i], sc[i]] for i in range(len(v))])
                
                ylabel('speed change [PU]')
                xlabel('laser [V]')
                xlim([min(voltages)-0.1, max(voltages)+0.1])
                #ylim([-2,2])
                title('day {0}, {1}'.format(-d,e),fontdict={'fontsize':fs})
    #figure(2)
    ct=0
#    for sig in aggregate_per_voltage.keys():
#        ct+=1
#        subplot(2,ndays,ct)
#        points=numpy.array(aggregate_per_voltage[sig])
#        voltages=list(set(points[:,0]))
#        voltages.sort()
#        means=[points[numpy.where(points[:,0]==v)[0],1].mean() for v in voltages]
#        plot(voltages, means)
#        ylabel('speed change [PU]')
#        xlabel('laser [V]')
#        xlim([min(voltages)-0.1, max(voltages)+0.1])
#        ylim([-2,2])
#        title(sig,fontdict={'fontsize':fs})
#            
#        pass
    

                
    show()
    
def lick_detection_folder(folder,fsample,lick_wait_time,threshold=0.25,max_width=0.1,min_width=0.01,mean_threshold=0.07):
    fns=[os.path.join(folder,f) for f in os.listdir(folder) if 'hdf5' in f and 'lick' in f.lower()]
    fns.sort()
    default_pars=[fsample,lick_wait_time,threshold,max_width,min_width,mean_threshold]
    pars=[]
    for f in fns:
        try:
            h=hdf5io.Hdf5io(f)
            h.load('sync')
            lick=h.sync[:,0]
            stimulus=h.sync[:,2]
            h.close()
            pi=[lick,stimulus]
            pi.extend(default_pars)
            pars.append(tuple(pi))
        except:
            pass
    ids=[experiment_data.id2timestamp(experiment_data.parse_recording_filename(f)['id']) for f in fns]
    p=multiprocessing.Pool(introspect.get_available_process_cores())
    res=list(map(lick_detection_wrapper,pars))
    output=[[ids[i], res[i][0],res[i][1], res[i][2]] for i in range(len(res))]
    return output
        
def lick_detection_wrapper(pars):
    lick,stim,lick_wait_time,fsample,threshold,max_width,min_width,mean_threshold=pars
    res=lick_detection(lick,stim,lick_wait_time,fsample,threshold,max_width,min_width,mean_threshold)
    return res
    
def lick_detection(lick,stimulus,fsample,lick_wait_time,threshold=0.25,max_width=0.1,min_width=0.01,mean_threshold=0.07):
    '''
    max_width=100 (0.1s)
    min_width=100 (0.01s)
    threshold=0.25V
    mean_threshold=0.07V
    '''
    indexes=numpy.nonzero(numpy.diff(numpy.where(lick>threshold,1,0)))[0]
    edge_distances=numpy.diff(indexes)
    pulse_start_indexes=numpy.where(numpy.logical_and(edge_distances<max_width*fsample, edge_distances>min_width*fsample))[0]
    pulse_start=indexes[pulse_start_indexes]
    pulse_end=indexes[pulse_start_indexes+1]
    keep_pulse_indexes=numpy.where(lick[pulse_start+(pulse_end-pulse_start)/2]>threshold)[0]
    pulse_start=pulse_start[keep_pulse_indexes]
    pulse_end=pulse_end[keep_pulse_indexes]
    if lick.mean()>mean_threshold:
        pulse_end=numpy.array([])
        pulse_start=numpy.array([])
    
    #Valid pulse is where next edge is within width_range
    #Filter indexes
    
    widths=pulse_end-pulse_start
    events=numpy.zeros_like(lick)
    if pulse_start.shape[0]>0:
        events[pulse_start]=1
    lick_times=pulse_start/float(fsample)
    stim_events=signal.trigger_indexes(stimulus)
    if stim_events.shape[0]>1:
        stimulus_end=stim_events[1]/float(fsample)
        successful_indexes=numpy.where(numpy.logical_and(lick_times>stimulus_end,lick_times<stimulus_end+lick_wait_time))[0]
        successful_lick_times=lick_times[successful_indexes]
    else:
        successful_lick_times=numpy.array([])
    return events,lick_times,successful_lick_times,stim_events/float(fsample)
    
    
#    h.close()
    
class LickSummary(object):
    def __init__(self, folder, n):
        self.read_data(folder)
        self.select_best(n)
        
    def read_data(self,folder):
        days=[fn for fn in os.listdir(folder) if os.path.isdir(os.path.join(folder, fn))]
        self.data={}
        self.latency={}
        for d in days:
            files=[os.path.join(folder, d, f) for f in os.listdir(os.path.join(folder, d)) if os.path.splitext(f)[1]=='.hdf5' and 'LickResponse' in f]
            self.data[d]={}
            self.latency[d]=[]
            for f in files:
                h=hdf5io.Hdf5io(f)
                [h.load(vn) for vn in ['stat','sync','machine_config','protocol','parameters']]
                if hasattr(h, 'stat') and h.stat!=None:
                    t=experiment_data.id2timestamp(experiment_data.parse_recording_filename(f)['id'])
                    lick=h.sync[:,0]
                    stimulus=h.sync[:,2]
                    events,lick_times,successful_lick_times,stim_events=lick_detection(lick,stimulus,
                                h.machine_config['AI_SAMPLE_RATE'],
                                h.protocol['LICK_WAIT_TIME'],
                                h.parameters['Voltage Threshold'],
                                h.parameters['Max Lick Duration'],
                                h.parameters['Min Lick Duration'],
                                h.parameters['Mean Voltage Threshold'])
                    h.stat['latency']=(successful_lick_times[0]-stim_events[1]) if successful_lick_times.shape[0]>0 else numpy.inf
                    self.latency[d].extend(list(lick_times-stim_events[0]))
                    import copy
                    self.data[d][t]=copy.deepcopy(h.stat)
                h.close()
                
    def select_best(self,n):
        n=int(n)
        self.best={}
        for d in self.data.keys():
            timestamps=self.data[d].keys()
            timestamps.sort()
            timestamps=numpy.array(timestamps)
            latency=numpy.array([self.data[d][ti]['latency'] for ti in timestamps])
            if n==0:
                successful_indexes=numpy.array([i for i in range(latency.shape[0]) if latency[i] !=numpy.inf])
                print(successful_indexes)
                if successful_indexes.shape[0]>0:
                    best_latencies=latency[successful_indexes]*1000
                    best_licks=numpy.array([[self.data[d][i]['Number of licks'], self.data[d][i]['Successful licks']] for i in timestamps[successful_indexes]])
                    self.best[d]={'latency': best_latencies, 'licks':best_licks}
            else:
                if all(numpy.isinf(latency)):
                    continue
                else:
                    best_index=numpy.array([latency[li:li+n].sum() for li in range(latency.shape[0]-n)]).argmin()
                    indexes=numpy.arange(best_index,best_index+n)
                    best_latencies=latency[indexes]*1000
                    if numpy.inf in best_latencies: 
                        indexes=numpy.array([i for i in range(best_latencies.shape[0]) if best_latencies[i]!=numpy.inf])+best_index
                        best_latencies=numpy.array([bl for bl in best_latencies if bl!=numpy.inf])
                    best_licks=numpy.array([[self.data[d][i]['Number of licks'], self.data[d][i]['Successful licks']] for i in timestamps[best_index:best_index+n]])
                self.best[d]={'latency': best_latencies, 'licks':best_licks}
        pass    
        
def check_hitmiss_files(filename):
    '''
    Check:
        1) measured durations are realistic
        2) Sync recording length is realistic
    '''
    if os.path.isdir(filename):
        files=[f for f in fileop.listdir_fullpath(filename) if os.path.splitext(f)[1]=='.hdf5']
    else:
        files=[filename]
    for f in files:
        if len(files)>1:
            print(f)
        ishitmiss='hitmiss' in os.path.basename(filename).split('_')[1].lower()
        h=hdf5io.Hdf5io(f)
        list(map(h.load, ['sync', 'machine_config',  'parameters', 'protocol', 'stat']))
        recording_duration=h.sync.shape[0]/float(h.machine_config['AI_SAMPLE_RATE'])
        protocol_duration=h.protocol['PRETRIAL_DURATION']
        h.stat=utils.array2object(h.stat)
        if h.stat['result']:
            protocol_duration+=h.protocol['DRINK_TIME']+h.protocol['REWARD_DELAY']
        else:
            protocol_duration+=h.protocol['RESPONSE_WINDOW']
        if protocol_duration>recording_duration:
            raise RuntimeError('protocol_duration duration ({0}) is longer than sync recording duration ({1})'.format(protocol_duration, recording_duration))
        dt=200e-3
        if 0:
            reward=h.sync[:, 0]
            stimulus=h.sync[:, 2]
            lick=h.sync[:, 3]
            protocol_state=h.sync[:, 4]
            plot(protocol_state+5);plot(stimulus);plot(reward);plot(lick);show()
        if abs(h.stat[ 'pretrial_duration'] - h.protocol['PRETRIAL_DURATION'])>dt:
            raise RuntimeError('Pretrial duration is measured to {0}, expected: {1}'.format(h.stat[ 'pretrial_duration'], h.protocol['PRETRIAL_DURATION']))
        
        if ishitmiss and h.stat['result'] and abs(h.stat['reward_delay']-(h.protocol['REWARD_DELAY']))>dt:
                if abs((h.stat[ 'reward_delay']-h.stat['lick_latency'])-h.protocol['REWARD_DELAY'])>dt:#Lick happens during stimulus
                    from visexpman.engine.hardware_interface import lick_detector
                    s,lt,pst=lick_detector.detect_events(h.sync,5000)
                    raise RuntimeError('Reward delay is measured to {0}, expected: {1}'.format(h.stat[ 'reward_delay'], h.protocol['REWARD_DELAY']+0*h.stat[ 'lick_latency']))
        if h.stat['result'] and abs(h.stat[ 'drink_time']-h.protocol['DRINK_TIME'])>dt:
            raise RuntimeError('Reward delay is measured to {0}, expected: {1}'.format(h.stat[ 'drink_time'], h.protocol['DRINK_TIME']))
        if ishitmiss and not h.stat['result'] and abs(h.stat['response_window']-h.protocol['RESPONSE_WINDOW'])>dt:
            raise RuntimeError('Response window is measured to {0}, expected: {1}'.format(h.stat['response_window'], h.protocol['RESPONSE_WINDOW']))
        h.close()
        
class HitmissAnalysis(object):
    '''
    Analysis type decided on subfolders in input folder:
        Day analyis:
            number of flashes,number of hits, success rate
            lick times histogram
        Animal analysis:
            success rate per day
            lick latency histogram for all days
        Multiple animals:
            aggregate success rate at each day to a single plot, different curve for each animal
    '''
    def __init__(self,folder,histogram_bin_time=20e-3, protocol='HitMiss', filter={}):
        self.protocol=protocol
        self.folder=folder
        self.filter=filter
        self.histogram_bin_time=histogram_bin_time*1e3
        items_in_folder=[f for f in fileop.listdir_fullpath(folder) if os.path.splitext(f)[1]=='.hdf5' or os.path.isdir(f)]
        nsubfolders=len([f for f in items_in_folder if os.path.isdir(f)])
        nitems=len(items_in_folder)
        nfiles=nitems-nsubfolders
        if nfiles==nitems:
            self.analysis_type='day'
            self.day_analysis()
        elif nfiles==1:
            self.analysis_type='animal'
            self.animal_analysis()
        elif nsubfolders==nitems:
            self.analysis_type='all'
            self.all_animals()
        else:
            raise RuntimeError('Unknown analysis, nfiles: {0}, nitems: {1}, nsubfolders: {2}, folder: {3}'.format(nfiles, nitems, nsubfolders, self.folder))
        
    def day_analysis(self,folder=None, filter=None):
        if isinstance(folder,str) and os.path.exists(folder):
            self.alldatafiles=[f for f in fileop.find_files_and_folders(folder)[1] if os.path.splitext(f)[1]=='.hdf5']
        else:
            self.alldatafiles=[f for f in fileop.find_files_and_folders(self.folder)[1] if os.path.splitext(f)[1]=='.hdf5']
        self.lick_latencies=[]
        self.reward_latencies=[]
        self.nsuccesfullicks=0
        self.nhits=0
        self.nflashes=0
        self.lick_times=[]
        for f in self.alldatafiles:
            try:
                if os.path.basename(f).split('_')[1]!=self.protocol: 
                     continue
                h=hdf5io.Hdf5io(f)
                stat=h.findvar('stat')
                if 'stimulus_t' not in stat:
                    h.close()
                    continue
                    sync=h.findvar('sync')
                    machine_config=h.findvar('machine_config')
                    from visexpman.engine.hardware_interface import lick_detector
                    stat=lick_detector.detect_events(sync,machine_config['AI_SAMPLE_RATE'])[0]
                    h.stat=stat
                    h.save('stat')
                if 'voltage' in self.filter and h.findvar('protocol')['LASER_INTENSITY'] != self.filter['voltage']:
                    h.close()
                    continue
                self.nflashes+=1
                h.close()
                self.nhits+=stat['result']
                self.nsuccesfullicks+=stat['lick_result']
                if 'lick_latency' in stat:
                    self.lick_latencies.append(stat['lick_latency']*1000)
                if 'reward_latency' in stat:
                    self.reward_latencies.append(stat['reward_latency']*1000)
                self.lick_times.extend((1000*(stat['lick_times']-stat['stimulus_t'][0])).tolist())
            except:
                import logging, traceback
                logging.info(f)
                logging.error(traceback.format_exc())
        self.lick_latencies=numpy.array(list(map(int,self.lick_latencies)))
        self.reward_latencies=numpy.array(list(map(int,self.reward_latencies)))
        self.lick_times=numpy.array(list(map(int,self.lick_times)))
        if self.nflashes==0:
            self.success_rate=0
            self.lick_success_rate=0
        else:
            self.success_rate=self.nhits/float(self.nflashes)
            self.lick_success_rate=self.nsuccesfullicks/float(self.nflashes)            
        return self.lick_times,self.lick_latencies,self.reward_latencies,self.nflashes,self.nhits,self.success_rate,self.lick_success_rate
        
    def add2day_analysis(self,filename):
        stat=utils.array2object(hdf5io.read_item(filename,'stat'))
        self.nhits+=stat['result']
        self.nflashes+=1
        self.success_rate=self.nhits/float(self.nflashes)
        if 'lick_latency' in stat:
            numpy.append(self.lick_latencies,stat['lick_latency']*1000)
        self.lick_times=numpy.concatenate((self.lick_times,numpy.cast['int'](stat['lick_times']*1000)))
        
    def animal_analysis(self, animal_name=None):
        '''
        data for plot 1: success rate vs day
        data for plot 2: lick latency histogram
        data for plot 3: lick time histogram for each day
        '''
        if animal_name==None:
            animal_folder=self.folder
        else:
            animal_folder=os.path.join(self.folder,animal_name)
        self.days=[os.path.basename(f) for f in fileop.listdir_fullpath(animal_folder) if os.path.isdir(f)]
        self.days.sort()
        lick_times_histogram={}
        lick_latency_histogram={}
        reward_latency_histogram={}
        success_rates=[]
        lick_success_rates=[]
        self.aggregated={}
        for d in self.days:
            lick_times,lick_latencies,reward_latencies,nflashes,nhits,success_rate,lick_success_rate = self.day_analysis(os.path.join(animal_folder,d))
            self.aggregated[d]={}
            self.aggregated[d]['lick_latencies']=lick_latencies
            self.aggregated[d]['reward_latencies']=reward_latencies
            self.aggregated[d]['lick_times']=lick_times
            lick_times_histogram[d]=lick_times
            lick_latency_histogram[d]=lick_latencies
            reward_latency_histogram[d]=reward_latencies
            success_rates.append(success_rate)
            lick_success_rates.append(lick_success_rate)
        success_rates=numpy.array(success_rates)
        lick_success_rates=numpy.array(lick_success_rates)
        lick_times_histogram=self.generate_histogram(lick_times_histogram)
        lick_latency_histogram=self.generate_histogram(lick_latency_histogram)
        reward_latency_histogram=self.generate_histogram(reward_latency_histogram)
        self.success_rates=success_rates
        self.lick_success_rates=lick_success_rates
        self.lick_times_histogram=lick_times_histogram
        self.lick_latency_histogram=lick_latency_histogram
        self.reward_latency_histogram=reward_latency_histogram
        return self.days, success_rates, self.lick_success_rates, lick_times_histogram,lick_latency_histogram
        
    def generate_histogram(self,data):
        try:
            values=numpy.concatenate(data.values())
        except ValueError:
            return None,None
        if values.shape[0]==0:
            return None,None
        bins=numpy.arange(values.min(),values.max(),self.histogram_bin_time)
        hist={}
        for k,v in data.items():
            if bins.shape[0]==1:
                hist[k]=numpy.array([v.shape[0]])
            elif bins.shape[0]==0:
                hist[k]=numpy.array([0])
            else:
                hist[k]=numpy.histogram(v,bins)[0]
        if bins.shape[0]>1:
            bins=bins[:-1]
        return bins,hist
        
    def all_animals(self):
        animals=os.listdir(self.folder)
        animal_success_rate={}
        for animal in animals:
            days, success_rates, lick_success_rates, lick_times_histogram,lick_latency_histogram = self.animal_analysis(animal)
            animal_success_rate[animal]=[days,success_rates]
        self.animal_success_rate=animal_success_rate
        return animal_success_rate
        
def extract_mouse_position(im, channel,threshold=100):
    from pylab import imshow,show
    import scipy.ndimage.measurements
    #green channel seems the best for extracting brightest white point.
#    from skimage.filters import threshold_otsu
    green=im[:,:,channel]
#    th=threshold_otsu(green)
    mask=numpy.where(green>threshold,1,0)
    if 0:
        #Find biggest object
        l,n=scipy.ndimage.measurements.label(mask)
        if n==0:
            return
        biggest_object=numpy.array([numpy.where(l==i)[0].shape[0] for i in range(1,n+1)]).argmax()+1
        mask=numpy.where(l==biggest_object,1,0)
        
    
    x,y=numpy.nonzero(mask)
    return x.mean(), y.mean()
    
def mouse_head_direction(image, threshold=80,  roi_size=20, saturation_threshold=0.6, value_threshold=0.4, debug=False, dim_red=False, old_version=False):
    #image[:, :100]=0#Mask bright side
    from skimage.color import rgb2hsv
    result=True
    #Clear watermark which is used for video integrity check
    image[0, 0]=0
    image[0, 1]=0
    try:
        if old_version:#Old method
            coo=numpy.array([int(c.mean()) for c in numpy.where(image.sum(axis=2)>3*threshold)])
        else:
            hsvim=rgb2hsv(image)
            sv=numpy.where(hsvim[:, :, 1]>saturation_threshold, 1, 0)*numpy.where(hsvim[:, :, 2]>0.1, 1, 0)
            coo=numpy.nonzero(signal.find_biggest_object(sv))
            coo=numpy.cast['int'](numpy.array(coo).mean(axis=1))
    except ValueError:#Image too dim
        result=False
        animal_position=numpy.array([numpy.NaN, numpy.NaN])
        red=numpy.array([numpy.NaN, numpy.NaN])
        green=numpy.array([numpy.NaN, numpy.NaN])
        blue=numpy.array([numpy.NaN, numpy.NaN])
        red_angle=numpy.NaN
        return result, animal_position, red_angle, red, green, blue, None, (numpy.nan, numpy.nan, numpy.nan)
    #Cut roi and detect red and green dots
    startx=coo[0]-roi_size
    starty=coo[1]-roi_size
    endx=coo[0]+roi_size
    endy=coo[1]+roi_size
    if startx<0:
        startx=0
    if starty<0:
        starty=0
    if endx>image.shape[0]-1:
        endx=image.shape[0]-1
    if endy>image.shape[1]-1:
        endy=image.shape[1]-1
    roirgb=image[startx: endx, starty: endy, :]
    if roirgb.max()<threshold and 0:
        #Assuming that bright non-led objects are present
        #Search for red/green/blue objects on entire image
        hsvim=rgb2hsv(image)
        sv=numpy.where(hsvim[:, :, 1]>saturation_threshold, 1, 0)*numpy.where(hsvim[:, :, 2]>0.1, 1, 0)
        coo=numpy.nonzero(signal.find_biggest_object(sv))
    roi=rgb2hsv(roirgb)
    if 0:
        roi=rgb2hsv(image)
        roi_size=0
        coo*=0
    roi[:,:,1]*=numpy.where(roi[:,:,2]>value_threshold,1,0)#Set saturation to 0 where value is low -> exclude these pixels from color detection
    animal_position=numpy.zeros(2)
    led_ct=0
    color_tolerance=0.15
    try:
        if not dim_red:
            green=numpy.array([int(c.mean()) for c in numpy.where(numpy.logical_and(abs(roi[:, :, 0]-0.333)<color_tolerance, roi[:, :, 1]>saturation_threshold))])
        else:
            green=numpy.array([int(c.mean()) for c in numpy.where(numpy.logical_and(abs(roi[:, :, 0]-0.333)<color_tolerance, roi[:, :, 2]>0.1))])
    
        green+=coo-roi_size
        animal_position+=green
        led_ct+=1
    except:
        green=numpy.array([numpy.NaN, numpy.NaN])
        result=False
        
    try:
        blue= numpy.array([int(c.mean()) for c in numpy.where(roirgb[:,:,2]>threshold)])
        blue+=coo-roi_size
        animal_position+=blue
        led_ct+=1
    except:
        blue=numpy.array([numpy.NaN, numpy.NaN])
        result=False
    try:
        if not dim_red:
            red=numpy.array([int(c.mean()) for c in numpy.where(numpy.logical_and(numpy.logical_or(roi[:, :, 0]<color_tolerance,  roi[:, :, 0]>1-color_tolerance), roi[:, :, 1]>saturation_threshold))])
        else:#Allow dim red
            red=numpy.array([int(c.mean()) for c in numpy.where(numpy.logical_and(numpy.logical_or(roi[:, :, 0]<color_tolerance,  roi[:, :, 0]>1-color_tolerance), roi[:, :, 2]>0.1))])#Detect dim red light
        red+=coo-roi_size
        animal_position+=red
        led_ct+=1
    except:
        red=numpy.array([numpy.NaN, numpy.NaN])
        result=False
    
    if numpy.isnan(red).all():
        red_angle=numpy.degrees(numpy.arctan2(*(blue-green)))-90
        if red_angle<-180:
            red_angle+=360
        result=True
    elif numpy.isnan(green).all():
        red_angle=numpy.degrees(numpy.arctan2(*(blue-red)))
        result=True
    elif numpy.isnan(blue).all():
        red_angle=numpy.degrees(numpy.arctan2(*(green-red)))
        result=True
    else:
        red_angle=numpy.degrees(numpy.arctan2(*(-0.5*(blue-green)+blue-red)))
        result=True
    red2_angle=numpy.degrees(numpy.arctan2(*(blue-green)))
    green_angle=numpy.degrees(numpy.arctan2(*(blue-red)))
    blue_angle=numpy.degrees(numpy.arctan2(*(green-red)))
        
    if led_ct==0:
        animal_position=numpy.array([numpy.NaN, numpy.NaN])
    else:
        animal_position=numpy.cast['int']((animal_position)/float(led_ct))
    if debug:
        img=numpy.rollaxis(numpy.array(3*[numpy.copy(image.sum(axis=2)/3)]), 0, 3)
        if not numpy.isnan(animal_position).any():
            for i in range(-2, 3):
                img[animal_position[0]+i,  animal_position[1], :]=255
                img[animal_position[0],  animal_position[1]+i, :]=255
        if not numpy.isnan(red).any():
            for i in range(-2, 3):
                img[red[0]+i,  red[1], 0]=255
                img[red[0],  red[1]+i, 0]=255
                img[red[0]+i,  red[1], 1:2]=0
                img[red[0],  red[1]+i, 1:2]=0
        if not numpy.isnan(blue).any():
            for i in range(-2, 3):
                img[blue[0], blue[1]+i, 2]=255
                img[blue[0]+i, blue[1], 2]=255
                img[blue[0]+i, blue[1], 0:1]=0
                img[blue[0], blue[1]+i, 0:1]=0
        if not numpy.isnan(green).any():
            for i in range(-2, 3):
                img[green[0]+i, green[1], 1]=255
                img[green[0], green[1]+i, 1]=255
                img[green[0], green[1]+i, 0]=0
                img[green[0]+i, green[1], 0]=0
                img[green[0], green[1]+i, 2]=0
                img[green[0]+i, green[1], 2]=0
        out=numpy.zeros((img.shape[0],  img.shape[1]*2, 3), dtype=numpy.uint8)
        out[:, :img.shape[1],  :]=image
        out[:, -img.shape[1]:,  :]=img
    else:
        out=None
    if 0:
        from PIL import Image, ImageDraw, ImageFont
        font = ImageFont.truetype("arial", 10)
        out=image[coo[0]-roi_size: coo[0]+roi_size, coo[1]-roi_size: coo[1]+roi_size, :]
        img=Image.fromarray(numpy.cast['uint8'](out))
        draw = ImageDraw.Draw(img)
        draw.text((0, 0),"{0}".format(int(red_angle)),(255,255,255),font=font)
        out=numpy.asarray(img)
#    if numpy.isnan(red_angle):
#        pdb.set_trace()

    return result, animal_position, red_angle, red, green, blue, out,  (red2_angle, green_angle, blue_angle)
    
def find_objects(frame,min_size,threshold=40):
    if frame.ndim==3:
        frame=frame[:,:,0]
    l,n=scipy.ndimage.label(numpy.where(frame>threshold,1.0,0.0))
    if n==0:
        return []
    else:
        objects=[]
        for i in range(1,n+1):
            coo=numpy.array(numpy.where(l==i))
            size=coo.shape[1]
            if size<min_size:
                continue
            coo=coo.mean(axis=1)
            objects.append([coo,size])
    return objects
    
def head_angle_ir(frame,min_size,threshold=40):
    objects=find_objects(frame,min_size,threshold)
    angle=numpy.nan
    if len(objects)==2:
        bigger=objects[numpy.array([ii[1] for ii in objects]).argmax()][0]
        smaller=objects[numpy.array([ii[1] for ii in objects]).argmin()][0]
        angle=numpy.degrees(numpy.arctan2(*(bigger-smaller)))
    return angle
    
def ir_angle(bigger, smaller,prev_angle):
    angle=numpy.degrees(numpy.arctan2(*(bigger-smaller)))
    dangle=angle-prev_angle
    dangle=(dangle+180)%360-180
    if abs(dangle)>120:
        angle=numpy.degrees(numpy.arctan2(*(smaller-bigger)))
    return angle
    
def track_led_objects(frame, objects_prev, angle_prev,min_size=20,threshold=40):
    objects=find_objects(frame,min_size,threshold)
    angle=numpy.nan
    if len(objects)>0:
        if len(objects)==1 and len(objects_prev)==0:
            pass
        elif len(objects)==2:
            bigger=objects[numpy.array([ii[1] for ii in objects]).argmax()][0]
            smaller=objects[numpy.array([ii[1] for ii in objects]).argmin()][0]
            if (bigger==smaller).all():
                bigger=objects[0][0]
                smaller=objects[1][0]
            angle=ir_angle(bigger, smaller,angle_prev)
        elif len(objects_prev)==2 and len(objects)==1:
            #Use previous values
            bigger_prev=objects_prev[numpy.array([ii[1] for ii in objects_prev]).argmax()][0]
            smaller_prev=objects_prev[numpy.array([ii[1] for ii in objects_prev]).argmin()][0]
            if (bigger_prev==smaller_prev).all():
                bigger_prev=objects_prev[0][0]
                smaller_prev=objects_prev[1][0]
            angle=ir_angle(bigger_prev, smaller_prev,angle_prev)
        else:
            if len(objects_prev)==2:
                #Need to match previous 2 objects to actual ones
                bigger_prev=objects_prev[numpy.array([ii[1] for ii in objects_prev]).argmax()][0]
                smaller_prev=objects_prev[numpy.array([ii[1] for ii in objects_prev]).argmin()][0]
                if (bigger_prev==smaller_prev).all():
                    bigger_prev=objects_prev[0][0]
                    smaller_prev=objects_prev[1][0]
                #Find the closest to the previous
                bigger_index=numpy.sqrt(((numpy.array([ii[0] for ii in objects])-bigger_prev)**2).sum(axis=1)).argmin()
                remaining_objects=[objects[ii] for ii in range(len(objects)) if ii!=bigger_index]
                smaller_index=numpy.sqrt(((numpy.array([ii[0] for ii in remaining_objects])-smaller_prev)**2).sum(axis=1)).argmin()
                bigger=objects[bigger_index][0]
                smaller=remaining_objects[smaller_index][0]
                #Eliminate extra objects
                objects=[objects[bigger_index],remaining_objects[smaller_index]]
                angle=ir_angle(bigger, smaller,angle_prev)
            elif len(objects_prev)!=2:
                pass
            else:
                pass
    else:
        pass#No LED detected
    return angle, objects
    
def track_ir_leds(fn,min_size=20,close_threshold=10):
    vv=skvideo.io.vread(fn)[:,:,:,0]
    if 1:
        videogen = skvideo.io.vreader(fn)
        objects=[]
        for frame in videogen:
            #frame=frame[200:400,100:600,0]
            objects.append(find_objects(frame,min_size))
        utils.object2npy(objects,'/tmp/o.npy')
    else:
        objects=utils.npy2object('/tmp/o.npy')
#    bigger=[]
#    smaller=[]
    angles=[numpy.nan]
    delta_angle=[]
    for i in range(len(objects)):
        angles.append(numpy.nan)
        if len(objects[i])>0:
            if len(objects[i])==1 and len(objects[i-1])==0:
                continue
            elif len(objects[i])==2:
                bigger=objects[i][numpy.array([ii[1] for ii in objects[i]]).argmax()][0]
                smaller=objects[i][numpy.array([ii[1] for ii in objects[i]]).argmin()][0]
                if (bigger==smaller).all():
                    bigger=objects[i][0][0]
                    smaller=objects[i][1][0]
                angles[-1]=ir_angle(bigger, smaller,angles[-2])
            elif len(objects[i-1])==2 and len(objects[i])==1:
                #Use previous values
                bigger_prev=objects[i-1][numpy.array([ii[1] for ii in objects[i-1]]).argmax()][0]
                smaller_prev=objects[i-1][numpy.array([ii[1] for ii in objects[i-1]]).argmin()][0]
                if (bigger_prev==smaller_prev).all():
                    bigger_prev=objects[i-1][0][0]
                    smaller_prev=objects[i-1][1][0]
                angles[-1]=ir_angle(bigger_prev, smaller_prev,angles[-2])
            else:
                if i>1 and len(objects[i-1])==2:
                    #Need to match previous 2 objects to actual ones
                    bigger_prev=objects[i-1][numpy.array([ii[1] for ii in objects[i-1]]).argmax()][0]
                    smaller_prev=objects[i-1][numpy.array([ii[1] for ii in objects[i-1]]).argmin()][0]
                    if (bigger_prev==smaller_prev).all():
                        bigger_prev=objects[i-1][0][0]
                        smaller_prev=objects[i-1][1][0]
                    #Find the closest to the previous
                    bigger_index=numpy.sqrt(((numpy.array([ii[0] for ii in objects[i]])-bigger_prev)**2).sum(axis=1)).argmin()
                    remaining_objects=[objects[i][ii] for ii in range(len(objects[i])) if ii!=bigger_index]
                    smaller_index=numpy.sqrt(((numpy.array([ii[0] for ii in remaining_objects])-smaller_prev)**2).sum(axis=1)).argmin()
                    bigger=objects[i][bigger_index][0]
                    smaller=remaining_objects[smaller_index][0]
                    #Eliminate extra objects
                    objects[i]=[objects[i][bigger_index],remaining_objects[smaller_index]]
                    angles[-1]=ir_angle(bigger, smaller,angles[-2])
                elif i>1 and len(objects[i-1])!=2:
                    pass
                else:
                    pass
        else:
            pass#No LED detected
        dangle=angles[-1]-angles[-2]
        if abs(dangle)>160:
            if numpy.sign(angles[-1]) == 1 and numpy.sign(angles[-2]) == -1:
                dangle-=360
            else:
                dangle+=360
        if abs(dangle)>50:
            pass
        delta_angle.append(dangle)
    ol=[[i,len(objects[i]),len(objects[i-1])] for i in range(1,len(objects)) if numpy.isnan(angles[i+1])]
    print(len([i for i in angles if numpy.isnan(i)]),len(objects))
    plot(delta_angle);show()
    return angles
        

class TestBehavAnalysis(unittest.TestCase):
    @unittest.skip('')
    def test_01_lick_detection(self):
        
        folder='/tmp/behav'
        
        fns=[os.path.join(folder,f) for f in os.listdir(folder) if 'hdf5' in f]
        fns.sort()
        licks=hdf5io.read_item('/tmp/traces.hdf5','licks')
        pp=not True
        fsample=1000
        threshold=0.25
        max_width=0.1
        min_width=0.01
        mean_threshold=0.07
        lick_wait_time=1
        result=lick_detection_folder(folder,fsample,lick_wait_time,threshold,max_width,min_width,mean_threshold)
        


        


    @unittest.skip('')
    def test_02_extract_speedchnage(self):
        if 1:
            process_all('/tmp/setup1')
        #else:
            plot_aggregated()
        #s=ProcessBehavioralData('/mnt/data/behavioral/dasha/setup1/Rat465+910/m23_rplp_RE/20160802','StimStopReward')

    @unittest.skip('')
    def test_03_blink_detect(self):
        fn='/tmp/fear/data_FearResponse_1466414204.hdf5'
        annotated = {
                'data_FearResponse_1466413859.hdf5': [582],
                'data_FearResponse_1466413981.hdf5': [233],
                'data_FearResponse_1466414084.hdf5': [59, 146, 299],#, 450, 590, 756, 895, 1049],
                'data_FearResponse_1466414204.hdf5': [41, 148, 271, 448, 743, 1056, 1272, 1303],
                'data_FearResponse_1466414305.hdf5': [130, 408, 436, 697, 738, 1028],
                'data_FearResponse_1466414405.hdf5': [6, 131, 338, 414, 430, 589, 681, 740, 781, 982, 1028, 1055, 1180, 1332, 1474],
                'data_FearResponse_1466414505.hdf5': [130, 253, 429, 727, 1027, 1147],
                'data_FearResponse_1466414606.hdf5': [123, 421, 727, 1018],
                'data_FearResponse_1466414706.hdf5': [138, 430, 731, 1040],
                'data_FearResponse_1466414806.hdf5': [134, 430, 730, 1034],
                'data_FearResponse_1466414907.hdf5': [129, 429, 727, 1034],
                'data_FearResponse_1466415007.hdf5': [120, 430, 720],
                'data_FearResponse_1466415107.hdf5': [175],
                }

        folder='/tmp/fear'
        #folder='/home/rz/temp/'
        out='/tmp/out/'
        fns=os.listdir(folder)
        fns.sort()
        for fn in fns:
            if fn[-4:]!='hdf5':
                continue
            print(fn)
            of=None#os.path.join(out,fn)
            with introspect.Timer():
                airpuff_t, airpuff, is_blinked, activity_t, activity = extract_eyeblink(os.path.join(folder,fn), debug=False,annotation=annotated)
                print(is_blinked.sum()/float(is_blinked.shape[0]))
                
    @unittest.skip('')
    def test_04_lick_summary(self):
        folder='c:\\Users\\mouse\\Desktop\\Lick BL6\\October 2016\\m2_BL6_lp'
        ls=LickSummary(folder,15)
        
    @unittest.skip('')
    def test_05_check_hitmissfiles(self):
        check_hitmiss_files('c:\\Data\\mouse\\test2\\20170114')
        
    @unittest.skip('')
    def test_06_hitmiss_analysis(self):
        folder='c:\\Data\\raicszol\\data4plotdev'
        folder='/tmp/data4plotdev'
        h=HitmissAnalysis(folder)
        h.add2day_analysis(h.alldatafiles[0])
        #HitmissAnalysis('/home/rz/mysoftware/data/data4plotdev/1')
        #HitmissAnalysis('/home/rz/mysoftware/data/data4plotdev')
    
    @unittest.skip('')
    def test_07_extract_mouse_position(self):
        folder=r'c:\temp\20190416'
        folder='/data/data/user/Zoltan/20190715_Miao_behav/tracking lost'
        folder='/tmp'
        folder=r'c:\temp'
        
        from PIL import Image
        files=fileop.listdir_fullpath(folder)
        files.sort()
        coordinates={}
        files=['/data/tmp/behav_201907251628326.hdf5']
        files=[r'x:\tmp\behav_201907251628326.hdf5']
        for filename in files:
            if 'png' in filename:
                frames=[numpy.asarray(Image.open(f)) for f in files]
            elif 'hdf5' not in filename: continue
            else:
                hh=hdf5io.Hdf5io(filename)
                nframes=hh.h5f.root.frames.shape[0]
                chunksize=1000
                nchunks=nframes/chunksize
                if nchunks==0:
                    nchunks=1
#                for chunki in range(nchunks):
                print (nchunks)
                chunki=0
                frames=hh.h5f.root.frames.read(chunki*chunksize,  (chunki+1)*chunksize)
                hh.close()
                #frames=hdf5io.read_item(filename,  'frames')
            
            coo=[]
            
    #        files.sort()
            framect=0
            coordinates[filename]=[]
#            frames=frames[::100]
            results=0
            nanct=0
            for f in frames:
#                with introspect.Timer():
                    #Find brightest area
                    framect+=1
#                    if framect%6!=0:
#                        continue
                    try:
                        f=numpy.copy(f)
                        result, position, red_angle, red, green, blue, debug=mouse_head_direction(f, roi_size=20, threshold=80,  saturation_threshold=0.6, value_threshold=0.4, debug=True)
                        results+=int(result)
                        outfolder=r'c:\temp\img'
                        outfolder='/tmp/img'
                        if os.path.exists(outfolder):
                            Image.fromarray(debug).save(os.path.join(outfolder,'{0}_{1:0=5}_{2:.1f}.png'.format(os.path.basename(filename),  framect,  red_angle)))
                        print((framect, result, position, red_angle, red, green, blue))
                        if numpy.isnan(position).any():
                            result, position, red_angle, red, green, blue, debug=mouse_head_direction(f, roi_size=20, threshold=80,  saturation_threshold=0.6, value_threshold=0.4, debug=True)
                            nanct+=1
                        pass
                    except:
                        import traceback
                        print(traceback.format_exc())
                        pdb.set_trace()
            if 'png' in filename:
                break
            print ((results,  frames.shape, nanct))
#        utils.object2array(coordinates).tofile('c:\\temp\\coo.bin')
        from pylab import plot,show
        coo=numpy.array(coo)
        plot(coo[:,0])
        plot(coo[:,1])
        show()
        pass
        
    @unittest.skip('')
    def test_08_align(self):
        sync_fn='/home/rz/mysoftware/data/vor/eye_tracking_only/all/behav_202012111657468.hdf5'
        video1_fn='/home/rz/mysoftware/data/vor/eye_tracking_only/all/behav_202012111657468.mp4'
        video2_fn='/home/rz/mysoftware/data/vor/eye_tracking_only/all/eye_202012111657468.mp4'
        #align_videos(video1_fn,video2_fn,sync_fn)
        align_videos_wrapper(sync_fn)
        
    @unittest.skip('')
    def test_09_ir_track(self):
        fn='/tmp/video0002 21-02-18 17-33-54.avi'
        fn='/home/rz/mysoftware/data/IR LED test'
        fns=['behav_202103041700174.mp4',#bad, one led is too dim
                'behav_202103041647489.mp4',#good
                'behav_202103041643104.mp4',#good
                'behav_202103041628593.mp4',#OK
                'behav_202103041510318.mp4',#good
                'behav_202103041507500.mp4',#good
                'behav_202103031800241.mp4',
                'behav_202103031757322.mp4']
        fn=os.path.join(fn,fns[3])
        fns=['/tmp/behav_202103171741289.mp4',
                '/tmp/behav_202103171705230.mp4',
                '/tmp/behav_202103171716063.mp4']
#        fn='/tmp/behav_202103171741289.mp4'
        for fn in fns:
            angles1=track_ir_leds(fn)
            vv=skvideo.io.vread(fn)[:,:,:,0]
            o=[]
            a=numpy.nan
            angles=[a]
            for frame in vv:
                a,o=track_led_objects(frame, o, a,min_size=20,threshold=40)
                angles.append(a)
            import pdb
            pdb.set_trace()
        return
        videogen = skvideo.io.vreader(fn)
        if 0:
            for frame in videogen:
                shape=frame.shape
                break
            a=numpy.zeros(shape)
            for frame in videogen:
                a=numpy.array([a,frame]).max(axis=0)
            a=a/a.max()

            imshow(skimage.transform.rotate(a,20)[200:400,100:600])
            show()
        bigger=[]
        smaller=[]
        ffprev=None
        objects=[]
        for frame in videogen:
            ff=skimage.transform.rotate(frame,00)[200:400,100:600,0]
            ffprev=numpy.copy(ff)
            objects.append(find_objects(ff))
            
            l,n=scipy.ndimage.label(numpy.where(ff>0.5,1,0))
            if n>2:
                if numpy.where(l>0)[0].shape[0]<10:
                    bigger.append([-1,-1])
                    smaller.append([-1,-1])
                else:
                    bigger.append([-2,-2])
                    smaller.append([-2,-2])
                    print('Check this1')
            elif n==0:
                bigger.append([0,0])
                smaller.append([0,0])
                continue
            else:
                try:
                    coo1xprev=numpy.copy(coo1x)
                    coo1yprev=numpy.copy(coo1y)
                    coo2xprev=numpy.copy(coo2x)
                    coo2yprev=numpy.copy(coo2y)
                    prev=True
                except:
                    prev=False
                coo1x,coo1y=numpy.where(l==1)
                coo2x,coo2y=numpy.where(l==2)
                #Cases: n=1, n=2
                if n==2:
                    if not prev:
                        if coo1x.shape[0]>coo2x.shape[0]:
                            bigger.append([coo1x.mean(),coo1y.mean()])
                            smaller.append([coo2x.mean(),coo2y.mean()])
                        else:
                            bigger.append([coo2x.mean(),coo2y.mean()])
                            smaller.append([coo1x.mean(),coo1y.mean()])
                    else:
                        prevxy1=coo1xprev.mean(), coo1yprev.mean()
                        prevxy2=coo2xprev.mean(), coo2yprev.mean()
                        xy1=coo1x.mean(), coo1y.mean()
                        xy2=coo2x.mean(), coo2y.mean()
                        pass
                elif n==1:
                    print('Not implemented')
                
                
                
                
                if coo1x.shape[0]==0 or coo2x.shape[0]==0:
                    print('Check this2')
                    bigger.append([-3,-3])
                    smaller.append([-3,-3])
                    continue
                if coo1x.shape[0]>coo2x.shape[0]:
                    if not prev:
                        bigger.append([coo1x.mean(),coo1y.mean()])
                        smaller.append([coo2x.mean(),coo2y.mean()])
                    else:
                        pass
                else:
                    bigger.append([coo2x.mean(),coo2y.mean()])
                    smaller.append([coo1x.mean(),coo1y.mean()])
                pass
        #    if len(bigger)>1000:
        #        break
        
        bigger=numpy.array(bigger)
        smaller=numpy.array(smaller)
        figure(1)
        title('angle')
        plot(numpy.degrees(numpy.arctan2(bigger[:,0],bigger[:,1])));plot(numpy.degrees(numpy.arctan2(smaller[:,0],smaller[:,1])))
        legend(['bigger','smaller'])
        figure(2)
        title('r')
        plot(numpy.sqrt(bigger[:,0]**2+bigger[:,1]**2));plot(numpy.sqrt(smaller[:,0]**2+smaller[:,1]**2));
        legend(['bigger','smaller'])
        show()
        pass
    
    def test_screen_ir_videos(self):
        folder='/home/rz/mysoftware/data/irtracking/0519'
        for thi in [80]:
            for fn in fileop.find_files(folder):
                if os.path.splitext(fn)[1]!='.avi': continue
                if 1:
                    videogen = skvideo.io.vreader(fn)
                    ct=0
                    for frame in videogen:
                        if ct==0:
                            mip=numpy.zeros_like(frame[:,:,0])
                        mip=numpy.dstack([mip,frame[:,:,0]]).max(axis=2)
                        ct+=1
                    maskx,masky=numpy.where(mip==255)
                    mask=numpy.zeros_like(frame[:,:,0])
                    mask[maskx.min():maskx.max(),masky.min():masky.max()]=1
                videogen = skvideo.io.vreader(fn)
#                figure(1)
#                imshow(mask)
#                figure(2)
#                imshow(mip)
#                show()
                ct=0
                o=[]
                a=numpy.nan
                angles=[]
                positions=[]
                ct=0
                mask=numpy.dstack([mask]*3)
                for frame in videogen:
#                    if ct==0:
#                        mip=numpy.zeros_like(frame[:,:,0])
#                    mip=numpy.dstack([mip,frame[:,:,0]]).max(axis=2)
#                    print(ct)
                    ct+=1
                    frame=numpy.copy(frame)
                    framem=frame*mask
                    result, position, red_angle, red, green, blue, debug=mouse_head_direction(framem.copy(), roi_size=20, threshold=thi,  saturation_threshold=0.6, value_threshold=0.4)
                    frame=frame[:,:,0]
                    a,o=track_led_objects(frame, o, a,min_size=20,threshold=80)
                    angles.append(a)
                    positions.append(position)     
                    if 0 and numpy.isnan(a):
                        imshow(frame)
                        show()
                    poserr=round(100*numpy.isnan(positions).any(axis=1).sum()/numpy.array(positions).shape[0],2)
                    angleerr=round(100*numpy.isnan(angles).sum()/numpy.array(angles).shape[0],2)
                    print(ct,os.path.basename(fn),poserr,angleerr)
#                pdb.set_trace()
#                    if ct==1000:
#                        break
#                imshow(mip)
#                show()
    #@unittest.skip('')
    def test(self):
        fn='/home/rz/tmp/ts/behav_202109142235399.mp4'
        videogen = skvideo.io.vreader(fn)
        i=0
        ra=[]
        for frame in videogen:
            framem=frame.copy()
            result, position, red_angle, red, green, blue, debug=mouse_head_direction(framem[:,100:,:],threshold=80,  roi_size=40)
#            print(i,red_angle)
            ra.append(red_angle)
            i+=1
        print(sum([numpy.isnan(ii) for ii in ra])/i)
        pass

if __name__ == "__main__":
    unittest.main()
