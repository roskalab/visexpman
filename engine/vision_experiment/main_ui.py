import time
import numpy
import os.path
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import pyqtgraph
import pyqtgraph.console

from visexpman.engine.generic import stringop,utils,gui,signal,fileop
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
        for button in ['start_experiment', 'stop', 'snap', 'exit']:
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
        self.setMinimumWidth(500)
        self.setMinimumHeight(500)
        self.setMaximumWidth(1000)
        self.setMaximumHeight(1000)
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

class MainUI(Qt.QMainWindow):
    def __init__(self, context):
        if QtCore.QCoreApplication.instance() is None:
            qt_app = Qt.QApplication([])
        Qt.QMainWindow.__init__(self)
        for c in ['machine_config', 'user_interface_name', 'socket_queues', 'warning', 'logger']:
            setattr(self,c,context[c])
        self.init_variables()
        self.resize(self.machine_config.GUI['GUI_SIZE']['col'], self.machine_config.GUI['GUI_SIZE']['row'])
        self._set_window_title()
        #Set up toobar
        self.toolbar = ToolBar(self)
        self.addToolBar(self.toolbar)
        #Set up statusbar
        self.statusbar = self.statusBar()
        self._write2statusbar('Application started')
        #Add dockable widgets
        self.debug = Debug(self)
        self.debug.setMinimumWidth(self.machine_config.GUI['GUI_SIZE']['col']/3)
        self._add_dockable_widget('Debug', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea, self.debug)
        self.image = Image(self)
        self._add_dockable_widget('Image', QtCore.Qt.RightDockWidgetArea, QtCore.Qt.RightDockWidgetArea, self.image)
        self.plot = gui.Plot(self)
        self.plot.setMinimumWidth(self.machine_config.GUI['GUI_SIZE']['col']/2)
        self._add_dockable_widget('Plot', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea, self.plot)
        self.show()
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
            
    def init_variables(self):
        self.text = ''
        self.source_name = '{0}' .format(self.user_interface_name)

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
    
    def printc(self, text, logonly = False):
        '''
        text is displayed on console and logged to logfile
        '''
        text = str(text)
        if not logonly:
            self.text  += utils.timestamp2hms(time.time()) + ' '  + text + '\n'
            self.textout.update(self.text)
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
        
    def exit_action(self):
        self.close()
        
    def closeEvent(self, e):
        e.accept()
        self.exit_action()
    
    
if __name__ == '__main__':
    import visexpman.engine
    context = visexpman.engine.application_init(user = 'zoltan', config = 'CaImagingTestConfig', user_interface_name = 'main_ui')
    context['logger'].start()
    MainUI(context=context)
    visexpman.engine.stop_application(context)
