from visexpman.engine.vision_experiment import experiment_data
import scipy.io
from matplotlib.pyplot import plot, show,figure,legend
import numpy
import os.path
from visexpA.engine.dataprocessors.signal import estimate_baseline

if __name__=='__main__':



    folder = '/mnt/datafast/'
#    folder = 'V:\\'
#    folder = '/mnt/rznb/'
    pmat = os.path.join(folder, 'debug',  'migueldata',  '20130315_C2#015Miguel_Ch2!spike0_00000_0.mat')
    pphys = os.path.join(folder, 'debug',  'migueldata',  '20130315_C2#015Miguel_Ch2!spike0.phys')
    raw_elphys_signal, metadata = experiment_data.read_phys(pphys)
    fs = float(metadata['Sample Rate'])
    prerecord_time =   float(metadata['Pre-Record Time (mS)'])/1000.0
    voltage_scale =   float(metadata['Waveform Scale Factors'])
    elphys_signal = raw_elphys_signal[0,:]
    te = numpy.linspace(0, elphys_signal.shape[0]/float(fs), elphys_signal.shape[0])
    stim_data = scipy.io.loadmat(pmat, mat_dtype=True)
    intensities = []
    for stim in stim_data['stimulus_frame_info'][0,:]:
        if str(stim['stimulus_type'][0][0][0]) == 'show_shape' and stim['is_last'][0][0][0][0]==0:
            intensities.extend(stim['parameters'][0][0]['color'][0][0].tolist())
        pass
    intensities = numpy.array(intensities)
    ti = numpy.linspace(0, intensities.shape[0]/stim_data['config']['machine_config'][0][0]['SCREEN_EXPECTED_FRAME_RATE'][0][0][0][0], intensities.shape[0])+prerecord_time
    #Restore experiment log
    log = {}
    timestamps = []
    for k in stim_data['experiment_log_dict'].dtype.names:
        log[k] = stim_data['experiment_log_dict'][k][0][0][0]
        timestamps.append(float(k.replace('time_','').replace('p','.')))
    timestamps.sort()
    f = open('/mnt/rznb/explog.txt','wt')
    for timestamp in timestamps:
        f.write(str(timestamp) + '\t' + log['time_' + str(timestamp).replace('.', 'p')]+'\r\n')
    f.close()
    baseline = estimate_baseline(elphys_signal,calculate_bandwidth=False)
    import spike_sort.core
    res = spike_sort.core.extract.detect_spikes({'data':numpy.array([elphys_signal-elphys_signal.min() ]), 'n_contacts': 1, 'FS': fs})['data']/1000.0
    
    figure(2)
    plot(ti, intensities)
#    plot(res[1:], 1/numpy.diff(res))
    time_window = 1.0
    tsp = []
    nspikes = []
    for i in range(int(te.max()/time_window)):
        tsp.append(i*time_window)
        mask = numpy.where(res < tsp[-1], True, False) 
        if i > 1:
            mask = mask * numpy.where(res >= tsp[-2], True, False)
        nspikes.append(numpy.nonzero(mask)[0].shape[0]/time_window)
    plot(tsp, nspikes)
    figure(1)
    plot(te, elphys_signal)
    
    show()

