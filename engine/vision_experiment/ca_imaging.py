import numpy
import time,copy
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import pyqtgraph
from visexpman.engine.generic import utils,gui,signal,fileop
from visexpman.engine.hardware_interface import camera_interface
from visexpman.engine.vision_experiment import gui_engine
import Queue
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

class CaImaging(gui.VisexpmanMainWindow):
    def __init__(self, context):
        if QtCore.QCoreApplication.instance() is None:
            qt_app = Qt.QApplication([])
        gui.VisexpmanMainWindow.__init__(self, context)
        self._start_engine(gui_engine.CaImagingEngine(self.machine_config, self.logger, self.socket_queues))
        self.toolbar = gui.ToolBar(self, ['live_ir_camera', 'live_two_photon', 'snap_two_photon', 'stop', 'exit'])
        self.addToolBar(self.toolbar)
        self.images=Images(self)
        self.images.image['Live'].img.setLevels(0,255)
        self.setCentralWidget(self.images)
        self.debug = gui.Debug(self)
        self._add_dockable_widget('Debug', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea, self.debug)
        self.params = gui.ParameterTable(self, self._get_params_config())
        self.params.setMinimumWidth(300)
        self.params.params.sigTreeStateChanged.connect(self.params_changed)
        self._add_dockable_widget('Settings', QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.LeftDockWidgetArea, self.params)
        self._set_window_title()
        self.show()
        self.load_all_parameters()
        self.timer_img_read=QtCore.QTimer()
        self.timer_img_read.start(80)#ms
        self.connect(self.timer_img_read, QtCore.SIGNAL('timeout()'), self.read_image)
        self.isrunning=False
        self.resize(self.machine_config.GUI['SIZE']['col'], self.machine_config.GUI['SIZE']['row'])
        import multiprocessing
        self.cmd=Queue.Queue()
        self.irimg=Queue.Queue()
        self.u=UdpListener(self.cmd,self.irimg)
        self.u.start()
        
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
            
    def _get_params_config(self):
        channels = self.machine_config.PMTS.keys()
        channels.append('IR')
        filter_names = ['none', '3x3 median filter', 'Histogram shift', 'Histogram equalize']
        image_channel_items = []
        for channel in channels:
            image_channel_items.append({'name': 'Enable {0}'.format(channel), 'type': 'bool', 'value': False})
            image_channel_items.append({'name': 'Display {0}'.format(channel), 'type': 'bool', 'value': False})
            image_channel_items.append({'name': '{0} filter'.format(channel), 'type': 'list', 'values': filter_names, 'value': ''})
        two_photon_items = ([
                                   {'name': 'Scan Height', 'type': 'float', 'value': 100.0, 'siPrefix': True, 'suffix': 'um'},
                {'name': 'Scan Width', 'type': 'float', 'value': 100.0, 'siPrefix': True, 'suffix': 'um'},
                {'name': 'Pixel Size', 'type': 'float', 'value': 1.0, 'siPrefix': True},
                {'name': 'Pixel Size Unit', 'type': 'list', 'values': ['pixel/um', 'um/pixel', 'us'], 'value': 'pixel/um'},
                {'name': 'Averaging', 'type': 'int', 'value': 1},
                                   ])
        pc =  [
                {'name': 'Image Channels', 'type': 'group', 'expanded' : True, 'children': image_channel_items},
                {'name': 'Two Photon Imaging', 'type': 'group', 'expanded' : True, 'children': two_photon_items},
                {'name': 'IR camera', 'type': 'group', 'expanded' : True, 'children': [
                    {'name': 'Exposure time', 'type': 'float', 'value': 100.0, 'siPrefix': True, 'suffix': 'ms'},
                    {'name': 'Gain', 'type': 'float', 'value': 1.0, },
                    ]},
                    {'name': 'Advanced', 'type': 'group', 'expanded' : False, 'children': [
                        {'name': 'Scanner', 'type': 'group', 'expanded' : True, 'children': [
                            {'name': 'Analog Input Sampling Rate', 'type': 'float', 'value': 400.0, 'siPrefix': True, 'suffix': 'kHz'},
                            {'name': 'Analog Output Sampling Rate', 'type': 'float', 'value': 400.0, 'siPrefix': True, 'suffix': 'kHz'},
                            {'name': 'Scan Center X', 'type': 'float', 'value': 0.0, 'siPrefix': True, 'suffix': 'um'},
                            {'name': 'Scan Center Y', 'type': 'float', 'value': 0.0, 'siPrefix': True, 'suffix': 'um'},
                            {'name': 'Stimulus Flash Duty Cycle', 'type': 'float', 'value': 100.0, 'siPrefix': True, 'suffix': '%'},
                            {'name': 'Stimulus Flash Delay', 'type': 'float', 'value': 0.0, 'siPrefix': True, 'suffix': 'us'},
                            {'name': 'X Scanner Flyback Time', 'type': 'float', 'value': 200, 'suffix': 'us'},
                            {'name': 'Y Scanner Flyback Time', 'type': 'float', 'value': 1000, 'suffix': 'us'},
                            {'name': 'Scanner Movement to Voltage Factor', 'type': 'float', 'value': 0.013},
                        ]},
                    ]}
                    ]
        return pc

    def read_image(self):
        if self.isrunning:
            self.to_engine.put({'function': 'read_2p', 'args':[]})

    def live_ir_camera_action(self):
        self.start_ir_camera_acquisition()
        
    def live_two_photon_action(self):
        self.to_engine.put({'function': 'live_2p', 'args':[]})
        
    def snap_two_photon_action(self):
        pass
        
    def stop_action(self):
        self.to_engine.put({'function': 'stop_2p', 'args':[]})
        #self.stop_ir_camera()
            
    def exit_action(self):
        self.send_all_parameters2engine()
        self._stop_engine()
        self.cmd.put('terminate')
        self.u.join()
#        if self.u.is_alive():
#            self.u.terminate()
        self.close()
        
    def params_changed(self, param, changes):
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
            
    def check_queue(self):
        while not self.from_engine.empty():
            msg = self.from_engine.get()
            if msg.has_key('printc'):
                self.printc(msg['printc'])
            elif msg.has_key('send_image_data'):
                self.meanimage, self.image_scale = msg['send_image_data']
                self.images.image['Live'].set_image(self.meanimage)
                self.images.image['Live'].set_scale(self.image_scale)
            elif msg.has_key('set_isrunning'):
                self.isrunning = msg['set_isrunning']
        if not self.irimg.empty():
            self.ir=self.irimg.get()
            self.ir=numpy.rollaxis(numpy.tile(numpy.rot90(numpy.fliplr(self.ir),1),(3,1,1)),0,3)
            self.images.image['Live'].set_image(self.ir,1)
            self.images.image['Live'].plot.setTitle(str(self.ir.sum()))
            
                
import threading,socket,multiprocessing
class UdpListener(threading.Thread):
#class UdpListener(multiprocessing.Process):
    def __init__(self,input,output):
#        multiprocessing.Process.__init__(self)
        threading.Thread.__init__(self)
        self.input=input
        self.output=output
        
    def run(self):
        sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
        sock.bind(('127.0.0.1', 8880))
        sock.settimeout(1)
        linect=0
        NLINES=30
        NCOLS=20
        image_width=1600/2
        frame=numpy.zeros(NLINES*image_width*NCOLS,dtype=numpy.uint8)
        framect=1
        buff=""
        lcs=[]

        while True:
            
            try:
                data, addr = sock.recvfrom(NCOLS*image_width+9) # buffer size is 1024 bytes
                
                buff+=data
                #linect=ord(data.split('start')[1][0])
                #print linect,self.input.empty()
                #lcs.append(linect)
                if 1:
                   # fileop.write_text_file('c:\\tmp\\buf.txt',str(len(buff))+' '+str(framect))
                    
                    if 'start' in buff and 'end' in buff:
                        msg=buff.split('start')[1].split('end')[0]
                        linect=ord(msg[0])
                        lines=msg[1:]
                        buff=buff.replace(buff.split('start')[0]+'start'+msg+'end','')
    #                    f=open('c:\\tmp\\lct.txt','at')
    #                    f.write('{0}\r\n'.format(linect))
    #                    f.close()
                        #print data
                        s=linect*image_width*NCOLS
                        e=(linect+1)*image_width*NCOLS
                        #print linect,len(data),linect>=1200/10
                        #print s,e,len(lines)
                        frame[s:e]=numpy.fromstring(lines,dtype=numpy.uint8)
                        #numpy.save('c:\\rz\\l.npy',numpy.fromstring(lines,dtype=numpy.uint8))
                        #print 2
                        #if linect>=1200/30-1:
                        lcs.append(linect)
                        #print linect,s,e,NLINES-1
                        if linect==NLINES-1:
                            #print 1
                            frameo=frame.reshape((NCOLS*NLINES,image_width))
                            
                            
                            
                            
                            
                            send=frameo
                        
                            self.output.put(send)
                            #fileop.write_text_file('c:\\tmp\\1.txt',str(time.time()))
                            #frame=numpy.zeros(1200*1600,dtype=numpy.uint8)
    #                        from PIL import Image
    #                        Image.fromarray(send).save('c:\\tmp\\ddd.png')
                            framect+=1
            except:
                import traceback
                fileop.write_text_file('c:\\tmp\\e.txt',traceback.format_exc())
            if not self.input.empty() and self.input.get()=='terminate':
                fileop.write_text_file('c:\\tmp\\lines.txt',str(lcs))
                break
           # time.sleep(1e-3)
#class CameraService(rpyc.Service):
#        
#    def on_connect(self):
#        # code that runs when a connection is created
#        # (to init the serivce, if needed)
#        print 'connect'
#        if camen:
#            self.camera=camera_interface.SpotCam()
#        
#    def exposed_set_exposure(self,e,g):
#        self.camera.set_exposure(e,g)
#        
#    def exposed_get_image(self):
#        return pickle.dumps(self.camera.get_image())
#
#    def on_disconnect(self):
#        # code that runs when the connection has already closed
#        # (to finalize the service, if needed)
#        print 'disconnect'
#        if camen:
#            self.camera.close()
#
#    def exposed_test(self,a): # this is an exposed method
#        print a
#        time.sleep(1)
#        return numpy.random.random((1200,1600))
#        
#    def exposed_stop_server(self):
#        q.put('exit')
#        
#    def __del__(self):
#        print 'close camera'
#        if camen and hasattr(self, 'camera'):
#            self.camera.close()
#        
#def run_camera_server():
#    from rpyc.utils.server import ThreadedServer,Server,OneShotServer
#    while True:
#        t = OneShotServer(CameraService, port = 18861)
#        t.start()
#        if not q.empty() and q.get()=='exit':
#            break
            
if __name__ == '__main__':
    import visexpman.engine
    context = visexpman.engine.application_init(user = 'zoltan', config = 'CaImagingTestConfig', user_interface_name = 'ca_imaging', log_sources = ['engine'])
    context['logger'].start()
    m = CaImaging(context=context)
    visexpman.engine.stop_application(context)
