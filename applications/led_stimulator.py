try:
    import PyDAQmx
    import PyDAQmx.DAQmxConstants as DAQmxConstants
    import PyDAQmx.DAQmxTypes as DAQmxTypes
except ImportError:
    pass
import os,logging,numpy,copy,pyqtgraph,scipy.signal,scipy.io,time
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from visexpman.engine.generic import gui, signal,utils
from visexpman.engine.analysis import elphys

class CWidget(QtGui.QWidget):
    def __init__(self,parent):
        QtGui.QWidget.__init__(self,parent)
        self.plotw=gui.Plot(self)
        self.plotw.setFixedWidth(950)
        self.plotw.setFixedHeight(200)
        self.plotw.plot.setTitle('Raw')
        self.plotw.plot.setLabels(left='mV', bottom='ms')
        self.plotfiltered={}
        for pn in ['Spike', 'Field Potential']:
            self.plotfiltered[pn]=gui.Plot(self)
            self.plotfiltered[pn].setFixedWidth(950)
            self.plotfiltered[pn].setFixedHeight(180)
            self.plotfiltered[pn].plot.setTitle(pn)
            self.plotfiltered[pn].plot.setLabels(left='mV', bottom='ms')
        params = [
                    {'name': 'Left LED', 'type': 'bool', 'value': True,},
                    {'name': 'Right LED', 'type': 'bool', 'value': True,},
                    {'name': 'Enable Average', 'type': 'bool', 'value': True,},
                    {'name': 'Stimulus Rate', 'type': 'int', 'value': 2, 'suffix': 'Hz', 'siPrefix': True},
                    {'name': 'LED on time', 'type': 'float', 'value': 100, 'suffix': 'ms', 'siPrefix': True},
                    {'name': 'Sample Rate', 'type': 'int', 'value': 20000, 'suffix': 'Hz', 'siPrefix': True},
                    {'name': 'Phase Shift', 'type': 'int', 'value': 0, 'suffix': 'deg', 'siPrefix': True},
                    {'name': 'Filter Frequency', 'type': 'int', 'value': 100, 'suffix': 'Hz', 'siPrefix': True},
                    {'name': 'Enable Filter', 'type': 'bool', 'value': True,},
                    {'name': 'LED Voltage', 'type': 'float', 'value': 5, 'suffix': 'V', 'siPrefix': True},
                    {'name': 'Advanced', 'type': 'group', 'expanded' : True, 'children': [
                                {'name': 'Filter Order', 'type': 'int', 'value': 3},
                                {'name': 'Tmin', 'type': 'float', 'value': 1.0, 'suffix': 's', 'siPrefix': True},
                                {'name': 'Psths bin time', 'type': 'float', 'value': 0.1, 'suffix': 's', 'siPrefix': True},
                                {'name': 'Spike Threshold', 'type': 'float', 'value': 4, 'suffix': 'mV', 'siPrefix': True},
                                {'name': 'DAQ device', 'type': 'str', 'value': 'Dev1'},
                                {'name': 'Simulate', 'type': 'bool', 'value': False,},
                                {'name': 'Buffer Size', 'type': 'int', 'value': 100,},
                                ]},]
        self.parametersw = gui.ParameterTable(self, params)
        self.parametersw.setFixedWidth(230)
        self.parametersw.setFixedHeight(400)
        self.l = QtGui.QGridLayout()#Organize the above created widgets into a layout
        self.l.addWidget(self.plotw, 0, 1, 1, 5)
        ct=0
        for v in self.plotfiltered.values():
            self.l.addWidget(v, ct+1, 1, 1, 5)
            ct+=1
        self.l.addWidget(self.parametersw, 0, 0, 2, 1)
        self.setLayout(self.l)

class LEDStimulator(gui.SimpleAppWindow):
    def init_gui(self):
        self.setWindowTitle('LED Stimulator')
        self.cw=CWidget(self)
        self.setCentralWidget(self.cw)
        self.cw.parametersw.params.sigTreeStateChanged.connect(self.settings_changed)
        self.setGeometry(30, 30, 1000,700)
        icon_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'icons')
        self.toolbar = gui.ToolBar(self, ['start', 'stop','save', 'exit'], icon_folder = icon_folder)
        self.toolbar.setToolTip('''
        Connections:
            AI0: Left LED
            AI2: Right LED
            AI1: amplifier's output
            AO0: Left LED
            AO1: Right LED
        Usage:
            1. Enable LEDs
            2. Adjust stimulation frequency
            3. Press start button
            4. Press stop and start for restaring averaging
        ''')
        self.addToolBar(self.toolbar)
        self.settings_changed()
        self.ao_sample_rate=1000
        self.daq_timeout=1
        self.running=False
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)
        self.counter=0

    def settings_changed(self):
        self.settings = self.cw.parametersw.get_parameter_tree(True)

    def start_action(self):
        if self.running:
            return
        logging.info('start')
        if self.generate_waveform():
            self.lowpass=scipy.signal.butter(self.settings['Filter Order'],float(self.settings['Filter Frequency'])/self.settings['Sample Rate'],'low')
            self.highpass=scipy.signal.butter(self.settings['Filter Order'],float(self.settings['Filter Frequency'])/self.settings['Sample Rate'],'high')
            self.sigs=[]
            self.ai_trace=numpy.empty((0, 3))
            self.running=True
            self.init_daq()
            self.start_daq()
            self.timer.start(int(1000*(self.tperiod)))

    def stop_action(self):
        if not self.running:
            return
        self.close_daq()
        logging.info('stop')
        self.running=False
        
    def save_action(self):
        if self.running:
            return
        self.foldername=self.ask4foldername('Select save location of current waveform', 'c:\\')
        if os.path.exists(self.foldername):
            gui.text_input_popup(self, 'Specify file name', 'file name', self.save_traces)
            
    def save_traces(self):
        name=str(self.w.input.input.text())
        if len(name)==0:
            name='untitled'
        name+='_'+utils.timestamp2ymdhms(time.time(), filename=True)
        self.w.close()
        filename=os.path.join(self.foldername, name+'.mat')
        if not hasattr(self, 't'):
            self.notify('Warning', 'No data to save')
            return
        scipy.io.savemat(filename, {'time': self.t, 'signals': self.signals})
        logging.info('Traces are saved to {0}'.format(filename))
        
    def exit_action(self):
        if self.running:
            self.stop_action()
        self.close()
        
    def generate_waveform(self):
        if (self.settings['Left LED'] or self.settings['Right LED'])==False:
            self.notify('Warning', 'Please enable at least one LED')
            return False
        tperiod=1.0/self.settings['Stimulus Rate']
        phase_shift=int(tperiod*self.ao_sample_rate*self.settings['Phase Shift']/360.)
        duty_cycle=self.settings['LED on time']*1e-3/tperiod
        nrepeats=numpy.ceil(self.settings['Tmin']/tperiod)
        self.waveform=self.settings['LED Voltage']*numpy.tile(numpy.concatenate((numpy.ones(int(tperiod*self.ao_sample_rate*duty_cycle)),
                numpy.zeros(int(tperiod*self.ao_sample_rate*(1-duty_cycle))))), nrepeats)
        phase_shifted=numpy.roll(self.waveform, phase_shift)
        self.waveform=numpy.array([self.waveform,phase_shifted])
        enable_mask=numpy.array([[self.settings['Left LED'],self.settings['Right LED']]]).T
        self.waveform*=enable_mask
        self.tperiod=self.waveform.shape[1]/float(self.ao_sample_rate)
        logging.info('Period time is {0:0.2f}'.format(self.tperiod))
        return True
        
    def process_ai_trace(self):
        '''
        Cut signal across rising edges of channel 0 (led left)
        
        '''
        buffer_size=self.settings['Buffer Size']
        trig=self.ai_trace[:, 1]
        edges=signal.detect_edges(trig,0.5*trig.max())
        if trig[0]>0.5*trig.max():
            edges=numpy.insert(edges, 0, 0)
        rising_edges=edges[::2]
        if rising_edges.shape[0]<2:
            return False
        if not all(trig[rising_edges-1]<trig[rising_edges]):
            self.notify('Error','Corrupted led control signal, recording will be automatically terminated')
            self.stop_action()
            return
        nperiods=rising_edges.shape[0]-1
        sections=numpy.split(self.ai_trace, rising_edges)[1:-1]
        section_length=min([s.shape[0] for s in sections])
        max_data_size=(buffer_size-0.2)*section_length
        if max_data_size<self.ai_trace.shape[0]:
            logging.info('cut data')
            self.ai_trace=self.ai_trace[-max_data_size:, :]
        self.cut2repeats=numpy.array([s[:section_length] for s in sections])#Dimensions: repeat, time, channel
        if self.settings['Simulate']:
            r=int(40e3/self.settings['Sample Rate'])
            sig=numpy.load(os.path.join(os.path.dirname(__file__),'..', 'data', 'test', 'lfp_mv_40kHz.npy'))[::r]
            repeat=numpy.int(numpy.ceil(section_length/float(sig.shape[0])))
            sig=numpy.tile(sig,repeat)[:section_length]
            for i in range(self.cut2repeats.shape[0]):
                self.cut2repeats[i, :, 2]=sig[:section_length]+numpy.random.random(section_length)+i*1e-3
        self.signals={}
        self.signals['last']={}
        self.signals['mean']={}
        self.signals['last']['elphys']=self.cut2repeats[-1, :, 2]
        self.signals['last']['left']=self.cut2repeats[-1, :, 0]
        self.signals['last']['right']=self.cut2repeats[-1, :, 1]
        self.signals['mean']['elphys']=self.cut2repeats[:, :, 2].mean(axis=0)
        self.t=signal.time_series(int(section_length), self.settings['Sample Rate'])*1e3
        return True
        
    def update(self):
        if self.running:
            ai_data=self.read_daq()
            logging.info(ai_data.shape)
            self.ai_trace=numpy.concatenate((self.ai_trace, ai_data))
            if not self.process_ai_trace():
                return
            if self.settings['Enable Filter']:
                self.lowpassfiltered=scipy.signal.filtfilt(self.lowpass[0],self.lowpass[1], self.signals['last']['elphys']).real
                self.highpassfiltered=scipy.signal.filtfilt(self.highpass[0],self.highpass[1], self.signals['last']['elphys']).real            
            k='mean' if self.settings['Enable Average'] else 'last'
            pp=[{'name': 'elphys', 'pen':pyqtgraph.mkPen(color=(255,150,0), width=0)},{'name': 'left', 'pen': pyqtgraph.mkPen(color=(10,20,30), width=3)}, 
                    {'name': 'right', 'pen': pyqtgraph.mkPen(color=(10,100,30), width=3)}]
            self.cw.plotw.update_curves(3*[self.t], [self.signals[k]['elphys'],self.signals['last']['left'],  self.signals['last']['right']],plotparams=pp)
            if self.settings['Enable Filter']:
                self.cw.plotfiltered['Field Potential'].update_curves(3*[self.t], [self.lowpassfiltered,self.signals['last']['left'],  self.signals['last']['right']],plotparams=pp)
                self.cw.plotfiltered['Spike'].update_curves(3*[self.t], [self.highpassfiltered,self.signals['last']['left'],  self.signals['last']['right']],plotparams=pp)
        
    def init_daq(self):
        self.analog_output = PyDAQmx.Task()
        self.analog_output.CreateAOVoltageChan('{0}/ao0:1'.format(self.settings['DAQ device']),
                                                            'ao',
                                                            0,
                                                            5.0,
                                                            DAQmxConstants.DAQmx_Val_Volts,
                                                            None)
        self.analog_input = PyDAQmx.Task()
        if self.settings['Left LED'] and self.settings['Right LED']:
            self.elphys_channel_index=1
            ch1=0
            ch2=1
        elif self.settings['Left LED'] and not self.settings['Right LED']:
            self.elphys_channel_index=1
            ch1=0
            ch2=1
        elif not self.settings['Left LED'] and self.settings['Right LED']:
            self.elphys_channel_index=0
            ch1=1
            ch2=2
        ch1=0
        ch2=2
        self.elphys_channel_index=1
        self.number_of_ai_channels=3
        ai_channels='{0}/ai{1}:{2}' .format(self.settings['DAQ device'], ch1, ch2)
        self.analog_input.CreateAIVoltageChan(ai_channels,
                                                'ai',
                                                DAQmxConstants.DAQmx_Val_RSE,
                                                -5.0,
                                                5.0,
                                                DAQmxConstants.DAQmx_Val_Volts,
                                                None)
        #self.analog_output.CfgDigEdgeStartTrig('/{0}/PFI0' .format(self.settings['DAQ device']), DAQmxConstants.DAQmx_Val_Rising)
        #self.analog_input.CfgDigEdgeStartTrig('/{0}/PFI1' .format(self.settings['DAQ device']), DAQmxConstants.DAQmx_Val_Rising)
        self.read = DAQmxTypes.int32()

    def start_daq(self):
        self.number_of_ao_samples=self.waveform.shape[1]
        self.number_of_ai_samples=int(self.waveform.shape[1]/float(self.ao_sample_rate)*self.settings['Sample Rate'])
        self.analog_output.CfgSampClkTiming("OnboardClock",
                                    self.ao_sample_rate,
                                    DAQmxConstants.DAQmx_Val_Rising,
                                    DAQmxConstants.DAQmx_Val_ContSamps,
                                    self.number_of_ao_samples)
        self.analog_input.CfgSampClkTiming("OnboardClock",
                                    self.settings['Sample Rate'],
                                    DAQmxConstants.DAQmx_Val_Rising,
                                    DAQmxConstants.DAQmx_Val_ContSamps,
                                    self.number_of_ai_samples)
        self.analog_output.WriteAnalogF64(self.number_of_ao_samples,
                                False,
                                self.daq_timeout,
                                DAQmxConstants.DAQmx_Val_GroupByChannel,
                                self.waveform,
                                None,
                                None)
        self.analog_input.StartTask()
        self.analog_output.StartTask()

    def read_daq(self):
        samples_to_read = self.number_of_ai_samples * self.number_of_ai_channels
        self.ai_data = numpy.zeros(self.number_of_ai_samples*self.number_of_ai_channels, dtype=numpy.float64)
        try:
            self.analog_input.ReadAnalogF64(self.number_of_ai_samples,
                                        self.daq_timeout,
                                        DAQmxConstants.DAQmx_Val_GroupByChannel,
                                        self.ai_data,
                                        samples_to_read,
                                        DAQmxTypes.byref(self.read),
                                        None)
        except PyDAQmx.DAQError:
            logging.error('Skipping data')
            import traceback
            logging.error(traceback.format_exc())
            return
        ai_data = self.ai_data[:self.read.value * self.number_of_ai_channels]
        ai_data = copy.deepcopy(ai_data.flatten('F').reshape((self.number_of_ai_channels, self.read.value)).transpose())
        return ai_data
        
    def close_daq(self):
        self.analog_output.ClearTask()
        self.analog_input.ClearTask()
    
    def show_psths(self):
        if self.settings['Enable Filter']:
            h,b,self.tspikerel=elphys.peristimulus_histogram(self.highpassfiltered,  self.trig[0], self.settings['Sample Rate'], self.settings['Psths bin time'], self.settings['Spike Threshold'])
            self.h=h
            self.b=b
            x=b[:-1]*1e3
            self.p=gui.Plot(None)
            pp=[{'fillLevel':-0.01, 'brush': (50,50,128,100)}]
            self.p.plot.setLabels(left='occurence', bottom='dt [ms]')
            self.p.plot.setYRange(0, max(h))
            self.p.plot.setTitle('Peristimulus histogram')
            self.p.update_curves([x],[h],plotparams=pp)
            self.p.show()

def led_stimulator():
    stim=LEDStimulator()

if __name__ == "__main__":
    stim=LEDStimulator()
