import numpy,unittest,os
from skimage.filters import threshold_otsu
from visexpman.engine.generic import signal,fileop
from visexpman.engine.vision_experiment import experiment_data

def spikes2polar(fn,threshold=10):
    h=experiment_data.CaImagingData(fn)
    h.load('sync')
    h.load('configs')
    h.load('tstim')
    elphys=h.sync[:,h.configs['machine_config']['ELPHYS_INDEX']]
    threshold_v=elphys.std()*threshold
    spikes=numpy.where(abs(elphys-elphys.mean())>threshold_v)[0]/float(h.configs['machine_config']['SYNC_RECORDER_SAMPLE_RATE'])
    direction_order=numpy.tile(h.configs['experiment_config']['DIRECTIONS'],h.configs['experiment_config']['REPETITIONS'])
    directions=list(set(direction_order))
    spike_count={}
    for i in range(len(directions)):
        d=directions[i]
        if d not in spike_count:
            spike_count[d]=0
        indexes=numpy.where(direction_order==d)[0]
        block_start=h.tstim[indexes*2]
        block_end=h.tstim[indexes*2+1]
        for r in range(block_start.shape[0]):
            spike_count[d]+=numpy.where(numpy.logical_and(spikes>block_start[r],spikes<block_end[r]))[0].shape[0]
        pass
    
    h.close()
    from pylab import plot,show,savefig,subplot,scatter,clf,cla
    import tempfile
    #Draw polarplot
    cla()
    clf()
    subplot(111, projection='polar')
    #
    theta=numpy.radians(numpy.array(spike_count.keys())[numpy.argsort(spike_count.keys())])
    theta=numpy.append(theta,0)
    r=numpy.array(spike_count.values())[numpy.argsort(spike_count.keys())]
    r=numpy.append(r,r[0])
    plot(theta, r,'o-')
#    plot(numpy.radians(numpy.arange(0,360,45)), numpy.linspace(10, 20, numpy.arange(0,360,45).shape[0]),'o-')
#    scatter(theta, r,cmap='hsv', alpha=0.75)
    fn=os.path.join(tempfile.gettempdir(),'polar.png')
    savefig(fn)
    from PIL import Image
    plotimg=numpy.asarray(Image.open(fn))[:,:,:3]
    return spike_count, plotimg
    
def extract_erg_repetitions(elphys,stim,fsample, pretrigger=1.0):
    if not signal.isbinary(stim):
        return
    rising_edges=numpy.where(numpy.diff(numpy.cast['int'](signal.signal2binary(stim)))==1)[0]+1
    falling_edges=numpy.where(numpy.diff(numpy.cast['int'](signal.signal2binary(stim)))==-1)[0]+1
    if falling_edges.shape[0]==0 or rising_edges.shape[0]<2:
        return
    pretrigger_samples=int(pretrigger*fsample)
    roi_start=rising_edges[numpy.where(rising_edges-pretrigger_samples>0)[0]][0]
    roi_end=falling_edges[-1]
    if roi_start>roi_end:
        return
    rising_edges=rising_edges[numpy.where(rising_edges<roi_end)[0]]
    falling_edges=falling_edges[numpy.where(falling_edges>roi_start)[0]]
    if rising_edges.shape[0]!=falling_edges.shape[0]:
        raise RuntimeError((rising_edges.shape[0],falling_edges.shape[0]))
    window_start=rising_edges[0:-1]-pretrigger_samples
    window_end=rising_edges[1:]-pretrigger_samples
    stim_start= rising_edges[0:-1]
    stim_end= falling_edges[0:-1]
    elphys_repetitions=[]
    for i in range(window_start.shape[0]):
        elphys_repetitions.append(elphys[window_start[i]:window_end[i]])
    elphys_repetitions=numpy.array(elphys_repetitions)
    elphys_average=elphys_repetitions.mean(axis=0)
    stim_start_index=int((stim_start-window_start).mean())#Within repetiton window
    stim_end_index=int((stim_end-window_start).mean())#Within repetiton window
    return elphys_repetitions, elphys_average, stim_start_index, stim_end_index

def peristimulus_histogram(waveform, stimulus_timing, fsample, binsize, spike_threshold):
    tspike=numpy.where(numpy.diff(numpy.where(waveform>spike_threshold, 1, 0))==1)[0]/float(fsample)
    tstim=signal.detect_edges(stimulus_timing,threshold_otsu(stimulus_timing))/float(fsample)
    tspikerel=tspike-tstim[0]
    bins=signal.generate_bins(tspikerel, binsize)
    h,b=numpy.histogram(tspikerel,bins)
    return h,b,tspikerel

class TestElphysAnalysis(unittest.TestCase):
    def test_01_psths(self):
        fsample=40e3
        binsize=50e-3
        wf=numpy.load(os.path.join('..', '..', 'data', 'test', 'lfp_mv_40kHz.npy'))
        pulse=numpy.concatenate((numpy.zeros(0.1* fsample), numpy.ones(0.1* fsample)))
        trig=numpy.zeros_like(wf)
        trig[:pulse.shape[0]]=pulse
        spike_threshold=4
        print peristimulus_histogram(wf, trig, fsample, binsize, spike_threshold)
        
    def test_02_spikes2polar(self):
        folder=os.path.join(os.path.dirname(fileop.visexpman_package_path()),'visexpman-testdata', 'data','spikes')
        for f in fileop.listdir(folder):
            spikes2polar(f)
            
    def test_03_erg(self):
        import hdf5io
        fn=os.path.join(os.path.dirname(os.path.dirname(fileop.visexpman_package_path())), 'visexpman-testdata', 'erg.hdf5')
        e=hdf5io.read_item(fn,'elphys')
        s=hdf5io.read_item(fn,'stim')
        fs=hdf5io.read_item(fn,'fsample')
        for i in range(len(e)):
            extract_erg_repetitions(e[i],s[i],fs,1)
        
        
if __name__ == "__main__":    
    unittest.main()
