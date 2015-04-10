import cPickle as pickle
import os
import os.path
import time
import threading
import Queue
import unittest
import numpy
import hdf5io
from visexpman.engine.vision_experiment import experiment_data, cone_data
from visexpman.engine.generic import fileop, signal

class GUIDataItem(object):
    def __init__(self,name,value,path):
        self.name = name
        self.n = name
        self.value = value
        self.v=value
        self.path = path
        self.p=path
        
class GUIData(object):
    def __init__(self,context_filename):
        self.context_filename = context_filename
        #TODO: reads data items from context file

    def add(self, name, value, path):
        setattr(self,name,GUIDataItem(name,value,path))#Overwritten if already exists

    def read(self, name = None, path = None, **kwargs):
        if name is not None and hasattr(self,name):
            return getattr(self,name).value
        elif path is not None:
            for v in dir(self):
                v = getattr(self,v)
                if isinstance(v, GUIDataItem) and (v.path == path or path in v.path):
                    return v.value

    def save(self,context_filename = None):
        if context_filename is None:
            context_filename = self.context_filename

class Analysis(object):
    def __init__(self,machine_config):
        self.machine_config = machine_config

    def open_datafile(self,filename):
        if fileop.parse_recording_filename(filename)['type'] != 'data':
            self.printc('This file cannot be displayed')
            return
        self.printc('Opening {0}'.format(filename))
        self.datafile = experiment_data.CaImagingData(filename)
        self.tsync, self.timg, self.meanimage, self.image_scale, self.raw_data = self.datafile.prepare4analysis()
        self.datafile.close()
        self.to_gui.put({'show_meanimage' :self.meanimage})
        
    def find_cells(self):
        if not hasattr(self, 'meanimage') or not hasattr(self, 'image_scale'):
            self.printc('Open datafile first')
            return
        self.printc('Searching for cells, please wait...')
        min_ = int(2/self.image_scale)
        max_ = int(3/self.image_scale)
        sigma = 0.5/self.image_scale
        threshold_factor = 1.0
        self.suggested_rois = cone_data.find_rois(numpy.cast['uint16'](signal.scale(self.meanimage, 0,2**16-1)), min_,max_,sigma,threshold_factor)
        self.suggested_roi_contours = map(cone_data.somaroi2edges, self.suggested_rois)
        self.image_w_suggested_rois = numpy.zeros((self.meanimage.shape[0], self.meanimage.shape[1], 3))
        self.image_w_suggested_rois[:,:,1] = self.meanimage
        for coo in self.suggested_roi_contours:
            self.image_w_suggested_rois[coo[:,0],coo[:,1],2]=self.meanimage.max()*0.4
        self.to_gui.put({'show_suggested_rois' :self.image_w_suggested_rois})
    
class GUIEngine(threading.Thread, Analysis):
    '''
    GUI engine: receives commands via queue interface from guiand performs the following actions:
     - stores data internally
     - initiates actions on gui or in engine
     
     Command format:
     {'command_name': [parameters]}
    '''

    def __init__(self, machine_config):
        self.machine_config = machine_config
        threading.Thread.__init__(self)
        self.from_gui = Queue.Queue()
        self.to_gui = Queue.Queue()
        self.guidata = GUIData(fileop.get_context_filename(machine_config))
        Analysis.__init__(self, machine_config)
        
    def get_queues(self):
        return self.from_gui, self.to_gui
        
    def test(self):
        self.to_gui.put({'function':'test', 'args':[]})
        
    def printc(self,txt):
        self.to_gui.put({'printc':str(txt)})
    
    def run(self):
        while True:
            try:
                if not self.from_gui.empty():
                    msg = self.from_gui.get()
                    if msg == 'terminate':
                        break
                else:
                    continue
                #parse message
                if msg.has_key('data'):#expected format: {'data': value, 'path': gui path, 'name': name}
                    self.guidata.add(msg['name'], msg['data'], msg['path'])#Storing gui data
                elif msg.has_key('read'):#engine might need additional data for executing a certain function
                    value = self.guidata.read(**msg)
                    getattr(self, 'to_gui').put(value)
                elif msg.has_key('function'):#Functions are simply forwarded
                    #Format: {'function: function name, 'args': [], 'kwargs': {}}
                    getattr(self, msg['function'])(*msg['args'])
            except:
                import traceback
                self.printc(traceback.format_exc())
            time.sleep(20e-3)

class TestGUIEngineIF(unittest.TestCase):
    def setUp(self):
        self.wait = 100e-3
        from visexpman.users.test.test_configurations import GUITestConfig
        self.machine_config = GUITestConfig()
        self.machine_config.user_interface_name = 'main_ui'
        self.machine_config.user = 'test'
        self.engine = GUIEngine(self.machine_config)
        self.from_gui, self.to_gui = self.engine.get_queues()
        self.engine.start()
        
    def test_01_add_and_read_data(self):
        v = 100
        self.from_gui.put({'data': v, 'name': 'dummy', 'path': 'test.dummy'})
        time.sleep(self.wait)
        self.assertEqual(self.engine.guidata.dummy.v, v)
        self.assertEqual(self.engine.guidata.dummy.n, 'dummy')
        self.from_gui.put({'read':None, 'name':'dummy'})
        time.sleep(self.wait)
        self.assertFalse(self.to_gui.empty())
        self.assertEqual(self.to_gui.get(), v)
        #access by path
        self.from_gui.put({'read':None, 'path':'dummy'})
        time.sleep(self.wait)
        self.assertFalse(self.to_gui.empty())
        self.assertEqual(self.to_gui.get(), v)
        #access by invalid path
        self.from_gui.put({'read':None, 'path':'dummy.'})
        time.sleep(self.wait)
        self.assertFalse(self.to_gui.empty())
        self.assertEqual(self.to_gui.get(), None)
        
    def test_02_function(self):
        function_call={'function': 'test', 'args': []}
        self.from_gui.put(function_call)
        time.sleep(self.wait)
        self.assertFalse(self.to_gui.empty())
        self.assertEqual(self.to_gui.get(), function_call)
        
    def tearDown(self):
        self.from_gui.put('terminate')
        self.engine.join()
        


if __name__=='__main__':
    unittest.main()
