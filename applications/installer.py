#TODO: progressbar
import os,subprocess,logging,time,sys,shutil,zipfile,tempfile
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

TEST=True

class Installer(Qt.QMainWindow):
    def __init__(self):
        if QtCore.QCoreApplication.instance() is None:
            self.qt_app = Qt.QApplication([])
        Qt.QMainWindow.__init__(self)
        self.setWindowTitle('Vision Experiment Manager Installer')
        self.setGeometry(0,0,0,0)
        if len(sys.argv)>1:
            self.location=sys.argv[1]
        else:
            self.location='unknown'
        self.installer_checksum=2478538140L
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
        self.tmpdirs=[]
        self.notifications=[]
        process = subprocess.Popen(['python', '-h'], stdout=subprocess.PIPE)
        out, err = process.communicate()
        if not TEST and 'usage: python [option] ... [-c cmd | -m mod | file | -] [arg] ...' in out:
            self.notify('Warning', 'Python is already installed')
            self.close()
        #Ask user to specify location of visexpman
        visexpman_default_folder='x:\\software'
        if self.location=='fmi' and not os.path.exists(visexpman_default_folder):
            if self.ask4confirmation('Please mount x drive manually. Abort installation?s',title='Question'):
                self.close()
                return
        visexpman_default_local_folder='c:\\visexp'
        if os.path.exists(visexpman_default_local_folder):
            if not self.ask4confirmation('{0} already exists, visexpman might be already installed, continue?'.format(visexpman_default_local_folder)):
                self.close()
                return
        visexpman_folder = visexpman_default_folder
        if not os.path.exists(visexpman_default_folder):
            visexpman_folder = visexpman_default_local_folder
            os.mkdir(visexpman_folder)
        self.visexpmanfolder=self.ask4foldername('Please select visexpman package location', visexpman_folder)
        self.install_daqmx=self.ask4confirmation('Do you want to install PyDAQmx and NI DAQ?')
        #Check installers:
        if TEST:
            d=os.path.join('c:\\temp','modules')
        else:
            d=os.path.join(os.getcwd(),'modules')
        self.installer_files=[os.path.join(d,f) for f in os.listdir(d)]
        if self.installer_checksum !=sum([os.path.getsize(f) for f in self.installer_files]):
            self.notify('Error', 'Invalid binari(es) in {0}'.format(self.d))
            self.close()
            return
        modules=['anaconda', 'opengl','pygame','opencv','pyqtgraph', 'pyserial', 'gedit', 'tcmd', 'meld']
        for module in modules:
            fn=self.modulename2filename(module)
            logging.info('Installing {0} ...'.format(fn))
            if not TEST:
                subprocess.call(fn,shell=True)
        python_module_folder='c:\\Anaconda\\Lib\\site-packages'
        if not os.path.exists(python_module_folder):
            self.notifications.append('Install pth file manually')
        else:
            logging.info('Creating pth file')
            fp=open(os.path.join(python_module_folder, 'v.pth'), 'wt')
            fp.write(self.visexpmanfolder.replace('\\','\\\\'))
            fp.close()
        if visexpman_folder not in self.visexpmanfolder:
            shutil.copy(self.modulename2filename('hdf5io'), self.visexpmanfolder)
            logging.info('hdf5io copied')
        self.install_ffmpeg()
        if self.install_daqmx:
            fn=self.modulename2filename('nidaq')
            folder=self.extract(fn, 'daq')
            self.tmpdirs.append(folder)
            subprocess.call(os.path.join(folder, 'setup.exe'),shell=True)
            #Untested from this point
            folder=self.extract(fn, 'pydaqmx')
            self.tmpdirs.append(folder)
            os.chdir(folder)
            subprocess.call('python setup.py install',shell=True)
            
        folder=self.extract(fn, 'eric')
        self.tmpdirs.append(folder)
        os.chdir(folder)
        subprocess.call('python install.py',shell=True)
        print 'TODO: create eric4 shortcut'
        #Verify installation
        os.chdir(visexpman_folder)
        subprocess.call('call shortcuts\\verify_installation.bat',shell=True)
        self.notifications.append('change windows theme to classical')
        self.notify('Warning', '\r\n'.join(self.notifications))
            
    def install_ffmpeg(self):
        shutil.copy(self.modulename2filename('ffmpeg'),  self.visexpmanfolder)
        self.notifications.append('add {0} to path environmental variable'.format(self.visexpmanfolder))
        


    def notify(self, title, message):
        QtGui.QMessageBox.question(self, title, message, QtGui.QMessageBox.Ok)
        
    def ask4foldername(self,title, directory):
        foldername = str(QtGui.QFileDialog.getExistingDirectory(self, title, directory))
        if os.name=='nt':
            foldername=foldername.replace('/','\\')
        return foldername
            
    def ask4confirmation(self, action2confirm,title='Confirm:'):
        reply = QtGui.QMessageBox.question(self, title, action2confirm, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.No:
            return False
        else:
            return True
            
    def modulename2filename(self,modulename):
        fn=[f for f in self.installer_files if modulename in f.lower()]
        if len(fn)!=1:
            self.notify('Error', '{0} installer component does not exists'.format(modulename))
        else:
            return fn[0]
            
    def extract(self, zip, tag):
        out=os.path.join(tempfile.gettempdir(), tag)
        if os.path.exists(out):
            shutil.rmtree(out)
        os.mkdir(out)
        z=zipfile.ZipFile(zip)
        z.extractall(out)
        z.close()
        return out

if __name__=='__main__':
    i=Installer()
    
