import time
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import pyqtgraph
from visexpman.engine.generic import utils,gui,signal,fileop
from visexpman.engine.hardware_interface import camera_interface

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
            
    def update_settings(self, values, paths, refs):
        self.settings = {}
        for i in range(len(paths)):
            self.settings[paths[i][-1]]=values[i]

class CaImaging(gui.VisexpmanMainWindow, CaImagingHardwareHandler):
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
        self.image.setMinimumWidth(self.machine_config.GUI['SIZE']['col']/2)
        self.image.setFixedHeight(self.machine_config.GUI['SIZE']['col']/2)
        self._add_dockable_widget('Image', QtCore.Qt.RightDockWidgetArea, QtCore.Qt.RightDockWidgetArea, self.image)
        self.settings = gui.ParameterTable(self, self._get_params_config())
        self.settings.setMinimumWidth(300)
        self.settings.params.sigTreeStateChanged.connect(self.settings_changed)
        self._add_dockable_widget('Settings', QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.LeftDockWidgetArea, self.settings)
        self.show()
        self.timer=QtCore.QTimer()
        self.timer.start(50)#ms
        self.connect(self.timer, QtCore.SIGNAL('timeout()'), self.read_image)
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
            
    def _get_params_config(self):
        channels = self.machine_config.PMTS.keys()
        channels.append('IR')
        filter_names = ['none', '3x3 median filter', 'Histogram shift', 'Histogram equalize']
        image_channel_items = []
        for channel in channels:
            image_channel_items.append({'name': 'Enable {0}'.format(channel), 'type': 'bool', 'value': False})
            image_channel_items.append({'name': '{0} filter'.format(channel), 'type': 'list', 'values': filter_names, 'value': ''})
        pc =  [
                {'name': 'Image channels', 'type': 'group', 'expanded' : True, 'children': image_channel_items},
                {'name': 'IR camera', 'type': 'group', 'expanded' : True, 'children': [
                    {'name': 'Exposure time', 'type': 'float', 'value': 100.0, 'siPrefix': True, 'suffix': 'ms'},
                    {'name': 'Gain', 'type': 'float', 'value': 1.0, },
                    
                    ]},
                    
                    ]
        return pc
            
    def read_image(self):
        im=self.read_ir_image()
        if im is not None:
            im*=0.2
            im+=0.5
            self.image.img.setImage(im, levels = (0,1))
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
        
    def settings_changed(self, param, changes):
        self.update_settings(*self.settings.get_parameter_tree())
            
if __name__ == '__main__':
    import visexpman.engine
    context = visexpman.engine.application_init(user = 'zoltan', config = 'CaImagingTestConfig', user_interface_name = 'ca_imaging', log_sources = ['engine'])
    context['logger'].start()
    m = CaImaging(context=context)
    visexpman.engine.stop_application(context)
