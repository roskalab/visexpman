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
from visexpman.engine.generic import fileop, signal,stringop,utils

class GUIDataItem(object):
    def __init__(self,name,value,path):
        self.name = name
        self.n = name
        self.value = value
        self.v=value
        self.path = path
        self.p=path
        
class GUIData(object):
    def add(self, name, value, path):
        setattr(self,stringop.to_variable_name(name),GUIDataItem(name,value,path))#Overwritten if already exists

    def read(self, name = None, path = None, **kwargs):
        if name is not None and hasattr(self,stringop.to_variable_name(name)):
            return getattr(self,stringop.to_variable_name(name)).value
        elif path is not None:
            for v in dir(self):
                v = getattr(self,v)
                if isinstance(v, GUIDataItem) and (v.path == path or path in v.path):
                    return v.value
                    
    def to_dict(self):
        return [{'name': getattr(self, vn).n, 'value': getattr(self, vn).v, 'path': getattr(self, vn).p} for vn in dir(self) if isinstance(getattr(self, vn), GUIDataItem)]
        
    def from_dict(self, data):
        for item in data:
            setattr(self, stringop.to_variable_name(item['name']), GUIDataItem(stringop.to_title(item['name']), item['value'], item['path']))
            
                    
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
        self.rois=[]
        self.to_gui.put({'send_image_data' :[self.meanimage, self.image_scale, self.tsync, self.timg]})
        background_threshold = self.guidata.read('Background threshold')*1e-2
        self.background = cone_data.calculate_background(self.raw_data,threshold=background_threshold)
        
    def find_cells(self):
        if not hasattr(self, 'meanimage') or not hasattr(self, 'image_scale'):
            self.printc('Open datafile first')
            return
        self.printc('Searching for cells, please wait...')
        min_ = int(self.guidata.read('Minimum cell radius')/self.image_scale)
        max_ = int(self.guidata.read('Maximum cell radius')/self.image_scale)
        sigma = self.guidata.read('Sigma')/self.image_scale
        threshold_factor = self.guidata.read('Threshold factor')
        self.suggested_rois = cone_data.find_rois(numpy.cast['uint16'](signal.scale(self.meanimage, 0,2**16-1)), min_,max_,sigma,threshold_factor)
        self.suggested_roi_contours = map(cone_data.somaroi2edges, self.suggested_rois)
        self.image_w_suggested_rois = numpy.zeros((self.meanimage.shape[0], self.meanimage.shape[1], 3))
        self.image_w_suggested_rois[:,:,1] = self.meanimage
        for coo in self.suggested_roi_contours:
            self.image_w_suggested_rois[coo[:,0],coo[:,1],2]=self.meanimage.max()*0.4
        self.to_gui.put({'show_suggested_rois' :self.image_w_suggested_rois})
        #Calculate roi bounding box
        self.roi_bounding_boxes = [[rc[:,0].min(), rc[:,0].max(), rc[:,1].min(), rc[:,1].max()] for rc in self.suggested_roi_contours]
        self.roi_rectangles = [[sum(r[:2])*0.5, sum(r[2:])*0.5, (r[1]-r[0]), (r[3]-r[2])] for r in self.roi_bounding_boxes]
        self.raw_roi_curves = [self.raw_data[:,:,r[:,0], r[:,1]].mean(axis=2).flatten()-self.background for r in self.suggested_rois]
        self._pack_roi_info()
        self.current_roi_index = 0
        self._normalize_roi_curves()
        self.display_roi_rectangles()
        self.display_roi_curve()
        
    def _pack_roi_info(self):
        self.rois.extend([{'raw': self.raw_roi_curves[i], 'rectangle': self.roi_rectangles[i], 'area': self.suggested_rois[i]} for i in range(len(self.roi_rectangles))])
        
    def _normalize_roi_curves(self):
        baseline_length = self.guidata.read('Baseline lenght')
        for r in self.rois:
            r['normalized'] = signal.df_over_f(self.timg, r['raw'], self.tsync[0], baseline_length)
        
    def display_roi_rectangles(self):
        self.to_gui.put({'display_roi_rectangles' :[list(numpy.array(r['rectangle'])*self.image_scale) for r in self.rois]})
        
    def display_roi_curve(self):
        if len(self.rois)>0:
            self.to_gui.put({'display_roi_curve': [self.timg, self.rois[self.current_roi_index]['normalized'], self.current_roi_index, self.tsync]})
        
    def remove_roi_rectangle(self):
        if len(self.rois)>0:
            self.to_gui.put({'remove_roi_rectangle' : numpy.array(self.rois[self.current_roi_index]['rectangle'][:2])*self.image_scale})
        
    def roi_mouse_selected(self,x,y):
        if len(self.rois)==0:
            return
        roi_centers = numpy.array([r['rectangle'][:2] for r in self.rois])
        p=numpy.array([x,y])
        self.current_roi_index = ((roi_centers-p)**2).sum(axis=1).argmin()
        self.display_roi_curve()
        
    def previous_roi(self):
        if not hasattr(self, 'current_roi_index'):
            return
        self.current_roi_index -= 1
        if self.current_roi_index==-1:
            self.current_roi_index=len(self.rois)-1
        self.display_roi_curve()
        
    def next_roi(self):
        if not hasattr(self, 'current_roi_index'):
            return
        self.current_roi_index += 1
        if self.current_roi_index==len(self.rois):
            self.current_roi_index=0
        self.display_roi_curve()
        
    def delete_roi(self):
        if not hasattr(self, 'current_roi_index'):
            return
        self.remove_roi_rectangle()
        self.printc('Removing roi: {0}'.format(self.rois[self.current_roi_index]['rectangle']))
        del self.rois[self.current_roi_index]
        if len(self.rois)==0:
            self.current_roi_index = 0
        elif len(self.rois)<=self.current_roi_index:
            self.current_roi_index = len(self.rois)-1
        self.display_roi_curve()
        
    def add_manual_roi(self, rectangle):
        rectangle = numpy.array(rectangle)/self.image_scale
        rectangle[0] +=0.5*rectangle[2]
        rectangle[1] +=0.5*rectangle[3]
        raw = self.raw_data[:,:,rectangle[0]-0.5*rectangle[2]: rectangle[0]+0.5*rectangle[2], rectangle[1]-0.5*rectangle[3]: rectangle[1]+0.5*rectangle[3]].mean(axis=2).mean(axis=2).flatten()
        self.rois.append({'rectangle': rectangle, 'raw': raw})
        self.current_roi_index = len(self.rois)-1
        self._normalize_roi_curves()
        self.to_gui.put({'fix_roi' : None})
        self.display_roi_curve()
        self.printc('Roi added, {0}'.format(rectangle))
    
class GUIEngine(threading.Thread, Analysis):
    '''
    GUI engine: receives commands via queue interface from gui and performs the following actions:
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
        self.context_filename = fileop.get_context_filename(self.machine_config)
        self.load_context()
        Analysis.__init__(self, machine_config)
        
    def load_context(self):
        self.guidata = GUIData()
        if os.path.exists(self.context_filename):
            self.guidata.from_dict(utils.array2object(hdf5io.read_item(self.context_filename, 'guidata', filelocking=False)))
        else:
            self.printc('Warning: Restart gui because parameters are not in guidata')#TODO: fix it!!!
            
    def save_context(self):
        hdf5io.save_item(self.context_filename, 'guidata', utils.object2array(self.guidata.to_dict()), filelocking=False, overwrite=True)
        
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
                elif msg.has_key('read'):#gui might need to read guidata database
                    value = self.guidata.read(**msg)
                    getattr(self, 'to_gui').put(value)
                elif msg.has_key('function'):#Functions are simply forwarded
                    #Format: {'function: function name, 'args': [], 'kwargs': {}}
                    getattr(self, msg['function'])(*msg['args'])
            except:
                import traceback
                self.printc(traceback.format_exc())
            time.sleep(20e-3)
        self.close()
        
    def close(self):
        self.save_context()

class TestGUIEngineIF(unittest.TestCase):
    def setUp(self):
        self.wait = 100e-3
        from visexpman.users.test.test_configurations import GUITestConfig
        self.machine_config = GUITestConfig()
        self.machine_config.user_interface_name = 'main_ui'
        self.machine_config.user = 'test'
        self.cf=fileop.get_context_filename(self.machine_config)
        fileop.remove_if_exists(self.cf)
        if '_03_' in self._testMethodName:
            guidata = GUIData()
            guidata.add('Sigma 1', 0.5, 'path/sigma')
            hdf5io.save_item(self.cf, 'guidata', utils.object2array(guidata.to_dict()), filelocking=False)
        self.engine = GUIEngine(self.machine_config)
        
        self.engine.save_context()
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
        
    def test_03_context(self):
        self.from_gui.put({'read':None, 'name':'Sigma 1'})
        time.sleep(self.wait)
        self.assertFalse(self.to_gui.empty())
        self.assertEqual(self.to_gui.get(), 0.5)
        
    def tearDown(self):
        self.from_gui.put('terminate')
        self.engine.join()
        self.assertTrue(os.path.exists(self.cf))
        


if __name__=='__main__':
    unittest.main()
