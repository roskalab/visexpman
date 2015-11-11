import sys
import subprocess,tempfile,os,unittest,numpy,scipy.io,scipy.signal
from pylab import *

import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import pyqtgraph

from visexpman.engine.generic import fileop,introspect,gui

def mcd2raw(filename):
    cmdfile=os.path.join(fileop.visexpman_package_path(), 'data', 'mcd2raw16.cmd')
    cmdfiletxt=fileop.read_text_file(cmdfile)
    outfile=os.path.join(tempfile.gettempdir(),os.path.basename(filename).replace('.mcd','.raw'))
    cmdfiletxt=cmdfiletxt.replace('infile', filename).replace('outfile', outfile)
    tmpcmdfile=os.path.join(tempfile.gettempdir(), 'cmd.cmd')
    fileop.write_text_file(tmpcmdfile, cmdfiletxt)
    mcdatatoolpath='c:\\Program Files (x86)\\Multi Channel Systems\\MC_DataTool\MC_DataTool'
    cmd='"{0}" -file {1}'.format(mcdatatoolpath, tmpcmdfile)
    if subprocess.call(cmd, shell=True) == 0:
        return outfile
        
def read_raw(filename):
    header=[]
    with open(filename) as f:
        for line in f:
            header.append(line)
            if 'EOH' in line:
                headerlen=len(''.join(header))
                f.seek(headerlen)
                data=numpy.fromfile(f,dtype=numpy.int16)
                break
    sample_rate=float([item for item in header if 'Sample rate = ' in item][0].split('=')[1])
    ad_scaling=float([item for item in header if 'El = ' in item][0].split('=')[2].split('\xb5V')[0])*1e-6
    channel_names=[item for item in header if 'Streams = ' in item][0].split('=')[1].strip().split(';')
    if data.shape[0]%len(channel_names) != 0:
        raise IOError('Invalid data in {0}. Datapoints: {1}, Channels: {2}'.format(filename, data.shape[0], nchannels))
    data=data.reshape((data.shape[0]/len(channel_names),len(channel_names))).T
    digital=data[0]+2**15
    elphys=data[1:]
    t=numpy.linspace(0,digital.shape[0]/sample_rate,digital.shape[0])
    return t,digital,elphys,channel_names,sample_rate,ad_scaling
    
def repetition_boundaries(digital,fsample,pre,post):
    pres=int(pre*fsample)
    posts=int(post*fsample)
    edges=numpy.nonzero(numpy.diff(digital))[0]
    edges[0::2]-=pres
    edges[1::2]+=posts
    return edges
    
def extract_repetitions(digital,elphys,fsample,pre,post):
    edges=repetition_boundaries(digital, fsample,pre,post)
    fragments = numpy.split(elphys,edges,axis=1)[1::2]
    fragment_length=min([f.shape[1] for f in fragments])
    repetitions = numpy.array([f[:,:fragment_length] for f in fragments])
    return repetitions
    
def save2mat(filename,**datafields):
    field_names=['t','digital','elphys','channel_names','sample_rate','ad_scaling,repetitions']
    scipy.io.savemat(filename,datafields,oned_as='column',do_compression=True)
    
def filter_trace(pars):
    lowpass, highpass,signal=pars
    lowpassfiltered=scipy.signal.filtfilt(lowpass[0],lowpass[1], signal).real
    highpassfiltered=scipy.signal.filtfilt(highpass[0],highpass[1], signal).real
    return lowpassfiltered, highpassfiltered
    
def filter(elphys, cutoff,order,fs,pool=None):
    lowpass=scipy.signal.butter(order,cutoff/fs,'low')
    highpass=scipy.signal.butter(order,cutoff/fs,'high')
    lowpassfiltered=numpy.zeros_like(elphys)
    highpassfiltered=numpy.zeros_like(elphys)
    import multiprocessing
    if pool is None:
        pool=multiprocessing.Pool(introspect.get_available_process_cores())
    pars=[(lowpass,highpass,elphys[i]) for i in range(elphys.shape[0])]
    res=pool.map(filter_trace,pars)
    pool.terminate()
    for i in range(len(res)):
        lowpassfiltered[i]=res[i][0]
        highpassfiltered[i]=res[i][1]
    return lowpassfiltered, highpassfiltered
       
def raw2spikes(filename,pre,post,filter_order,fcut,spike_threshold_std, spike_window_time):
    '''
    1) Extract data from raw file
    2) Filter signal, separate baseline and high frequency part
    3) Low frequency part: average repetitions
    4) High frequency part: detect spikes
    5) Split spikes to repetitions and aggregate them
    6) Calculate spiking frq
    '''
    t,digital,elphys,channel_names,sample_rate,ad_scaling = read_raw(filename)
    l,h=filter(elphys,fcut,filter_order,sample_rate)
    low_frequency_avg=extract_repetitions(digital,l,sample_rate,pre,post).mean(axis=0)
    #threshold for spike detection:
    threshold=h.std(axis=1)*spike_threshold_std
    thresholded=(h.T-threshold).T
    binary=numpy.where(thresholded>0,1,0)
    #Extract spike times:
    spike_indexes=numpy.where(numpy.diff(binary,axis=1)==1)
    spike_times=[spike_indexes[1][numpy.where(spike_indexes[0]==channel)[0]] for channel in set(spike_indexes[0])]
    edges=repetition_boundaries(digital, sample_rate,pre,post)
    nrepetitions=edges.shape[0]/2
    repetition_window_length=numpy.diff(edges)[::2].max()
    spike_binnings=int(spike_window_time*sample_rate)
    bins=numpy.arange(repetition_window_length/spike_binnings)*spike_binnings
    trep=(bins+0.5*spike_binnings)/sample_rate
    spiking_frqs=[]
    spiking_maps = []
    for channel in range(len(spike_times)):
        aggr_per_channel=[]
        spiking_map=numpy.zeros((nrepetitions, repetition_window_length), dtype=numpy.uint8)
        for rep in numpy.arange(nrepetitions)*2:
            start=edges[rep]
            end=edges[rep+1]
            spike_times_in_rep = spike_times[channel][numpy.where(numpy.logical_and(spike_times[channel]>start,spike_times[channel]<end))[0]]
            spike_times_in_rep-=start
            aggr_per_channel.extend(list(spike_times_in_rep))
            spiking_map[rep/2][spike_times_in_rep]=1
        spiking_maps.append(spiking_map)
        hist,bins=numpy.histogram(aggr_per_channel,bins)
        spiking_frq=hist/spike_window_time/edges.shape[0]/2
        spiking_frqs.append(spiking_frq)
    spiking_frqs=numpy.array(spiking_frqs)
    return spiking_frqs,low_frequency_avg,spiking_maps
    
class ElphysViewerFunctions(unittest.TestCase):
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
        wf=unittest_aggregator.prepare_test_data('mcdraw')
        for f in fileop.listdir_fullpath(wf):
            raw2spikes(f,200e-3,200e-3,3,300,2,5e-3)
#            t,digital,elphys,channel_names,sample_rate,ad_scaling = read_raw(f)
#            self.assertEqual(t.shape[0],digital.shape[0])
#            self.assertEqual(elphys.shape[0]+1,len(channel_names))
#            repetitions=extract_repetitions(digital,elphys,sample_rate,200e-3,200e-3)
#            self.assertTrue(all([r.shape[1] for r in repetitions]))#All elements equal
#            data2mat={}
#            data2mat['t']=t
#            data2mat['digital']=digital
#            data2mat['elphys']=elphys
#            data2mat['channel_names']=channel_names
#            data2mat['sample_rate']=sample_rate
#            data2mat['ad_scaling']=ad_scaling
#            
#            l,h=filter(elphys, 300,3,sample_rate)
#            
#            save2mat(os.path.join('/tmp',os.path.basename(f)).replace('.raw','.mat'),**data2mat)
            
    
            
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
    def __init__(self,parent,nplots):
        pyqtgraph.GraphicsLayoutWidget.__init__(self,parent)
        self.nplots=nplots
        self.setBackground((255,255,255))
        self.setAntialiasing(True)
        self.plots=[]
        for i in range(nplots):
            p=self.addPlot()
            p.enableAutoRange()
            p.showGrid(True,True,1.0)
            self.plots.append(p)
            if (i+1)%2==0 and i!=0:
                self.nextRow()
            
class CWidget(QtGui.QWidget):
    '''
    The central widget of the user interface which contains the image, the plot and the various controls for starting experiment or adjusting parameters
    '''
    def __init__(self,parent):
        QtGui.QWidget.__init__(self,parent)
        self.df=DataFileBrowser(self,'/home/rz/rzws/dataslow/elphys_viewer',['mat', 'mcd', 'raw'])
        self.df.setMinimumWidth(400)
        self.df.setMaximumWidth(500)
        self.df.setMinimumHeight(400)
        params_config=[\
                {'name': 'Filter Order', 'type': 'int', 'value': 3},
                {'name': 'Filter Cut Frequency', 'type': 'float', 'value': 300, 'siPrefix': True, 'suffix': 'Hz'},
                {'name': 'Spike Threshold', 'type': 'float', 'value': 3, 'suffix': 'std','siPrefix': True},
                {'name': 'Spiking Frequency Window Size', 'type': 'float', 'value': 5e-3, 'suffix': 's','siPrefix': True},
                {'name': 'Pre Stimulus Time', 'type': 'float', 'value': 200e-3, 'suffix': 's','siPrefix': True},
                {'name': 'Post Stimulus Time', 'type': 'float', 'value': 200e-3, 'suffix': 's','siPrefix': True},
                    ]

        self.params = gui.ParameterTable(self, params_config)
        self.params.setMinimumWidth(400)
        self.params.setMaximumWidth(500)
        self.params.setMaximumHeight(300)
        self.plots=MultiplePlots(self,16)
        self.plots.setMinimumWidth(800)
        
        self.l = QtGui.QGridLayout()
        self.l.addWidget(self.df, 0, 0, 1, 1)
        self.l.addWidget(self.params, 1, 0, 1, 1)
        self.l.addWidget(self.plots, 0, 2, 2, 1)
        
        self.setLayout(self.l)

class ElphysViewer(gui.SimpleAppWindow):
    #TODO: context
    #TODO: save params to file
    #TODO figure out stim type
    #TODO give warning when filter params are changed!!!
    def init_gui(self):
        self.toolbar = gui.ToolBar(self, ['add_note', 'save','reconvert_all', 'concatenate_files', 'exit'])
        TOOLBAR_HELP = '''
        Add Note: note will be saved to currently open file
        Save: 
        Reconvert All: With current settings apply filtering/spike detection/calculation for all files in selected folder
        Concatenate Files: concatenate electrophysiology traces in all files in a selected folder and save to a raw format.
        '''
        self.addToolBar(self.toolbar)
        self.toolbar.setToolTip(TOOLBAR_HELP)
        self.setWindowTitle('Electrophyisiology Datafile Viewer')
        self.cw=CWidget(self)
        self.setCentralWidget(self.cw)
        self.debugw.setMinimumWidth(800)
        self.debugw.setMinimumHeight(250)
        self.setMinimumWidth(1200)
        self.setMinimumHeight(750)
        self.maximized=True
        self.cw.df.filetree.doubleClicked.connect(self.open_file)
        import multiprocessing
        self.pool=multiprocessing.Pool(introspect.get_available_process_cores())
        
    def open_file(self, index):
        self.filename = gui.index2filename(index)
        if os.path.isdir(self.filename): return#Double click on folder is ignored
        ext = fileop.file_extension(self.filename)
        params=self.cw.params.get_parameter_tree(True)
        if ext == 'raw':
            pre=params['Pre Stimulus Time']
            post=params['Post Stimulus Time']
            filter_order=params['Filter Order']
            fcut=params['Filter Cut Frequency']
            spike_threshold_std=params['Spike Threshold']
            spike_window_time=params['Spiking Frequency Window Size']
            self.pb = gui.Progressbar(10)
            self.pb.show()

            self.spiking_frqs,self.low_frequency_avg,self.spiking_maps = raw2spikes(self.filename,pre,post,filter_order,fcut,spike_threshold_std, spike_window_time)
            
        elif ext == 'mat':
            data=scipy.io.loadmat(self.filename,mat_dtype=True)
            fnflatten=['sample_rate','ad_scaling']
            for fni in fnflatten:
                setattr(self, fni, data[fni].flatten()[0])
            self.digital=data['digital'].flatten()
            self.t=data['t'].flatten()
            self.elphys=data['elphys'].flatten()
            self.log('{0} opened'.format(self.filename))

            

    def exit_action(self):
        self.close()
        
    def save_action(self):
        pass
        
    def add_note_action(self):
        pass
        
    def reconvert_all_action(self):
        pass

    def concatenate_files_action(self):
        pass

if __name__=='__main__':
    if len(sys.argv)==1:
        unittest.main()
    else:
        g=ElphysViewer()
