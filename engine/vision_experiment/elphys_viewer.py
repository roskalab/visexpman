import sys,multiprocessing,time
import subprocess,tempfile,os,unittest,numpy,scipy.io,scipy.signal
from pylab import *

import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import pyqtgraph

from visexpman.engine.generic import fileop,introspect,gui

ELECTRODE_ORDER=[16,1,15,2,12,5,13,4,10,7,9,8,11,6,14,3]#TODO: add this to parameter tree

def mcd2raw(filename, nchannels=16,outfolder=None,header_separately=False):
    cmdfile=os.path.join(fileop.visexpman_package_path(), 'data', 'mcd2raw{0}.cmd'.format(nchannels))
    cmdfiletxt_template=fileop.read_text_file(cmdfile)
    if outfolder is None:
        outfolder=tempfile.gettempdir()
    outfile=os.path.join(outfolder,os.path.basename(filename).replace('.mcd','.raw'))
    cmdfiletxt=cmdfiletxt_template.replace('infile', filename).replace('outfile', outfile)
    if header_separately:
        cmdfiletxt=cmdfiletxt.replace('-WriteHeader\n','')
    tmpcmdfile=os.path.join(tempfile.gettempdir(), 'cmd.cmd')
    fileop.write_text_file(tmpcmdfile, cmdfiletxt)
    mcdatatoolpath='c:\\Program Files (x86)\\Multi Channel Systems\\MC_DataTool\MC_DataTool'
    cmd='"{0}" -file {1}'.format(mcdatatoolpath, tmpcmdfile)
    if header_separately:
        cmdfiletxt=cmdfiletxt_template.replace('infile', filename).replace('outfile', outfile.replace('.raw', 'h.raw'))
        tmpcmdfile2=os.path.join(tempfile.gettempdir(), 'cmd2.cmd')
        cmd2='"{0}" -file {1}'.format(mcdatatoolpath, tmpcmdfile2)
        fileop.write_text_file(tmpcmdfile2, cmdfiletxt)
    res1=subprocess.call(cmd, shell=True)==0
    res2= subprocess.call(cmd2, shell=True) == 0 if header_separately else True
    if all([res1,res2]):
        return outfile
        
def mcd2raws(folder,queue):
    fns=[f for f in os.listdir(folder) if f[-3:]=='mcd']
    for f in fns:
        fn=os.path.join(folder,f)
        outfile=mcd2raw(fn,outfolder=folder)
        queue.put('Converted {2}/{3}, {0}->{1}'.format(fn,outfile, fns.index(f)+1, len(fns)))
        
def read_raw(filename):
    header=[]
    if os.path.exists(filename.replace('.raw', 'h.raw')):
        headerfile=filename.replace('.raw', 'h.raw')
        read_data_separately=True
    else:
        headerfile=filename
        read_data_separately=False
    with open(headerfile) as f:
        for line in f:
            header.append(line)
            if 'EOH' in line:
                headerlen=len(''.join(header))+(len(header) if os.name=='nt' else 0)#Win: \n is at the line, linux: \r\n is at the end of line
                if read_data_separately:
                    data=numpy.fromfile(filename,dtype=numpy.int16)
                else:
                    f.seek(headerlen)
                    data=numpy.fromfile(f,dtype=numpy.uint16)
                break
    sample_rate=float([item for item in header if 'Sample rate = ' in item][0].split('=')[1])
    ad_scaling=float([item for item in header if 'El = ' in item][0].split('El =')[1].split('\xb5V')[0])*1e-6
    
    try:
        adc_offset=int([item for item in header if 'ADC zero' in item][0].split(' = ')[1])
    except IndexError:
        adc_offset=0
    if len([item for item in header if 'An = ' in item])>0:
        ai_scaling=float([item for item in header if 'An = ' in item][0].split('El =')[1].split('\xb5V')[0])*1e-6
    else:
        ai_scaling=None
    channel_names=[item for item in header if 'Streams = ' in item][0].split('=')[1].strip().split(';')
    if data.shape[0]%len(channel_names) != 0:
        raise IOError('Invalid data in {0}. Datapoints: {1}, Channels: {2}'.format(filename, data.shape[0], len(channel_names)))
    data=data.reshape((data.shape[0]/len(channel_names),len(channel_names))).T
    if ai_scaling is not None:
        analog=data[0]*ai_scaling
        offset=2
    else:
        analog=0
        offset=1
    digital=data[offset-1]
    elphys=data[offset:]
    elphys = numpy.cast['int'](elphys)-adc_offset
    t=numpy.linspace(0,digital.shape[0]/sample_rate,digital.shape[0])
    return t,analog,digital,elphys,channel_names,sample_rate,ad_scaling,adc_offset
    
def calculate_repetition_boundaries(digital,fsample,pre,post,is_movingbar,ndirections=None):
    pres=int(pre*fsample)
    posts=int(post*fsample)
    boundaries=numpy.nonzero(numpy.diff(digital))[0]
    boundaries[0::2]-=pres
    boundaries[1::2]+=posts
    if is_movingbar:
        boundaries=boundaries[-ndirections*(boundaries.shape[0]/ndirections):]#assuming unexpected transitions at the beginning of the sync signal
        #assuming the duration of the last sweep:
        last_sweep_duration = int(numpy.diff(boundaries)[2*ndirections-1::2*ndirections].mean())
        boundaries = numpy.append(boundaries,boundaries[-1]+last_sweep_duration)
        boundaries = boundaries[::2][::ndirections]
        boundaries = numpy.repeat(boundaries,2)[1:-1]
    return boundaries
    
def extract_repetitions(digital,elphys,fsample,pre,post, is_movingbar=False,ndirections=None):
    repetition_boundaries=calculate_repetition_boundaries(digital, fsample,pre,post,is_movingbar,ndirections)
    fragments = numpy.split(elphys,repetition_boundaries,axis=1)[1::2]
    fragment_length=min([f.shape[1] for f in fragments])
    repetitions = numpy.array([f[:,:fragment_length] for f in fragments])
    return repetitions
       
def filter_trace(pars):
    lowpass, highpass,signal=pars
    lowpassfiltered=scipy.signal.filtfilt(lowpass[0],lowpass[1], signal).real
    highpassfiltered=scipy.signal.filtfilt(highpass[0],highpass[1], signal).real
    return lowpassfiltered, highpassfiltered
    
def filter(elphys, cutoff,order,fs):
    lowpass=scipy.signal.butter(order,cutoff/fs,'low')
    highpass=scipy.signal.butter(order,cutoff/fs,'high')
    lowpassfiltered=numpy.zeros_like(elphys)
    highpassfiltered=numpy.zeros_like(elphys)
    pool=multiprocessing.Pool(introspect.get_available_process_cores())
    pars=[(lowpass,highpass,elphys[i]) for i in range(elphys.shape[0])]
    res=pool.map(filter_trace,pars)
    pool.terminate()
    for i in range(len(res)):
        lowpassfiltered[i]=res[i][0]
        highpassfiltered[i]=res[i][1]
    return lowpassfiltered, highpassfiltered
    
def spikes2bins(pars):
    channel,nrepetitions,repetition_window_length,repetition_boundaries,spike_times,spike_window_boundaries,spike_window=pars
    aggr_per_channel=[]
    spiking_map=numpy.ones((nrepetitions, repetition_window_length), dtype=numpy.uint8)
    for rep in numpy.arange(nrepetitions)*2:
        start=repetition_boundaries[rep]
        end=repetition_boundaries[rep+1]
        spike_times_in_rep = spike_times[numpy.where(numpy.logical_and(spike_times>start,spike_times<end))[0]]
        spike_times_in_rep-=start
        aggr_per_channel.extend(list(spike_times_in_rep))
        spiking_map[rep/2][spike_times_in_rep]=0
    hist,b=numpy.histogram(aggr_per_channel,spike_window_boundaries)
    spiking_frq=hist/spike_window/repetition_boundaries.shape[0]/2
    binning=numpy.median(numpy.diff(spike_window_boundaries))
    return spiking_frq, image_column_binning(spiking_map,binning).T

def image_column_binning(img,binning):
    flattened=img[:,:img.shape[1]-img.shape[1]%binning].flatten()
    return flattened.reshape(img.shape[0],(img.shape[1]-img.shape[1]%binning)/binning,binning).mean(axis=2)

def raw2spikes(filename,pre,post,filter_order,fcut,spike_threshold_std, spike_window,repetition_range,queue=None):
    '''
    1) Extract data from raw file
    2) Filter signal, separate baseline and high frequency part
    3) Low frequency part: average repetitions
    4) High frequency part: detect spikes
    5) Split spikes to repetitions and aggregate them
    6) Calculate spiking frq
    '''
    if hasattr(queue,'put'):
        queue.put('Reading file')
    t,analog,digital,elphys,channel_names,sample_rate,ad_scaling,adc_offset = read_raw(filename)
    filedata={'t':t,'analog': analog,'digital': digital, 'elphys': elphys, 'channel_names': numpy.array(channel_names),'sample_rate': sample_rate,'ad_scaling': ad_scaling}
    if hasattr(queue,'put'):
        queue.put('Filtering data')
    l,h=filter(elphys,fcut,filter_order,sample_rate)
    stimulus_name,stimulus_parameters=filename2stimulusname(filename)
    is_movingbar='movingbar' == stimulus_name
    ndirections=stimulus_parameters.get('ndirections',None)
    low_frequency_avg=extract_repetitions(digital,l,sample_rate,pre,post,is_movingbar=is_movingbar, ndirections=ndirections).mean(axis=0)
    if hasattr(queue,'put'):
        queue.put('Detecting spikes')
    #threshold for spike detection:
    threshold=h.std(axis=1)*spike_threshold_std
    thresholded=(h.T-threshold).T
    binary=numpy.where(thresholded>0,1,0)
    #Extract spike times:
    spike_indexes=numpy.where(numpy.diff(binary,axis=1)==1)
    spike_times=[spike_indexes[1][numpy.where(spike_indexes[0]==channel)[0]] for channel in set(spike_indexes[0])]
    if hasattr(queue,'put'):
        queue.put('Calculating spiking frequency and spiking maps')
    repetition_boundaries=calculate_repetition_boundaries(digital, sample_rate,pre,post,is_movingbar=is_movingbar,ndirections=ndirections)
    #Select repetitions:
    if len(repetition_range)==2:
        repetition_boundaries=repetition_boundaries[repetition_range[0]*2:repetition_range[1]*2]
    nrepetitions=repetition_boundaries.shape[0]/2
    repetition_window_length=numpy.diff(repetition_boundaries)[::2].max()
    nsampe_in_spike_window=int(spike_window*sample_rate)
    spike_window_boundaries=numpy.arange(repetition_window_length/nsampe_in_spike_window)*nsampe_in_spike_window
    spiking_frqs=[]
    spiking_maps = []
    pars=[(channel,nrepetitions, repetition_window_length,repetition_boundaries,spike_times[channel],spike_window_boundaries,spike_window) for channel in range(len(spike_times))]
    if 0:
        pool=multiprocessing.Pool(introspect.get_available_process_cores())
        res=pool.map(spikes2bins,pars)
        pool.terminate()
    else:
        res= [spikes2bins(pars[i]) for i in range(len(pars))]
    for i in range(len(res)):
        spiking_frq, spiking_map = res[i]
        spiking_maps.append(spiking_map)
        spiking_frqs.append(spiking_frq)
    spiking_frqs=numpy.array(spiking_frqs)
    spiking_maps = numpy.array(spiking_maps)
    if hasattr(queue,'put'):
        queue.put([spiking_frqs,low_frequency_avg*ad_scaling,spiking_maps,sample_rate,filedata])
    return spiking_frqs,low_frequency_avg*ad_scaling,spiking_maps,sample_rate
    
def concatenate_rawfiles(filenames,channel):
    orderedfn=filenames
    orderedfn.sort()
    data2concat=[]
    for filename in orderedfn:
        t,analog,digital,elphys,channel_names,sample_rate,ad_scaling,adc_offset = read_raw(filename)
        data2concat.append(elphys[channel])
    data2concat = numpy.concatenate(data2concat)
    output_filename=fileop.generate_filename(os.path.join(os.path.dirname(filenames[0]),'{2}_concat_electrode_{0}_nfiles_{1}.bin'.format(channel, len(filenames),os.path.basename(os.path.dirname(filenames[0])))))
    fp=open(output_filename,'wb')
    numpy.save(fp,numpy.cast['uint16'](data2concat+adc_offset))
    fp.close()
    return output_filename

def filename2ndirections(filename):
    return int(os.path.basename(filename).split('bar')[0])
    
def filename2stimulusname(filename):
    fn=os.path.basename(filename).lower()
    if 'led' in fn:
        return 'led',{}
    elif 'bars' in fn:
        return 'movingbar', {'ndirections':filename2ndirections(filename)}
    else:
        return 'unknown', {}

class TestElphysViewerFunctions(unittest.TestCase):
    def generate_datafile(self):
        header=[]
        with open(fileop.listdir_fullpath(self.wf)[0]) as f:
            for line in f:
                header.append(line)
                if 'EOH' in line:
                    break
        header=''.join(header)
        recording_duration=10.0
        fsample=25e3
        stimdur=0.2
        stim_period=1.0
        nstim=8
        spike_amplitude=100
        data=numpy.zeros((17,fsample*recording_duration),dtype=numpy.int16)
        stim_sync=numpy.concatenate((numpy.ones((stim_period-stimdur)*0.5*fsample),numpy.zeros(stimdur*fsample),numpy.ones((stim_period-stimdur)*0.5*fsample)))
        stim_sync=numpy.tile(stim_sync,nstim)
        data[0,-stim_sync.shape[0]:]=stim_sync-2**15
        data[0,:-stim_sync.shape[0]]=data[0,stim_sync.shape[0]]
        data[1:,:]=numpy.cast['int16']=numpy.random.random(data[1:,:].shape)*10-5
        offset=data.shape[1]-stim_sync.shape[0]+((stim_period-stimdur)*0.5+0.5*stimdur)*fsample
        pulses=numpy.arange(nstim)*fsample*stim_period
        indexes=numpy.cast['int'](numpy.concatenate([pulses+offset+d for d in range(3)]))
        for i in ELECTRODE_ORDER:
            data[i][indexes+200*ELECTRODE_ORDER.index(i)]=spike_amplitude
        f=open(os.path.join(self.wf,'g.raw'),'wb')
        f.write(header)
        data.flatten('F').tofile(f)
        f.close()
    
    @unittest.skipIf(os.name!='nt', 'Works only on Windows')
    def test_01_mcd2raw(self):
        from visexpman.users.test import unittest_aggregator
        wf=unittest_aggregator.prepare_test_data('mcd')
        for f in fileop.listdir_fullpath(wf):
            outfile=mcd2raw(f)
            self.assertTrue(os.path.exists(outfile))
            self.assertEqual(int(numpy.log10(os.path.getsize(f))),int(numpy.log10(os.path.getsize(outfile))))
            
    def test_02_raw2mat(self):
        from visexpman.users.test import unittest_aggregator
        self.wf=unittest_aggregator.prepare_test_data('mcdraw')
#        self.generate_datafile()
        for f in fileop.listdir_fullpath(self.wf):
            raw2spikes(f,0 if 'bar' in f else 200e-3,0 if 'bar' in f else 350e-3,3,300,2,20e-3 if 'bar' in f else 5e-3)

    def test_03_concat(self):
        from visexpman.users.test import unittest_aggregator
        self.wf=unittest_aggregator.prepare_test_data('mcdraw')
        concatenate_rawfiles(fileop.listdir_fullpath(self.wf),0)
            
    
            
class DataFileBrowser(QtGui.QWidget):
    def __init__(self,parent, root, extensions):
        QtGui.QWidget.__init__(self,parent)
        self.root=root
        self.filetree=gui.FileTree(self, root, extensions)
        self.filetree.setColumnWidth(0,250)
        self.filetree.setToolTip('Double click on file to open')
        self.select_folder=QtGui.QPushButton('Select Folder',self)
        self.select_folder.setMaximumWidth(150)
        self.connect(self.select_folder, QtCore.SIGNAL('clicked()'), self.select_folder_clicked)
        self.l = QtGui.QGridLayout()
        self.l.addWidget(self.filetree, 0, 0, 4, 1)
        self.l.addWidget(self.select_folder, 4, 0, 1, 1)
        self.setLayout(self.l)
       
    def select_folder_clicked(self):
        folder=self.parent().parent().ask4foldername('Select folder', self.root)
        if folder=='': return
        self.root=folder
        self.filetree.set_root(folder)
    
class MultiplePlots(pyqtgraph.GraphicsLayoutWidget):
    def __init__(self,parent,nplots,electrode_spacing,stimulus_time=None):
        pyqtgraph.GraphicsLayoutWidget.__init__(self,parent)
        self.setMinimumWidth(1024)
        self.setMinimumHeight(768)
        self.move(0,0)
        self.nplots=nplots
        self.electrode_spacing=electrode_spacing
        self.setBackground((255,255,255))
        self.setAntialiasing(True)
        self.plots=[]
        self.stimulus_time=stimulus_time
        for i in range(nplots):
            p=self.addPlot()
            p.enableAutoRange()
            p.showGrid(True,True,1.0)
            self.plots.append(p)
            if (i+1)%2==0 and i!=0:
                self.nextRow()
                
    def plot(self,x,y,pen=(0,0,0),label='',spike=False,text = []):
        yi=numpy.array(y)
        ymin=y.min()
        ymax=y.max()
        for i in range(self.nplots):
            self.plots[i].setLabels(left='{1}, {0:1.0f} um'.format(-self.electrode_spacing*i*1e6,label), bottom='time [ms]')
            self.plots[i].setYRange(ymin,ymax)
            if spike:
                curve = self.plots[i].plot(pen=pen,stepMode=True, fillLevel=0, brush=(0,0,0,150))
                curve.setData(x, y[i][:-1])
            else:
                curve = self.plots[i].plot(pen=pen)
                curve.setData(x, y[i])
            if self.stimulus_time is not None:
                if len(self.stimulus_time)==2:
                    c=(30,30,30,80)
                    linear_region = pyqtgraph.LinearRegionItem(self.stimulus_time, movable=False, brush = c)
                    self.plots[i].addItem(linear_region)
                else:
                    boundaries=self.stimulus_time.tolist()
                    boundaries.append(x[-1])
                    c=[0,0,0,80]
                    for section in range(len(boundaries)-1):
                        if section%2==1:continue
                        import copy
                        c_=copy.deepcopy(c)
                        c_[section/2]=30
                        linear_region = pyqtgraph.LinearRegionItem(boundaries[section:section+2], movable=False, brush = tuple(c_))
                        self.plots[i].addItem(linear_region)
#                    linear_region = pyqtgraph.LinearRegionItem(self.stimulus_time[:2], movable=False, brush = c)
#                    self.plots[i].addItem(linear_region)
#                    linear_region = pyqtgraph.LinearRegionItem(self.stimulus_time[-2:], movable=False, brush = c)
#                    self.plots[i].addItem(linear_region)
            if len(text)>0:
                textw = pyqtgraph.TextItem(text=text[i], color=(0,0,0), anchor=(-1,-1), border=(0,0,0,0), fill=(0, 0, 0, 0))
                self.plots[i].addItem(textw)
                textw.setPos(0, y.max())
            
class MultipleImages(pyqtgraph.GraphicsLayoutWidget):
    def __init__(self,parent, nplots,electrode_spacing):
        self.nplots=nplots
        pyqtgraph.GraphicsLayoutWidget.__init__(self,parent)
        self.setMinimumWidth(1024)
        self.setMinimumHeight(768)
        self.move(0,0)
        self.setBackground((255,255,255))
        self.plots=[]
        self.imgs=[]
        for i in range(nplots):
            p=self.addPlot()
            p.setLabels(left='{0:1.0f} um'.format(-electrode_spacing*i*1e6), bottom='t [s]')
            img = pyqtgraph.ImageItem(border='w')
            p.addItem(img)
            self.imgs.append(img)
            self.plots.append(p)
            if (i+1)%4==0 and i!=0:
                self.nextRow()
                
    def set(self,images):
        for i in range(self.nplots):
            self.imgs[i].setImage(images[i])
            self.imgs[i].setLevels([images.min(),images.max()])
            
class CWidget(QtGui.QWidget):
    '''
    The central widget of the user interface which contains the image, the plot and the various controls for starting experiment or adjusting parameters
    '''
    def __init__(self,parent):
        QtGui.QWidget.__init__(self,parent)
        self.root = sys.argv[1] if os.path.exists(sys.argv[1]) else '/tmp'
        self.df=DataFileBrowser(self,self.root,['mat', 'mcd', 'raw'])
        self.df.setMinimumWidth(400)
        self.df.setMaximumWidth(500)
        self.df.setMinimumHeight(400)
        params_config=[\
                {'name': 'Filter Order', 'type': 'int', 'value': 3},
                {'name': 'Filter Cut Frequency', 'type': 'float', 'value': 300, 'siPrefix': True, 'suffix': 'Hz'},
                {'name': 'Spike Threshold', 'type': 'float', 'value': 2, 'suffix': 'std','siPrefix': True},
                {'name': 'Spiking Frequency Window Size', 'type': 'float', 'value': 5e-3, 'suffix': 's','siPrefix': True},
                {'name': 'Pre Stimulus Time', 'type': 'float', 'value': 200e-3, 'suffix': 's','siPrefix': True},
                {'name': 'Post Stimulus Time', 'type': 'float', 'value': 400e-3, 'suffix': 's','siPrefix': True},
                {'name': 'Electrode Spacing', 'type': 'float', 'value': 50e-6, 'suffix': 'm','siPrefix': True},
                {'name': 'Repetition Range', 'type': 'str', 'value': '', },
                {'name': 'Electrode Order', 'type': 'list', 'value': ELECTRODE_ORDER,'readonly':True},
                    ]

        self.params = gui.ParameterTable(self, params_config)
        self.params.setMinimumWidth(400)
        self.params.setMaximumWidth(500)
        self.params.setMaximumHeight(300)

        self.l = QtGui.QGridLayout()
        self.l.addWidget(self.df, 0, 0, 1, 1)
        self.l.addWidget(self.params, 0, 1, 1, 1)
        self.setLayout(self.l)

class ElphysViewer(gui.SimpleAppWindow):
    #TODO: context
    def init_gui(self):
        self.toolbar = gui.ToolBar(self, ['convert_mcd_files', 'add_note', 'save','reconvert_all', 'concatenate_files', 'close_plots', 'exit'])
        TOOLBAR_HELP = '''
        Convert Mcd Files: All mcd files in the current folder will be converted to raw
        Add Note: note will be saved to current file
        Save: Save current file to mat
        Reconvert All: With current settings apply filtering/spike detection/calculation for all files in selected folder
        Concatenate Files: concatenate selected electrophysiology channel data in selected files and save it to a binary file.
        Close Plots: close all currently displayed plot windows
        '''
        self.addToolBar(self.toolbar)
        self.toolbar.setToolTip(TOOLBAR_HELP)
        self.setWindowTitle('Electrophyisiology Datafile Viewer')
        self.cw=CWidget(self)
        self.setCentralWidget(self.cw)
        self.debugw.setMinimumWidth(800)
        self.debugw.setMinimumHeight(250)
        self.setMinimumWidth(1000)
        self.setMinimumHeight(800)
        self.move(100,120)
        self.maximized=False
        self.cw.df.filetree.doubleClicked.connect(self.open_file)
        self.queue_timer=QtCore.QTimer()
        self.queue_timer.start(100)#ms
        self.connect(self.queue_timer, QtCore.SIGNAL('timeout()'), self.check_queue)
        self.queue=multiprocessing.Queue()
        self.progressbar_states={'reading':0, 'filtering':5,'spikes':50,'spiking map':80}
        self.matsaver_started=False
        self.mcd_converter_started=False
        self.note=''
        self.max_savetime=60
        self.lf_plots=[]
        self.hf_plots=[]
        self.images=[]
        
    def check_queue(self):
        if not self.queue.empty():
            msg=self.queue.get()
            if isinstance(msg,list):
                self.worker.join()
                self.spiking_frqs,self.low_frequency_avg,self.spiking_maps,self.fsample, self.filedata= msg
                self.show_data()
                self.pb.update(100)
                del self.pb
                self.log('Done')
            elif isinstance(msg,str):
                if hasattr(self,'pb'):
                    p=[v for k,v in self.progressbar_states.items() if k in msg.lower()]
                    if len(p)==1:
                        self.pb.update(p[0])
                    elif 'Converted' in msg:
                        progress = map(float,msg.split(',')[0].split('Converted')[1].split('/'))
                        progress=int(progress[0]/progress[1]*100)
                        self.pb.update(progress)
                self.log(msg)
        if self.matsaver_started and not self.matsaver.is_alive():
            self.log('Done')
            self.matsaver_started=False
            self.pb.update(self.max_savetime)
            time.sleep(0.1)
            self.pb.close()
            del self.pb
        if self.mcd_converter_started and not self.mcd_converter.is_alive():
            self.mcd_converter_started=False
            self.log('Done')
            time.sleep(0.1)
            self.pb.close()
            del self.pb
        
    def open_file(self, index):
        self.filename = gui.index2filename(index).replace('\\\\','\\')
        if os.path.isdir(self.filename): return#Double click on folder is ignored
        ext = os.path.splitext(self.filename)[1]
        params=self.cw.params.get_parameter_tree(True)
        if ext == '.raw':
            self.stimulus_name,self.stimulus_parameters=filename2stimulusname(self.filename)
            self.is_movingbar='movingbar' == self.stimulus_name
            self.ndirections=self.stimulus_parameters.get('ndirections',None)
            pre=0 if self.is_movingbar else params['Pre Stimulus Time']
            post=0 if self.is_movingbar else params['Post Stimulus Time']
            filter_order=params['Filter Order']
            fcut=params['Filter Cut Frequency']
            spike_threshold_std=params['Spike Threshold']
            spike_window=params['Spiking Frequency Window Size']
            if params['Repetition Range']!='':
                repetition_range=map(int,params['Repetition Range'].split(','))
            else:
                repetition_range=[]
            self.worker=multiprocessing.Process(target=raw2spikes,args=(self.filename,pre,post,filter_order,fcut,spike_threshold_std, spike_window,repetition_range,self.queue))
            self.worker.start()
            self.log('Opening {0}'.format(self.filename))
            self.pb = gui.Progressbar(100,autoclose=True,name='Opening and processing file')
            self.pb.show()
        
    def show_data(self):
        params=self.cw.params.get_parameter_tree(True)
        spike_window=params['Spiking Frequency Window Size']
        post=params['Post Stimulus Time']
        pre=params['Pre Stimulus Time']
        electrode_order=numpy.array(params['Electrode Order'])-1
        self.tplothf=1e3*numpy.linspace(0,self.spiking_frqs.shape[1]*spike_window,self.spiking_frqs.shape[1])
        self.tplotlf=1e3*numpy.linspace(0,self.low_frequency_avg.shape[1]/self.fsample,self.low_frequency_avg.shape[1])
        self.nchannels=self.spiking_frqs.shape[0]
        if self.is_movingbar:
            self.stimulus_time_hf = numpy.arange(0,self.ndirections)*self.tplothf.max()/self.ndirections
            self.stimulus_time_lf = numpy.arange(0,self.ndirections)*self.tplotlf.max()/self.ndirections
        else:
            self.stimulus_time_hf = numpy.array([self.tplothf[numpy.where(self.tplothf<pre*1e3)[0].max()],self.tplothf[numpy.where(self.tplothf>self.tplothf.max()-post*1e3)[0].min()]])
            self.stimulus_time_lf = numpy.array([self.tplotlf[numpy.where(self.tplotlf<pre*1e3)[0].max()],self.tplotlf[numpy.where(self.tplotlf>self.tplotlf.max()-post*1e3)[0].min()]])
        self.hf_plots.append(MultiplePlots(None,self.nchannels,params['Electrode Spacing'],stimulus_time=self.stimulus_time_hf))
        self.hf_plots[-1].setWindowTitle('{0} Spiking Frequencies'.format(os.path.basename(self.filename)))
        self.hf_plots[-1].plot(self.tplothf,self.spiking_frqs[electrode_order],label='Hz',spike=True)
        
        self.lf_plots.append(MultiplePlots(None,self.nchannels,params['Electrode Spacing'],stimulus_time=self.stimulus_time_lf))
        self.lf_plots[-1].setWindowTitle('{0} Baselines'.format(os.path.basename(self.filename)))
        mini=numpy.where(self.tplotlf>self.stimulus_time_lf[0])[0].min()
        maxi=numpy.where(self.tplotlf<self.stimulus_time_lf[1])[0].max()
        t=['min={0:0.2f}, dt={1:0.0f}'.format(trace.min(),1000*trace.argmin()/float(self.fsample)) for trace in (self.low_frequency_avg[electrode_order]*1e6)[:,mini:maxi]]
        self.lf_plots[-1].plot(self.tplotlf,self.low_frequency_avg[electrode_order]*1e6,label='uV',text=t)

        self.images.append(MultipleImages(None,self.nchannels,params['Electrode Spacing']))
        self.images[-1].setWindowTitle('{0} Spike Maps'.format(os.path.basename(self.filename)))
        #Color spiking maps
        self.colored_maps=[]
        for i in range(self.spiking_maps.shape[0]):
            self.colored_maps.append(numpy.tile(self.spiking_maps[i],(3,1,1)))
        self.colored_maps=numpy.array(self.colored_maps)
        self.map_coloring_boundaries = numpy.round(self.stimulus_time_hf*1e-3/spike_window)
        if self.map_coloring_boundaries.shape[0]==2:
            self.colored_maps[:,2,self.map_coloring_boundaries[0]:self.map_coloring_boundaries[1],:]=1.0#blue
        else:
            for section in range(self.map_coloring_boundaries.shape[0]):
                end = self.tplothf[-1]*1e-3/spike_window if section+1==self.map_coloring_boundaries.shape[0] else self.map_coloring_boundaries[section+1]
                if section%2==1:continue
                self.colored_maps[:,section/2,self.map_coloring_boundaries[section]:end,:]=1.0
        #Scale maps
        self.scaled_maps=numpy.repeat(self.colored_maps,int(1.0/spike_window),axis=3)
        self.scaled_maps=numpy.rollaxis(self.scaled_maps,1,4)
        self.images[-1].set(self.scaled_maps[electrode_order])
        [img.setScale(spike_window) for img in self.images[-1].imgs]
        
        self.hf_plots[-1].show()
        self.lf_plots[-1].show()
        self.images[-1].show()

    def exit_action(self):
        self.clear_plotwidgets()
        self.close()
            
    def clear_plotwidgets(self):
        widgets=[]
        for w in ['hf_plots', 'lf_plots','images']:
            if hasattr(self, w):
                widgets.extend(getattr(self,w))
        if hasattr(self,'add_note'):
            widgets.append(self.addnote)
        [w.close() for w in widgets]
        if hasattr(self, 'lf_plots'):
            del self.lf_plots
        if hasattr(self, 'hf_plots'):
            del self.hf_plots
        if hasattr(self, 'images'):
            del self.images
        if hasattr(self, 'addnote'):
            del self.addnote
        
    def save_action(self):
        if not hasattr(self, 'spiking_frqs'):
            self.notify_user('Warning','No file opened')
            return
        if hasattr(self,'matsaver') and self.matsaver.is_alive():
            self.notify_user('Warning','Saving in progress')
            return
        data2save = {}
        data2save['parameters']=self.cw.params.get_parameter_tree(True,True)
        data2save['spiking_frqs'] = self.spiking_frqs
        data2save['low_frequency_avg'] = self.low_frequency_avg
        data2save['spiking_maps'] = self.spiking_maps
        data2save['fsample'] = self.fsample
        data2save['note'] = self.note
        data2save.update(self.filedata)
        filename=self.filename.replace(os.path.splitext(self.filename)[1],'.mat')
        self.matsaver=multiprocessing.Process(target=scipy.io.savemat,kwargs={'file_name':filename,'mdict':data2save,'oned_as':'column','do_compression':True})
        self.matsaver.start()
        self.matsaver_started=True
        self.log('Saving to {0}'.format(filename))
        self.pb = gui.Progressbar(self.max_savetime,name='Saving file',timer=True)
        self.pb.show()
        
    def convert_mcd_files_action(self):
        self.mcd_folder=self.ask4foldername('MCD file conversion, select folder', self.cw.root)
        if os.name!='nt':
            self.notify_user('Warning','mcd file conversion is supported only on Windows OS')
            return
        #mcd2raws(self.mcd_folder, self.queue)
        self.mcd_converter=multiprocessing.Process(target=mcd2raws,args=(self.mcd_folder, self.queue))
        self.mcd_converter.start()
        self.mcd_converter_started=True
        self.log('Conversion started')
        self.pb = gui.Progressbar(100,name='Mcd to raw')
        self.pb.show()
        
    def add_note_action(self):
        self.addnote=gui.AddNote(None,self.note)
        self.addnote.connect(self.addnote, QtCore.SIGNAL('addnote'),self.store_note)
        
    def store_note(self,note):
        self.note=note
        
    def reconvert_all_action(self):
        pass

    def concatenate_files_action(self):
        self.files2concatenate = self.ask4filenames('Select raw files to concatenate', self.cw.df.root, '*.raw')
        if len(self.files2concatenate)==0: return
        depths=-numpy.arange(len(ELECTRODE_ORDER))*self.cw.params.get_parameter_tree(True)['Electrode Spacing']*1e6
        selected_depth, ok = QtGui.QInputDialog.getItem(self,'', 'Select electrode', ['{0:.0f} um'.format(depth) for depth in depths])
        if not ok: return
        self.selected_electrode = ELECTRODE_ORDER[numpy.where(depths==float(str(selected_depth).split(' ')[0]))[0][0]]
        self.log('Electrode {0} selected'.format(self.selected_electrode))
        outfile=concatenate_rawfiles(self.files2concatenate,self.selected_electrode-1)
        self.log('Concatenated data saved to {0}'.format(outfile))
        
    def close_plots_action(self):
        self.clear_plotwidgets()
        self.lf_plots=[]
        self.hf_plots=[]
        self.images=[]

if __name__=='__main__':
    if len(sys.argv)==1:
        unittest.main()
    else:
        g=ElphysViewer()
