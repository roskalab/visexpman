import time
import scipy.io
import copy
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
from visexpman.engine.generic import fileop, signal,stringop,utils,introspect

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
        
    def keep_rois(self, keep):
        if keep:
            if hasattr(self, 'rois'):
                self.reference_rois = [{'rectangle': r['rectangle'], 'area' :r.get('area',None)} for r in self.rois]
                self.reference_roi_filename = copy.deepcopy(self.filename)
        else:
            if hasattr(self, 'reference_rois'):
                del self.reference_rois

    def open_datafile(self,filename):
        self._check_unsaved_rois()
        if fileop.parse_recording_filename(filename)['type'] != 'data':
            self.notify('Warning', 'This file cannot be displayed')
            return
        self.filename = filename
        self.printc('Opening {0}'.format(filename))
        self.datafile = experiment_data.CaImagingData(filename)
        self.tsync, self.timg, self.meanimage, self.image_scale, self.raw_data = self.datafile.prepare4analysis()
        self.to_gui.put({'send_image_data' :[self.meanimage, self.image_scale, self.tsync, self.timg]})
        background_threshold = self.guidata.read('Background threshold')*1e-2
        self.background = cone_data.calculate_background(self.raw_data,threshold=background_threshold)
        self.rois = self.datafile.findvar('rois')
        if hasattr(self, 'reference_rois'):
            if self.rois is not None and len(self.rois)>0:
                if not self.ask4confirmation('File already contains Rois. These will be overwritten with Rois from previous file. Is thak OK?'):
                    return
            #Calculate roi curves
            self.rois = copy.deepcopy(self.reference_rois)
            self._extract_roi_curves()
            self._normalize_roi_curves()
            self.current_roi_index = 0
            self.display_roi_rectangles()
            self.display_roi_curve()
        elif self.rois is None:#No reference rois, noting is loaded from file
            self.rois=[]
        else:
            self.current_roi_index = 0
            self.display_roi_rectangles()
            self.display_roi_curve()
            self._roi_area2image()
        self.datafile.close()
        
        
    def find_cells(self):
        if not hasattr(self, 'meanimage') or not hasattr(self, 'image_scale'):
            self.notify('Warning', 'Open datafile first')
            return
        if len(self.rois)>0:
            if not self.ask4confirmation('Automatic cell detection will remove current rois. Are you sure?'):
                return
        self.rois = []
        self.printc('Searching for cells, please wait...')
        min_ = int(self.guidata.read('Minimum cell radius')/self.image_scale)
        max_ = int(self.guidata.read('Maximum cell radius')/self.image_scale)
        sigma = self.guidata.read('Sigma')/self.image_scale
        threshold_factor = self.guidata.read('Threshold factor')
        self.suggested_rois = cone_data.find_rois(numpy.cast['uint16'](signal.scale(self.meanimage, 0,2**16-1)), min_,max_,sigma,threshold_factor)
        self._filter_rois()
        #Calculate roi bounding box
        self.roi_bounding_boxes = [[rc[:,0].min(), rc[:,0].max(), rc[:,1].min(), rc[:,1].max()] for rc in self.suggested_rois]
        self.roi_rectangles = [[sum(r[:2])*0.5, sum(r[2:])*0.5, (r[1]-r[0]), (r[3]-r[2])] for r in self.roi_bounding_boxes]
        self.rois = [{'rectangle': self.roi_rectangles[i], 'area': self.suggested_rois[i]} for i in range(len(self.roi_rectangles))]
        self._extract_roi_curves()
        self._normalize_roi_curves()
        self._roi_area2image()
        self.current_roi_index = 0
        self.display_roi_rectangles()
        self.display_roi_curve()
        
    def _roi_area2image(self):
        areas = [self._clip_area(copy.deepcopy(r['area'])) for r in self.rois if r.has_key('area') and hasattr(r['area'], 'dtype')]
        import multiprocessing
        p=multiprocessing.Pool(introspect.get_available_process_cores())
        contours=p.map(cone_data.area2edges, areas)
        self.image_w_rois = numpy.zeros((self.meanimage.shape[0], self.meanimage.shape[1], 3))
        self.image_w_rois[:,:,1] = self.meanimage
        for coo in contours:
            self.image_w_rois[coo[:,0],coo[:,1],2]=self.meanimage.max()*0.4
        self.to_gui.put({'show_suggested_rois' :self.image_w_rois})
        
    def _filter_rois(self):
        self.suggested_rois = [r for r in self.suggested_rois if min(r[:,0].max()-r[:,0].min(), r[:,1].max()-r[:,1].min())>2]#Roi bounding rectangle's sides are greater than 2 pixel
        #remove overlapping rois
        import itertools
        removeable_rois = []
        for roi1, roi2 in itertools.combinations(self.suggested_rois,2):
            mask1=numpy.zeros(self.meanimage.shape)
            mask1[roi1[:,0], roi1[:,1]]=1
            mask2=numpy.zeros(self.meanimage.shape)
            mask2[roi2[:,0], roi2[:,1]]=1
            mask=mask1+mask2
            overlapping_pixels = numpy.where(mask==2)[0].shape[0]
            maximal_acceptable_overlap = min(roi1.shape[0], roi2.shape[0])*0.05#5% overlap is allowed
            if overlapping_pixels>maximal_acceptable_overlap:
                removeable_rois.extend([roi1, roi2])
        self.suggested_rois = [sr for sr in self.suggested_rois if len([rr for rr in removeable_rois if numpy.array_equal(rr, sr)])==0]
        
    def _extract_roi_curves(self):
        for r in self.rois:
            if r.has_key('area') and hasattr(r['area'], 'dtype'):
                area = self._clip_area(copy.deepcopy(r['area']))
                r['raw'] = self.raw_data[:,:,area[:,0], area[:,1]].mean(axis=2).flatten()-self.background
            elif r.has_key('rectangle'):
                r['raw'] = self.raw_data[:,:,r['rectangle'][0]-0.5*r['rectangle'][2]: r['rectangle'][0]+0.5*r['rectangle'][2], r['rectangle'][1]-0.5*r['rectangle'][3]: r['rectangle'][1]+0.5*r['rectangle'][3]].mean(axis=2).mean(axis=2).flatten()
                r['raw'] -= self.background
                
    def _clip_area(self,area):
        for i in range(2):#Make sure that indexing is correct even if area falls outside the image
            area[:,i] = numpy.where(area[:,i]>=self.raw_data.shape[i+2]-1,self.raw_data.shape[i+2]-1,area[:,i])
            area[:,i] = numpy.where(area[:,i]<0,0,area[:,i])
        return area
        
    def _normalize_roi_curves(self):
        baseline_length = self.guidata.read('Baseline lenght')
        for r in self.rois:
            r['normalized'] = signal.df_over_f(self.timg, r['raw'], self.tsync[0], baseline_length)
            if r.has_key('matches'):
                for fn in r['matches'].keys():
                    raw = r['matches'][fn]['raw']
                    timg = r['matches'][fn]['timg']
                    t0=r['matches'][fn]['tsync'][0]
                    r['matches'][fn]['normalized'] = signal.df_over_f(timg, raw, t0, baseline_length)
        
    def display_roi_rectangles(self):
        self.to_gui.put({'display_roi_rectangles' :[list(numpy.array(r['rectangle'])*self.image_scale) for r in self.rois]})
        
    def display_roi_curve(self, show_repetitions=True):
        if len(self.rois)>0:
            if self.rois[self.current_roi_index].has_key('matches') and show_repetitions:
                x=[]
                y=[]
                for fn in self.rois[self.current_roi_index]['matches'].keys():
                    #collect matches, shift matched curve's timing such that sync events fall into the same time
                    tdiff = self.tsync[0]-self.rois[self.current_roi_index]['matches'][fn]['tsync'][0]
                    x.append(self.rois[self.current_roi_index]['matches'][fn]['timg']+tdiff)
                    y.append(self.rois[self.current_roi_index]['matches'][fn]['normalized'])
                x.append(self.timg)
                y.append(self.rois[self.current_roi_index]['normalized'])
                self.to_gui.put({'display_roi_curve': [x, y, self.current_roi_index, self.tsync]})
            else:
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
        self._roi_area2image()
        
    def delete_all_rois(self):
        if not hasattr(self, 'current_roi_index'):
            return
        if not self.ask4confirmation('Removing all rois. Are you sure?'):
            return
        self.rois = []
        del self.current_roi_index
        self.to_gui.put({'delete_all_rois': None})
        self._roi_area2image()
        
    def add_manual_roi(self, rectangle):
        rectangle = numpy.array(rectangle)/self.image_scale
        rectangle[0] +=0.5*rectangle[2]
        rectangle[1] +=0.5*rectangle[3]
        raw = self.raw_data[:,:,rectangle[0]-0.5*rectangle[2]: rectangle[0]+0.5*rectangle[2], rectangle[1]-0.5*rectangle[3]: rectangle[1]+0.5*rectangle[3]].mean(axis=2).mean(axis=2).flatten()
        raw -= self.background
        self.rois.append({'rectangle': rectangle.tolist(), 'raw': raw})
        self.current_roi_index = len(self.rois)-1
        self._normalize_roi_curves()
        self.to_gui.put({'fix_roi' : None})
        self.display_roi_curve()
        self.printc('Roi added, {0}'.format(rectangle))
        
    def _check_unsaved_rois(self):
        if not hasattr(self,'filename'):
            return
        rois = hdf5io.read_item(self.filename, 'rois', filelocking=False)
        if (rois is not None and hasattr(self, 'rois') and len(rois)!=len(self.rois)) or (rois is None and len(self.rois)>0):
            if self.ask4confirmation('Do you want to save unsaved rois?'):
                self.save_rois_and_export()
        
    def save_rois_and_export(self):
        file_info = os.stat(self.filename)
        self.datafile = experiment_data.CaImagingData(self.filename)
        self.datafile.rois = copy.deepcopy(self.rois)
        if hasattr(self, 'reference_roi_filename'):
            self.datafile.repetition_link = [fileop.parse_recording_filename(self.reference_roi_filename)['id']]
            self.datafile.save(['repetition_link'], overwrite=True)
        self.datafile.save(['rois'], overwrite=True)
        #List main nodes of hdf5 file
        items = [r._v_name for r in self.datafile.h5f.list_nodes('/')]
        #Copy data to dictionary
        data={}
        for item in items:
            self.datafile.load(item)
            data[item]=getattr(self.datafile,item)
        outfile=self.filename.replace('.hdf5', '.mat')
        #Write to mat file
        scipy.io.savemat(outfile, data, oned_as = 'row', long_field_names=True)
        fileop.set_file_dates(outfile, file_info)
        self.datafile.close()
        fileop.set_file_dates(self.filename, file_info)
        self.printc('ROIs are saved to {0}'.format(self.filename))
        
    def roi_shift(self, h, v):
        for r in self.rois:
            r['rectangle'][0] += h
            r['rectangle'][1] += v
            if r.has_key('area') and hasattr(r['area'], 'dtype'):
                r['area'] += numpy.array([h,v])
        self._extract_roi_curves()
        self._normalize_roi_curves()
        self._roi_area2image()
        self.display_roi_rectangles()
        self.display_roi_curve()
        
    def find_repetitions(self):
        if not hasattr(self,'filename'):
            return
        self.printc('Searching for repetitions, please wait...')
        aggregated_rois = cone_data.find_repetitions(self.filename, self.machine_config.EXPERIMENT_DATA_PATH)
        self.aggregated_rois = aggregated_rois
        files = []
        for i in range(len(self.rois)):
            if aggregated_rois[i].has_key('matches'):
                self.rois[i]['matches'] = aggregated_rois[i]['matches']
                files.extend(self.rois[i]['matches'].keys())
        if len(files)>0:
            self.printc('Repetitions found in {0} files: {1}'.format(len(list(set(files))), ', ' .join(list(set(files)))))
        else:
            self.printc('No repetitions found')
        self._normalize_roi_curves()
        self.display_roi_curve()
        
    def close_analysis(self):
        self._check_unsaved_rois()
    
class GUIEngine(threading.Thread, Analysis):
    '''
    GUI engine: receives commands via queue interface from gui and performs the following actions:
     - stores data internally
     - initiates actions on gui or in engine
     
     Command format:
     {'command_name': [parameters]}
    '''

    def __init__(self, machine_config, log):
        self.log=log
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
            
    def dump(self, filename=None):
        #TODO: include logfile and context file content
        variables = ['rois', 'reference_rois', 'reference_roi_filename', 'filename', 'tsync', 'timg', 'meanimage', 'image_scale'
                    'raw_data', 'background', 'current_roi_index', 'suggested_rois', 'roi_bounding_boxes', 'roi_rectangles', 'image_w_rois',
                    'aggregated_rois', 'context_filename']
        dump_data = {}
        for v in variables:
            if hasattr(self, v):
                dump_data[v] = getattr(self,v)
        dump_data['machine_config'] = self.machine_config.serialize()
        if filename is None:
            import tempfile
            filename = os.path.join(tempfile.gettempdir(), 'dump_{0}.hdf5'.format(utils.timestamp2ymdhms(time.time()).replace(':','-').replace(' ', '-')))
        hdf5io.save_item(filename, 'dump_data', utils.object2array(dump_data), filelocking=False)
        self.printc('All variables dumped to {0}'.format(filename))
            
    def save_context(self):
        hdf5io.save_item(self.context_filename, 'guidata', utils.object2array(self.guidata.to_dict()), filelocking=False, overwrite=True)
        
    def get_queues(self):
        return self.from_gui, self.to_gui
        
    def test(self):
        self.to_gui.put({'function':'test', 'args':[]})
        
    def printc(self,txt):
        self.to_gui.put({'printc':str(txt)})
        
    def ask4confirmation(self,message):
        self.to_gui.put({'ask4confirmation':message})
        while True:
            if not self.from_gui.empty():
                break
            time.sleep(0.05)
        return self.from_gui.get()
        
    def notify(self,title,message):
        self.to_gui.put({'notify':{'title': title, 'msg':message}})
    
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
                    self.log.info(msg, 'engine')
            except:
                import traceback
                self.printc(traceback.format_exc())
            time.sleep(20e-3)
        self.close()
        
    def close(self):
        self.close_analysis()
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
