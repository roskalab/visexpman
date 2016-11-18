import numpy,hdf5io,os,random
from pylab import plot,show
from visexpman.engine.generic import fileop
from visexpman.engine.analysis import behavioral_data
datafolder='/home/rz/mysoftware/data/lick'
aggregated_file=os.path.join(datafolder,'aggregated.hdf5')
def aggregate_lick_waveforms():
    files=[f for f in fileop.find_files_and_folders(datafolder)[1] if os.path.splitext(f)[1]=='.hdf5']
    data={}
    lick_indexes={}
    for f in files:
        h=hdf5io.Hdf5io(f)
        h.load('parameters')
        h.load('protocol')
        h.load('machine_config')
        lick=h.findvar('sync')[:,0]
        stimulus=h.findvar('sync')[:,2]
        events,lick_times,successful_lick_times,stim_events = behavioral_data.lick_detection(lick,stimulus,
                        h.machine_config['AI_SAMPLE_RATE'],
                        h.protocol['LICK_WAIT_TIME'],
                        threshold=h.parameters['Voltage Threshold'],
                        max_width=h.parameters['Max Lick Duration'],
                        min_width=h.parameters['Min Lick Duration'],
                        mean_threshold=h.parameters['Mean Voltage Threshold'])
        data[os.path.basename(f)]=lick
        lick_indexes[os.path.basename(f)]=lick_times*h.machine_config['AI_SAMPLE_RATE']
        h.close()
        
    h1=hdf5io.Hdf5io(aggregated_file)
    h1.lick=data
    h1.indexes=lick_indexes
    h1.save(['lick','indexes'])
    h1.close()
    
def read_waveforms(nsamples=10):
    lick_indexes=hdf5io.read_item(aggregated_file,'indexes')
    lick=hdf5io.read_item(aggregated_file,'lick')
    if nsamples>0:
        random.seed(0)
        selection=[random.choice(lick.keys()) for k in range(nsamples)]
    else:
        selection=lick.keys()
    #Concatenate:
    offset=0
    selection.sort()
    licks=numpy.empty(0)
    indexes=numpy.empty(0)
    for k in selection:
        licks=numpy.concatenate((licks, lick[k]))
        if lick_indexes[k]!=[]:
            indexes=numpy.concatenate((indexes, lick_indexes[k]+offset))
        offset+=lick[k].shape[0]
    indexes=numpy.cast['int'](indexes)
    return licks, indexes
    
def test_lick_detector():
    licks, indexes=read_waveforms(nsamples=10)
    from visexpman.engine.hardware_interface import daq_instrument
    #ao0: waveform, ai0: lick detector output which is compared with indexes, 
    #ai1: ao0 resampled and compared with original signal. This tests how the detector's analog input distorts the lick signal
    aidata=daq_instrument.analogio('Dev1/ai0:1','Dev1/ao0',1000,licks)
    
    
    
        
        
if __name__ == "__main__":
    #aggregate_lick_waveforms()
    read_waveforms()
    
