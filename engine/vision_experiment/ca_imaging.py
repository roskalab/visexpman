import time
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import pyqtgraph
from visexpman.engine.generic import utils,gui,signal,fileop
from visexpman.engine.hardware_interface import camera_interface

class ImageChannels(QtGui.QWidget):
    '''
    Select filters or displayable image channels
    '''
    def __init__(self, parent):
        self.parent = parent
        QtGui.QWidget.__init__(self, parent)
        self.channels = parent.machine_config.PMTS.keys()
        self.channels.append('IR')
        self.filter_names = ['none', '3x3 median filter', 'Histogram shift', 'Histogram equalize']
        self.enable = {}
        self.filters = {}
        self.layout = QtGui.QGridLayout()
        pos = 0
        for ch in self.channels:
            self.enable[ch]=gui.LabeledCheckBox(self, ch)
            self.filters[ch]=QtGui.QComboBox(self)
            self.filters[ch].addItems(QtCore.QStringList(self.filter_names))
            self.filters[ch].setMaximumWidth(150)
            self.layout.addWidget(self.enable[ch], 0, pos)
            self.layout.addWidget(self.filters[ch], 1, pos)
            self.connect(self.enable[ch].input, QtCore.SIGNAL('stateChanged(int)'), self.image_channels_changed)
            self.connect(self.filters[ch], QtCore.SIGNAL('currentIndexChanged(int)'), self.image_channels_changed)
            pos+=1
        self.setLayout(self.layout)
        
    def read_state(self):
        self.state = {}
        for ch in self.channels:
            self.state[ch] = {'enabled': self.enable[ch].input.checkState()==2, 'filter': str(self.filters[ch].currentText())}
        
    def image_channels_changed(self):
        #reading state:
        self.read_state()
        self.parent.printc(self.state)
        
class CaImagingHardwareHandler(object):
    def start_ir_camera_acquisition(self):
        self.camera=camera_interface.SpotCamAcquisition(log=self.logger if hasattr(self, 'logger') else None)
        self.camera.start()
        self.camera.command.put('ok')
        self.printc('Camera started')
        
    def stop_ir_camera(self):
        if hasattr(self, 'camera') and self.camera.is_alive():
            self.camera.command.put('terminate')
            self.camera.join(1)
            self.printc('Camera stopped')
            
    def read_ir_image(self):
        if hasattr(self, 'camera') and hasattr(self.camera, 'response') and not self.camera.response.empty():
            self.camera.command.put('ok')
            return self.camera.response.get()

class CaImaging(gui.VisexpmanMainWindow, CaImagingHardwareHandler):
    def __init__(self, context):
        if QtCore.QCoreApplication.instance() is None:
            qt_app = Qt.QApplication([])
        gui.VisexpmanMainWindow.__init__(self, context)
        self.toolbar = gui.ToolBar(self, ['live_ir_camera', 'live_two_photon', 'snap_two_photon', 'stop', 'exit'])
        self.addToolBar(self.toolbar)
        self.image_channels = ImageChannels(self)
        self._add_dockable_widget('Image channels', QtCore.Qt.TopDockWidgetArea, QtCore.Qt.TopDockWidgetArea, self.image_channels)
        self.debug = gui.Debug(self)
        self._add_dockable_widget('Debug', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea, self.debug)
        self.image = gui.Image(self)
        self.image.plot.setLabels(left='um', bottom='um')
        self.image.setMinimumWidth(self.machine_config.GUI['SIZE']['col']/2)
        self.image.setFixedHeight(self.machine_config.GUI['SIZE']['col']/2)
        self._add_dockable_widget('Image', QtCore.Qt.RightDockWidgetArea, QtCore.Qt.RightDockWidgetArea, self.image)
        self.show()
        self.timer=QtCore.QTimer()
        self.timer.start(70)#ms
        self.connect(self.timer, QtCore.SIGNAL('timeout()'), self.read_image)
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
            
    def read_image(self):
        im=self.read_ir_image()
        if im is not None:
            self.image.img.setImage(im)
            self.image.setFixedWidth(float(im.shape[0])/im.shape[1]*self.image.height())
            
    def live_ir_camera_action(self):
        self.start_ir_camera_acquisition()
        
    def live_two_photon_action(self):
        pass
        
    def snap_two_photon_action(self):
        pass
        
    def stop_action(self):
        self.stop_ir_camera()
            
    def exit_action(self):
        self.stop_ir_camera()
        self.close()
            
if __name__ == '__main__':
    import visexpman.engine
    context = visexpman.engine.application_init(user = 'zoltan', config = 'CaImagingTestConfig', user_interface_name = 'ca_imaging', log_sources = ['engine'])
    context['logger'].start()
    m = CaImaging(context=context)
    visexpman.engine.stop_application(context)
