import copy
import time
import numpy
import os.path
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import pyqtgraph
import pyqtgraph.console

from visexpman.engine.generic import stringop,utils,gui,signal,fileop
from visexpman.engine.vision_experiment import gui_engine
TOOLBAR_ICON_SIZE = 35

class ToolBar(QtGui.QToolBar):
    '''
    Toolbar holding the following shortcuts:
    -experiment start, stop, snap, live start, exit
    '''
    def __init__(self, parent):
        self.parent=parent
        QtGui.QToolBar.__init__(self, 'Toolbar', parent)
        self.add_buttons()
        self.setIconSize(QtCore.QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE))
        self.setFloatable(False)
        self.setMovable(False)
        
    def add_buttons(self):
        icon_folder = os.path.join(fileop.visexpman_package_path(),'data', 'icons')
        for button in ['start_experiment', 'stop', 'snap', 'find_cells', 'previous_roi', 'next_roi', 'delete_roi', 'add_roi', 'save_rois', 'delete_all_rois', 'exit']:
            a = QtGui.QAction(QtGui.QIcon(os.path.join(icon_folder, '{0}.png'.format(button))), stringop.to_title(button), self)
            a.triggered.connect(getattr(self.parent, button+'_action'))
            self.addAction(a)
        
    def hideEvent(self,e):
        self.setVisible(True)
        
class RoiShift(gui.ArrowButtons):
    def __init__(self,parent):
        gui.ArrowButtons.__init__(self, 'Shift Rois', parent)
        
    def arrow_clicked(self, direction):
        h=0
        v=0
        if direction == 'left':
            h -= 1
        elif direction == 'right':
            h += 1
        elif direction == 'down':
            v -= 1
        elif direction == 'up':
            v += 1
        self.parent.parent.to_engine.put({'function': 'roi_shift', 'args':[h,v]})
        
class PythonConsole(pyqtgraph.console.ConsoleWidget):
    def __init__(self, parent):
        pyqtgraph.console.ConsoleWidget.__init__(self, namespace={'self':parent.parent, 'utils':utils, 'fileop': fileop, 'signal':signal, 'numpy': numpy}, text = 'self: MainUI, numpy, utils, fileop, signal')
        
class Image(gui.Image):
    def __init__(self, parent, roi_diameter=3):
        gui.Image.__init__(self, parent, roi_diameter)
        self.setFixedWidth(parent.machine_config.GUI['SIZE']['col']/2)
        self.setFixedHeight(parent.machine_config.GUI['SIZE']['col']/2)
        self.plot.setLabels(left='um', bottom='um')
        self.connect(self, QtCore.SIGNAL('roi_mouse_selected'), parent.roi_mouse_selected)
            
class Debug(QtGui.QTabWidget):
    def __init__(self,parent):
        self.parent=parent
        QtGui.QTabWidget.__init__(self,parent)
        self.log = gui.TextOut(self)
        self.console = PythonConsole(self)
        self.addTab(self.log, 'Log')
        self.addTab(self.console, 'Console')
        self.setTabPosition(self.South)
        
class FileBrowser(QtGui.QTabWidget):
    def __init__(self,parent, config):
        self.parent=parent
        QtGui.QTabWidget.__init__(self,parent)
        for k,v in config.items():
            setattr(self, k, gui.FileTree(self, v[0], v[1]))
            self.addTab(getattr(self, k), stringop.to_title(k))
            getattr(self, k).doubleClicked.connect(self.file_selected)
        self.setTabPosition(self.South)
        self.setToolTip('Double click on file to open')
        
    def file_selected(self,index):
        filename = str(index.model().filePath(index))
        if os.path.isdir(filename): return#Double click on folder is ignored
        ext = fileop.file_extension(filename)
        if ext == 'hdf5':
            function = 'open_datafile'
            scope = 'analysis'
            self.parent.to_engine.put({'function': 'keep_rois', 'args':[self.parent.analysis_helper.keep_rois.input.checkState()==2]})
            self.parent.analysis_helper.keep_rois.input.setCheckState(0)
        elif ext == 'py':
            function = 'open_stimulus_file'
            scope = 'tbd'
        else:
            raise NotImplementedError(filename)
        self.parent.to_engine.put({'function': function, 'args':[filename]})
        
class AnalysisHelper(QtGui.QWidget):
    def __init__(self, parent):
        self.parent = parent
        QtGui.QWidget.__init__(self, parent)
        self.show_rois = gui.LabeledCheckBox(self, 'Show/hide rois')
        self.show_rois.input.setCheckState(2)
        self.keep_rois = gui.LabeledCheckBox(self, 'Keep rois')
        self.keep_rois.setToolTip('Check this it before opening next file and rois will be kept as a reference set and will be used for the next file')
        self.show_repetitions = gui.LabeledCheckBox(self, 'Show Repetitions')
        self.find_repetitions = QtGui.QPushButton('Find repetitions' ,parent=self)
        self.roi_adjust = RoiShift(self)
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.show_rois,0,0,1,1)
        self.layout.addWidget(self.keep_rois,1,0,1,1)
        self.layout.addWidget(self.roi_adjust,0,1,2,2)
        self.layout.addWidget(self.show_repetitions,0,3,1,1)
        self.layout.addWidget(self.find_repetitions,1,3,1,1)
        self.setLayout(self.layout)
        self.setMaximumHeight(100)
        self.connect(self.find_repetitions, QtCore.SIGNAL('clicked()'), self.find_repetitions_clicked)
        
    def find_repetitions_clicked(self):
        self.parent.to_engine.put({'function': 'find_repetitions', 'args':[]})

class MainUI(Qt.QMainWindow):
    def __init__(self, context):
        if QtCore.QCoreApplication.instance() is None:
            qt_app = Qt.QApplication([])
        Qt.QMainWindow.__init__(self)
        for c in ['machine_config', 'user_interface_name', 'socket_queues', 'warning', 'logger']:
            setattr(self,c,context[c])
        self._init_variables()
        self._start_engine()
        self.resize(self.machine_config.GUI['SIZE']['col'], self.machine_config.GUI['SIZE']['row'])
        self._set_window_title()
        #Set up toobar
        self.toolbar = ToolBar(self)
        self.addToolBar(self.toolbar)
        #Set up statusbar
        self.statusbar = self.statusBar()
        self._write2statusbar('Application started')
        #Add dockable widgets
        self.debug = Debug(self)
        self.debug.setMinimumWidth(self.machine_config.GUI['SIZE']['col']/3)
        self._add_dockable_widget('Debug', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea, self.debug)
        self.image = Image(self)
        self._add_dockable_widget('Image', QtCore.Qt.RightDockWidgetArea, QtCore.Qt.RightDockWidgetArea, self.image)
        self.plot = gui.Plot(self)
        self.plot.setMinimumWidth(self.machine_config.GUI['SIZE']['col']/2)
        self.plot.plot.setLabels(bottom='sec')
        self._add_dockable_widget('Plot', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea, self.plot)
        self.filebrowser = FileBrowser(self, self.filebrowser_config)
        self._add_dockable_widget('File Browser', QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.LeftDockWidgetArea, self.filebrowser)
        self.params = gui.ParameterTable(self, self.params_config)
        self.params.setFixedWidth(300)
        self.params.params.sigTreeStateChanged.connect(self.parameter_changed)
        self._add_dockable_widget('Parameters', QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.LeftDockWidgetArea, self.params)
        self._load_all_parameters()
        
        self.analysis_helper = AnalysisHelper(self)
        self._add_dockable_widget('Analysis helper', QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.LeftDockWidgetArea, self.analysis_helper)
        
        self.show()
        self.timer=QtCore.QTimer()
        self.timer.start(50)#ms
        self.connect(self.timer, QtCore.SIGNAL('timeout()'), self.check_queue)
        
        self.connect(self.analysis_helper.show_rois.input, QtCore.SIGNAL('stateChanged(int)'), self.show_rois_changed)
        self.connect(self.analysis_helper.show_repetitions.input, QtCore.SIGNAL('stateChanged(int)'), self.show_repeptitions_changed)
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
            
    def check_queue(self):
        while not self.from_engine.empty():
            msg = self.from_engine.get()
            if msg.has_key('printc'):
                self.printc(msg['printc'])
            elif msg.has_key('send_image_data'):
                self.meanimage, self.image_scale, self.tsync, self.timg = msg['send_image_data']
                self.image.remove_all_rois()
                self.image.set_image(self.meanimage, color_channel = 1)
                self.image.set_scale(self.image_scale)
                self._write2statusbar('File opened')
            elif msg.has_key('show_suggested_rois'):
                self.image_w_rois = msg['show_suggested_rois']
                self.image.set_image(self.image_w_rois)
            elif msg.has_key('display_roi_rectangles'):
                self.image.remove_all_rois()
                [self.image.add_roi(r[0],r[1], r[2:], movable=False) for r in msg['display_roi_rectangles']]
                self._write2statusbar('Suggested rois displayed')
                self.printc('Displaying {0} rois'.format(len(msg['display_roi_rectangles'])))
            elif msg.has_key('display_roi_curve'):
                timg, curve, index, tsync = msg['display_roi_curve']
                #Highlight roi
                self.image.highlight_roi(index)
                if isinstance(timg, list) and isinstance(curve, list):
                    self.plot.update_curves(timg, curve,plot_average = True)
                else:
                    #Update plot
                    self.plot.update_curve(timg, curve)
                self.plot.add_linear_region(*list(tsync))
            elif msg.has_key('remove_roi_rectangle'):
                 self.image.remove_roi(*list(msg['remove_roi_rectangle']))
            elif msg.has_key('fix_roi'):
                for r in self.image.rois:
                    r.translatable=False
            elif msg.has_key('ask4confirmation'):
                reply = QtGui.QMessageBox.question(self, 'Confirm following action', msg['ask4confirmation'], QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
                self.to_engine.put(reply == QtGui.QMessageBox.Yes)
            elif msg.has_key('notify'):
                QtGui.QMessageBox.question(self, msg['notify']['title'], msg['notify']['msg'], QtGui.QMessageBox.Ok)
            elif msg.has_key('delete_all_rois'):
                self.image.remove_all_rois()
                
    def _init_variables(self):
        self.text = ''
        self.source_name = '{0}' .format(self.user_interface_name)
        self.filebrowser_config = {'data_file': [self.machine_config.EXPERIMENT_DATA_PATH, ['hdf5', 'mat']], 'stimulus_file': ['/tmp', ['py']]}#TODO: load py files from config or context

        self.params_config = [
                {'name': 'Analysis', 'type': 'group', 'expanded' : True, 'children': [
                    {'name': 'Cell detection', 'type': 'group', 'expanded' : False, 'children': [
                        {'name': 'Minimum cell radius', 'type': 'float', 'value': 2.0, 'siPrefix': True, 'suffix': 'um'},
                        {'name': 'Maximum cell radius', 'type': 'float', 'value': 3.0, 'siPrefix': True, 'suffix': 'um'},
                        {'name': 'Sigma', 'type': 'float', 'value': 1.0},
                        {'name': 'Threshold factor', 'type': 'float', 'value': 1.0}
                        ]
                    },
                    {'name': 'Baseline lenght', 'type': 'float', 'value': 1.0, 'siPrefix': True, 'suffix': 's'},
                    {'name': 'Background threshold', 'type': 'float', 'value': 10, 'siPrefix': True, 'suffix': '%'},
                    ]
                    }]



#                {'name': 'Basic parameter data types', 'type': 'group', 'children': [
#                {'name': 'Integer', 'type': 'int', 'value': 10},
#                {'name': 'Float', 'type': 'float', 'value': 10.5, 'step': 0.1},
#                {'name': 'String', 'type': 'str', 'value': "hi"},
##                {'name': 'List', 'type': 'list', 'values': [1,2,3], 'value': 2},
##                {'name': 'Named List', 'type': 'list', 'values': {"one": 1, "two": "twosies", "three": [3,3,3]}, 'value': 2},
#                {'name': 'Boolean', 'type': 'bool', 'value': True, 'tip': "This is a checkbox"},
##                {'name': 'Color', 'type': 'color', 'value': "FF0", 'tip': "This is a color button"},
#            ]},
#            {'name': 'Numerical Parameter Options', 'type': 'group', 'children': [
#                {'name': 'Units + SI prefix', 'type': 'float', 'value': 1.2e-6, 'step': 1e-6, 'siPrefix': True, 'suffix': 'V'},
#                {'name': 'Limits (min=7;max=15)', 'type': 'int', 'value': 11, 'limits': (7, 15), 'default': -6},
#                {'name': 'DEC stepping', 'type': 'float', 'value': 1.2e6, 'dec': True, 'step': 1, 'siPrefix': True, 'suffix': 'Hz'},
#        
#    ]}]
        
    def _start_engine(self):
        self.engine = gui_engine.GUIEngine(self.machine_config, self.logger)
        self.to_engine, self.from_engine = self.engine.get_queues()
        self.engine.start()
        
    def _stop_engine(self):
        self.to_engine.put('terminate')
        self.engine.join()
        
    def _set_window_title(self, animal_file=''):
        self.setWindowTitle('{0}{1}' .format(utils.get_window_title(self.machine_config), ' - ' + animal_file if len(animal_file)>0 else ''))
        
    def _write2statusbar(self,txt):
        self.statusbar.showMessage(txt)
        
    def _add_dockable_widget(self, title, position, allowed_areas, widget):
        dock = QtGui.QDockWidget(title, self)
        dock.setAllowedAreas(allowed_areas)
        dock.setWidget(widget)
        self.addDockWidget(position, dock)
        dock.setFeatures(dock.DockWidgetMovable | dock.DockWidgetClosable |dock.DockWidgetFloatable)
        
    def _get_parameter_tree(self):
        nodes = [[children for children in self.params.params.children()]]
        import itertools
        while True:
            nodes.append(list(itertools.chain(*[n.children() for n in nodes[-1]])))
            if len(nodes[-1])==0: break
        nodes = list(itertools.chain(*nodes))
        leafes = [n for n in nodes if len(n.children())==0]
        paths = []
        refs = []
        values = []
        for l in leafes:
            value = l.value()
            name = l.name()
            path = []
            ref= copy.deepcopy(l)
            while True:
                if ref.parent() is None: break
                else: 
                    path.append(ref.name())
                    ref= ref.parent()
            path.append('params')
            path.reverse()
            paths.append(path)
            values.append(value)
            refs.append(l)
        return values, paths, refs

    def _dump_all_parameters(self):
        values, paths, refs = self._get_parameter_tree()
        for i in range(len(refs)):
            self.to_engine.put({'data': values[i], 'path': '/'.join(paths[i]), 'name': refs[i].name()})
            
    def _load_all_parameters(self):
        values, paths, refs = self._get_parameter_tree()
        paths = ['/'.join(p) for p in paths]
        for item in self.engine.guidata.to_dict():
            r = refs[paths.index([p for p in paths if p == item['path']][0])]
            r.setValue(item['value'])
            r.setDefault(item['value'])
    
    def printc(self, text, logonly = False):
        '''
        text is displayed on console and logged to logfile
        '''
        text = str(text)
        if not logonly:
            self.text  += utils.timestamp2hms(time.time()) + ' '  + text + '\n'
            self.debug.log.update(self.text)
        loglevels = ['warning', 'error']
        loglevel = [l for l in loglevels if l in text.lower()]
        if len(loglevel)>0:
            loglevel = loglevel[0]
            getattr(self.logger, loglevel)(text.replace('{0}: '.format(loglevel.upper()),''), self.source_name)
        else:
            self.logger.info(text, self.source_name)
    
    ############# Actions #############
    def start_experiment_action(self):
        pass
        
    def stop_action(self):
        pass
        
    def snap_action(self):
        pass
        
    def find_cells_action(self):
        self.to_engine.put({'function': 'find_cells', 'args':[]})
        
    def previous_roi_action(self):
        self.to_engine.put({'function': 'previous_roi', 'args':[]})

    def next_roi_action(self):
        self.to_engine.put({'function': 'next_roi', 'args':[]})
        
    def delete_roi_action(self):
        self.to_engine.put({'function': 'delete_roi', 'args':[]})
        
    def add_roi_action(self):
        '''
        Adds (all) manually placed roi(s)
        '''
        movable_rois = [r for r in self.image.rois if r.translatable]#Rois manually placed
        if len(movable_rois)>1:
            self.printc('Only one manually placed roi can be added!')
            return
        elif len(movable_rois)==0:
            self.printc('Put roi first on image!')
            return
        roi=movable_rois[0] 
        rectangle = [roi.x(), roi.y(),  roi.size().x(),  roi.size().y()]
        self.to_engine.put({'function': 'add_manual_roi', 'args':[rectangle]})
        
    def save_rois_action(self):
        '''Also exports to mat file'''
        self.to_engine.put({'function': 'save_rois_and_export', 'args':[]})
        
    def delete_all_rois_action(self):
        self.to_engine.put({'function': 'delete_all_rois', 'args':[]})
        
    def exit_action(self):
        self._dump_all_parameters()
        self._stop_engine()
        self.close()
    
    ############# Events #############
    def show_rois_changed(self,state):
        if hasattr(self, 'image_w_rois'):
            im = numpy.copy(self.image_w_rois)
            im[:,:,2] *= state==2
            self.image.set_image(im)
            
    def show_repeptitions_changed(self,state):
        self.to_engine.put({'function': 'display_roi_curve', 'args':[state==2]})
        
    def roi_mouse_selected(self,x,y):
        self.to_engine.put({'function': 'roi_mouse_selected', 'args':[x,y]})
    
    def parameter_changed(self, param, changes):
        for change in changes:
            #find out tree
            ref = copy.deepcopy(change[0])
            tree = []
            while True:
                if hasattr(ref, 'name') and callable(getattr(ref, 'name')):
                    tree.append(getattr(ref, 'name')())
                    ref = copy.deepcopy(ref.parent())
                else:
                    break
            tree.reverse()
            self.to_engine.put({'data': change[2], 'path': '/'.join(tree), 'name': change[0].name()})
            self.printc('Warning: Curve normalization is not recalculated')

    def closeEvent(self, e):
        e.accept()
        self.exit_action()
    
if __name__ == '__main__':
    import visexpman.engine
    context = visexpman.engine.application_init(user = 'zoltan', config = 'CaImagingTestConfig', user_interface_name = 'main_ui', log_sources = ['engine'])
    
    context['logger'].start()
    m = MainUI(context=context)
    visexpman.engine.stop_application(context)
