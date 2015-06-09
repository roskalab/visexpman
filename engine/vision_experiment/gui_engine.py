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
import shutil
import itertools

import hdf5io
from visexpman.engine.vision_experiment import experiment_data, cone_data,experiment
from visexpman.engine.hardware_interface import queued_socket
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


class ExperimentHandler(object):
    '''
    Takes care of all microscope, hardware related tasks
    Handles stimulus files, initiates recording and stimulation, 
    '''
    def open_stimulus_file(self, filename, classname):
        if not os.path.exists(filename):
            self.printc('{0} does not exists'.format(filename))
            return
        self.printc('Opening {0} in gedit, scroll to {1}'.format(filename, classname))
        import subprocess
        process = subprocess.Popen(['gedit', filename], shell=self.machine_config.OS != 'Linux')
        
    def start_experiment(self):
        cf=self.guidata.read('Selected experiment class')
        classname=cf.split(os.sep)[-1]
        filename=os.sep.join(cf.split(os.sep)[:-1])
        #Find out duration
        experiment_duration = experiment.get_experiment_duration(classname, self.machine_config, source = fileop.read_text_file(filename))
        #TODO: CONTINUE HERE: Calculate and check scan parameters
        #Pack scanner signals with guidata and add entry to issued commands
        


class Analysis(object):
    def __init__(self,machine_config):
        self.machine_config = machine_config
        
    def keep_rois(self, keep):
        if keep:
            if hasattr(self, 'rois'):
                self.reference_rois = [{'rectangle': r['rectangle'], 'area' :r.get('area',None)} for r in self.rois]
                for r in self.reference_rois:
                    if r['area'] is None:
                        del r['area']
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
        self._recalculate_background()
        self.rois = self.datafile.findvar('rois')
        if hasattr(self, 'reference_rois'):
            if self.rois is not None and len(self.rois)>0:
                if not self.ask4confirmation('File already contains Rois. These will be overwritten with Rois from previous file. Is that OK?'):
                    return
            #Calculate roi curves
            self.rois = copy.deepcopy(self.reference_rois)
            self._extract_roi_curves()
            self._normalize_roi_curves()
            self.current_roi_index = 0
            self.display_roi_rectangles()
            self.display_roi_curve()
            self._roi_area2image()
        elif self.rois is None:#No reference rois, noting is loaded from file
            self.rois=[]
            self._init_meanimge_w_rois()
        else:
            self.current_roi_index = 0
            self.display_roi_rectangles()
            self.display_roi_curve()
            self._roi_area2image()
        self.datafile.close()
        
    def _init_meanimge_w_rois(self):
        self.image_w_rois = numpy.zeros((self.meanimage.shape[0], self.meanimage.shape[1], 3))
        self.image_w_rois[:,:,1] = self.meanimage
        
    def _recalculate_background(self):
        background_threshold = self.guidata.read('Background threshold')*1e-2
        self.background = cone_data.calculate_background(self.raw_data,threshold=background_threshold)
        self.background_threshold=background_threshold
        
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
        
    def _roi_area2image(self, recalculate_contours = True, shiftx = 0, shifty = 0):
        areas = [self._clip_area(copy.deepcopy(r['area'])) for r in self.rois if r.has_key('area') and hasattr(r['area'], 'dtype')]
        if recalculate_contours:
            import multiprocessing
            p=multiprocessing.Pool(introspect.get_available_process_cores())
            contours=p.map(cone_data.area2edges, areas)
            self._init_meanimge_w_rois()
            for coo in contours:
                self.image_w_rois[coo[:,0],coo[:,1],2]=self.meanimage.max()*0.4
        else:
            self.image_w_rois[:,:,2] = numpy.roll(self.image_w_rois[:,:,2], shiftx, 0)
            self.image_w_rois[:,:,2] = numpy.roll(self.image_w_rois[:,:,2], shifty, 1)
        self.to_gui.put({'show_suggested_rois' :self.image_w_rois})
        
    def _filter_rois(self):
        self.suggested_rois = [r for r in self.suggested_rois if min(r[:,0].max()-r[:,0].min(), r[:,1].max()-r[:,1].min())>2]#Roi bounding rectangle's sides are greater than 2 pixel
        #remove overlapping rois
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
                r['raw'] = self.raw_data[:,:,area[:,0], area[:,1]].mean(axis=2).flatten()
            elif r.has_key('rectangle'):
                r['raw'] = self.raw_data[:,:,r['rectangle'][0]-0.5*r['rectangle'][2]: r['rectangle'][0]+0.5*r['rectangle'][2], r['rectangle'][1]-0.5*r['rectangle'][3]: r['rectangle'][1]+0.5*r['rectangle'][3]].mean(axis=2).mean(axis=2).flatten()
                
    def _clip_area(self,area):
        for i in range(2):#Make sure that indexing is correct even if area falls outside the image
            area[:,i] = numpy.where(area[:,i]>=self.raw_data.shape[i+2]-1,self.raw_data.shape[i+2]-1,area[:,i])
            area[:,i] = numpy.where(area[:,i]<0,0,area[:,i])
        return area
        
    def _normalize_roi_curves(self):
        if not hasattr(self, 'rois'):
            return
        baseline_length = self.guidata.read('Baseline lenght')
        for r in self.rois:
            r['normalized'] = signal.df_over_f(self.timg, r['raw']-self.background, self.tsync[0], baseline_length)
            r['baseline_length'] = baseline_length
            r['background'] = self.background
            r['background_threshold']=self.background_threshold
            if r.has_key('matches'):
                for fn in r['matches'].keys():
                    raw = r['matches'][fn]['raw']
                    timg = r['matches'][fn]['timg']
                    t0=r['matches'][fn]['tsync'][0]
                    r['matches'][fn]['normalized'] = signal.df_over_f(timg, raw, t0, baseline_length)
        
    def display_roi_rectangles(self):
        self.to_gui.put({'display_roi_rectangles' :[list(numpy.array(r['rectangle'])*self.image_scale) for r in self.rois]})
        
    def display_roi_curve(self):
        show_repetitions = self.guidata.show_repetitions.v if hasattr(self.guidata, 'show_repetitions') else False
        if hasattr(self, 'rois') and len(self.rois)>0:
            x_, y_, x, y, parameters = self._extract_repetition_data(self.rois[self.current_roi_index])
            if not show_repetitions or len(x) == 1:
                x=x[0]
                y=y[0]
            self.to_gui.put({'display_roi_curve': [x, y, self.current_roi_index, self.tsync]})
            self.to_gui.put({'display_trace_parameters':parameters[0]})
        
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
        if not self.unittest and not self.ask4confirmation('Removing this ROI. Are you sure?'):
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
        if not self.unittest and not self.ask4confirmation('Removing all rois. Are you sure?'):
            return
        self.rois = []
        del self.current_roi_index
        self.to_gui.put({'delete_all_rois': None})
        self._roi_area2image()
        self.printc('All rois removed')
        
    def add_manual_roi(self, rectangle):
        rectangle = numpy.array(rectangle)/self.image_scale
        rectangle[0] +=0.5*rectangle[2]
        rectangle[1] +=0.5*rectangle[3]
        raw = self.raw_data[:,:,rectangle[0]-0.5*rectangle[2]: rectangle[0]+0.5*rectangle[2], rectangle[1]-0.5*rectangle[3]: rectangle[1]+0.5*rectangle[3]].mean(axis=2).mean(axis=2).flatten()
        self.rois.append({'rectangle': rectangle.tolist(), 'raw': raw})
        self.current_roi_index = len(self.rois)-1
        self._normalize_roi_curves()
        self.to_gui.put({'fix_roi' : None})
        self.display_roi_curve()
        self.printc('Roi added, {0}'.format(rectangle))
        
    def _check_unsaved_rois(self, warning_only=False):
        if not hasattr(self,'filename'):
            return
        rois = hdf5io.read_item(self.filename, 'rois', filelocking=False)
        if (hasattr(self, 'rois') and rois is not None and len(rois)!=len(self.rois)) or (rois is None and hasattr(self, 'rois') and len(self.rois)>0):
            if warning_only:
                print 'Rois are not saved'
            elif self.ask4confirmation('Do you want to save unsaved rois?'):
                self.save_rois_and_export()
        
    def save_rois_and_export(self):
        if not hasattr(self, 'filename'):
            return
        file_info = os.stat(self.filename)
        self.datafile = experiment_data.CaImagingData(self.filename)
        self.datafile.load('rois')
        if hasattr(self.datafile, 'rois'):
            if not self.ask4confirmation('File already contains Rois. These will be overwritten. Is that OK?'):
                self.datafile.close()
                return
        self.datafile.rois = copy.deepcopy(self.rois)
        if hasattr(self, 'reference_roi_filename'):
            self.datafile.repetition_link = [fileop.parse_recording_filename(self.reference_roi_filename)['id']]
            self.datafile.save(['repetition_link'], overwrite=True)
        self.datafile.save(['rois'], overwrite=True)
        self.datafile.convert(self.engine.guidata.read('Save File Format'))
        fileop.set_file_dates(self.filename, file_info)
        self.printc('ROIs are saved to {0}'.format(self.filename))
        self.printc('Data exported to  {0}'.format(outfile))
        
    def roi_shift(self, h, v):
        if not hasattr(self, 'rois'):
            return
        for r in self.rois:
            r['rectangle'][0] += h
            r['rectangle'][1] += v
            if r.has_key('area') and hasattr(r['area'], 'dtype'):
                r['area'] += numpy.array([h,v])
        self._extract_roi_curves()
        self._normalize_roi_curves()
        self._roi_area2image(recalculate_contours = False, shiftx = h, shifty = v)
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
        
    def display_trace_parameter_distribution(self):
        if not hasattr(self, 'rois'):
            return
        include_all_files = self.guidata.include_all_files.v if hasattr(self.guidata, 'include_all_files') else False
        if include_all_files:
            self.printc('Creating statistics for all files is not supported')
            return
        self.printc('Creating statistics from traces, please wait...')
        allparams = []
        for r in self.rois:
            x_, y_, x, y, parameters = self._extract_repetition_data(r)
            allparams.extend(parameters)
        self.distributions = {}
        for par1,par2 in itertools.combinations(allparams[0].keys(),2):
            self.distributions[par1+'@'+par2] = [[p[par1], p[par2]]for p in allparams]
            self.distributions[par1+'@'+par2] = numpy.array(self.distributions[par1+'@'+par2]).T
        self.to_gui.put({'display_trace_parameter_distributions':self.distributions})
        
    def _extract_repetition_data(self,roi):
        '''
        Extracts the following from a roi:
        1) parameters for each repetition
        2) ca signal and time series for each repetition
        3) Mean of ca signals
        '''
        mean_of_repetitions = self.guidata.mean_of_repetitions.v if hasattr(self.guidata, 'mean_of_repetitions') else False
        baseline_length = self.guidata.read('Baseline lenght')
        x=[self.timg]
        y=[roi['normalized']]
        parameters = []
        if roi.has_key('matches'):
            for fn in roi['matches'].keys():
                #collect matches, shift matched curve's timing such that sync events fall into the same time
                tdiff = self.tsync[0]-self.rois[self.current_roi_index]['matches'][fn]['tsync'][0]
                x.append(self.rois[self.current_roi_index]['matches'][fn]['timg']+tdiff)
                y.append(self.rois[self.current_roi_index]['matches'][fn]['normalized'])
        for i in range(len(x)):
            baseline_mean, amplitude, rise, fall, drop, fitted  = cone_data.calculate_trace_parameters(y[i], self.tsync, x[i], baseline_length)
            parameters.append({'amplitude':amplitude, 'rise': rise, 'fall': fall, 'drop':drop})
        x_,y_ = signal.average_of_traces(x,y)
        parameters_ = {}
        if mean_of_repetitions:
            for pn in parameters[0].keys():
                parameters_[pn] = numpy.array([par[pn] for par in parameters]).mean()
            parameters = [parameters_]
        return x_, y_, x, y, parameters
        
    def close_analysis(self):
        self._check_unsaved_rois(warning_only=True)
    
class GUIEngine(threading.Thread, queued_socket.QueuedSocketHelpers, Analysis, ExperimentHandler):
    '''
    GUI engine: receives commands via queue interface from gui and performs the following actions:
     - stores data internally
     - initiates actions on gui or in engine
     
     Command format:
     {'command_name': [parameters]}
    '''

    def __init__(self, machine_config, log, socket_queues, unittest=False):
        self.socket_queues=socket_queues
        self.unittest=unittest
        self.log=log
        self.machine_config = machine_config
        #queued_socket.QueuedSocketHelpers.__init__(self, self.socket_queues)
        threading.Thread.__init__(self)
        self.from_gui = Queue.Queue()
        self.to_gui = Queue.Queue()
        self.context_filename = fileop.get_context_filename(self.machine_config)
        self.load_context()
        self.widget_status = {}
        self.last_periodic = time.time()
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
                    'aggregated_rois', 'context_filename', 'guidata']
        dump_data = {}
        for v in variables:
            if hasattr(self, v):
                dump_data[v] = getattr(self,v)
        dump_data['machine_config'] = self.machine_config.serialize()
        if filename is None:
            import tempfile
            filename = os.path.join(tempfile.gettempdir(), 'dump_{0}.hdf5'.format(utils.timestamp2ymdhms(time.time()).replace(':','-').replace(' ', '-')))
        hdf5io.save_item(filename, 'dump_data', utils.object2array(dump_data), filelocking=False)
        self.printc('GUI engine dumped to {0}'.format(filename))
            
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
        
    def update_widget_status(self, status):
        '''
        Update widget status
        
        Engine shall know whether a pop up window is open or not
        '''
        for k,v in status.items():
            self.widget_status[k]=v
            
    def check_parameter_changes(self, parameter_name):
        '''
        parameter_name: name of parameter changed
        Depending on which parameter changed certain things has to be recalculated
        '''
        tpp_opened = utils.safe_has_key(self.widget_status, 'tpp') and self.widget_status['tpp']
        if 'Background threshold' in parameter_name:
            self._normalize_roi_curves()
            self.display_roi_curve()
        elif 'Baseline lenght' in parameter_name:
            self._normalize_roi_curves()
            self.display_roi_curve()
            if tpp_opened:
                self.display_trace_parameter_distribution()
        elif 'Include all files' in parameter_name:
            if tpp_opened:
                self.display_trace_parameter_distribution()
        elif 'Mean of repetitions' in parameter_name:
            self.display_roi_curve()
            if tpp_opened:
                self.display_trace_parameter_distribution()
    
    def run(self):
        while True:
            try:
                self.last_run = time.time()#helps determining whether the engine still runs
                if not self.from_gui.empty():
                    msg = self.from_gui.get()
                    if msg == 'terminate':
                        break
                else:
                    continue
                #parse message
                if msg.has_key('data'):#expected format: {'data': value, 'path': gui path, 'name': name}
                    self.guidata.add(msg['name'], msg['data'], msg['path'])#Storing gui data
                    self.check_parameter_changes(msg['name'])
                elif msg.has_key('read'):#gui might need to read guidata database
                    value = self.guidata.read(**msg)
                    getattr(self, 'to_gui').put(value)
                elif msg.has_key('function'):#Functions are simply forwarded
                    #Format: {'function: function name, 'args': [], 'kwargs': {}}
#                    with introspect.Timer(str(msg)):
                    getattr(self, msg['function'])(*msg['args'])
                    if hasattr(self, 'log') and hasattr(self.log, 'info'):
                        self.log.info(msg, 'engine')
                self.periodic()
            except:
                import traceback
                self.printc(traceback.format_exc())
                self.dump()
                self.close_open_files()
            time.sleep(20e-3)
        self.close()
        
    def periodic(self):
        return
        if self.last_run-self.last_periodic>2.0:
            self.last_periodic=time.time()
            self.update_network_connection_status()
            
        
    def update_network_connection_status(self):
        #Check for network connection status
        self.connected_nodes = ''
        n_connected = 0
        n_connections = len(self.socket_queues.keys())
        for remote_node_name, socket in self.socket_queues.items():
            if self.ping(timeout=1.0, connection=remote_node_name):
                self.connected_nodes += remote_node_name + ' '
                n_connected += 1
        self.printc('Network connections: {2} {0}/{1}'.format(n_connected, n_connections, self.connected_nodes))
        
    def close_open_files(self):
        if hasattr(self, 'datafile') and self.datafile.h5f.isopen==1:
            self.datafile.close()
            self.printc('{0} file is closed'.format(self.datafile.filename))
            
        
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
        import visexpman.engine
        self.appcontext = visexpman.engine.application_init(user = 'test', config = 'GUITestConfig', user_interface_name = 'main_ui', log_sources = ['engine'])
        self.appcontext['logger'].start()
        self.engine = GUIEngine(self.machine_config, self.appcontext['logger'], self.appcontext['socket_queues'], unittest=True)
        
        self.engine.save_context()
        self.from_gui, self.to_gui = self.engine.get_queues()
        self.engine.start()
        utils.empty_queue(self.to_gui)
        
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
        
    def test_04_online_analysis_procedure(self):
        from visexpman.users.test import unittest_aggregator
        import tempfile
        self._init_guidata()
        ref_folder = os.path.join(fileop.select_folder_exists(unittest_aggregator.TEST_test_data_folder), 'cone_gui')
        self.working_folder = os.path.join(tempfile.gettempdir(), 'guienginetest')
        if os.path.exists(self.working_folder):
            shutil.rmtree(self.working_folder)
        self.engine.machine_config.EXPERIMENT_DATA_PATH = self.working_folder
        shutil.copytree(ref_folder, self.working_folder)
        files = fileop.listdir_fullpath(self.working_folder)
        protocol_files = [f for f in files if fileop.file_extension(f) == 'txt']
        protocols = dict(map(self._parse_protocol_files, protocol_files))
        for n in protocols.keys():
            protocol = protocols[n]
            [self.from_gui.put(p) for p in protocol]
            resp = []
            tlast = time.time()
            while True:
                if not self.to_gui.empty():
                    resp.append(self.to_gui.get())
                    tlast = time.time()
                if time.time()-tlast>60:#assuming that the execution of any function does not take longer than 30 sec
                    break
            printc_messages = [r['printc'] for r in resp if r.has_key('printc')]
            print n
            for p in printc_messages:
                print p
            self.assertEqual([p for p in printc_messages if 'error' in p], [])#No error in printc messages
            files = [p.split(' ')[-1] for p in printc_messages if 'ROIs are saved to ' in p]
            #Check if mat files are available
            self.assertTrue(all([os.path.exists(f.replace('.hdf5', '.mat')) for f in files]))
            replink_occurences=0
            for file in files:
                h=hdf5io.Hdf5io(file,filelocking=False)
                rois = h.findvar('rois')
                if 'data_C20_unknownstim_1423227193_0.hdf5' in file and n == 'manual_rois.txt':#Test for all rois removed
                    self.assertEqual(len(rois), 0)
                else:
                    self.assertGreater(len(rois), 0)
                    #Area key is not available when manual rois are used
                    self.assertEqual(len([r for r in rois if 'area' in r.keys()]), 0 if n == 'manual_rois.txt' else len(rois))
                repetition_link = h.findvar('repetition_link')
                replink_occurences+=len(repetition_link)
                h.close()
            self.assertEqual(replink_occurences,len(files))
            if n == 'manual_rois.txt':
                self.assertTrue(hasattr(self.engine, 'distributions'))
                self.assertEqual(len(list(set(numpy.array([k.split('@') for k in self.engine.distributions.keys()]).flatten().tolist()))), 4)#Distribution of 4 parameters are created
                #Each distribution contains two column data
                numpy.testing.assert_equal(numpy.array([d.shape[0] for d in self.engine.distributions.values()]),2)
            elif n == 'automated_roi_detection.txt':
                self.assertTrue('All rois removed' in printc_messages)
                self.assertEqual(self.engine.rois, [])
            #Check roi matches, all aggregated_rois have one match. It is important that finding repetitions shall take place at the end of the protocol
            try:
                self.assertEqual(abs(numpy.array([len(r['matches']) for r in self.engine.aggregated_rois])-1).sum(),0)
            except:
                import traceback
                print traceback.format_exc()
                import pdb
                pdb.set_trace()
        
    def _parse_protocol_files(self,filename):
        protocol = [line.split('\t')[1] for line in fileop.read_text_file(filename).split('\n') if 'INFO/engine' in line]
        protocol_cmds = []
        for i in range(len(protocol)):
            if '/mnt/rzws/experiment_data/test/' in protocol[i]:
                path=protocol[i].split('[\'')[1].split('\']')[0]
                new_path = path.replace('/mnt/rzws/experiment_data/test',self.working_folder).replace('/',os.sep)
                protocol[i] = protocol[i].replace(path, new_path)
            exec('cmd='+protocol[i])
            protocol_cmds.append(cmd)
        return os.path.split(filename)[1], protocol_cmds
        
    def _init_guidata(self):
        self.engine.guidata.from_dict([{'path': 'params/Analysis/Background threshold', 'name': 'Background Threshold', 'value': 10}, 
            {'path': 'params/Analysis/Baseline lenght', 'name': 'Baseline Lenght', 'value': 1.0},
            {'path': 'params/Analysis/Trace statistics/Include all files', 'name': 'Include All Files', 'value': False}, 
            {'path': 'params/Analysis/Trace statistics/Mean of repetitions', 'name': 'Mean of repetitions', 'value': True}, 
            {'path': 'analysis_helper/show_repetitions/input', 'name': 'Show Repetitions', 'value': True}, 
            {'path': 'params/Analysis/Cell detection/Maximum cell radius', 'name': 'Maximum Cell Radius', 'value': 3.0},
            {'path': 'params/Analysis/Cell detection/Minimum cell radius', 'name': 'Minimum cell radius', 'value': 1.0},
            {'path': 'params/Analysis/Cell detection/Sigma', 'name': 'Sigma', 'value': 1.0}, 
            {'path': 'params/Analysis/Cell detection/Threshold factor', 'name': 'Threshold Factor', 'value': 1.0}])
        
    def tearDown(self):
        self.from_gui.put('terminate')
        self.engine.join()
        import visexpman.engine
        visexpman.engine.stop_application(self.appcontext)
        self.assertTrue(os.path.exists(self.cf))
        if hasattr(self, 'working_folder') and os.path.exists(self.working_folder):
            shutil.rmtree(self.working_folder)
        


if __name__=='__main__':
    unittest.main()
