import sys
import os
from os import listdir
from os.path import isfile, join, basename
from PyQt5.QtGui import QStandardItemModel
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QComboBox, QTreeView, QGridLayout
#from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot, Qt
 
class RepoFileSelector(QWidget):
    
    usersFolder = "/Users/anbucci/Software/visexpman/users/" #path completo 

    def __init__(self):
        super().__init__()
        self.title = 'PyQt5 button - pythonspot.com'
        self.left = 10
        self.top = 10
        self.width = 800
        self.height = 600
        self.initUI()


 
    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        # start button
        btnStart = QPushButton('Start', self)
        btnStart.setToolTip('Start stimulus')
        btnStart.clicked.connect(self.on_click)
        
        # quit button
        btnQuit = QPushButton('Cancel', self)
        btnQuit.setToolTip('Quit stimulus')
        btnQuit.clicked.connect(self.off_click)      

        # dropdown box
        comboUser = QComboBox(self)        
        dirNames = [x[0] for x in os.walk(self.usersFolder)]
        dirNames.pop(0)
        for dirs in dirNames:
            comboUser.addItem(os.path.basename(os.path.normpath(dirs)))


        comboUser.currentIndexChanged[str].connect(self.on_comboUser_currentIndexChanged)


        # directory view
        self.tree = QTreeView()                
        self.model = QStandardItemModel(0, 1, self)
        self.model.setHeaderData(0, Qt.Horizontal, "Name")
        self.tree.setModel(self.model)

        windowLayout = QGridLayout()
        windowLayout.addWidget(comboUser,0,0)
        windowLayout.addWidget(self.tree,0,1)
        windowLayout.addWidget(btnStart,2,0)
        windowLayout.addWidget(btnQuit,2,1)
        self.setLayout(windowLayout)
        self.show()


 
    @pyqtSlot()
    def on_click(self):
        #TODO this will be the selected file from filelist
       # selected_file = "matej-testing_stimuli.py"
        print('Run visexp_app')
        #os.system("export PYTHONPATH=~/Software:PYTHONPATH")
        #os.system("../../visexpman/engine/visexp_app.py -u anbucci -c MEAConfig -a stim -s " + basename(selected_file))
        #os.system("python ./engine/visexp_app.py -u anbucci -c MEAConfig -a stim -s " + basename(selected_file))
        


    def off_click(self):
        print('End stimulus')


    @pyqtSlot(str)
    def on_comboUser_currentIndexChanged(self, index):        
        mypath = self.usersFolder + str(index)
        
        onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
                
        self.model.setRowCount(0)

        for item in onlyfiles:    
            self.model.insertRow(0)
            self.model.setData(self.model.index(0, 0), item)
            
        print(onlyfiles)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = RepoFileSelector()
    sys.exit(app.exec_())