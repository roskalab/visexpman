'''
generic.gui module has generic gui widgets like labeled widgets. It also contains some gui helper function
'''
import os
import numpy
import time,unittest
import copy,logging,tempfile
import queue as Queue
import PyQt5.Qt as Qt
#import PyQt5.QtGui as QtGui
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtGui as QtGui
import PyQt5.QtCore as QtCore
import pyqtgraph
import pyqtgraph.console
from visexpman.engine.generic import utils,stringop,fileop,signal,introspect
from pyqtgraph.parametertree import Parameter, ParameterTree
import traceback,sys

def excepthook(excType, excValue, tracebackobj):
    msg='\n'.join(traceback.format_tb(tracebackobj))+str(excType.__name__)+': '+str(excValue)
    print(msg)
    error_messages.put(msg)
    
sys.excepthook = excepthook

error_messages = Queue.Queue()


def get_icon(name, icon_folder=None):
    if icon_folder is None:
        root = os.path.join(fileop.visexpman_package_path(),'data', 'icons')
    else:
        root = icon_folder
    return QtGui.QIcon(os.path.join(root, '{0}.png'.format(name)))
    
def set_win_icon():
    '''
    Ensures that icon is visible on win7 taskbar
    '''
    if os.path.exists('C:\\Users'):
        import ctypes
        myappid = 'visexpman main user interface' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        
        
class VisexpmanMainWindow(Qt.QMainWindow):
    def __init__(self, context = {}):
        Qt.QMainWindow.__init__(self)
        set_win_icon()
        if context != {}:
            for c in ['machine_config', 'user_interface_name', 'socket_queues', 'warning', 'logger']:
                setattr(self,c,context[c])
            self.source_name = '{0}' .format(self.user_interface_name)
        self.text = ''
        self.error_timer = QtCore.QTimer()
        self.error_timer.timeout.connect(self.catch_error_message)
        self.error_timer.start(200)
        self.timer=QtCore.QTimer()
        self.timer.start(50)#ms
        self.timer.timeout.connect(self.check_queue)
        self.enable_help=False
        if self.enable_help:
            menubar = self.menuBar()
            helpmenu=menubar.addMenu("&Help")
            show_manual_action = QtGui.QAction("Show Manual", self)
            show_about_action = QtGui.QAction("About", self)
            helpmenu.addAction(show_manual_action)
            helpmenu.addAction(show_about_action)
            self.helper = QtGui.QToolButton()
            self.tooltip_state=False
            self.helper.setFixedSize(22, 22)
            self.iconfolder=os.path.join(fileop.visexpman_package_path(),'data', 'icons')
            self.helper.setIcon(QtGui.QIcon(os.path.join(self.iconfolder, "help_off.png")))
            self.helper.setToolTip('Click here for detailed help')
            self.helper.clicked.connect(self.help_click)
            menubar.setCornerWidget(self.helper)
            self.tooltiplist = []
            for item in self.findChildren(QtGui.QWidget):#TODO: implement aggregating tooltip strings automatically
                self.tooltiplist.append(item.toolTip())
                item.setToolTip("")
        
    def help_click(self):
        widgets = self.findChildren(QtGui.QWidget)
        if(self.tooltip_state):
            self.helper.setIcon(QtGui.QIcon(os.path.join(self.iconfolder,"help_on.png")))
            for item in widgets:
                item.setToolTip("")
            self.helper.setToolTip('Click here for detailed help')            
            self.tooltip_state = False
        else:
            self.helper.setIcon(QtGui.QIcon(os.path.join(self.iconfolder,"help_off.png")))
            for item in widgets:
                item.setToolTip(self.tooltiplist[widgets.index(item)])
            self.helper.setToolTip('Click here to hide tooltips')
            self.tooltip_state = True
        
    def check_queue(self):
        pass

    def _set_window_title(self, animal_file='', tag=''):
        self.setWindowTitle('{0}{1}' .format(utils.get_window_title(self.machine_config), ' - ' + animal_file if len(animal_file)>0 else ''+tag))
        
    def _add_dockable_widget(self, title, position, allowed_areas, widget):
        dock = QtWidgets.QDockWidget(title, self)
        dock.setAllowedAreas(allowed_areas)
        dock.setWidget(widget)
        self.addDockWidget(position, dock)
        dock.setFeatures(dock.DockWidgetMovable | dock.DockWidgetClosable |dock.DockWidgetFloatable)
        return dock
        
    def _write2statusbar(self,txt):
        self.statusbar.showMessage(txt)
        
    def printc(self, text, logonly = False, popup_error=True):
        '''
        text is displayed on console and logged to logfile
        '''
        text = str(text)
        if not logonly:
            self.text  += utils.timestamp2hms(time.time()) + ' '  + text + '\n'
            self.debug.log.update(self.text)
        loglevels = ['warning', 'error']
        loglevel = [l for l in loglevels if l in text.lower()]
        if 'error' in text.lower() and popup_error:
            QtWidgets.QMessageBox.question(self, 'Error', text, QtWidgets.QMessageBox.Ok)
        if len(loglevel)>0:
            loglevel = loglevel[0]
            getattr(self.logger, loglevel)(text.replace('{0}: '.format(loglevel.upper()),''), self.source_name)
        else:
            self.logger.info(text, self.source_name)
            
    def catch_error_message(self):
        if not error_messages.empty():
            self.logger.error(error_messages.get())
            
    def _start_engine(self,engine):
        self.engine = engine
        self.to_engine, self.from_engine = self.engine.get_queues()
        self.engine.start()
        
    def _stop_engine(self):
        self.to_engine.put('terminate')
        self.engine.join()
        
    def send_all_parameters2engine(self):
        values, paths, refs = self.params.get_parameter_tree()
        for i in range(len(refs)):
            self.to_engine.put({'data': values[i], 'path': '/'.join(paths[i]), 'name': refs[i].name()})
            
    def load_all_parameters(self):
#        print('AAA')
        values, paths, refs = self.params.get_parameter_tree()
#        print('BBB')
        paths = ['/'.join(p) for p in paths]
        if hasattr(self, 'engine'):
            for item in self.engine.guidata.to_dict():
                mwname = item['path'].split('/')[0]
                if mwname == 'params':
                    try:
                        r = refs[paths.index([p for p in paths if p == item['path']][0])]
                    except IndexError:
                        continue
                    r.setValue(item['value'])
                    r.setDefault(item['value'])
                elif mwname == 'stimulusbrowser':
                    self.stimulusbrowser.select_stimulus(item['value'])
                elif mwname == 'hash':
                    continue
                else:
                    ref = introspect.string2objectreference(self, 'self.'+item['path'].replace('/','.'))
                    wname = ref.__class__.__name__.lower()
                    if 'checkbox' in wname:
                        ref.setCheckState(2 if item['value'] else 0)
                    elif 'qtabwidget' in wname:
                        ref.setCurrentIndex(item['value'])
        else:
            if not hasattr(self,  'settings'):
                self.settings=self.parameters
            for k, v in self.settings.items():
                try:
                    r = refs[paths.index([p for p in paths if k in p][0])]
                except IndexError:
                    continue
#                print((k, v, r))
                import pdb
                r.setValue(v)
                r.setDefault(v)
#        print('!!!')

    def plotw(self, x, y):
        '''
        use cases: 
        1) x, y list of arrays
        2) x 2d numpy array, y fsample
        '''
        if hasattr(x, 'dtype'):
            xi=x.shape[1]*[numpy.arange(x.shape[0])/y]#y as fsample
            yi=[x[:, i]+i*10 for i in range(x.shape[1])]
            self.pt=Plot(None)
            self.pt.update_curves(xi, yi)
            self.pt.show()
        else:
            self.pt=Plot(None)
            self.pt.update_curves(x, y)
            self.pt.show()
        
    def closeEvent(self, e):
        e.accept()
        print('close event')
        self.exit_action()

class SimpleGuiWindow(Qt.QMainWindow):
    def __init__(self, logfolder=tempfile.gettempdir()):
        if QtCore.QCoreApplication.instance() is None:
            self.qt_app = Qt.QApplication([])
        Qt.QMainWindow.__init__(self)
        if not hasattr(self, 'logfile'):
            self.logfile = os.path.join(logfolder, 'log_{0}.txt'.format(utils.timestamp2ymdhms(time.time(), filename=True)))
#        logging.basicConfig(filename= self.logfile,
#                    format='%(asctime)s %(levelname)s\t%(message)s',
#                    level=logging.INFO)
        self.logtext=''
        self.debugw = Debug(self)
        self.logw=self.debugw.log
        self.add_dockwidget(self.debugw, 'Log/Debug', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea)
        self.init_gui()
        self.error_timer = QtCore.QTimer()
        self.error_timer.timeout.connect(self.catch_error_message)
        self.error_timer.start(300)
        self.log_update_timer = QtCore.QTimer()#Makes sure that whole logfile is always displayed on screen
        self.log_update_timer.timeout.connect(self.logfile2screen)
        self.log_update_timer.start(300)
        if hasattr(self,'maximized') and self.maximized:
            self.showMaximized()
        else:
            self.show()
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()

    def init_gui(self):
        '''
        Placeholder for creating application specific widgets and layout
        '''
                    
    def logfile2screen(self):
        if not os.path.exists(self.logfile):
            return
        newlogtext=fileop.read_text_file(self.logfile)
        if len(newlogtext)!=len(self.logtext):
            self.logtext=newlogtext
            self.logw.update(self.logtext)
            
    def set_status(self,state, color):
        self.statusbar.status_msg.setStyleSheet(f'background:{color};')
        self.statusbar.status_msg.setText(state)
        QtCore.QCoreApplication.instance().processEvents()

    def log(self, msg, loglevel='info'):
        getattr(logging, loglevel)(str(msg))
        print(f'{loglevel}: {msg}')
        if os.path.exists(self.logfile):
            self.logw.update(fileop.read_text_file(self.logfile))
        
    def catch_error_message(self):
        if not error_messages.empty():
            self.log(error_messages.get(),'error')
            
    def add_dockwidget(self, widget, title, position, allowed_areas):
        dock = QtWidgets.QDockWidget(title, self)
        dock.setAllowedAreas(allowed_areas)
        dock.setWidget(widget)
        self.addDockWidget(position, dock)
        dock.setFeatures(dock.DockWidgetMovable | dock.DockWidgetClosable |dock.DockWidgetFloatable)
        
    def ask4confirmation(self, action2confirm):
        reply = QtWidgets.QMessageBox.question(self, 'Confirm:', action2confirm, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.No:
            return False
        else:
            return True
            
    def ask4filename(self,title, directory, filter):
        filename = QtWidgets.QFileDialog.getOpenFileName(self, title, directory, filter)[0]
        if os.name=='nt':
            filename=filename.replace('/','\\')
        return filename
        
    def ask4filenames(self,title, directory, filter):
        filenames = QtWidgets.QFileDialog.getOpenFileNames(self, title, directory, filter)[0]
        if os.name=='nt':
            filenames=[filename.replace('/','\\') for filename in filenames]
        return filenames
        
    def ask4foldername(self,title, directory):
        foldername = QtWidgets.QFileDialog.getExistingDirectory(self, title, directory)
        if os.name=='nt':
            foldername=foldername.replace('/','\\')
        return foldername
        
    def notify_user(self, title, message):#OBSOLETE
        self.notify(self, title, message)
        
    def notify(self, title, message):
        QtWidgets.QMessageBox.question(self, title, message, QtWidgets.QMessageBox.Ok)
        
    def plotw(self, x, y):
        '''
        use cases: 
        1) x, y list of arrays
        2) x 2d numpy array, y fsample
        '''
        if hasattr(x, 'dtype'):
            xi=x.shape[1]*[numpy.arange(x.shape[0])/y]#y as fsample
            yi=[x[:, i]+i*10 for i in range(x.shape[1])]
            self.pt=Plot(None)
            self.pt.update_curves(xi, yi)
            self.pt.show()
        else:
            self.pt=Plot(None)
            self.pt.update_curves(x, y)
            self.pt.show()
            
class SimpleAppWindow(SimpleGuiWindow):
    '''
    Deprecated
    '''

class Progressbar(QtWidgets.QWidget):
    def __init__(self, maxtime, name = '', autoclose = False, timer=False):
        self.maxtime = maxtime
        self.autoclose = autoclose
        QtWidgets.QWidget.__init__(self)
        self.setWindowTitle(name)
        self.progressbar = QtGui.QProgressBar(self)
        self.progressbar.setTextVisible(False)
        self.progressbar.setRange(0, maxtime)
        self.progressbar.setMinimumWidth(300)
        self.progressbar.setMinimumHeight(30)
        self.setMinimumWidth(320)
        self.setMinimumHeight(50)
        self.move(10,10)
        self.l = QtGui.QGridLayout()
        self.l.addWidget(self.progressbar, 0, 0, 1, 1)
        self.setLayout(self.l)
        self.t0=time.time()
        if timer:
            self.maxtime=100
            self.timer=QtCore.QTimer()
            self.timer.start(200)#ms
            self.connect(self.timer, QtCore.SIGNAL('timeout()'), self.update_time)
    
    def update(self,value):
        self.progressbar.setValue(value)
        if self.autoclose and value == 100:
            self.close()
        
    def update_time(self):
        now=time.time()
        dt=now-self.t0
        if dt>self.maxtime:
            dt = self.maxtime
            self.timer.stop()
            if self.autoclose:
                self.close()
        self.progressbar.setValue(dt)

class ToolBar(QtWidgets.QToolBar):
    '''
    Toolbar holding the following shortcuts:
    -experiment start, stop, snap, live start, exit
    '''
    def __init__(self, parent, icon_names, toolbar_size = 35, icon_folder=None):
        self.icon_names = icon_names
        self.parent=parent
        self.icon_folder = icon_folder
        QtWidgets.QToolBar.__init__(self, 'Toolbar', parent)
        self.add_buttons()
        self.setIconSize(QtCore.QSize(toolbar_size, toolbar_size))
        self.setFloatable(False)
        self.setMovable(False)
        
    def add_buttons(self):
        for button in self.icon_names:
            a = QtWidgets.QAction(get_icon(button,self.icon_folder), stringop.to_title(button), self)
            a.triggered.connect(getattr(self.parent, button+'_action'))
            self.addAction(a)
            
    def hideEvent(self,e):
        self.setVisible(True)
        
class Debug(QtWidgets.QTabWidget):
    def __init__(self,parent):
        self.parent=parent
        QtWidgets.QTabWidget.__init__(self,parent)
        self.log = TextOut(self)
        self.console = PythonConsole(self)
        self.addTab(self.log, 'Log')
        self.addTab(self.console, 'Python Debug')
        self.setTabPosition(self.South)

class PythonConsole(pyqtgraph.console.ConsoleWidget):
    def __init__(self, parent, selfw = None):
        if selfw == None:
            selfw = parent.parent
        pyqtgraph.console.ConsoleWidget.__init__(self, namespace={'self':selfw, 'utils':utils, 'fileop': fileop, 'signal':signal, 'numpy': numpy, 'os':os}, text = 'self: main gui widget, numpy, utils, fileop, signal, os, experiment_data')

class ParameterTable(ParameterTree):
    def __init__(self, parent, params):
        self.parent = parent
        ParameterTree.__init__(self, parent, showHeader=False)
        self.params = Parameter.create(name='params', type='group', children=params)
        self.setParameters(self.params, showTop=False)
        
    def update(self, params):
        self.params = Parameter.create(name='params', type='group', children=params)
        self.setParameters(self.params, showTop=False)
        
        
    def get_parameter_tree(self, return_dict = False,variable_names=False):
        nodes = [[children for children in self.params.children()]]
        import itertools
        while True:
            nodes.append(list(itertools.chain(*[n.children() for n in nodes[-1]])))
            if len(nodes[-1])==0: break
        nodes = list(itertools.chain(*nodes))
        leafes = [n for n in nodes if len(n.children())==0]
        paths = []
        refs = []
        values = []
#        print('!!!get_parameter_tree!!!')
        for l in leafes:
            value = l.value()
            name = l.name()
#            print ((name, value))
            path = []
#            ref=copy.deepcopy(l)
            ref=l
            while True:
                if ref.parent() is None: break
                else: 
                    path.append(ref.name())
                    ref= ref.parent()
            path.append('params')
            path.reverse()
            paths.append(path)
            values.append(value)
            refs.append(l)
        if return_dict:
            res = {}
            for i in range(len(paths)):
                k='/'.join(paths[i])
                if variable_names:
                    k=stringop.to_variable_name(k)
                res[k]=values[i]
            return res
        else:
            return values, paths, refs

class AddNote(QtWidgets.QWidget):
    def __init__(self, parent,text,togui_queue):
        self.togui_queue=togui_queue
        QtWidgets.QWidget.__init__(self, parent)
        self.text=QtGui.QTextEdit(self)
        self.text.setPlainText(text)
        self.text.ensureCursorVisible()
        self.text.setCursorWidth(1)
        self.text.moveCursor(QtGui.QTextCursor.End)
        self.text.setFixedWidth(250)
        self.text.setFixedHeight(80)
        self.move(100,100)
        self.save=QtGui.QPushButton('Save' ,parent=self)
        self.l = QtGui.QGridLayout()
        self.l.addWidget(self.text, 0, 0, 1, 1)
        self.l.addWidget(self.save, 0, 1, 1, 1)
        self.setLayout(self.l)
        self.save.clicked.connect(self.save_note)
        self.show()
        
    def save_note(self):
        if QtCore.QT_VERSION_STR[0]=='5':
            self.togui_queue.put({'save_comment':str(self.text.toPlainText())})
        else:
            self.emit(QtCore.SIGNAL('addnote'),str(self.text.toPlainText()))
        self.close()
            
class TextOut(QtWidgets.QTextEdit):
    def __init__(self, parent):
        QtWidgets.QTextEdit.__init__(self, parent)
        self.setPlainText('')
        self.setReadOnly(True)
        self.ensureCursorVisible()
        self.setCursorWidth(5)
        
    def update(self, text):
        self.setPlainText(text)
        self.moveCursor(QtGui.QTextCursor.End)
        
class Plot(pyqtgraph.GraphicsLayoutWidget):
    def __init__(self,parent,**kwargs):
        pyqtgraph.GraphicsLayoutWidget.__init__(self,parent)
        self.setBackground((255,255,255))
        self.setAntialiasing(True)
        self.plot=self.addPlot(**kwargs)
        self.plot.enableAutoRange()
        self.plot.showGrid(True,True,1.0)
        
    def update_curve(self, x, y, pen=(0,0,0), plotparams = {}, autoDownsample=False):
        self._clear_curves()
        self.curve = self.plot.plot(pen=pen, **plotparams, autoDownsample=autoDownsample)
        self.curve.setData(x, y)
        if min(y) == max(y) or numpy.isnan(min(y)) or numpy.isnan(max(y)):
            return
        self.plot.setYRange(min(y), max(y))
        
    def update_curves(self, x, y, plot_average=False, colors = [], plotparams=[], autoDownsample=False):
        self._clear_curves()
        if len(x)==0: return
        ncurves = len(x)
        self.curves = []
        minimums = []
        maximums = []
        if len(plotparams)>0 and any([True for pp in plotparams if 'name' in pp.keys()]):
            if self.plot.legend != None:
                self.plot.legend.removeItem(self.plot.legend)
            # Checking if parameters exist:
            if 'labelTextColor' in plotparams[0] and plotparams[0]['labelTextColor'] != None:
                labelTextColor=pyqtgraph.mkColor(plotparams[0]['labelTextColor'])

            else: 
                labelTextColor=pyqtgraph.mkColor('r')
            if 'offset' in plotparams[0] and plotparams[0]['offset'] != None:
                offset=plotparams[0]['offset']
            else: 
                offset=(30, 30)
            if 'brush' in plotparams[0] and plotparams[0]['brush'] != None:
                brush=pyqtgraph.mkBrush(plotparams[0]['brush'])
            else: 
                brush=pyqtgraph.mkBrush(0)
            self.plot.addLegend(offset=offset, labelTextColor=labelTextColor, brush=brush)
            self.plot.legend.setScale(0.7)
            if 'labelTextSize' in plotparams[0] and plotparams[0]['labelTextSize'] != None:
                self.plot.legend.setLabelTextSize(plotparams[0]['labelTextSize'])
            
        for i in range(ncurves):
            if len(plotparams)>0:
                self.curves.append(self.plot.plot(**plotparams[i], autoDownsample=autoDownsample))
            else:
                if colors == []:
                    pen = (0,0,0)
                else:
                    pen=pyqtgraph.mkPen(width=4.5, color=colors[i])
                self.curves.append(self.plot.plot(pen=pen, autoDownsample=autoDownsample))
            self.curves[-1].setData(x[i], y[i])
            minimums.append(y[i].min())
            maximums.append(y[i].max())
        if plot_average:
            self.curves.append(self.plot.plot(autoDownsample=autoDownsample))
            self.curves[-1].setPen((200,0,0), width=3)
            x_,y_ = signal.average_of_traces(x,y)
            self.curves[-1].setData(x_, y_)
        if min(minimums)<max(maximums):
            self.plot.setYRange(min(minimums), max(maximums))
        
    def _clear_curves(self):
        if hasattr(self, 'curve'):
            self.plot.removeItem(self.curve)
            del self.curve
        if hasattr(self, 'curves'):
            map(self.plot.removeItem, self.curves)
            del self.curves
        self.plot.clear()
        
    def add_linear_region(self, boundaries, color=(40,40,40,100)):
        if len(boundaries)%2==1:
            raise RuntimeError('Invalid boundaries: {0}'.format(boundaries))
        if hasattr(self,'linear_regions'):
            for linear_region in self.linear_regions:
                self.plot.removeItem(linear_region)
        self.linear_regions=[]
        for i in range(int(len(boundaries)/2)):
            self.linear_regions.append(pyqtgraph.LinearRegionItem(boundaries[2*i:2*(i+1)], movable=False, brush = color))
            self.plot.addItem(self.linear_regions[-1])
            
class TimeAxisItemHHmm(pyqtgraph.AxisItem):
    def __init__(self, *args, **kwargs):
        pyqtgraph.AxisItem.__init__(self,*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        return [QtCore.QTime().addMSecs(value).toString('hh:mm') for value in values]
        
class TimeAxisItemYYMMDD(pyqtgraph.AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [QtCore.QDate(self.year,self.month,self.day).addDays(value).toString('yyyy-MM-dd') for value in values]

            
class TabbedPlots(QtWidgets.QWidget):
    def __init__(self, parent,names,plot_kwargs={}):
        QtGui.QWidget.__init__(self, parent)
        self.names=names
        self.tab = QtGui.QTabWidget(self)
        self.tab.setTabPosition(self.tab.South)
        for pn in names:
            p=Plot(self, **plot_kwargs.get(pn,{}))
            setattr(self, pn, p)
            self.tab.addTab(p, pn)
            
class TabbedImages(QtWidgets.QWidget):
    def __init__(self, parent,names):
        QtGui.QWidget.__init__(self, parent)
        self.names=names
        self.tab = QtGui.QTabWidget(self)
        self.tab.setTabPosition(self.tab.South)
        for pn in names:
            p=Image(self)
            setattr(self, pn, p)
            self.tab.addTab(p, pn)

        
class Image(pyqtgraph.GraphicsLayoutWidget):
    def __init__(self,parent, roi_diameter = 20, background_color = (255,255,255), selected_color = (255,0,0), unselected_color = (150,100,100),enable_manual_points=False,image_clickable=False):
        pyqtgraph.GraphicsLayoutWidget.__init__(self,parent)
        self.enable_manual_points=enable_manual_points
        self.image_clickable=image_clickable
        self.default_roi_type='rect'
        self.unselected_color = unselected_color
        self.selected_color = selected_color
        self.setBackground(background_color)
        self.roi_default_diameter = roi_diameter
        self.plot=self.addPlot()
        self.img = pyqtgraph.ImageItem(border='w')
        self.plot.addItem(self.img)
        self.plot.showGrid(True,True,1.0)
        self.scene().sigMouseClicked.connect(self.mouse_clicked)
        self.rois = []    
        self.dot_size=6
        self.concatenate_manual_points=False
        
        if 0: #Experimental code for adding custom context menu
            #Add LUT min/max slider to context menu
            self.min=LabeledSlider(None,'Min')
            self.min.input.setOrientation(QtCore.Qt.Horizontal)
            self.min.input.valueChanged.connect(self.min_changed)
            menu=self.plot.vb.menu
            setmin= QtGui.QWidgetAction(menu)
            setmin.setDefaultWidget(self.min)
            menu.addAction(setmin)
    
    def min_changed(self):
        self.min.valuelabel.setText(str(self.min.input.value()))
        print(self.min.input.value())
        self.img.setLevels([self.min.input.value()*1e-2,1.0]) 
        
    def set_image(self, image, color_channel=None, alpha = 0.8, imargs={}):
        self.rawimage=image
        im=alpha*numpy.ones((image.shape[0],image.shape[1], 4))*image.max()
        if len(image.shape) == 2 and color_channel is not None:
            im[:,:,:3] = 0
            if color_channel == 'all':
                for i in range(3):
                    im[:,:,i] = image
            elif isinstance(color_channel, int):
                im[:,:,color_channel] = image
            else:
                raise RuntimeError('Invalid image configuration: {0}, {1}'.format(image.shape, color_channel))
        elif len(image.shape) == 3 and image.shape[2] ==3:
            im[:,:,:3]=image
        self.img.setImage(im,**imargs)
        
    def set_scale(self,scale):
        self.img.setScale(scale)
        
    def add_polygon(self,points):
        self.points=points.tolist()
        print(self.points)
        pl=self.plot.plot(points[:,0],points[:,1], pen=(0,0,185),symbolBrush=(0,0,185), symbolPen='b', pxMode=True,symbolSize=self.dot_size)
        self.manual_points=[pl]

    def mouse_clicked(self,e):
        print(e)
        p=self.img.mapFromScene(e.scenePos())
        if self.image_clickable:
            if e.double():
                if hasattr(self, 'clicked_callback'):
                    self.clicked_callback(p.x(),p.y())
        if self.enable_manual_points:
            if e.double():
#                print(int(e.buttons()))
#                print(e.modifiers())
                if int(e.buttons()) == 1:
                    if e.modifiers()==QtCore.Qt.ControlModifier or e.modifiers()==QtCore.Qt.ShiftModifier:
                        if len(self.manual_points)>0:
                            if self.concatenate_manual_points:
                                self.plot.removeItem(self.manual_points[-1])
                                del self.manual_points[-1]
                                del self.points[-1]
                                points=numpy.array(self.points)
                                if len(points)>0:
                                    pl=self.plot.plot(points[:,0],points[:,1], pen=(0,0,185),symbolBrush=(0,0,185), symbolPen='b', pxMode=True,symbolSize=self.dot_size)
                                    self.manual_points.append(pl)
                            else:
                                self.point_coos=numpy.array([[self.manual_points[pi].xvalue,self.manual_points[pi].yvalue] for pi in range(len(self.manual_points))])
                                distance_square_sums=((self.point_coos-numpy.array([[p.x(),p.y()]]))**2).sum(axis=1)                            
                                self.plot.removeItem(self.manual_points[distance_square_sums.argmin()])
                                del self.manual_points[distance_square_sums.argmin()]
                    else:
                        if not hasattr(self, 'manual_points'):
                            self.manual_points=[]
                        #ppp=pyqtgraph.mkPen(color='r', width=0.4)
                        #
                        if self.concatenate_manual_points:
                            if len(self.manual_points)==0:
                                self.points=[[p.x(),p.y()]]
                            else:
                                #points=[[p.xvalue, p.yvalue] for p in self.manual_points]
                                self.points.append([p.x(),p.y()])
                            if len(self.manual_points):
                                self.plot.removeItem(self.manual_points[-1])
                                del self.manual_points[-1]
                            points=numpy.array(self.points)
                            pl=self.plot.plot(points[:,0],points[:,1], pen=(0,0,185),symbolBrush=(0,0,185), symbolPen='b', pxMode=True,symbolSize=self.dot_size)
                        else:
                            pl=self.plot.plot(numpy.array([p.x()]),numpy.array([p.y()]),  pen=None, symbol='o',symbolSize=self.dot_size)
                        pl.xvalue=p.x()
                        pl.yvalue=p.y()
                        self.manual_points.append(pl)
                elif int(e.buttons()) == 2:
                    print(self.manual_points)
        elif not self.image_clickable:
            ctrl_pressed=int(QtGui.QApplication.keyboardModifiers())&QtCore.Qt.ControlModifier!=0
            if e.double():
                if int(e.buttons()) == 1:
                    if hasattr(self, 'queue'):
                        self.queue.put((p.x(), p.y()))
                        return
                    else:
                        self.add_roi(p.x()*self.img.scale(), p.y()*self.img.scale(),type=self.default_roi_type)
                elif int(e.buttons()) == 2:
                    self.remove_roi(p.x()*self.img.scale(), p.y()*self.img.scale())
                else:
                    self.emit(QtCore.SIGNAL('wheel_double_click'), p.x(), p.y())
                #self.update_roi_info()
            elif not e.double() and int(e.buttons()) != 1 and int(e.buttons()) != 2:
                self.emit(QtCore.SIGNAL('roi_mouse_selected'), p.x(), p.y(),ctrl_pressed)
        
    def add_roi(self,x,y, size=None, type='rect', movable = True):
        if size is None:
            size = [self.roi_default_diameter,self.roi_default_diameter]
        if type == 'circle':
            roi = pyqtgraph.CircleROI([x-0.5*size, y-0.5*size], [size, size])
        elif type =='point':
            s=[0.3,0.3] if size==None else size
            roi = pyqtgraph.ROI((x,y),size=s,movable=False,removable=True)
        elif type == 'rect':
            roi = pyqtgraph.RectROI((x-0.5*size[0],y-0.5*size[1]),size=size, movable = movable)
        roi.setPen((self.unselected_color[0],self.unselected_color[1],self.unselected_color[2],255), width=2)
        #roi.sigRegionChanged.connect(self.update_roi_info)
        self.rois.append(roi)
        self.plot.addItem(self.rois[-1])
        
        
    def remove_roi(self,x,y):
        distances = [(r.pos().x()-x)**2+(r.pos().y()-y)**2 for r in self.rois]
        if len(distances)==0:return
        removable_roi = self.rois[numpy.array(distances).argmin()]
        self.plot.removeItem(removable_roi)
        self.rois.remove(removable_roi)
        
    def remove_all_rois(self):
        for r in self.rois:
            self.plot.removeItem(r)
        self.rois = []
        self.plot.items = [item for item in self.plot.items if not 'ROI' in item.__class__.__name__]
        
    def set_roi_visibility(self,x,y,visibility):
        distances = [(r.pos().x()-x)**2+(r.pos().y()-y)**2 for r in self.rois]
        if len(distances)==0:return
        selected_roi = self.rois[numpy.array(distances).argmin()]
        selected_roi.setVisible(visibility)
        
    def update_roi_info(self):
        self.roi_info = [[i, self.rois[i].x(), self.rois[i].y(), self.rois[i].size().x()] for i in range(len(self.rois))]
        self.emit(QtCore.SIGNAL('roi_update'))
        
    def add_linear_region(self, boundaries, color=(40,40,40,100)):
        if len(boundaries)%2==1:
            raise RuntimeError('Invalid boundaries: {0}'.format(boundaries))
        if hasattr(self,'linear_regions'):
            for linear_region in self.linear_regions:
                self.plot.removeItem(linear_region)
        self.linear_regions=[]
        for i in range(len(boundaries)//2):
            self.linear_regions.append(pyqtgraph.LinearRegionItem(boundaries[2*i:2*(i+1)], movable=False, brush = color))
            self.plot.addItem(self.linear_regions[-1])
        
        
#    def load_rois(self,roi_info):
#        scale=1
#        self.roi_info = roi_info
#        for r in self.rois:
#            self.plot.removeItem(r)
#        self.rois=[]
#        for r in roi_info:
#            self.add_roi(r[1]+0.5*r[3],r[2]+0.5*r[3],r[3])
#        self.emit(QtCore.SIGNAL('roi_update'))
        
    def highlight_roi(self, index):
        for i in range(len(self.rois)):
            if isinstance(index,list):
                if i in index:
                    self.rois[i].setPen(self.selected_color)
                else:
                    self.rois[i].setPen(self.unselected_color)
            else:
                if i == index:
                    self.rois[i].setPen(self.selected_color)
                else:
                    self.rois[i].setPen(self.unselected_color)
                    


                
def index2filename(index):
    filename = str(index.model().filePath(index))
    #Make compatible filename with win and linux systems
    filename = filename.replace('/', os.sep)
    filename = list(filename)
    filename[0] = filename[0].lower()
    filename = ''.join(filename)
    return filename
        
class FileTree(QtWidgets.QTreeView):
    def __init__(self,parent, root, filterlist = []):
        if not os.path.exists(root):
            raise RuntimeError('{0} does not exists, file tree cannot be created'.format(root))
        self.parent=parent
        QtWidgets.QTreeView.__init__(self,parent)
        self.model = QtWidgets.QFileSystemModel(self)
        self.setModel(self.model)
        self.set_root(root)
        if hasattr(QtCore, 'QStringList'):
            self.model.setNameFilters(QtCore.QStringList(filterlist))
        else:
            self.model.setNameFilters(filterlist)
        self.model.setNameFilterDisables(False)
        self.hideColumn(2)
        self.setColumnWidth(0,350)
        self.setColumnWidth(1,70)
        self.setColumnWidth(2,100)
#        self.doubleClicked.connect(self.test)
#        self.connect(self.selectionModel(), QtCore.SIGNAL('itemClicked(int)'), self.test)
        
    def test(self,i):
        print(self.model.filePath(self.currentIndex()))
        
    def set_root(self,root):
        self.setRootIndex(self.model.setRootPath( root ))

class ArrowButtons(QtWidgets.QGroupBox):
    def __init__(self, name, parent):
        self.parent=parent
        QtWidgets.QGroupBox.__init__(self, name, parent)
        self.setAlignment(Qt.Qt.AlignHCenter)
        config = {'up': 'arrow_up', 'down': 'arrow_down', 'left': 'previous_roi', 'right': 'next_roi'}
        self.buttons={}
        for n, picfile in config.items():
            iconpath = os.path.join(fileop.visexpman_package_path(),'data', 'icons', '{0}.png'.format(picfile) )
            self.buttons[n] = QtGui.QPushButton(QtGui.QIcon(iconpath), '' ,parent=self)
            self.buttons[n].setFlat(True)
            self.buttons[n].setFixedWidth(23)
            self.buttons[n].setFixedHeight(23)
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.buttons['up'], 0, 1)
        self.layout.addWidget(self.buttons['down'], 2, 1)
        self.layout.addWidget(self.buttons['left'], 1, 0)
        self.layout.addWidget(self.buttons['right'], 1, 2)
        self.setFixedWidth(86)
        self.setFixedHeight(86)
        self.setLayout(self.layout)
        for k in config.keys():
            self.connect(self.buttons[k], QtCore.SIGNAL('clicked()'), getattr(self, k))
        self.connect(self, QtCore.SIGNAL('arrow'), self.arrow_clicked)
        
    def up(self):
        self.emit(QtCore.SIGNAL('arrow'),'up')
        
    def down(self):
        self.emit(QtCore.SIGNAL('arrow'),'down')
        
    def left(self):
        self.emit(QtCore.SIGNAL('arrow'),'left')
        
    def right(self):
        self.emit(QtCore.SIGNAL('arrow'),'right')
        
    def arrow_clicked(self, direction):
        '''User should redefine this'''
        
class ImageAdjust(QtWidgets.QWidget):
    '''
    Default value in input field:
        self.input.setText(TEXT)
    '''
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.high = QtGui.QSlider(Qt.Qt.Horizontal,self)
        self.low = QtGui.QSlider(Qt.Qt.Horizontal,self)
        hl=QtGui.QLabel('High', self)
        ll=QtGui.QLabel('Low', self)
        self.fit_image=QtGui.QPushButton('Fit Image' ,parent=self)
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(ll, 0, 0)
        self.layout.addWidget(self.low, 0, 1)
        self.layout.addWidget(hl, 0, 2)
        self.layout.addWidget(self.high, 0, 3)
        self.layout.addWidget(self.fit_image, 0, 4)
        self.setLayout(self.layout)
        self.high.setFixedWidth(100)
        self.low.setFixedWidth(100)
        
class LabeledInput(QtWidgets.QWidget):
    '''
    Default value in input field:
        self.input.setText(TEXT)
    '''
    def __init__(self, parent, label):
        QtGui.QWidget.__init__(self, parent)
        self.label = label
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.labelw = QtGui.QLabel(self.label, self)
        self.input = QtGui.QLineEdit(self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.labelw, 0, 0)
        self.layout.addWidget(self.input, 0, 1)
        self.setLayout(self.layout)

class LabeledComboBox(QtWidgets.QWidget):
    '''
    Default value in input field:
        self.input.setText(TEXT)
    '''
    def __init__(self, parent, label,items=None,editable=False):
        QtGui.QWidget.__init__(self, parent)
        self.label = label
        self.create_widgets()
        if editable:
            self.input.setEditable(editable)
        self.create_layout()
        if items is not None:
            self.update_items(items)

    def create_widgets(self):
        self.labelw = QtGui.QLabel(self.label, self)
        self.input = QtGui.QComboBox(self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.labelw, 0, 0)
        self.layout.addWidget(self.input, 0, 1)
        self.setLayout(self.layout)
        
    def update_items(self,items):
        self.input.blockSignals(True)
        self.input.clear()
        self.input.blockSignals(False)
        self.input.addItems(items)
        
class LabeledListWidget(QtWidgets.QWidget):
    '''
    Default value in input field:
        self.input.setText(TEXT)
    '''
    def __init__(self, parent, label,items=None):
        QtGui.QWidget.__init__(self, parent)
        self.label = label
        self.create_widgets()
        self.create_layout()
        if items is not None:
            self.list.addItems(QtCore.QStringList(items))
            
    def get_selected_item_names(self):
        return [str(i.text()) for i in map(self.list.item, [s.row() for s in self.list.selectedIndexes()])]

    def create_widgets(self):
        self.labelw = QtGui.QLabel(self.label, self)
        self.list = QtGui.QListWidget(self)
        self.list.setSelectionMode(self.list.MultiSelection)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.labelw, 0, 0)
        self.layout.addWidget(self.list, 1, 0)
        self.setLayout(self.layout)
        
class LabeledCheckBox(QtWidgets.QWidget):
    '''
    Default value in input field:
    self.input.setText(TEXT)
    '''
    def __init__(self, parent, label):
        QtWidgets.QWidget.__init__(self, parent)
        self.label = label
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.labelw = QtWidgets.QLabel(self.label, self)
        self.input = QtWidgets.QCheckBox(self)

    def create_layout(self):
        self.layout = QtWidgets.QGridLayout()
        self.layout.addWidget(self.labelw, 0, 0)
        self.layout.addWidget(self.input, 0, 1)
        self.setLayout(self.layout)
        
class LabeledSlider(QtWidgets.QWidget):
    def __init__(self, parent, label):
        QtGui.QWidget.__init__(self, parent)
        self.label = label
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        self.labelw = QtGui.QLabel(self.label, self)
        self.input = QtGui.QSlider(self)
        self.valuelabel= QtGui.QLabel('', self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.labelw, 0, 0)
        self.layout.addWidget(self.input, 0, 1)
        self.layout.addWidget(self.valuelabel, 0, 2)
        self.setLayout(self.layout)
        
class PushButtonWithParameter(QtWidgets.QWidget):
    '''
    Default value in input field:
        self.input.setText(TEXT)
    '''
    def __init__(self, parent, buttonname, parametername):
        QtGui.QWidget.__init__(self, parent)
        self.parametername = parametername
        self.buttonname = buttonname
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.input = LabeledInput(self, self.parametername)
        self.button = QtGui.QPushButton(self.buttonname, self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.input, 0, 1, 1, 2)
        self.layout.addWidget(self.button, 0, 0)
        self.setLayout(self.layout)
               
def update_combo_box_list(self, widget, new_list,  selected_item = None):
    current_value = widget.currentText()
    try:
        if current_value in new_list:
            current_index = new_list.index(current_value)
        else:
            current_index = 0
    except:
        current_index = 0
        self.printc((current_value, new_list))
        self.printc(traceback.format_exc())
    items_list = QtCore.QStringList(new_list)
    widget.blockSignals(True)
    widget.clear()
    widget.addItems(QtCore.QStringList(new_list))
    widget.blockSignals(False)
    if selected_item != None and selected_item in new_list:
        widget.setCurrentIndex(new_list.index(selected_item))
    else:
        widget.setCurrentIndex(current_index)
    
def connect_and_map_signal(self, widget, mapped_signal_parameter, widget_signal_name = 'clicked'):
    self.signal_mapper.setMapping(widget, QtCore.QString(mapped_signal_parameter))
    getattr(getattr(widget, widget_signal_name), 'connect')(self.signal_mapper.map)

def get_combobox_items(combobox):
    return [str(combobox.itemText(i)) for i in range(combobox.count())]
    
def text_input_popup(self, title, name, callback):
    self.w=QtGui.QWidget(None)
    self.w.setWindowTitle(title)
    self.w.setGeometry(50,50,400,100)
    self.w.input=LabeledInput(self.w,name)
    self.w.okbtn=QtGui.QPushButton('OK', parent=self.w)
    self.w.l = QtGui.QGridLayout()
    self.w.l.addWidget(self.w.input, 0, 0, 1, 1)
    self.w.l.addWidget(self.w.okbtn, 1, 0, 1, 1)
    self.w.setLayout(self.w.l)
    self.w.connect(self.w.okbtn, QtCore.SIGNAL('clicked()'), callback)
    self.w.show()
    
class FileInput(Qt.QMainWindow):
    def __init__(self, title,root='.',filter='*.*', mode='file', default='',message=''):
        if QtCore.QCoreApplication.instance() is None:
            self.qt_app = Qt.QApplication([])
        Qt.QMainWindow.__init__(self)
        self.setWindowTitle(title)
        self.title=title
        self.filter=filter
        self.root=root
        self.mode=mode
        self.message=message
        self.default=default
        self.setGeometry(50,50,400,100)
        self.timer=QtCore.QTimer()
        self.timer.singleShot(50, self.popup)#ms
        self.show()
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
            
    def popup(self):
        if self.mode=='file':
            filename = str(QtWidgets.QFileDialog.getOpenFileName(self, self.title, self.root, self.filter)[0])
        elif self.mode=='files':
            filename = map(str,QtWidgets.QFileDialog.getOpenFileNames(self, self.title, self.root, self.filter))
        elif self.mode=='folder':
            filename= str(QtWidgets.QFileDialog.getExistingDirectory(self, self.title, self.root))
        elif self.mode=='text':
            text, ok = QtGui.QInputDialog.getText(self, self.title, '', QtGui.QLineEdit.Normal, self.default)
            self.text=str(text)
        elif self.mode=='message':
            QtWidgets.QMessageBox.question(self, self.title, self.message, QtWidgets.QMessageBox.Ok)
        if self.mode not in ['text','message']:
            if os.name=='nt':
                if isinstance(filename,list):
                    filename=[f.replace('/','\\') for f in filename]
                else:
                    filename=filename.replace('/','\\')
            self.filename=filename
        self.close()
        
def file_input(title='',root='.',filter='*.*', mode='file'):
    g=FileInput(title, root, filter, mode)
    print (g.filename)
    return g.filename
    
def text_input(title='',default=''):
    g=FileInput(title, mode='text',default=default)
    print(g.text)
    return g.text
    
def message(title,message):
    g=FileInput(title, mode='message', message=message)

class ImageClick(Qt.QMainWindow):
    def __init__(self, image,title='',npoints=1):
        if QtCore.QCoreApplication.instance() is None:
            self.qt_app = Qt.QApplication([])
        Qt.QMainWindow.__init__(self)
        self.setWindowTitle(title)
        self.title=title
        self.npoints=npoints
        self.image=Image(self,enable_manual_points=True)#Creating the central widget which contains the image, the plot and the control widgets
        self.image.concatenate_manual_points=True
        self.image.queue=Queue.Queue()
        self.image.set_image(image)
        self.image.setFixedWidth(image.shape[0])
        self.image.setFixedHeight(image.shape[1])
        self.setCentralWidget(self.image)
        self.setGeometry(50,50,image.shape[0]+10,image.shape[1]+10)
        self.timer=QtCore.QTimer()
        self.timer.start(500)#ms
        self.timer.timeout.connect(self.check_exit)
        self.show()
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
            
    def check_exit(self):
        if self.image.queue.qsize()>=self.npoints:
            self.close()
            
    def closeEvent(self, e):
        e.accept()
        print('close event')
            
def image_click(image,title='',npoints=1):
    ic=ImageClick(numpy.fliplr(numpy.flipud(numpy.rot90(image))),title=title,npoints=npoints)
    while ic.isVisible():
        time.sleep(2)
        print('Wait for click')
    points=[]
    while not ic.image.queue.empty():
        points.append(ic.image.queue.get())
    points=[(p[0],image.shape[0]-p[1]) for p in points]
    return points

class GuiTest(unittest.TestCase):
    @unittest.skip('')
    def test_01_ask4filename(self):
        for m in ['files', 'file', 'folder']:
            print(file_input('TEST', mode=m))
            
    @unittest.skip('')
    def test_02_ask4number(self):
        print(text_input('TEXT'))
        
    def test_03_click_image(self):
        print(image_click(numpy.random.random((900,1200,3)),'Title',3))

if __name__=='__main__':
    unittest.main()
