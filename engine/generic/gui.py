'''
generic.gui module has generic gui widgets like labeled widgets. It also contains some gui helper function
'''
import os
import numpy
import time,unittest
import copy,Queue,logging,tempfile
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import pyqtgraph
import pyqtgraph.console
from visexpman.engine.generic import utils,stringop,fileop,signal,introspect
from pyqtgraph.parametertree import Parameter, ParameterTree
import traceback,sys

def excepthook(excType, excValue, tracebackobj):
    msg='\n'.join(traceback.format_tb(tracebackobj))+str(excType.__name__)+': '+str(excValue)
    print msg
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
        self.connect(self.timer, QtCore.SIGNAL('timeout()'), self.check_queue)
        
    def check_queue(self):
        pass

    def _set_window_title(self, animal_file=''):
        self.setWindowTitle('{0}{1}' .format(utils.get_window_title(self.machine_config), ' - ' + animal_file if len(animal_file)>0 else ''))
        
    def _add_dockable_widget(self, title, position, allowed_areas, widget):
        dock = QtGui.QDockWidget(title, self)
        dock.setAllowedAreas(allowed_areas)
        dock.setWidget(widget)
        self.addDockWidget(position, dock)
        dock.setFeatures(dock.DockWidgetMovable | dock.DockWidgetClosable |dock.DockWidgetFloatable)
        
    def _write2statusbar(self,txt):
        self.statusbar.showMessage(txt)
        
    def printc(self, text, logonly = False):
        '''
        text is displayed on console and logged to logfile
        '''
        text = str(text)
        if not logonly:
            self.text  += utils.timestamp2hms(time.time()) + ' '  + text + '\n'
            self.debug.log.update(self.text)
        loglevels = ['warning', 'error']
        loglevel = [l for l in loglevels if l in text.lower()]
        if 'error' in text.lower():
            QtGui.QMessageBox.question(self, 'Error', text, QtGui.QMessageBox.Ok)
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
        values, paths, refs = self.params.get_parameter_tree()
        paths = ['/'.join(p) for p in paths]
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
        
    def closeEvent(self, e):
        e.accept()
        self.exit_action()

class SimpleAppWindow(Qt.QMainWindow):
    def __init__(self):
        if QtCore.QCoreApplication.instance() is None:
            self.qt_app = Qt.QApplication([])
        Qt.QMainWindow.__init__(self)
        if not hasattr(self, 'logfile'):
            self.logfile = os.path.join(tempfile.gettempdir(), 'log_{0}.txt'.format(utils.timestamp2ymdhms(time.time(), filename=True)))
        logging.basicConfig(filename= self.logfile,
                    format='%(asctime)s %(levelname)s\t%(message)s',
                    level=logging.INFO)
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
        newlogtext=fileop.read_text_file(self.logfile)
        if len(newlogtext)!=len(self.logtext):
            self.logtext=newlogtext
            self.logw.update(self.logtext)

    def log(self, msg, loglevel='info'):
        getattr(logging, loglevel)(str(msg))
        self.logw.update(fileop.read_text_file(self.logfile))
        
    def catch_error_message(self):
        if not error_messages.empty():
            self.log(error_messages.get(),'error')
            
    def add_dockwidget(self, widget, title, position, allowed_areas):
        dock = QtGui.QDockWidget(title, self)
        dock.setAllowedAreas(allowed_areas)
        dock.setWidget(widget)
        self.addDockWidget(position, dock)
        dock.setFeatures(dock.DockWidgetMovable | dock.DockWidgetClosable |dock.DockWidgetFloatable)
        
    def ask4confirmation(self, action2confirm):
        reply = QtGui.QMessageBox.question(self, 'Confirm:', action2confirm, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.No:
            return False
        else:
            return True
            
    def ask4filename(self,title, directory, filter):
        filename = str(QtGui.QFileDialog.getOpenFileName(self, title, directory, filter))
        if os.name=='nt':
            filename=filename.replace('/','\\')
        return filename
        
    def ask4filenames(self,title, directory, filter):
        filenames = map(str,QtGui.QFileDialog.getOpenFileNames(self, title, directory, filter))
        if os.name=='nt':
            filenames=[filename.replace('/','\\') for filename in filenames]
        return filenames
        
    def ask4foldername(self,title, directory):
        foldername = str(QtGui.QFileDialog.getExistingDirectory(self, title, directory))
        if os.name=='nt':
            foldername=foldername.replace('/','\\')
        return foldername
        
    def notify_user(self, title, message):#OBSOLETE
        self.notify(self, title, message)
        
    def notify(self, title, message):
        QtGui.QMessageBox.question(self, title, message, QtGui.QMessageBox.Ok)

class Progressbar(QtGui.QWidget):
    def __init__(self, maxtime, name = '', autoclose = False, timer=False):
        self.maxtime = maxtime
        self.autoclose = autoclose
        QtGui.QWidget.__init__(self)
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

class ToolBar(QtGui.QToolBar):
    '''
    Toolbar holding the following shortcuts:
    -experiment start, stop, snap, live start, exit
    '''
    def __init__(self, parent, icon_names, toolbar_size = 35, icon_folder=None):
        self.icon_names = icon_names
        self.parent=parent
        self.icon_folder = icon_folder
        QtGui.QToolBar.__init__(self, 'Toolbar', parent)
        self.add_buttons()
        self.setIconSize(QtCore.QSize(toolbar_size, toolbar_size))
        self.setFloatable(False)
        self.setMovable(False)
        
    def add_buttons(self):
        for button in self.icon_names:
            a = QtGui.QAction(get_icon(button,self.icon_folder), stringop.to_title(button), self)
            a.triggered.connect(getattr(self.parent, button+'_action'))
            self.addAction(a)
            
    def hideEvent(self,e):
        self.setVisible(True)
        
class Debug(QtGui.QTabWidget):
    def __init__(self,parent):
        self.parent=parent
        QtGui.QTabWidget.__init__(self,parent)
        self.log = TextOut(self)
        self.console = PythonConsole(self)
        self.addTab(self.log, 'Log')
        self.addTab(self.console, 'Python Debug')
        self.setTabPosition(self.South)

class PythonConsole(pyqtgraph.console.ConsoleWidget):
    def __init__(self, parent, selfw = None):
        if selfw == None:
            selfw = parent.parent
        pyqtgraph.console.ConsoleWidget.__init__(self, namespace={'self':selfw, 'utils':utils, 'fileop': fileop, 'signal':signal, 'numpy': numpy, 'os':os}, text = 'self: main gui widget, numpy, utils, fileop, signal, os')

class ParameterTable(ParameterTree):
    def __init__(self, parent, params):
        self.parent = parent
        ParameterTree.__init__(self, parent, showHeader=False)
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
        for l in leafes:
            value = l.value()
            name = l.name()
            path = []
            ref= copy.deepcopy(l)
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
                k=paths[i][-1]
                if variable_names:
                    k=stringop.to_variable_name(k)
                res[k]=values[i]
            return res
        else:
            return values, paths, refs

class AddNote(QtGui.QWidget):
    def __init__(self, parent,text):
        QtGui.QWidget.__init__(self, parent)
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
        self.connect(self.save, QtCore.SIGNAL('clicked()'), self.save_note)
        self.show()
        
    def save_note(self):
        self.emit(QtCore.SIGNAL('addnote'),str(self.text.toPlainText()))
        self.close()
            
class TextOut(QtGui.QTextEdit):
    def __init__(self, parent):
        QtGui.QTextEdit.__init__(self, parent)
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
        
    def update_curve(self, x, y, pen=(0,0,0), plotparams = {}):
        self._clear_curves()
        self.curve = self.plot.plot(pen=pen, **plotparams)
        self.curve.setData(x, y)
        if min(y) == max(y) or numpy.isnan(min(y)) or numpy.isnan(max(y)):
            return
        self.plot.setYRange(min(y), max(y))
        
    def update_curves(self, x, y, plot_average=False, colors = [], plotparams=[]):
        self._clear_curves()
        if len(x)==0: return
        ncurves = len(x)
        self.curves = []
        minimums = []
        maximums = []
        if len(plotparams)>0 and any([True for pp in plotparams if 'name' in pp.keys()]):
            if self.plot.legend != None:
                self.plot.legend.scene().removeItem(self.plot.legend)
            self.plot.addLegend()
            self.plot.legend.setScale(0.7)
        for i in range(ncurves):
            if len(plotparams)>0:
                self.curves.append(self.plot.plot(**plotparams[i]))
            else:
                if colors == []:
                    pen = (0,0,0)
                else:
                    pen=colors[i]
                self.curves.append(self.plot.plot(pen=pen))
            self.curves[-1].setData(x[i], y[i])
            minimums.append(y[i].min())
            maximums.append(y[i].max())
        if plot_average:
            self.curves.append(self.plot.plot())
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
        
    def add_linear_region(self, boundaries, color=(40,40,40,100)):
        if len(boundaries)%2==1:
            raise RuntimeError('Invalid boundaries: {0}'.format(boundaries))
        if hasattr(self,'linear_regions'):
            for linear_region in self.linear_regions:
                self.plot.removeItem(linear_region)
        self.linear_regions=[]
        for i in range(len(boundaries)/2):
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

            
class TabbedPlots(QtGui.QWidget):
    def __init__(self, parent,names,plot_kwargs={}):
        QtGui.QWidget.__init__(self, parent)
        self.names=names
        self.tab = QtGui.QTabWidget(self)
        self.tab.setTabPosition(self.tab.South)
        for pn in names:
            p=Plot(self, **plot_kwargs.get(pn,{}))
            setattr(self, pn, p)
            self.tab.addTab(p, pn)
            
class TabbedImages(QtGui.QWidget):
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
    def __init__(self,parent, roi_diameter = 20, background_color = (255,255,255), selected_color = (255,0,0), unselected_color = (150,100,100)):
        pyqtgraph.GraphicsLayoutWidget.__init__(self,parent)
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

    def mouse_clicked(self,e):
        p=self.img.mapFromScene(e.scenePos())
        ctrl_pressed=int(QtGui.QApplication.keyboardModifiers())&QtCore.Qt.ControlModifier!=0
        if e.double():
            if int(e.buttons()) == 1:
                self.add_roi(p.x()*self.img.scale(), p.y()*self.img.scale())
            elif int(e.buttons()) == 2:
                self.remove_roi(p.x()*self.img.scale(), p.y()*self.img.scale())
            else:
                self.emit(QtCore.SIGNAL('wheel_double_click'), p.x(), p.y())
            self.update_roi_info()
        elif not e.double() and int(e.buttons()) != 1 and int(e.buttons()) != 2:
            self.emit(QtCore.SIGNAL('roi_mouse_selected'), p.x(), p.y(),ctrl_pressed)
        
    def add_roi(self,x,y, size=None, type='rect', movable = True):
        if size is None:
            size = [self.roi_default_diameter,self.roi_default_diameter]
        if type == 'circle':
            roi = pyqtgraph.CircleROI([x-0.5*size, y-0.5*size], [size, size])
        elif type =='point':
            roi = pyqtgraph.ROI((x,y),size=[0.3,0.3],movable=False,removable=False)
        elif type == 'rect':
            roi = pyqtgraph.RectROI((x-0.5*size[0],y-0.5*size[1]),size=size, movable = movable)
        roi.setPen((self.unselected_color[0],self.unselected_color[1],self.unselected_color[2],255), width=2)
        roi.sigRegionChanged.connect(self.update_roi_info)
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
        for i in range(len(boundaries)/2):
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
        
class FileTree(QtGui.QTreeView):
    def __init__(self,parent, root, filterlist = []):
        if not os.path.exists(root):
            raise RuntimeError('{0} does not exists, file tree cannot be created'.format(root))
        self.parent=parent
        QtGui.QTreeView.__init__(self,parent)
        self.model = QtGui.QFileSystemModel(self)
        self.setModel(self.model)
        self.set_root(root)
        self.model.setNameFilters(QtCore.QStringList(filterlist))
        self.model.setNameFilterDisables(False)
        self.hideColumn(2)
        self.setColumnWidth(0,350)
        self.setColumnWidth(1,70)
        self.setColumnWidth(2,100)
#        self.doubleClicked.connect(self.test)
#        self.connect(self.selectionModel(), QtCore.SIGNAL('itemClicked(int)'), self.test)
        
    def test(self,i):
        print self.model.filePath(self.currentIndex())
        
    def set_root(self,root):
        self.setRootIndex(self.model.setRootPath( root ))

class ArrowButtons(QtGui.QGroupBox):
    def __init__(self, name, parent):
        self.parent=parent
        QtGui.QGroupBox.__init__(self, name, parent)
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
        
class ImageAdjust(QtGui.QWidget):
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
        


class GroupBox(QtGui.QGroupBox):#OBSOLETE
    def __init__(self, parent, name):
        QtGui.QGroupBox.__init__(self, name, parent)
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        pass
        
    def create_layout(self):
        pass

class LabeledInput(QtGui.QWidget):
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

class LabeledComboBox(QtGui.QWidget):
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
        self.input.addItems(QtCore.QStringList(items))
        
class LabeledListWidget(QtGui.QWidget):
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
        
class LabeledCheckBox(QtGui.QWidget):
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
        self.input = QtGui.QCheckBox(self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.labelw, 0, 0)
        self.layout.addWidget(self.input, 0, 1)
        self.setLayout(self.layout)
        
class PushButtonWithParameter(QtGui.QWidget):
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
        
class ParameterTableOBSOLETE(QtGui.QTableWidget):#Obsolete
    '''
    A special QTable with two columns: first holds the parameter names, the second holds the corresponding parameter values
    '''
    def __init__(self, parent):
        QtGui.QTableWidget.__init__(self, parent)
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(QtCore.QStringList(['Parameter name', 'value']))
        self.verticalHeader().setDefaultSectionSize(20)
        
    def set_values(self, parameters, parname_order=None):
        '''
        Sets the content of the table.
        parameters: dictionary: keys: parameter names, values: parameter values.
        '''
        self.parameters = parameters
        if parameters.has_key('self.editable') and parameters['self.editable'] == 'False':
            lock=True
        else:
            lock=False
        if parameters.has_key('self.editable'):
            del parameters['self.editable']
        if parameters.has_key('self.editable'):
            nrows = len(parameters)-1
        else:
            nrows = len(parameters)
        self.setRowCount(nrows)
        self.setVerticalHeaderLabels(QtCore.QStringList(nrows*['']))
        for row in range(nrows):
            if parname_order is None:
                parname = str(parameters.keys()[row])
            else:
                parname = parname_order[row]
            item = QtGui.QTableWidgetItem(parname)
            item.setToolTip(parname)
            item.setFlags(QtCore.Qt.ItemIsSelectable| QtCore.Qt.ItemIsEnabled)
            self.setItem(row, 0, item)#Set parameter name
            #Setting value of table element depends on the widget type
            if self.cellWidget(row,1) is None:
                value = str(parameters[parname]).split('#')
                if len(value) == 2:
                    comment = value[1]
                value = value[0]
                item=QtGui.QTableWidgetItem(value)
                if 'comment' in locals():
                    item.setToolTip(comment)
                if lock:
                    item.setFlags(QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsEnabled)
                self.setItem(row, 1, item)
            elif hasattr(self.cellWidget(row,1), 'date'):
                d, m, y=map(int, str(parameters[parname]).split('-'))
                self.cellWidget(row,1).setDate(QtCore.QDate(y, m, d))
            elif hasattr(self.cellWidget(row,1), 'currentText'):
                #Find out index
                items = get_combobox_items(self.cellWidget(row,1))
                if str(parameters[parname]) in items:
                    index = items.index(str(parameters[parname]))
                    self.cellWidget(row,1).setCurrentIndex(index)
                elif self.cellWidget(row,1).isEditable():
                    self.cellWidget(row,1).setEditText(str(parameters[parname]))

    def get_values(self):
        '''
        Return values of table in a dictionary format
        '''
        current_values = {}
        for row in range(self.rowCount()):
            parname = str(self.item(row,0).text())
            if hasattr(self.item(row,1), 'text') and self.cellWidget(row,1) is None and hasattr(self.item(row,1), 'toolTip'):
                    current_values[parname] = [str(self.item(row,1).text()), str(self.item(row,1).toolTip())]
            elif hasattr(self.item(row,1), 'text'):
                current_values[parname] = str(self.item(row,1).text())
            elif hasattr(self.cellWidget(row,1), 'date'):
                date = self.cellWidget(row,1).date()
                current_values[parname] = '{0}-{1}-{2}'.format(date.day(), date.month(), date.year())
            elif hasattr(self.cellWidget(row,1), 'currentText'):
                current_values[parname] = str(self.cellWidget(row,1).currentText())
            elif self.item(row,1) is None:
                current_values[parname] = ''
            else:
                raise NotImplementedError('Reader for this type of widget is not implemented {0}. Parameter name: {1}'.format(self.item(row,1), parname))
        return current_values
        
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

def load_experiment_config_names(config, widget):#OBSOLETE
    '''
    Loads all experiment config names and adds them to a dropdown widget
    OBSOLETE
    '''
    if hasattr(config, 'user'):
        import visexpman
        experiment_config_list = utils.fetch_classes('visexpman.users.' + config.user,  required_ancestors = visexpman.engine.vision_experiment.experiment.ExperimentConfig, direct = False)
        experiment_config_names = []
        for experiment_config in experiment_config_list:
            experiment_config_names.append(experiment_config[1].__name__)
        experiment_config_names.sort()
        widget.addItems(QtCore.QStringList(experiment_config_names))
        try:
            if hasattr(config, 'EXPERIMENT_CONFIG'):
                widget.setCurrentIndex(experiment_config_names.index(config.EXPERIMENT_CONFIG))
        except ValueError:
            pass
    return experiment_config_list
    
class WidgetControl(object):#OBSOLETE
    def __init__(self, poller, config, widget):
        self.config = config
        self.poller = poller
        self.widget = widget
        self.printc = self.poller.printc
    
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
