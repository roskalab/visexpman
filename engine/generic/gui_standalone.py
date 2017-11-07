import os,unittest
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
class FileInput(Qt.QMainWindow):
    def __init__(self, title,root='.',filter='*.*', mode='file'):
        if QtCore.QCoreApplication.instance() is None:
            self.qt_app = Qt.QApplication([])
        Qt.QMainWindow.__init__(self)
        self.setWindowTitle(title)
        self.title=title
        self.filter=filter
        self.root=root
        self.mode=mode
        self.setGeometry(50,50,400,100)
        self.timer=QtCore.QTimer()
        self.timer.singleShot(50, self.popup)#ms
        self.show()
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
            
    def popup(self):
        if self.mode=='file':
            filename = str(QtGui.QFileDialog.getOpenFileName(self, self.title, self.root, self.filter))
        elif self.mode=='files':
            filename = map(str,QtGui.QFileDialog.getOpenFileNames(self, self.title, self.root, self.filter))
        elif self.mode=='folder':
            filename= str(QtGui.QFileDialog.getExistingDirectory(self, self.title, self.root))
        if os.name=='nt':
            if isinstance(filename,list):
                filename=[f.replace('/','\\') for f in filename]
            else:
                filename=filename.replace('/','\\')
        self.filename=filename
        self.close()
        
def fileinput(title='',root='.',filter='*.*', mode='file'):
    g=FileInput(title, root, filter, mode)
    print g.filename
    return g.filename

class GuiTest(unittest.TestCase):
    def test_01_ask4filename(self):
        for m in ['files', 'file', 'folder']:
            print fileinput('TEST', mode=m)

if __name__=='__main__':
    unittest.main()
