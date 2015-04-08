'''
generic.gui module has generic gui widgets like labeled widgets. It also contains some gui helper function
'''

import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import pyqtgraph
from visexpman.engine.generic import utils,stringop

class TextOut(QtGui.QTextEdit):
    def __init__(self, parent):
        QtGui.QTextEdit.__init__(self, parent)
        self.setPlainText('')
        self.setReadOnly(True)
        self.ensureCursorVisible()
        self.setCursorWidth(5)
        
    def update(self, text):
        self.setPlainText(text)
        self.moveCursor(QtGui.QTextCursor.End)
        
class Plot(pyqtgraph.GraphicsLayoutWidget):
    def __init__(self,parent):
        pyqtgraph.GraphicsLayoutWidget.__init__(self,parent)
        self.setBackground((255,255,255))
#        self.gw.setFixedHeight(300)
        self.setAntialiasing(True)
        self.plot=self.addPlot()
        self.plot.enableAutoRange()
        self.plot.showGrid(True,True,1.0)
        self.curve = self.plot.plot(pen=(0,0,0))
        
class Image(pyqtgraph.GraphicsLayoutWidget):
    def __init__(self,parent, roi_diameter = 20, background_color = (255,255,255), selected_color = (255,0,0), unselected_color = (150,100,100)):
        pyqtgraph.GraphicsLayoutWidget.__init__(self,parent)
        self.unselected_color = unselected_color
        self.selected_color = selected_color
        self.setBackground(background_color)
        self.roi_default_diameter = roi_diameter
        self.plot=self.addPlot()
        self.img = pyqtgraph.ImageItem(border='w')
        self.plot.addItem(self.img)
        self.plot.showGrid(True,True,1.0)
        self.scene().sigMouseClicked.connect(self.mouse_clicked)
        self.rois = []
        
    def set_image(self, image, alpha = 0.8):
        im=alpha*numpy.ones((image.shape[0],image.shape[1], 4))*image.max()
        im[:,:,:3]=image
        self.img.setImage(im)
        
    def set_scale(self,scale):
        self.img.setScale(scale)

    def mouse_clicked(self,e):
        p=self.img.mapFromScene(e.scenePos())
        if e.double():
            if int(e.buttons()) == 1:
                self.add_roi(p.x()*self.img.scale(), p.y()*self.img.scale())
            elif int(e.buttons()) == 2:
                self.remove_roi(p.x()*self.img.scale(), p.y()*self.img.scale())
            self.update_roi_info()
        elif not e.double() and int(e.buttons()) != 1 and int(e.buttons()) != 2 and hasattr(self, 'roi_info'):
            self.emit(QtCore.SIGNAL('roi_mouse_selected'), ((numpy.array([[r[1], r[2]] for r in self.roi_info])-numpy.array([p.x()*self.img.scale(), p.y()*self.img.scale()]))**2).sum(axis=1).argmin())
        
    def add_roi(self,x,y, size=None, type='rect'):
        if size is None:
            size = self.roi_default_diameter
        if type == 'circle':
            roi = pyqtgraph.CircleROI([x-0.5*size, y-0.5*size], [size, size])
        elif type =='point':
            roi = pyqtgraph.ROI((x,y),size=[0.3,0.3],movable=False,removable=False)
        elif type == 'rect':
            if not hasattr(size, '__getitem__'):
                size = [size,size]
            roi = pyqtgraph.RectROI((x-0.5*size[0],y-0.5*size[1]),size=size)
        roi.setPen((self.unselected_color[0],self.unselected_color[1],self.unselected_color[2],255), width=2)
        roi.sigRegionChanged.connect(self.update_roi_info)
        self.rois.append(roi)
        self.plot.addItem(self.rois[-1])
        
    def remove_roi(self,x,y):
        distances = [(r.pos().x()-x)**2+(r.pos().y()-y)**2 for r in self.rois]
        if len(distances)==0:return
        removable_roi = self.rois[numpy.array(distances).argmin()]
        self.plot.removeItem(removable_roi)
        self.rois.remove(removable_roi)
    
    def set_roi_visibility(self,x,y,visibility):
        distances = [(r.pos().x()-x)**2+(r.pos().y()-y)**2 for r in self.rois]
        if len(distances)==0:return
        selected_roi = self.rois[numpy.array(distances).argmin()]
        selected_roi.setVisible(visibility)
        
    def update_roi_info(self):
        self.roi_info = [[i, self.rois[i].x(), self.rois[i].y(), self.rois[i].size().x()] for i in range(len(self.rois))]
        self.emit(QtCore.SIGNAL('roi_update'))
        
    def load_rois(self,roi_info):
        scale=1
        self.roi_info = roi_info
        for r in self.rois:
            self.plot.removeItem(r)
        self.rois=[]
        for r in roi_info:
            self.add_roi(r[1]+0.5*r[3],r[2]+0.5*r[3],r[3])
        self.emit(QtCore.SIGNAL('roi_update'))


class GroupBox(QtGui.QGroupBox):#OBSOLETE
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

class LabeledComboBox(QtGui.QWidget):
    '''
    Default value in input field:
        self.input.setText(TEXT)
    '''
    def __init__(self, parent, label,items=None):
        QtGui.QWidget.__init__(self, parent)
        self.label = label
        self.create_widgets()
        self.create_layout()
        if items is not None:
            self.update_items(items)
            

    def create_widgets(self):
        self.labelw = QtGui.QLabel(self.label, self)
        self.input = QtGui.QComboBox(self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.labelw, 0, 0)
        self.layout.addWidget(self.input, 0, 1)
        self.setLayout(self.layout)
        
    def update_items(self,items):
        self.input.blockSignals(True)
        self.input.clear()
        self.input.blockSignals(False)
        self.input.addItems(QtCore.QStringList(items))
        
class LabeledListWidget(QtGui.QWidget):
    '''
    Default value in input field:
        self.input.setText(TEXT)
    '''
    def __init__(self, parent, label,items=None):
        QtGui.QWidget.__init__(self, parent)
        self.label = label
        self.create_widgets()
        self.create_layout()
        if items is not None:
            self.list.addItems(QtCore.QStringList(items))
            
    def get_selected_item_names(self):
        return [str(i.text()) for i in map(self.list.item, [s.row() for s in self.list.selectedIndexes()])]

    def create_widgets(self):
        self.labelw = QtGui.QLabel(self.label, self)
        self.list = QtGui.QListWidget(self)
        self.list.setSelectionMode(self.list.MultiSelection)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.labelw, 0, 0)
        self.layout.addWidget(self.list, 1, 0)
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
        
    def set_values(self, parameters, parname_order=None):
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
            if parname_order is None:
                parname = str(parameters.keys()[row])
            else:
                parname = parname_order[row]
            item = QtGui.QTableWidgetItem(parname)
            item.setToolTip(parname)
            item.setFlags(QtCore.Qt.ItemIsSelectable| QtCore.Qt.ItemIsEnabled)
            self.setItem(row, 0, item)#Set parameter name
            #Setting value of table element depends on the widget type
            if self.cellWidget(row,1) is None:
                value = str(parameters[parname]).split('#')
                if len(value) == 2:
                    comment = value[1]
                value = value[0]
                item=QtGui.QTableWidgetItem(value)
                if 'comment' in locals():
                    item.setToolTip(comment)
                if lock:
                    item.setFlags(QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsEnabled)
                self.setItem(row, 1, item)
            elif hasattr(self.cellWidget(row,1), 'date'):
                d, m, y=map(int, str(parameters[parname]).split('-'))
                self.cellWidget(row,1).setDate(QtCore.QDate(y, m, d))
            elif hasattr(self.cellWidget(row,1), 'currentText'):
                #Find out index
                items = get_combobox_items(self.cellWidget(row,1))
                if str(parameters[parname]) in items:
                    index = items.index(str(parameters[parname]))
                    self.cellWidget(row,1).setCurrentIndex(index)
                elif self.cellWidget(row,1).isEditable():
                    self.cellWidget(row,1).setEditText(str(parameters[parname]))

    def get_values(self):
        '''
        Return values of table in a dictionary format
        '''
        current_values = {}
        for row in range(self.rowCount()):
            parname = str(self.item(row,0).text())
            if hasattr(self.item(row,1), 'text') and self.cellWidget(row,1) is None and hasattr(self.item(row,1), 'toolTip'):
                    current_values[parname] = [str(self.item(row,1).text()), str(self.item(row,1).toolTip())]
            elif hasattr(self.item(row,1), 'text'):
                current_values[parname] = str(self.item(row,1).text())
            elif hasattr(self.cellWidget(row,1), 'date'):
                date = self.cellWidget(row,1).date()
                current_values[parname] = '{0}-{1}-{2}'.format(date.day(), date.month(), date.year())
            elif hasattr(self.cellWidget(row,1), 'currentText'):
                current_values[parname] = str(self.cellWidget(row,1).currentText())
            elif self.item(row,1) is None:
                current_values[parname] = ''
            else:
                raise NotImplementedError('Reader for this type of widget is not implemented {0}. Parameter name: {1}'.format(self.item(row,1), parname))
        return current_values
        
def update_combo_box_list(self, widget, new_list,  selected_item = None):
    current_value = widget.currentText()
    try:
        if current_value in new_list:
            current_index = new_list.index(current_value)
        else:
            current_index = 0
    except:
        current_index = 0
        self.printc((current_value, new_list))
        self.printc(traceback.format_exc())
    items_list = QtCore.QStringList(new_list)
    widget.blockSignals(True)
    widget.clear()
    widget.addItems(QtCore.QStringList(new_list))
    widget.blockSignals(False)
    if selected_item != None and selected_item in new_list:
        widget.setCurrentIndex(new_list.index(selected_item))
    else:
        widget.setCurrentIndex(current_index)

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

def get_combobox_items(combobox):
    return [str(combobox.itemText(i)) for i in range(combobox.count())]
