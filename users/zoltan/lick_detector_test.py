import numpy,hdf5io,os,random, unittest, time
from pylab import plot,show, legend, xlabel, ylabel
from visexpman.engine.generic import fileop
from visexpman.engine.analysis import behavioral_data
datafolder='/home/rz/mysoftware/data/lick'
datafolder='c:\\visexp\\data'

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
    
class TestLick(unittest.TestCase):
    @unittest.skip('')
    def test_lick_detector(self):
        ignore=['data_LickResponse_201610232030107.hdf5', 
        'data_LickResponse_201610232100184.hdf5', 
        'data_LickResponse_201610241732272.hdf5', 
        'data_LickResponse_201610232030249.hdf5', 
        'data_LickResponse_201610241732272.hdf5', 
        'data_LickResponse_201611111239353.hdf5', 
        'data_LickResponse_201610241746417.hdf5', 
        'data_LickResponse_201611031555226.hdf5', 
        'data_LickResponse_201611031553506.hdf5', 
        'data_LickResponse_201611122054328.hdf5', 
        'data_LickResponse_201610232032200.hdf5', 
        'data_LickResponse_201610241752478.hdf5', 
        'data_LickResponse_201610241745259.hdf5', 
        'data_LickResponse_201611122110287.hdf5'
        ]
        
        lick_indexes=hdf5io.read_item(aggregated_file,'indexes')
        lick=hdf5io.read_item(aggregated_file,'lick')
        
#        exclude.insert(0, '1')
#        lick_indexes['1']=numpy.array([0])
#        lick['1']=numpy.linspace(0, 0.5, 1000)
        nsamples=600/300
        fs=1000.
        random.seed(1)
        selection=[random.choice(lick.keys()) for k in range(nsamples)]
        failed=[]
        for s in selection:
            if s in ignore: continue
            print selection.index(s), len(selection)
            lickwf=lick[s]
            indexes=numpy.cast['int'](numpy.array(lick_indexes[s]))
            if indexes.shape[0]==0:
                continue
            #print s, indexes.shape[0]
            from visexpman.engine.hardware_interface import daq_instrument
            sample_factor=10.
            #ao0: waveform, ai0: lick detector output which is compared with indexes, 
            #ai1: ao0 resampled and compared with original signal. This tests how the detector's analog input distorts the lick signal
            ai=daq_instrument.SimpleAnalogIn('Dev1/ai0:3',fs*sample_factor, lickwf.shape[0]/fs)
            daq_instrument.set_waveform( 'Dev1/ao0',lickwf.reshape(1, lickwf.shape[0]),sample_rate = fs)
            aidata=ai.finish()
            detector_pulses=numpy.where(numpy.diff(numpy.where(aidata[:,3]>2.5,1,0))==1)[0]
            for i in indexes:
                if i<110 or lickwf.shape[0]-i<110:#Ignore  pulses at very beginning and end
                    continue
                dt=(detector_pulses/sample_factor-i)
                dt=numpy.where(dt<0, numpy.inf, dt)
                if dt.shape[0]==0:
                    pass
                dt=dt.min()
                if not (dt>0 and dt<110):
                    pass
                    pass
                    print i, s, dt
                    failed.append(s)
                    break
                self.assertTrue(dt>0)
                self.assertTrue(dt<110)
            if 1:
                expected=numpy.zeros(lickwf.shape[0]*sample_factor)
                expected[indexes*int(sample_factor)]=1
                t=numpy.arange(expected.shape[0], dtype=numpy.float)/(fs*sample_factor)
                plot(t, aidata[:,0]);plot(t, aidata[:,1]);plot(t, aidata[:,2]);plot(t, aidata[:,3]);plot(t, expected)
                ylabel('V')
                legend(['water', 'test signal','laser','detector output',  'expected output'])
                show()
                pass
        print failed
        
    def test_protocol(self):
        import serial
        s=serial.Serial('COM8', 115200, timeout=1)
        time.sleep(2)
        s.write('ping\r\n')
        time.sleep(1)
        print s.read(100)
        time.sleep(1)
        s.close()
    
    
    
    
        
        
if __name__ == "__main__":
    unittest.main()
    
    
