try:
    import PyQt4.Qt as Qt
    import PyQt4.QtGui as QtGui
    import PyQt4.QtCore as QtCore
except ImportError:
    import PyQt5.Qt as Qt
    import PyQt5.QtGui as QtGui
    import PyQt5.QtCore as QtCore
from visexpman.engine.generic import gui
import cv2,numpy

class WebcamViewer(gui.SimpleAppWindow):
    
    def __init__(self):
        gui.SimpleAppWindow.__init__(self)
        
    def init_gui(self):
        camw=1024#1920/2
        camh=768#1080/2
        imgh=900
        self.setGeometry(0,0,1950,1080)
        self.cw=QtGui.QWidget(self)
        self.cw.img=gui.Image(self)
        self.cw.img.setFixedHeight(imgh)
        self.cw.img.setFixedWidth(imgh*float(camw)/camh)
        self.setCentralWidget(self.cw)#Setting it as a central widget
        self.debugw.setFixedHeight(200)
        self.camera = cv2.VideoCapture(0)
        self.camera.set(3, camw)
        self.camera.set(4, camh)
        self.cam_timer=QtCore.QTimer()
        self.cam_timer.start(40)#ms
        self.connect(self.cam_timer, QtCore.SIGNAL('timeout()'), self.read_frame)
    
    def read_frame(self):
        ret, frame = self.camera.read()
        if frame is None or not ret:
            return
        frame=frame[frame.shape[0]/4:3*frame.shape[0]/4,frame.shape[1]/4:3*frame.shape[1]/4,:]
        frame_color_corrected=numpy.zeros_like(frame)
        frame_color_corrected[:,:,0]=frame[:,:,2]
        frame_color_corrected[:,:,1]=frame[:,:,1]
        frame_color_corrected[:,:,2]=frame[:,:,0]
        frame_color_corrected=numpy.fliplr(frame_color_corrected)
        frame_color_corrected=frame_color_corrected.swapaxes(0,1)
        
        self.cw.img.set_image(frame_color_corrected,alpha=1.0)
        
    def closeEvent(self, e):
        e.accept()
        self.camera.release()
        
if __name__ == '__main__':
    WebcamViewer()
