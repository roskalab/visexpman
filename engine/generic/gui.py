'''
generic.gui module has generic gui widgets like labeled widgets. It also contains some gui helper function
'''

import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

from visexpman.engine.generic import utils

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
        
class PushButtonWithParameter(QtGui.QWidget):
    '''
    Default value in input field:
        self.input.setText(TEXT)
    '''
    def __init__(self, parent, buttonname, parametername):
        QtGui.QWidget.__init__(self, parent)
        self.parametername = parametername
        self.buttonname = buttonname
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.input = LabeledInput(self, self.parametername)
        self.button = QtGui.QPushButton(self.buttonname, self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.input, 0, 1, 1, 2)
        self.layout.addWidget(self.button, 0, 0)
        self.setLayout(self.layout)
        
class ParameterTable(QtGui.QTableWidget):
    '''
    A special QTable with two columns: first holds the parameter names, the second holds the corresponding parameter values
    '''
    def __init__(self, parent):
        QtGui.QTableWidget.__init__(self, parent)
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(QtCore.QStringList(['Parameter name', 'value']))
        self.verticalHeader().setDefaultSectionSize(20)
        
    def set_values(self, parameters):
        '''
        Sets the content of the table.
        parameters: dictionary: keys: parameter names, values: parameter values.
        '''
        self.parameters = parameters
        if parameters.has_key('self.editable') and parameters['self.editable'] == 'False':
            lock=True
        else:
            lock=False
        if parameters.has_key('self.editable'):
            del parameters['self.editable']
        if parameters.has_key('self.editable'):
            nrows = len(parameters)-1
        else:
            nrows = len(parameters)
        self.setRowCount(nrows)
        self.setVerticalHeaderLabels(QtCore.QStringList(nrows*['']))
        for row in range(nrows):
            parname = str(parameters.keys()[row])
            item = QtGui.QTableWidgetItem(parname)
            item.setFlags(QtCore.Qt.ItemIsSelectable| QtCore.Qt.ItemIsEnabled)
            self.setItem(row, 0, item)
            item=QtGui.QTableWidgetItem(str(parameters[parameters.keys()[row]]))
            if lock:
                item.setFlags(QtCore.Qt.ItemIsSelectable| QtCore.Qt.ItemIsEnabled)
            self.setItem(row, 1, item)

    def get_values(self):
        '''
        Return values of table in a dictionary format
        '''
        current_values = {}
        for row in range(self.rowCount()):
            current_values[str(self.item(row,0).text())] = str(self.item(row,1).text())
        return current_values

def load_experiment_config_names(config, widget):
    '''
    Loads all experiment config names and adds them to a dropdown widget
    OBSOLETE
    '''
    if hasattr(config, 'user'):
        import visexpman
        experiment_config_list = utils.fetch_classes('visexpman.users.' + config.user,  required_ancestors = visexpman.engine.vision_experiment.experiment.ExperimentConfig, direct = False)
        experiment_config_names = []
        for experiment_config in experiment_config_list:
            experiment_config_names.append(experiment_config[1].__name__)
        experiment_config_names.sort()
        widget.addItems(QtCore.QStringList(experiment_config_names))
        try:
            if hasattr(config, 'EXPERIMENT_CONFIG'):
                widget.setCurrentIndex(experiment_config_names.index(config.EXPERIMENT_CONFIG))
        except ValueError:
            pass
    return experiment_config_list
    
class WidgetControl(object):
    def __init__(self, poller, config, widget):
        self.config = config
        self.poller = poller
        self.widget = widget
        self.printc = self.poller.printc
    
def connect_and_map_signal(self, widget, mapped_signal_parameter, widget_signal_name = 'clicked'):
    self.signal_mapper.setMapping(widget, QtCore.QString(mapped_signal_parameter))
    getattr(getattr(widget, widget_signal_name), 'connect')(self.signal_mapper.map)
