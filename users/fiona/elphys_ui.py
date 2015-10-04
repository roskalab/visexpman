import numpy,scipy.io
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from pyqtgraph.parametertree import Parameter, ParameterTree
from visexpman.engine.generic import gui,utils,videofile

class CWidget(QtGui.QWidget):
    def __init__(self,parent):
        QtGui.QWidget.__init__(self,parent)
        self.plotw=gui.Plot(self)
        self.plotw.setFixedWidth(600)
        self.plotw.setFixedHeight(250)
        self.parametersw = ParameterTree(self, showHeader=False)
        self.parametersw.setFixedWidth(300)
        self.parametersw.setFixedHeight(250)
        params = [
                    {'name': 'Clamp Mode', 'type': 'list', 'value': 'eps', 'values': ['current','voltage']},
                    {'name': 'Sampling Rate', 'type': 'float', 'value': 10000.0, 'suffix': ' Hz' },
                    {'name': 'Imaging IP Address', 'type': 'str', 'value': '0.0.0.0'},
                    {'name': 'Enable Imaging', 'type': 'bool', 'value': True},
                    {'name': 'Square signal', 'type': 'group', 'expanded' : True, 'children': [
                    {'name': 'Amplitude', 'type': 'float', 'value': 1,  'suffix': ' mV or uA'},
                    {'name': 'Pulse width', 'type': 'float', 'value': 100,  'suffix': ' ms'},
                    {'name': 'Frequency', 'type': 'float', 'value': 100,  'suffix': ' Hz'},
                    {'name': 'Number of pulses', 'type': 'int', 'value': 10},
                                                                                                ]}]
        
        self.parameters = Parameter.create(name='params', type='group', children=params)
        self.parametersw.setParameters(self.parameters, showTop=False)
        self.start_experiment = QtGui.QPushButton('Start experiment', parent=self)
        self.select_folder = QtGui.QPushButton('Select data save folder', parent=self)
        self.load_waveform= QtGui.QPushButton('Load waveform', parent=self)
        self.l = QtGui.QGridLayout()
        self.l.addWidget(self.plotw, 0, 0, 2, 3)
        self.l.addWidget(self.parametersw, 0, 3, 2, 2)
        self.l.addWidget(self.select_folder, 2, 0, 1, 1)
        self.l.addWidget(self.load_waveform, 2, 1, 1, 1)
        self.l.addWidget(self.start_experiment, 2, 2, 1, 1)
        self.setLayout(self.l)



class ElphysUI(gui.SimpleAppWindow):
    def init_gui(self):
        self.setWindowTitle('Electrophysiological Stimulator')
        self.cw=CWidget(self)
        self.setCentralWidget(self.cw)
        self.resize(800,500)

if __name__ == '__main__':
    gui = ElphysUI()
