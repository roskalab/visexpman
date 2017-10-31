import os,logging,numpy
import PyQt4.QtGui as QtGui
from visexpman.engine.generic import gui

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
                    {'name': 'Sample Rate', 'type': 'int', 'value': 10000, 'suffix': 'Hz', 'siPrefix': True},
                    {'name': 'LED Voltage', 'type': 'float', 'value': 5, 'suffix': 'V', 'siPrefix': True},
                    {'name': 'Duty Cycle', 'type': 'float', 'value': 50, 'suffix': '%', 'siPrefix': True},
                    {'name': 'Tmin', 'type': 'float', 'value': 0.5, 'suffix': 's', 'siPrefix': True},
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
            AI1: Right LED
            AI2: amplifier's output
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

    def settings_changed(self):
        self.settings = self.cw.parametersw.get_parameter_tree(True)

    def start_action(self):
        logging.info('start')

    def stop_action(self):
        logging.info('stop')

    def exit_action(self):
        self.close()
        
    def generate_waveform(self):
        tperiod=1.0/self.settings['Stimulus Rate']
        nrepeats=numpy.ceils(self.settings['Tmin']/tperiod)
        self.waveform=self.settings['LED Voltage']*numpy.tile(numpy.concatenate((numpy.ones(tperiod*self.settings['Sample Rate']*self.settings['Duty Cycle']*1e-2),
                numpy.zeros(tperiod*self.settings['Sample Rate']*(100-self.settings['Duty Cycle'])*1e-2))), nrepeats)
        self.waveform=numpy.array(2*[self.waveform])
        
        self.settings['Left LED']
        self.settings['Right LED']
        self.settings['Sample Rate']
        self.settings['Stimulus Rate']
        self.settings['LED Voltage']

if __name__ == "__main__":
    stim=LEDStimulator()
