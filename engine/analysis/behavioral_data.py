#TODO: low volt/high/mid voltage?? volt instead of all voltage values
#TODO: color assignment
import hdf5io,unittest,numpy,os,multiprocessing
from visexpman.engine.generic import introspect,fileop,utils,signal
from visexpman.engine.vision_experiment import experiment_data
from pylab import *
from scipy.ndimage.filters import gaussian_filter

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
                print speed_pre
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
            print signew
            #if signew not in bp:continue
            p=ProcessBehavioralData(day,'StimStopReward')
            if hasattr(p, 'speed_change_vs_voltage'):
                aggregated[signew]=p.speed_change_vs_voltage
                aggregated_mean[signew]=numpy.array([[v, aggregated[signew][numpy.where(aggregated[signew]==v)[0],0].mean()] for v in list(set(aggregated[signew][:,1]))])
            else:
                print 'ignored'
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
    res=map(lick_detection_wrapper,pars)
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
                print successful_indexes
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
            print f
        ishitmiss='hitmiss' in os.path.basename(filename).split('_')[1].lower()
        h=hdf5io.Hdf5io(f)
        map(h.load, ['sync', 'machine_config',  'parameters', 'protocol', 'stat'])
        recording_duration=h.sync.shape[0]/float(h.machine_config['AI_SAMPLE_RATE'])
        protocol_duration=h.protocol['PRETRIAL_DURATION']
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
                if not stat.has_key('stimulus_t'):
                    h.close()
                    continue
                    sync=h.findvar('sync')
                    machine_config=h.findvar('machine_config')
                    from visexpman.engine.hardware_interface import lick_detector
                    stat=lick_detector.detect_events(sync,machine_config['AI_SAMPLE_RATE'])[0]
                    h.stat=stat
                    h.save('stat')
                if self.filter.has_key('voltage') and h.findvar('protocol')['LASER_INTENSITY'] != self.filter['voltage']:
                    h.close()
                    continue
                self.nflashes+=1
                h.close()
                self.nhits+=stat['result']
                self.nsuccesfullicks+=stat['lick_result']
                if stat.has_key('lick_latency'):
                    self.lick_latencies.append(stat['lick_latency']*1000)
                if stat.has_key('reward_latency'):
                    self.reward_latencies.append(stat['reward_latency']*1000)
                self.lick_times.extend((1000*(stat['lick_times']-stat['stimulus_t'][0])).tolist())
            except:
                import logging, traceback
                logging.info(f)
                logging.error(traceback.format_exc())
        self.lick_latencies=numpy.array(map(int,self.lick_latencies))
        self.reward_latencies=numpy.array(map(int,self.reward_latencies))
        self.lick_times=numpy.array(map(int,self.lick_times))
        if self.nflashes==0:
            self.success_rate=0
            self.lick_success_rate=0
        else:
            self.success_rate=self.nhits/float(self.nflashes)
            self.lick_success_rate=self.nsuccesfullicks/float(self.nflashes)            
        return self.lick_times,self.lick_latencies,self.reward_latencies,self.nflashes,self.nhits,self.success_rate,self.lick_success_rate
        
    def add2day_analysis(self,filename):
        stat=hdf5io.read_item(filename,'stat')
        self.nhits+=stat['result']
        self.nflashes+=1
        self.success_rate=self.nhits/float(self.nflashes)
        if stat.has_key('lick_latency'):
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
            print fn
            of=None#os.path.join(out,fn)
            with introspect.Timer():
                airpuff_t, airpuff, is_blinked, activity_t, activity = extract_eyeblink(os.path.join(folder,fn), debug=False,annotation=annotated)
                print is_blinked.sum()/float(is_blinked.shape[0])
                
    @unittest.skip('')
    def test_04_lick_summary(self):
        folder='c:\\Users\\mouse\\Desktop\\Lick BL6\\October 2016\\m2_BL6_lp'
        ls=LickSummary(folder,15)
        
    @unittest.skip('')
    def test_05_check_hitmissfiles(self):
        check_hitmiss_files('c:\\Data\\mouse\\test2\\20170114')
        
    #@unittest.skip('')
    def test_06_hitmiss_analysis(self):
        folder='c:\\Data\\raicszol\\data4plotdev'
        folder='/tmp/data4plotdev'
        h=HitmissAnalysis(folder)
        h.add2day_analysis(h.alldatafiles[0])
        #HitmissAnalysis('/home/rz/mysoftware/data/data4plotdev/1')
        #HitmissAnalysis('/home/rz/mysoftware/data/data4plotdev')
        
    def test_07_extract_mouse_position(self):
        files=fileop.listdir_fullpath('/tmp/b')
        from PIL import Image
        coo=[]
        files.sort()
        for f in files:
            with introspect.Timer():
                res= extract_mouse_position(numpy.asarray(Image.open(f)))
            if res!=None:
                coo.append(res)
        from pylab import plot,show
        coo=numpy.array(coo)
        plot(coo[:,0])
        plot(coo[:,1])
        show()
        pass

if __name__ == "__main__":
    unittest.main()
