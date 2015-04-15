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
        icon_folder = os.path.join(os.path.split(__file__)[0],'..','..','data', 'icons')
        for button in ['start_experiment', 'stop', 'snap', 'find_cells', 'previous_roi', 'next_roi', 'delete_roi', 'save_rois', 'export2mat', 'exit']:
            a = QtGui.QAction(QtGui.QIcon(os.path.join(icon_folder, '{0}.png'.format(button))), stringop.to_title(button), self)
            a.triggered.connect(getattr(self.parent, button+'_action'))
            self.addAction(a)
        
    def hideEvent(self,e):
        self.setVisible(True)
        
class PythonConsole(pyqtgraph.console.ConsoleWidget):
    def __init__(self, parent):
        pyqtgraph.console.ConsoleWidget.__init__(self, namespace={'self':parent.parent, 'utils':utils, 'fileop': fileop, 'signal':signal, numpy: 'numpy'}, text = 'self: MainUI, numpy, utils, fileop, signal')
        
class Image(gui.Image):
    def __init__(self, parent, roi_diameter=10):
        gui.Image.__init__(self, parent, roi_diameter)
        self.setFixedWidth(parent.machine_config.GUI['SIZE']['col']/2)
        self.setFixedHeight(parent.machine_config.GUI['SIZE']['col']/2)
        if 0:
            self.connect(self, QtCore.SIGNAL('roi_update'), parent.analysis.roi_update)
            self.connect(self, QtCore.SIGNAL('roi_mouse_selected'), parent.analysis.roi_mouse_selected)
            
            
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
            setattr(self, k, gui.FileTree(self, v[0], [v[1]]))
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
        elif ext == 'py':
            function = 'open_stimulus_file'
            scope = 'tbd'
        else:
            raise NotImplementedError(filename)
        self.parent.to_engine.put({'function': function, 'args':[filename]})

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
        self._add_dockable_widget('Plot', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea, self.plot)
        self.filebrowser = FileBrowser(self, self.filebrowser_config)
        self._add_dockable_widget('File Browser', QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.LeftDockWidgetArea, self.filebrowser)
        self.params = gui.ParameterTable(self, self.params_config)
        self.params.setFixedWidth(300)
        self.params.params.sigTreeStateChanged.connect(self.parameter_changed)
        self._add_dockable_widget('Parameters', QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.LeftDockWidgetArea, self.params)
        self._load_all_parameters()
        self.show()
        self.timer=QtCore.QTimer()
        self.timer.start(200)#ms
        self.connect(self.timer, QtCore.SIGNAL('timeout()'), self.check_queue)
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
            
    def check_queue(self):
        while not self.from_engine.empty():
            msg = self.from_engine.get()
            if msg.has_key('printc'):
                self.printc(msg['printc'])
            elif msg.has_key('show_meanimage'):
                self.image.set_image(msg['show_meanimage'], color_channel = 1)
                self.image.set_scale(self.engine.image_scale)
                self._write2statusbar('File opened')
            elif msg.has_key('show_suggested_rois'):
                self.image.set_image(msg['show_suggested_rois'])
                self.image.set_scale(self.engine.image_scale)
                self._write2statusbar('Suggested rois displayed')
            elif msg.has_key('send_rois'):
                self.rois = msg['send_rois']
                for roi in self.rois:
                    self.image.add_roi(roi['rectangle'][0],roi['rectangle'][1], roi['rectangle'][2])
                self.current_roi_index = 0
                self.roi_changed()
                self.printc('{0} rois are displayed'.format(len(self.rois)))
            
                
    def _init_variables(self):
        self.text = ''
        self.source_name = '{0}' .format(self.user_interface_name)
        self.filebrowser_config = {'data_file': ['/tmp/rei_data_c2', 'hdf5'], 'stimulus_file': ['/tmp', 'py']}#TODO: load from context
        self.params_config = [
                {'name': 'Analysis', 'type': 'group', 'expanded' : True, 'children': [
                    {'name': 'Cell detection', 'type': 'group', 'expanded' : False, 'children': [
                        {'name': 'Minimum cell radius', 'type': 'float', 'value': 2.0, 'siPrefix': True, 'suffix': 'um'},
                        {'name': 'Maximum cell radius', 'type': 'float', 'value': 4.0, 'siPrefix': True, 'suffix': 'um'},
                        {'name': 'Sigma', 'type': 'float', 'value': 0.5},
                        {'name': 'Threshold factor', 'type': 'float', 'value': 1.0}
                        ]
                    },
                    {'name': 'Baseline duration', 'type': 'float', 'value': 1.0, 'siPrefix': True, 'suffix': 's'},
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
        self.engine = gui_engine.GUIEngine(self.machine_config)
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
        self.current_roi_index -= 1
        self.roi_changed()
        
    def next_roi_action(self):
        self.current_roi_index += 1
        self.roi_changed()
        
    def delete_roi_action(self):
        pass
        
    def exit_action(self):
        self._dump_all_parameters()
        self._stop_engine()
        self.close()
    
    ############# Events #############
    def roi_changed(self):
        roi = self.rois[self.current_roi_index]
        #Highlight roi
        self.image.highlight_roi(self.current_roi_index)
                
       # Continue here!!!!!!!
        #Update plot
        
        
        
    
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

    def closeEvent(self, e):
        e.accept()
        self.exit_action()
    
    
if __name__ == '__main__':
    import visexpman.engine
    context = visexpman.engine.application_init(user = 'zoltan', config = 'CaImagingTestConfig', user_interface_name = 'main_ui')
    
    context['logger'].start()
    m = MainUI(context=context)
    visexpman.engine.stop_application(context)
