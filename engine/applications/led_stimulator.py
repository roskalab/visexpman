try:
    import PyDAQmx
    import PyDAQmx.DAQmxConstants as DAQmxConstants
    import PyDAQmx.DAQmxTypes as DAQmxTypes
except ImportError:
    pass
import os,logging,numpy,copy,pyqtgraph
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from visexpman.engine.generic import gui, signal


class CWidget(QtGui.QWidget):
    def __init__(self,parent):
        QtGui.QWidget.__init__(self,parent)
        self.plotw=gui.Plot(self)
        self.plotw.setFixedWidth(950)
        self.plotw.setFixedHeight(300)
        params = [
                    {'name': 'Left LED', 'type': 'bool', 'value': False,},
                    {'name': 'Right LED', 'type': 'bool', 'value': False,},
                    {'name': 'Enable Average', 'type': 'bool', 'value': True,},
                    {'name': 'Stimulus Rate', 'type': 'int', 'value': 1, 'suffix': 'Hz', 'siPrefix': True},
                    {'name': 'LED on time', 'type': 'float', 'value': 100, 'suffix': 'ms', 'siPrefix': True},
                    {'name': 'Sample Rate', 'type': 'int', 'value': 10000, 'suffix': 'Hz', 'siPrefix': True},
                    {'name': 'LED Voltage', 'type': 'float', 'value': 5, 'suffix': 'V', 'siPrefix': True},
                    {'name': 'Tmin', 'type': 'float', 'value': 0.5, 'suffix': 's', 'siPrefix': True},
                    {'name': 'DAQ device', 'type': 'str', 'value': 'Dev1'},
                                                                                                ]
        self.parametersw = gui.ParameterTable(self, params)
        self.parametersw.setFixedWidth(230)
        self.parametersw.setFixedHeight(300)
        self.l = QtGui.QGridLayout()#Organize the above created widgets into a layout
        self.l.addWidget(self.plotw, 0, 1, 1, 5)
        self.l.addWidget(self.parametersw, 0, 0, 1, 1)
        self.setLayout(self.l)

class LEDStimulator(gui.SimpleAppWindow):
    def init_gui(self):
        self.setWindowTitle('LED Stimulator')
        self.cw=CWidget(self)
        self.setCentralWidget(self.cw)
        self.cw.parametersw.params.sigTreeStateChanged.connect(self.settings_changed)
        self.resize(1000,500)
        icon_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'icons')
        self.toolbar = gui.ToolBar(self, ['start', 'stop','exit'], icon_folder = icon_folder)
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
            4. Watch plot
        ''')
        self.addToolBar(self.toolbar)
        self.settings_changed()
        self.ao_sample_rate=1000
        self.daq_timeout=1
        self.running=False
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)

    def settings_changed(self):
        self.settings = self.cw.parametersw.get_parameter_tree(True)

    def start_action(self):
        logging.info('start')
        self.running=True

    def stop_action(self):
        logging.info('stop')
        self.running=False

    def exit_action(self):
        self.close()
        
    def generate_waveform(self):
        tperiod=1.0/self.settings['Stimulus Rate']
        duty_cycle=self.settings['LED on time']*1e-3/tperiod
        nrepeats=numpy.ceil(self.settings['Tmin']/tperiod)
        self.waveform=self.settings['LED Voltage']*numpy.tile(numpy.concatenate((numpy.ones(int(tperiod*self.ao_sample_rate*duty_cycle)),
                numpy.zeros(int(tperiod*self.ao_sample_rate*(1-duty_cycle))))), nrepeats)
        self.waveform=numpy.array(2*[self.waveform])
        enable_mask=numpy.array([[self.settings['Left LED'],self.settings['Right LED']]]).T
        self.waveform*=enable_mask
        
    def update(self):
        if self.running:
            newsig=numpy.random.random(1000)
            if not hasattr(self, 'sigs'):
                self.sigs=[]
            self.sigs.append(newsig)
            self.sig=numpy.array(self.sigs).mean(axis=0)
            self.trig=5*numpy.concatenate((numpy.ones(500),numpy.zeros(500)))
            t=signal.time_series(self.trig.shape[0], self.settings['Sample Rate'])
            pp=[{'name': 'sig', 'pen':pyqtgraph.mkPen(color=(255,150,0), width=0)},{'name': 'trig', 'pen': pyqtgraph.mkPen(color=(10,20,30), width=3)}]
            self.cw.plotw.update_curves(2*[t], [self.sig,self.trig],plotparams=pp)
        
    def init_daq(self):
        self.analog_output = PyDAQmx.Task()
        self.analog_output.CreateAOVoltageChan(self.settings['DAQ device'],
                                                            'ao',
                                                            0,
                                                            5.0,
                                                            DAQmxConstants.DAQmx_Val_Volts,
                                                            None)
        self.analog_output.CfgDigEdgeStartTrig('/{0}/ai/StartTrigger' .format(self.settings['DAQ device']), DAQmxConstants.DAQmx_Val_Rising)
        self.analog_input = PyDAQmx.Task()
        if self.settings['Left LED'] and self.settings['Right LED']:
            ch1=0
            ch2=1
        elif self.settings['Left LED'] and not self.settings['Right LED']:
            ch1=0
            ch2=1
        elif not self.settings['Left LED'] and self.settings['Right LED']:
            ch1=1
            ch2=2
        ai_channels='{0}/ai{1}:{2}' .format(self.settings['DAQ device'], ch1, ch2)
        self.analog_input.CreateAIVoltageChan(ai_channels,
                                                'ai',
                                                DAQmxConstants.DAQmx_Val_RSE,
                                                -5.0,
                                                5.0,
                                                DAQmxConstants.DAQmx_Val_Volts,
                                                None)
        self.read = DAQmxTypes.int32()

    def start_daq(self):
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
        self.analog_output.StartTask()
        self.analog_input.StartTask()

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
            if self.finite_samples:
                import traceback
                self.printl(traceback.format_exc())
        ai_data = self.ai_data[:self.read.value * self.number_of_ai_channels]
        self.printl(self.ai_data.shape)
        ##self.ai_raw_data = self.ai_data
        ai_data = copy.deepcopy(ai_data.flatten('F').reshape((self.number_of_ai_channels, self.read.value)).transpose())
        self.queues['data'].put(ai_data)
        self.ai_frames += 1
        return ai_data
        
    def close_daq(self):
        self.analog_output.ClearTask()
        self.analog_input.ClearTask()


if __name__ == "__main__":
    stim=LEDStimulator()
