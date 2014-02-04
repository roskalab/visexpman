from visexpman.engine.vision_experiment import experiment_data
from visexpman.engine.generic import fileop
from visexpman.engine.generic import utils
import scipy.signal
import scipy.io
from matplotlib.pyplot import plot, show,figure,legend, xlabel,title,savefig, clf, subplot, ylabel
import numpy
import os.path
import os
import shutil
import spike_sort.core
from visexpA.engine.datahandlers import hdf5io
#from visexpA.engine.dataprocessors.signal import estimate_baseline
THRESHOLD = 'auto'

cell_thresholds = {

                    '20130408\\c2': 4, 
                    '20130319\\c1': 6, 
                    '20130301\\c1':8, 
                    '20130222\\c3':6, 
                    '20130213\\c1':6, 
                    'PV2' : 6, 
                    'PV5': 5, 
                    'PV6': 5, 
                   }

class EplhysProcessor(object):
    def __init__(self, folder):
        self.folder=folder
        self.plot_folder = os.path.join(self.folder, 'plots')
        if os.path.exists(self.plot_folder):
            shutil.rmtree(self.plot_folder)
        os.mkdir(self.plot_folder)
        self.figure_counter = 1
        if False:
            self.check_stimulation_uniformity('gaussian.py')
        else:
            p=os.path.join(self.folder, 'data.hdf5')
            matfiles = utils.array2object(hdf5io.read_item(p, 'matfiles', filelocking=False))
            intensities = utils.array2object(hdf5io.read_item(p, 'intensities', filelocking=False))
            self.ti = hdf5io.read_item(p, 'ti', filelocking=False)
            sizes = [i.shape[0] for i in intensities]
            wrong_matfiles = [matfiles[i] for i in range(len(sizes)) if sizes[i] != 9000]
            all_intensities = numpy.zeros((len(intensities), intensities[0].shape[0]))
            stats = numpy.zeros((len(intensities), 3, 2))
            for i in range(len(intensities)):
                if len(intensities[i].shape) == 2:
                    all_intensities[i] = intensities[i][:, 0]
                else:
                    all_intensities[i] = intensities[i]
                stats[i, 0, 0] = all_intensities[i][:3000].mean()
                stats[i, 0, 1] = all_intensities[i][:3000].std()
                stats[i, 1, 0] = all_intensities[i][3000:6000].mean()
                stats[i, 1, 1] = all_intensities[i][3000:6000].std()
                stats[i, 2, 0] = all_intensities[i][6000:].mean()
                stats[i, 2, 1] = all_intensities[i][6000:].std()
            if False:
                figure(1)
                plot(stats[:, 0, 0])
                plot(stats[:, 2, 0])
                figure(2)
                plot(stats[:, 0, 1])
                plot(stats[:, 1, 1])
                plot(stats[:, 2, 1])
                figure(3)
                plot(stats[:, 1, 0])
                show()
            self.intensity = all_intensities[0]
            for f in fileop.find_files_and_folders(self.folder, extension = 'phys')[1]:
#                if 'PV2/20130305C4/C1/20130305_C1#002Miguelgaussian_Ch2!spike0' in f:
                    threshold = [cell_thresholds[cell_name] for cell_name in cell_thresholds.keys() if cell_name.lower() in f.lower()]
                    if len(threshold)==1:
                        self.process_file(f, threshold[0])
                    else:
                        print threshold, f

    def check_stimulation_uniformity(self, stimulus_name):
        '''
        Check if all stimulations were identical
        '''
        matfiles = []
        intensities = []
        for matfile in fileop.find_files_and_folders(self.folder, extension = 'mat')[1]:
            try:
                t, intensity = self.read_spot_intensity(matfile)
                intensities.append(intensity)
                matfiles.append(matfile)
            except:
                print matfile
        
        p=os.path.join(self.folder, 'data.hdf5')
        hdf5io.save_item(p, 'matfiles', utils.object2array(matfiles),  filelocking=False)
        hdf5io.save_item(p, 'intensities', utils.object2array(intensities),  filelocking=False)
        hdf5io.save_item(p, 'ti', t,  filelocking=False)
        
    def restore_experiment_log(self, matfilename, outfile=None):#Not working
        stim_data = scipy.io.loadmat(matfilename, mat_dtype=True)
        log = {}
        timestamps = []
        for k in stim_data['experiment_log_dict'].dtype.names:
            log[k] = stim_data['experiment_log_dict'][k][0][0][0]
            timestamps.append(float(k.replace('time_','').replace('p','.')))
        timestamps.sort()
        logs = ''
        if outfile is not None:
            f = open(outfile,'wt')
        for timestamp in timestamps:
            line = str(timestamp) + '\t' + log['time_' + str(timestamp).replace('.', 'p')]+'\r\n'
            logs += line
            if outfile is not None:
                f.write(line)
        if outfile is not None:
            f.close()
        return logs
        
    def read_spot_intensity(self, filename):
        stim_data = scipy.io.loadmat(filename, mat_dtype=True)
        intensities = []
        if len(stim_data['stimulus_frame_info'][0,:])>10:
            for stim in stim_data['stimulus_frame_info'][0,:]:
                if str(stim['stimulus_type'][0][0][0]) == 'show_shape' and stim['is_last'][0][0][0][0]==0:
                    intensities.append(stim['parameters'][0][0]['color'][0][0][0][0])
        else:
            for stim in stim_data['stimulus_frame_info'][0,:]:
                if str(stim['stimulus_type'][0][0][0]) == 'show_shape' and stim['is_last'][0][0][0][0]==0:
                    intensities.extend(stim['parameters'][0][0]['color'][0][0].tolist())
                    break
                pass
        intensities = numpy.array(intensities)
        ti = numpy.linspace(0, intensities.shape[0]/stim_data['config']['machine_config'][0][0]['SCREEN_EXPECTED_FRAME_RATE'][0][0][0][0], intensities.shape[0])
        return ti, intensities
        
    def highpass_filter(self, signal, cutoff_frequency, fsample, twindow=25e-3):
        filter_window = 25e-3 #s
        ntaps = int(twindow*fsample)
        if ntaps%2==0:
            ntaps += 1
        b = scipy.signal.firwin(ntaps, cutoff_frequency/(0.5*fsample), pass_zero=False)
        a = [1.0]
        return scipy.signal.lfilter(b, a, signal)
        
    def generate_time_intervals(self, t, time_window):
        time_intervals = (numpy.arange(-int(abs(t.min())/time_window),0)*time_window).tolist()
        time_intervals.insert(0, t.min())
        time_intervals.extend((numpy.arange(int(t.max()/time_window))*time_window).tolist())
        time_intervals.append(t.max())
        return numpy.array(time_intervals)
        
    def process_file(self, filename, threshold = THRESHOLD, time_window = 5.0):
        raw_elphys_signal, metadata = experiment_data.read_phys(filename)
        if raw_elphys_signal.shape[0] == 0 or os.stat(filename).st_size < 2000:
            return
        fsample = float(metadata['Sample Rate'])
        #Filter elphys signal
        filtered_elphys_signal = self.highpass_filter(raw_elphys_signal[0], 100.0,  fsample)
        #Detect spikes
        spike_times = spike_sort.core.extract.detect_spikes({'data':numpy.array([filtered_elphys_signal]), 'n_contacts': 1, 'FS': fsample},  thresh = '{0}'.format(threshold))['data'][1:]/1000.0
        t_elphys = numpy.arange(0, filtered_elphys_signal.shape[0])/fsample
        import copy
        t_stim = copy.deepcopy(self.ti)
        #shift time vectors
        time_offset = 50.0 + 0*float(metadata['Pre-Record Time (mS)'])/1000.0
        for tv in [t_elphys, t_stim, spike_times]:
            tv -= time_offset
        #Generate time intevals
        time_intervals = self.generate_time_intervals(t_elphys, time_window)
        t_spiking_frequency = []
        spiking_frequency = []
        for i in range(time_intervals.shape[0]-1):
            tstart = time_intervals[i]
            tend = time_intervals[i+1]
            t = tstart + 0.5*(tend-tstart)
            t_spiking_frequency.append(t)
            spiking_frequency.append(numpy.nonzero(numpy.where(spike_times<tend, True, False) * numpy.where(spike_times>tstart, True, False))[0].shape[0]/time_window)
        t_spiking_frequency = numpy.array(t_spiking_frequency)
        spiking_frequency = numpy.array(spiking_frequency)
        title(filename)
        subplot(311)
        ylabel('Spiking frequency [Hz]')
        plot(t_spiking_frequency, spiking_frequency)
        plot(time_intervals, numpy.ones_like(time_intervals), '.')
        subplot(312)
        ylabel('Raw signal')
        plot(t_elphys, raw_elphys_signal[0])
        plot(time_intervals, numpy.ones_like(time_intervals), '.')
        subplot(313)
        ylabel('Stimulus intensity [PU]')
        plot(t_stim, self.intensity)
        plot(time_intervals, numpy.ones_like(time_intervals), '.')
        xlabel('Time [s]')
        print filename
        if t_stim.max()/t_elphys.max() < 1.5:#Ignore short recordings
            savefig(os.path.join(self.plot_folder, filename.replace(self.folder, '').replace(os.sep, '_').replace('.phys', '.png')), dpi=300)
            record = {}
            record['threshold'] = threshold
            record['time_window'] = time_window
            record['t_elphys'] = t_elphys
            record['elphys_signal'] = raw_elphys_signal[0]
            record['t_spikes'] = t_spiking_frequency
            record['spiking_frequency'] = spiking_frequency
            record['t_stimulus'] = t_stim
            record['spot_intensity'] = self.intensity
            scipy.io.savemat(os.path.join(self.plot_folder,  filename.replace(self.folder, '').replace(os.sep, '_').replace('.phys', '.mat')), record, oned_as = 'row', long_field_names=True)
            clf()
        pass

    def process_file1(self,filename, threshold = THRESHOLD):
        try:
            raw_elphys_signal, metadata = experiment_data.read_phys(filename)
            if raw_elphys_signal.shape[0] == 0 or os.stat(filename).st_size < 2000:
                return
            fs = float(metadata['Sample Rate'])
            prerecord_time = float(metadata['Pre-Record Time (mS)'])/1000.0
            voltage_scale = float(metadata['Waveform Scale Factors'])
            elphys_signal = raw_elphys_signal[0,:]
            te = numpy.linspace(0, elphys_signal.shape[0]/float(fs), elphys_signal.shape[0])
            import copy
            ti = copy.deepcopy(self.ti)
            filter_window = 25e-3 #s
            ntaps = int(filter_window*fs)
            if ntaps%2==0:
                ntaps += 1
            fcutoff = 100.0 #Hz
            from scipy import signal
            b = signal.firwin(ntaps, fcutoff/(0.5*fs), pass_zero=False)
            a = [1.0]
            data = elphys_signal
            data_filtered = scipy.signal.lfilter(b, a, data)
            import spike_sort.core
            res = spike_sort.core.extract.detect_spikes({'data':numpy.array([data_filtered]), 'n_contacts': 1, 'FS': fs},  thresh = '{0}'.format(threshold))['data']/1000.0
            time_offset = 50+prerecord_time#50 sec is the TIME_COURSE experiment parameter
            fig=figure(1)
            time_window = 5.0
            time_window_offset = int(time_offset)%int(time_window)
            tsp = []
            spiking_frequency = []
            for i in range(int((te.max()-te.min()-time_window_offset)/time_window)):
                tsp.append(i*time_window+time_window_offset)
                mask = numpy.where(res < tsp[-1], True, False) 
                if i > 1:
                    mask = mask * numpy.where(res >= tsp[-2], True, False)
                spiking_frequency.append(numpy.nonzero(mask)[0].shape[0]/time_window)
            tsp = numpy.array(tsp)-time_offset
            ti -= time_offset
            te -= time_offset
            plot(tsp, spiking_frequency)
            plot(ti, self.intensity)
            legend(['Spiking frequency [Hz]', 'spot intensity [PU]'])
            xlabel('Time [s]')
            title(filename)
            print filename,  ti.max(),  max(tsp),  te.max()
            if ti.max()/te.max() < 1.5:#Ignore short recordings
                savefig(os.path.join(self.plot_folder,  filename.replace(self.folder, '').replace(os.sep, '_').replace('.phys', '.png')))
                record = {}
                record['threshold'] = threshold
                record['time_window'] = time_window
                record['t_elphys'] = te
                record['elphys_signal'] = elphys_signal
                record['t_spikes'] = tsp
                record['spiking_frequency'] = spiking_frequency
                record['t_stimulus'] = ti
                record['spot_intensity'] = self.intensity
                scipy.io.savemat(os.path.join(self.plot_folder,  filename.replace(self.folder, '').replace(os.sep, '_').replace('.phys', '.mat')), record, oned_as = 'row', long_field_names=True)
            clf()
        except:
            pass
        

if __name__=='__main__':

    folder = '/mnt/datafast/'
#    folder = 'V:\\'
#    folder = 'C:\\_del'
#    folder = '/mnt/rznb/'
    e=EplhysProcessor(os.path.join(folder,  'debug', 'migueldata'))
#    e=EplhysProcessor('c:\\_del\\miguel')
