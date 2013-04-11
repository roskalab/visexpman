import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

class GroupBox(QtGui.QGroupBox):
    def __init__(self, parent, name):
        QtGui.QGroupBox.__init__(self, name, parent)
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        pass
        
    def create_layout(self):
        pass

class LabeledInput(QtGui.QWidget):
    '''
    Default value in input field:
        self.input.setText(TEXT)
    '''
    def __init__(self, parent, label):
        QtGui.QWidget.__init__(self, parent)
        self.label = label
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.labelw = QtGui.QLabel(self.label, self)
        self.input = QtGui.QLineEdit(self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.labelw, 0, 0)
        self.layout.addWidget(self.input, 0, 1)
        self.setLayout(self.layout)

class LabeledCheckBox(QtGui.QWidget):
    '''
    Default value in input field:
        self.input.setText(TEXT)
    '''
    def __init__(self, parent, label):
        QtGui.QWidget.__init__(self, parent)
        self.label = label
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.labelw = QtGui.QLabel(self.label, self)
        self.input = QtGui.QCheckBox(self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.labelw, 0, 0)
        self.layout.addWidget(self.input, 0, 1)
        self.setLayout(self.layout)

class LabeledComboBox(QtGui.QWidget):
    '''
    Default value in input field:
        self.input.setText(TEXT)
    '''
    def __init__(self, parent, label):
        QtGui.QWidget.__init__(self, parent)
        self.label = label
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.labelw = QtGui.QLabel(self.label, self)
        self.input = QtGui.QComboBox(self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.labelw, 0, 0)
        self.layout.addWidget(self.input, 0, 1)
        self.setLayout(self.layout)
