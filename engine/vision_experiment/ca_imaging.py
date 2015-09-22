import numpy
import time
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import pyqtgraph
from visexpman.engine.generic import utils,gui,signal,fileop
from visexpman.engine.hardware_interface import camera_interface
import Queue
import rpyc
import cPickle as pickle
camen= not False
q=Queue.Queue()

class CaImagingHardwareHandler(object):
    def start_ir_camera_acquisition(self):
        self.camera=camera_interface.SpotCam()
#        self.camera=camera_interface.SpotCamAcquisition()
        self.camera.set_exposure(self.settings['Exposure time']*1e-3, self.settings['Gain'])
        self.camera_running=True
#        self.camera.command.put({'set_exposure':[self.settings['Exposure time'], self.settings['Gain']]})
#        self.camera.start()
        self.printc('Camera started')
        
    def stop_ir_camera(self):
#        if hasattr(self, 'camera') and self.camera.is_alive():
#            self.camera.command.put('terminate')
#            self.camera.join(1)
        if hasattr(self, 'camera'):
            self.camera_running=False
            self.camera.close()
            del self.camera
            self.printc('Camera stopped')

    def read_ir_image(self):
        if hasattr(self, 'camera'):
            return self.camera.get_image()
#        if hasattr(self, 'camera') and hasattr(self.camera, 'response') and not self.camera.response.empty():
#            self.camera.command.put({'get_image':''})
#            return self.camera.response.get()
            
            
    def update_settings(self, values, paths, refs):
        self.settings = {}
        for i in range(len(paths)):
            self.settings[paths[i][-1]]=values[i]
            
    def help(self):
        import rpyc
        self.c=rpyc.connect('localhost',port = 18861)
        self.c.root.set_exposure(self.settings['Exposure time']*1e-3, self.settings['Gain'])
        self.camera_running=True
        
class Images(QtGui.QWidget):
    def __init__(self, parent):
        self.parent = parent
        QtGui.QWidget.__init__(self, parent)
        image_names = ['Live', 'Reference']
        self.image={}
        self.layout = QtGui.QHBoxLayout()
        for n in image_names:
            self.image[n]=gui.Image(self)
            self.image[n].plot.setLabels(left='um', bottom='um')
            self.image[n].plot.setTitle(n)
            self.image[n].setMinimumWidth(self.parent.machine_config.GUI['SIZE']['col']/2.5)
            self.image[n].setFixedHeight(self.parent.machine_config.GUI['SIZE']['col']/2.5)
            self.layout.addWidget(self.image[n])
        self.setLayout(self.layout)

class CaImaging(gui.VisexpmanMainWindow, CaImagingHardwareHandler):
    def __init__(self, context):
        if QtCore.QCoreApplication.instance() is None:
            qt_app = Qt.QApplication([])
        gui.VisexpmanMainWindow.__init__(self, context)
        self.toolbar = gui.ToolBar(self, ['live_ir_camera', 'live_two_photon', 'snap_two_photon', 'stop', 'exit'])
        self.addToolBar(self.toolbar)
        self.images=Images(self)
        self.setCentralWidget(self.images)
        self.debug = gui.Debug(self)
        self._add_dockable_widget('Debug', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea, self.debug)
        self.settings = gui.ParameterTable(self, self._get_params_config())
        self.settings.setMinimumWidth(300)
        self.settings.params.sigTreeStateChanged.connect(self.settings_changed)
        self._add_dockable_widget('Settings', QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.LeftDockWidgetArea, self.settings)
        self._set_window_title()
        self.show()
        self.settings_changed()
        self.timer=QtCore.QTimer()
        self.timer.start(80)#ms
        self.connect(self.timer, QtCore.SIGNAL('timeout()'), self.read_image)
        self.camera_running = False
        self.resize(self.machine_config.GUI['SIZE']['col'], self.machine_config.GUI['SIZE']['row'])
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
        if self.camera_running:
#            self.printc('reading image')
            im=pickle.loads(self.c.root.get_image())
            self.im=im
            if im is not None:
#                im*=0.2
#                im+=0.5
                im=im.T
                self.images.image['Live'].img.setImage(im, levels = (0,255))
                self.images.image['Live'].setFixedWidth(float(im.shape[0])/im.shape[1]*self.images.image['Live'].height())
            
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
        
    def settings_changed(self):
        self.update_settings(*self.settings.get_parameter_tree())
        
class CameraService(rpyc.Service):
        
    def on_connect(self):
        # code that runs when a connection is created
        # (to init the serivce, if needed)
        print 'connect'
        if camen:
            self.camera=camera_interface.SpotCam()
        
    def exposed_set_exposure(self,e,g):
        self.camera.set_exposure(e,g)
        
    def exposed_get_image(self):
        return pickle.dumps(self.camera.get_image())

    def on_disconnect(self):
        # code that runs when the connection has already closed
        # (to finalize the service, if needed)
        print 'disconnect'
        if camen:
            self.camera.close()

    def exposed_test(self,a): # this is an exposed method
        print a
        time.sleep(1)
        return numpy.random.random((1200,1600))
        
    def exposed_stop_server(self):
        q.put('exit')
        
    def __del__(self):
        print 'close camera'
        if camen and hasattr(self, 'camera'):
            self.camera.close()
        
def run_camera_server():
    from rpyc.utils.server import ThreadedServer,Server,OneShotServer
    while True:
        t = OneShotServer(CameraService, port = 18861)
        t.start()
        if not q.empty() and q.get()=='exit':
            break
            
if __name__ == '__main__':
    import visexpman.engine
    context = visexpman.engine.application_init(user = 'zoltan', config = 'CaImagingTestConfig', user_interface_name = 'ca_imaging', log_sources = ['engine'])
    context['logger'].start()
    m = CaImaging(context=context)
    visexpman.engine.stop_application(context)
