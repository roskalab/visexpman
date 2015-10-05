import os,time,threading,socket,Queue
import numpy,scipy.io
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from pyqtgraph.parametertree import Parameter, ParameterTree
from visexpman.engine.generic import gui,utils,videofile,configuration
from visexpman.engine.hardware_interface import daq_instrument

class ElphysConfig(object):
    def __init__(self):
        self.INITIAL_RECORDING_DELAY=5.0
        self.POST_RECORD_TIME=5.0
        self.IMAGING_IP = '172.27.26.40'#'127.0.0.1'

class CWidget(QtGui.QWidget):
    def __init__(self,parent):
        QtGui.QWidget.__init__(self,parent)
        self.plotw=gui.Plot(self)
        self.plotw.setFixedWidth(600)
        self.plotw.setFixedHeight(300)
        self.parametersw = ParameterTree(self, showHeader=False)
        self.parametersw.setFixedWidth(300)
        self.parametersw.setFixedHeight(300)
        params = [
                    {'name': 'Clamp Mode', 'type': 'list', 'value': 'current', 'values': ['I','U']},
                    {'name': 'Waveform', 'type': 'list', 'value': 'square', 'values': ['square','from file']},
                    {'name': 'Sampling Rate', 'type': 'float', 'value': 10000.0, 'suffix': ' Hz' },
                    {'name': 'Voltage Clamp Gain', 'type': 'float', 'value': 20, 'suffix': ' mV/V' },
                    {'name': 'Current Clamp Gain', 'type': 'float', 'value': 400.0, 'suffix': ' pA/V' },
                    {'name': 'Imaging IP Address', 'type': 'str', 'value': parent.config.IMAGING_IP},
                    {'name': 'Enable Imaging', 'type': 'bool', 'value': True},
                    {'name': 'Square Signal', 'type': 'group', 'expanded' : True, 'children': [
                    {'name': 'Amplitude', 'type': 'float', 'value': 1,  'suffix': ' mV or pA'},
                    {'name': 'Pulse Width', 'type': 'float', 'value': 20,  'suffix': ' ms'},
                    {'name': 'Frequency', 'type': 'float', 'value': 10,  'suffix': ' Hz'},
                    {'name': 'Number of Pulses', 'type': 'int', 'value': 5},
                                                                                                ]}]
        self.parameters = Parameter.create(name='params', type='group', children=params)
        self.parametersw.setParameters(self.parameters, showTop=False)
        self.start_experiment = QtGui.QPushButton('Start Experiment', parent=self)
        self.select_folder = QtGui.QPushButton('Data Save Folder', parent=self)
        self.load_waveform= QtGui.QPushButton('Load Waveform', parent=self)
        self.recording_name= gui.LabeledInput(self, 'Recording Name')
        self.recording_name.input.setMinimumWidth(100)
        self.selected_folder = QtGui.QLabel('', self)
        self.open_recording = QtGui.QPushButton('Open Recording', parent=self)
        self.l = QtGui.QGridLayout()
        self.l.addWidget(self.plotw, 0, 0, 2, 4)
        self.l.addWidget(self.parametersw, 0, 4, 2, 2)
        self.l.addWidget(self.select_folder, 2, 0, 1, 1)
        self.l.addWidget(self.selected_folder, 3, 0, 1, 1)
        self.l.addWidget(self.load_waveform, 2, 1, 1, 1)
        self.l.addWidget(self.recording_name, 2, 2, 1, 1)
        self.l.addWidget(self.start_experiment, 2, 3, 1, 1)
        self.l.addWidget(self.open_recording, 2, 4, 1, 1)
        self.setLayout(self.l)
        
class DaqRecorder(threading.Thread):
    def __init__(self, waveform, sample_rate, ai_channel,ao_channel,trigger_message,imaging_ip,result):
        threading.Thread.__init__(self)
        self.waveform=waveform
        self.sample_rate=sample_rate
        self.ai_channel=ai_channel
        self.ao_channel=ao_channel
        self.trigger_message=trigger_message
        self.imaging_ip=imaging_ip
        self.result=result
        
    def run(self):
        recording=daq_instrument.analogio(self.ai_channel,self.ao_channel,self.sample_rate,self.waveform,timeout=1,action=self.trigger_imaging)
        self.result.put(recording)
        
    def trigger_imaging(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(self.trigger_message, (self.imaging_ip, 446))
        

class ElphysUI(gui.SimpleAppWindow):
    def init_gui(self):
        self.config=ElphysConfig()
        self.setWindowTitle('Electrophysiology')
        self.cw=CWidget(self)
        self.setCentralWidget(self.cw)
        self.resize(800,500)
        self.cw.parameters.sigTreeStateChanged.connect(self.parameter_changed)
        self.connect(self.cw.select_folder, QtCore.SIGNAL('clicked()'), self.select_folder)
        self.connect(self.cw.load_waveform, QtCore.SIGNAL('clicked()'), self.load_waveform)
        self.connect(self.cw.start_experiment, QtCore.SIGNAL('clicked()'), self.start_experiment)
        self.connect(self.cw.open_recording, QtCore.SIGNAL('clicked()'), self.open_recording)
        
        self.calculate_clamp_signal(self.cw.parameters)
        self.default_folder='c:\\' if os.name=='nt' else '/'
        self.output_folder=self.default_folder
        self.cw.selected_folder.setText(self.output_folder)

        self.finish_experiment_timer = QtCore.QTimer()#Makes sure that whole logfile is always displayed on screen
        self.finish_experiment_timer.timeout.connect(self.finish_experiment)
        self.finish_experiment_timer.start(800)
        self.running=False

    def parameter_changed(self, param, changes):
        self.calculate_clamp_signal(param)
        
    def calculate_clamp_signal(self, param):
        self.signal_name=[p for p in param.children() if p.name()=='Waveform'][0].value()
        if self.signal_name == 'square':
            self.square_params=dict([[p.name(), p.value()] for p in [p for p in param.children() if p.name()=='Square Signal'][0].children()])
            sr=[p for p in param.children() if p.name()=='Sampling Rate'][0].value()
            self.sample_rate=sr
            onsamples=self.square_params['Pulse Width']*1e-3*sr
            offsamples=sr/self.square_params['Frequency']-onsamples
            if offsamples<0:
                self.log('Decrease square signal frequency or pulse width')
                return
            self.clamp_signal = numpy.tile(numpy.concatenate((numpy.ones(onsamples),numpy.zeros(offsamples))), self.square_params['Number of Pulses'])
            self.clamp_signal = numpy.concatenate((numpy.zeros(offsamples), self.clamp_signal))*self.square_params['Amplitude']
            self.clamp_mode=[p for p in param.children() if p.name()=='Clamp Mode'][0].value()
            if self.clamp_mode=='I':
                factor=[p for p in param.children() if p.name()=='Current Clamp Gain'][0].value()*1e-12
            elif self.clamp_mode=='U':
                factor=[p for p in param.children() if p.name()=='Voltage Clamp Gain'][0].value()*1e-3
            self.clamp_signal_command = self.clamp_signal*factor
            self.clamp_signal_command=numpy.concatenate((numpy.zeros(self.config.INITIAL_RECORDING_DELAY*sr),self.clamp_signal_command, numpy.zeros(self.config.POST_RECORD_TIME*sr)))
            self.clamp_signal_t = numpy.arange(self.clamp_signal.shape[0])/sr
            self.cw.plotw.update_curve(self.clamp_signal_t,self.clamp_signal, pen=(0,150,0))
        elif self.signal_name == 'from file':
            pass
            
    def select_folder(self):
        self.output_folder=self.ask4foldername('Select output folder', self.default_folder)            
        self.cw.selected_folder.setText(self.output_folder)
        
    def load_waveform(self):
        self.waveform_file=self.ask4filename('Select waveform file', self.default_folder, '*.txt')
        self.log('{0} file loaded'.format(self.waveform_file))
        
    def open_recording(self):
        self.openfile=self.ask4filename('Select recording', self.default_folder, '*.mat')
        self.log('{0} file opened'.format(self.openfile))
        
    def start_experiment(self):
        '''
        1) Start daq recording (insert initial delay)
        2) Start imaging
        3) Daq recording ends
        4) Collect imaging datafile
        5) Save to datafile and display results
        '''
        recording_name=str(self.cw.recording_name.input.text())
        fileformat='mat'
        self.recording_filename=os.path.join(self.output_folder, '{0}_{1}.{2}'.format(recording_name, utils.timestamp2ymdhms(time.time(), filename=True), fileformat))
        self.calculate_clamp_signal(self.cw.parameters)
        imaging_ip=[p for p in self.cw.parameters.children() if p.name()=='Imaging IP Address'][0].value()
        imaging_duration=self.clamp_signal.shape[0]/self.sample_rate+self.config.INITIAL_RECORDING_DELAY
        self.imaging_filename = self.recording_filename.replace('.'+fileformat,'')
        trigger_message='sec {0} filename {1}'.format(imaging_duration,self.imaging_filename)
        self.recordingq=Queue.Queue()
        #ai5: y sacnner signal
        self.daq=DaqRecorder(self.clamp_signal_command, self.sample_rate, 'Dev1/ai1:6','Dev1/ao1',trigger_message, imaging_ip,self.recordingq)
        self.daq.start()
        self.running=True
        self.log('Recording started, trigger message: {0}'.format(trigger_message))
        
    def finish_experiment(self):
        if self.running:
            self.daq.join()
            self.log('Recording finished')
            self.running=False
            if self.recordingq.empty():
                self.log('No response from recorded thread','error')
                return
            recording=self.recordingq.get()
            data2save={}
            data2save['recorded']=recording
            data2save['clamp_signal']=self.clamp_signal
            data2save['clamp_signal_command']= self.clamp_signal_command
            data2save['imaging_filename']= self.imaging_filename
            data2save['waveform_name']= self.signal_name
            data2save['sample_rate']= self.sample_rate
            data2save['clamp_mode']= self.clamp_mode
            data2save['current_clamp_gain'] = [p for p in self.cw.parameters.children() if p.name()=='Current Clamp Gain'][0].value()
            data2save['voltage_clamp_gain'] = [p for p in self.cw.parameters.children() if p.name()=='Voltage Clamp Gain'][0].value()
            scipy.io.savemat(self.recording_filename, data2save,oned_as='row')
            self.log('Data saved to {0}'.format(self.recording_filename))

if __name__ == '__main__':
    gui = ElphysUI()
