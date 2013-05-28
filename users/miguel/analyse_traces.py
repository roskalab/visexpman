from visexpman.engine.vision_experiment import experiment_data
import scipy.io
from matplotlib.pyplot import plot, show,figure,legend
import numpy
import os.path

if __name__=='__main__':



    folder = '/mnt/datafast/'
    folder = 'V:\\'
    pmat = os.path.join(folder, 'debug',  'migueldata',  '20130315_C2#015Miguel_Ch2!spike0_00000_0.mat')
    pphys = os.path.join(folder, 'debug',  'migueldata',  '20130315_C2#015Miguel_Ch2!spike0.phys')
    raw_elphys_signal, metadata = experiment_data.read_phys(pphys)
    fs = float(metadata['Sample Rate'])
    prerecord_time =   float(metadata['Pre-Record Time (mS)'])/1000.0
    voltage_scale =   float(metadata['Waveform Scale Factors'])
    elphys_signal = raw_elphys_signal[0,:]*voltage_scale
    
    stim_data = scipy.io.loadmat(pmat, mat_dtype=True)
    stim_data['stimulus_frame_info']
    plot(elphys_signal[::10])
    show()

