import numpy,unittest,os
from skimage.filters import threshold_otsu
from visexpman.engine.generic import signal

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
        
if __name__ == "__main__":    
    unittest.main()
