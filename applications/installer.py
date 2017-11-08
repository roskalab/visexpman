#TODO: progressbar
import os,subprocess,logging,time,sys,shutil
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

class Installer(Qt.QMainWindow):
    def __init__(self):
        if QtCore.QCoreApplication.instance() is None:
            self.qt_app = Qt.QApplication([])
        Qt.QMainWindow.__init__(self)
        self.setWindowTitle('Vision Experiment Manager Installer')
        self.setGeometry(0,0,0,0)
        self.location=sys.argv[1]
        self.dependencies_checksum=0
        self.logfile = os.path.join('install_log_{0}.txt'.format(time.time()))
        logging.basicConfig(filename= self.logfile,
                    format='%(asctime)s %(levelname)s\t%(message)s',
                    level=logging.INFO)
        self.timer=QtCore.QTimer()
        self.timer.singleShot(50, self.installer)#ms
        self.show()
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
            
    def installer(self):
        process = subprocess.Popen(['python', '-h'], stdout=subprocess.PIPE)
        out, err = process.communicate()
        if 'usage: python [option] ... [-c cmd | -m mod | file | -] [arg] ...' in out:
            self.notify('Warning', 'Python is already installed')
            self.close()
        #Ask user to specify location of visexpman
        visexpman_default_folder='x:\\software'
        if self.location=='fmi':
            if not os.path.exists(visexpman_default_folder):
                cmd='net use x: \\rldata.fmi.ch\data /persistent:Yes'
                subprocess.call(cmd, shell=True)
                self.notify('Warning', 'Type credentials')
        visexpman_default_local_folder='c:\\visexp'
        if os.path.exists(visexpman_default_local_folder):
            if not self.ask4confirmation('{0} already exists, visexpman might be already installed, continue?'.format(visexpman_default_local_folder)):
                self.close()
        if not os.path.exists(visexpman_default_folder):
            visexpman_folder = visexpman_default_local_folder
            os.mkdir(visexpman_folder)
        self.visexpmanfolder=self.ask4foldername('Please select visexpman package location', visexpman_folder)
        self.install_daqmx=self.ask4confirmation('Do you want to install PyDAQmx and NI DAQ?')
        #Check installers:
        d=os.path.join(os.getcwd(),'dependencies')
        installer_files=[os.path.join(d,f) for f in os.listdir(d)]
        if self.dependencies_checksum !=sum([os.path.getsize(f) for f in installer_files]):
            self.notify('Error', 'Invalid binari(es) in {0}'.format(d))
            self.close()
        modules=['anaconda', 'opengl','pygame','opencv','pyqtgraph', 'pyserial', 'gedit', 'tcmd']
        for module in modules:
            fn=self.modulename2filename(module)
            logging.info('Installing {0} ...'.format(fn))
            subprocess.call(fn,shell=True)        
        print 'TODO: create pth file'
        if visexpman_folder not in self.visexpmanfolder:
            print 'TODO: copy hdf5io to self.visexpmanfolder'
        self.install_ffmpeg()
        if self.install_daqmx:
            fn=self.modulename2filename('daqmx')
            print 'TODO: unzip'
            print 'TODO: install PyDAQmx'
        subprocess.call('cd {0}&python install.py'.format(self.modulename2filename('eric')),shell=True)
        print 'TODO: create eric4 shortcut'
        #Verify installation
        subprocess.call('cd {0}&call shortcuts\\verify_installation.bat'.format(visexpman_folder),shell=True)
            
        
            
    def install_ffmpeg(self):
        print 'TODO: copy ffmpeg to program files'
        print 'TODO: Add path to system path'
        


    def notify(self, title, message):
        QtGui.QMessageBox.question(self, title, message, QtGui.QMessageBox.Ok)
        
    def ask4foldername(self,title, directory):
        foldername = str(QtGui.QFileDialog.getExistingDirectory(self, title, directory))
        if os.name=='nt':
            foldername=foldername.replace('/','\\')
        return foldername
            
    def ask4confirmation(self, action2confirm):
        reply = QtGui.QMessageBox.question(self, 'Confirm:', action2confirm, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.No:
            return False
        else:
            return True
            
    def modulename2filename(self,modulename):
        fn=[f for f in self.installer_files if modulename in f.lower()]
        if len(fn)!=1:
            self.notify('{0} installer component does not exists'.format(modulename))
        else:
            return fn[0]

if __name__=='__main__':
    i=Installer()
    
