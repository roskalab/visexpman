import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import pyqtgraph
from visexpman.engine.generic import utils,gui,signal,fileop

class ImageChannels(QtGui.QWidget):
    '''
    Select filters or displayable image channels
    '''
    def __init__(self, parent):
        self.parent = parent
        QtGui.QWidget.__init__(self, parent)

class CaImaging(gui.VisexpmanMainWindow):
    def __init__(self, context):
        if QtCore.QCoreApplication.instance() is None:
            qt_app = Qt.QApplication([])
        gui.VisexpmanMainWindow.__init__(self, context)
        self.toolbar = gui.ToolBar(self, ['live_ir_camera', 'live_two_photon', 'snap_two_photon', 'stop', 'exit'])
        self.addToolBar(self.toolbar)
        self.debug = gui.Debug(self)
        self._add_dockable_widget('Debug', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea, self.debug)
        self.image = gui.Image(self)
        self.image.plot.setLabels(left='um', bottom='um')
        self.image.setFixedWidth(self.machine_config.GUI['SIZE']['col']/2)
        self.image.setFixedHeight(self.machine_config.GUI['SIZE']['col']/2)
        self._add_dockable_widget('Image', QtCore.Qt.RightDockWidgetArea, QtCore.Qt.RightDockWidgetArea, self.image)
        
        
        self.show()
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
            
    def live_ir_camera_action(self):
        pass
        
    def live_two_photon_action(self):
        pass
        
    def snap_two_photon_action(self):
        pass
        
    def stop_action(self):
        pass
            
    def exit_action(self):
        self.close()
            
if __name__ == '__main__':
    import visexpman.engine
    context = visexpman.engine.application_init(user = 'zoltan', config = 'CaImagingTestConfig', user_interface_name = 'ca_imaging', log_sources = ['engine'])
    
    context['logger'].start()
    m = CaImaging(context=context)
    visexpman.engine.stop_application(context)
