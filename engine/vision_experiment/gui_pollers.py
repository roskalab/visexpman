#OBSOLETE
import sys
import shutil
import time
import re
import Queue
import traceback
import numpy
import os
import os.path
import webbrowser
import copy
import tempfile
import scipy.io
import warnings
try:
    import Image
except ImportError:
    from PIL import Image
    
if os.name == 'nt':
    import winsound
else:
    winsound = None
    
import PyQt4.Qt as Qt
import PyQt4.QtCore as QtCore

from visexpman.engine.vision_experiment import experiment_data,gui
from visexpman.engine.hardware_interface import mes_interface,network_interface,stage_control,scanner_control,flowmeter,daq_instrument
from visexpman.engine import generic
from visexpman.engine.generic import utils,signal,fileop,stringop,introspect 
from visexpman.engine.generic import gui as gui_generic
if 0:
    from visexpA.engine.datadisplay import imaged
    from visexpA.engine.datahandlers import matlabfile
import hdf5io
from visexpman.engine.hardware_interface import queued_socket
try:
    import visexpA.engine.component_guesser as cg
except:
    pass

ANESTHESIA_HISTORY_UPDATE_PERIOD = 60.0
class Poller(QtCore.QThread, queued_socket.QueuedSocketHelpers):
    '''
    Generic poller thread that receives commands via queues and executes them. Additionally can access gui
    '''
    #Initializing, loader methods
    def __init__(self, parent):
        if hasattr(parent, 'socket_queues'):
            queued_socket.QueuedSocketHelpers.__init__(self, parent.socket_queues)
        self.signal_id_queue = Queue.Queue() #signal parameter is passed to handler
        self.parent = parent
        self.config = self.parent.config
        if hasattr(self.config,'testmode'):
            self.testmode=self.config.testmode
        else:
            self.testmode = None
        QtCore.QThread.__init__(self)
        self.abort = False
        self.nperiods = 0
        self.connect_signals()

    def connect_signals(self):
        pass
        
    def init_run(self):
        pass

    def printc(self, text):
        self.emit(QtCore.SIGNAL('printc'), text)

    def run(self):
        self.init_run()
        last_time = time.time()
        startup_time = last_time
        while not self.abort:
            now = time.time()
            elapsed_time = now - last_time
            if elapsed_time > self.config.GUI['GUI_REFRESH_PERIOD']:
                last_time = now
                self.periodic()
            self.run_in_all_iterations()
            self.handle_commands()
            self.handle_events()
            time.sleep(1e-2)
        self.close()
        self.printc('poller stopped')

    def run_in_all_iterations(self):
        pass

    def close(self):
        pass

    def periodic(self):
        pass

    def handle_commands(self):
        '''
        Handle commands coming via queues (mainly from network thread)
        '''
        pass

    def handle_events(self):
        '''
        Handle mapped signals that are connected to gui widgets
        '''
        if not self.signal_id_queue.empty():
            function_call = self.signal_id_queue.get()
            if '.' in function_call:
                function_call = function_call.split('.')
                if len(function_call) != 2:
                    raise RuntimerError('Expected format: <attribute name>.<method name>')
                try:
                    getattr(getattr(self, function_call[0]),function_call[1])()
                except:
                    self.printc(traceback.format_exc())
                    self.printc(function_call)
            elif hasattr(self, function_call):
                try:
                    getattr(self, function_call)()
                except:
                    self.printc(traceback.format_exc())
            else:
                self.printc('{0} method does not exists'.format(function_call))

    def pass_signal(self, signal_id):
        self.signal_id_queue.put(str(signal_id))
        
    ####### Popup dialog boxes #####
    
    def ask4confirmation(self, action2confirm):
        if introspect.is_test_running():
            return True
        else:
            self.emit(QtCore.SIGNAL('ask4confirmation'), action2confirm)
            while self.gui_thread_queue.empty() :
                time.sleep(0.1) 
            return self.gui_thread_queue.get()
        
    def ask4filename(self, title, directory, filter):
        utils.empty_queue(self.gui_thread_queue)
        self.emit(QtCore.SIGNAL('ask4filename'),title, directory, filter)
        while self.gui_thread_queue.empty() :
            time.sleep(0.1)
        return self.gui_thread_queue.get()
    
    def notify_user(self, title, message):
        if introspect.is_test_running():
            self.printc(message)
        else:
            self.emit(QtCore.SIGNAL('notify_user'), title, message)
            while self.gui_thread_queue.empty() :
                time.sleep(0.1) 
            return self.gui_thread_queue.get()

parameter_extract = re.compile('EOC(.+)EOP')
command_extract = re.compile('SOC(.+)EOC')

################### Poller #######################
class CorticalGUIPoller(Poller):
    #Initializing, loader methods
    def __init__(self, parent):
        self.gui_thread_queue = Queue.Queue()
        Poller.__init__(self, parent)
        self.xz_scan_acquired = False
        self.stage_origin_set = False
        self.cell_status_changed_in_cache = False
        self.queues = {}
        self.queues['mouse_file_handler'] = Queue.Queue()
        self.init_network()
        self.mes_interface = mes_interface.MesInterface(self.config, self.queues, self.connections)
        self.init_variables()
        self.load_context()
        self.initialize_mouse_file()

    def connect_signals(self):
        Poller.connect_signals(self)
        self.parent.connect(self, QtCore.SIGNAL('mouse_file_list_changed'),  self.parent.mouse_file_list_changed)
        self.parent.connect(self, QtCore.SIGNAL('update_scan_regions'),  self.parent.update_scan_regions)
        self.parent.connect(self, QtCore.SIGNAL('show_image'),  self.parent.show_image)
        self.parent.connect(self, QtCore.SIGNAL('update_widgets_when_mouse_file_changed'),  self.parent.update_widgets_when_mouse_file_changed)
        self.parent.connect(self, QtCore.SIGNAL('ask4confirmation'),  self.parent.ask4confirmation)
        self.parent.connect(self, QtCore.SIGNAL('select_cell_changed'),  self.parent.select_cell_changed)
        self.parent.connect(self, QtCore.SIGNAL('update_anesthesia_history'),  self.parent.update_anesthesia_history)
        self.parent.connect(self, QtCore.SIGNAL('update_analysis_status'),  self.parent.update_analysis_status)

    def init_run(self):
        self.connect_signals_to_widgets()

    def connect_signals_to_widgets(self):
        self.parent.connect(self, QtCore.SIGNAL('clear_image_display'), self.parent.images_widget.clear_image_display)

    def init_network(self):
        self.command_relay_server = network_interface.CommandRelayServer(self.config)
        self.connections = {}
        self.queues['mes'] = {}
        self.queues['mes']['out'] = Queue.Queue()
        self.queues['mes']['in'] = Queue.Queue()
        self.connections['mes'] = network_interface.start_client(self.config, 'GUI', 'GUI_MES', self.queues['mes']['in'], self.queues['mes']['out'])
        self.queues['stim'] = {}
        self.queues['stim']['out'] = Queue.Queue()
        self.queues['stim']['in'] = Queue.Queue()
        self.connections['stim'] = network_interface.start_client(self.config, 'GUI', 'GUI_STIM', self.queues['stim']['in'], self.queues['stim']['out'])
        self.queues['analysis'] = {}
        self.queues['analysis']['out'] = Queue.Queue()
        self.queues['analysis']['in'] = Queue.Queue()
        self.connections['analysis'] = network_interface.start_client(self.config, 'GUI', 'GUI_ANALYSIS', self.queues['analysis']['in'], self.queues['analysis']['out'])

    def init_jobhandler(self):
        if not self.jobhandler_reset_issued:
            status = self.command_relay_server.get_connection_status()
            if status['GUI_ANALYSIS/GUI'] and status['GUI_ANALYSIS/ANALYSIS']:
                self.reset_jobhandler()
                self.jobhandler_reset_issued = True

    def reset_jobhandler(self):
        self.queues['analysis']['out'].put('SOCreset_jobhandlerEOCEOP')

    def show_image(self, image, channel, scale, line = [], origin = None):
        self.emit(QtCore.SIGNAL('show_image'), image, channel, scale, line, origin)

    def update_scan_regions(self):
        self.emit(QtCore.SIGNAL('update_scan_regions'))
        
    def update_anesthesia_history(self):
        self.emit(QtCore.SIGNAL('update_anesthesia_history'))
        
    def update_analysis_status(self):
        self.emit(QtCore.SIGNAL('update_analysis_status'))

    def run_in_all_iterations(self):
        self.update_network_connection_status()

    def close(self):
        #Stop applications if system test is running
        if os.path.split(sys.argv[0])[1] == 'system_test_runner.py':
            self.queues['mes']['out'].put('SOCexitEOCEOP')
            self.queues['stim']['out'].put('SOCexitEOCEOP')
            self.queues['analysis']['out'].put('SOCexitEOCEOP')
            time.sleep(5.0)
        self.printc('Wait till server is closed')
        self.queues['mes']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.queues['stim']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.queues['analysis']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.command_relay_server.shutdown_servers()
        self.save_cells()
        h = hdf5io.Hdf5io(self.config.CONTEXT_FILE, filelocking=self.config.ENABLE_HDF5_FILELOCKING)
        self.save_widget_context(h)
        h.close()
        #delete files:
        for file_path in self.files_to_delete:
            if os.path.exists(file_path):
                os.remove(file_path)
        #Delete MES tmp files
        try:
            import tempfile
            for f in os.listdir(tempfile.gettempdir()):
                fullpath = os.path.join(tempfile.gettempdir(), f)
                if 'mat' in fullpath:
                    os.remove(fullpath)
        except:
            print traceback.format_exc()
        for connection in self.connections.values():
            connection.wait()
        print 'Poller stopped'

    def periodic(self):
        are_new_file, self.mouse_files = update_mouse_files_list(self.config, self.mouse_files)
        if are_new_file:
            self.emit(QtCore.SIGNAL('mouse_file_list_changed'))
        self.init_jobhandler()
        now = time.time()
        if now - self.prev_date_updated > ANESTHESIA_HISTORY_UPDATE_PERIOD:
            self.parent.update_anesthesia_history_date_widget()
            self.prev_date_updated = now
        if self.measurement_running:
            elapsed_time = int(time.time() - self.measurement_starttime)
            if elapsed_time > self.measurement_duration:
                elapsed_time = self.measurement_duration
            self.parent.main_widget.experiment_control_groupbox.experiment_progress.setValue(elapsed_time)
            if elapsed_time > self.measurement_duration * 1.5:
                self.parent.main_widget.experiment_control_groupbox.start_experiment_button.setEnabled(True)
        else:
            self.parent.main_widget.experiment_control_groupbox.experiment_progress.setValue(0)

    def handle_commands(self):
        '''
        Handle commands coming via queues (mainly from network thread
        '''
        try:
            for k, queue in self.queues.items():                
                if hasattr(queue, 'has_key') and queue.has_key('in') and not queue['in'].empty():
                    messages = queue['in'].get()
                    if 'EOPSOC' in messages:
                        messages = messages.replace('EOPSOC','EOP@@@SOC').split('@@@')
                    else:
                        messages = [messages]
                    for message in messages:
                        command = command_extract.findall(message)
                        if len(command) > 0:
                            command = command[0]
                        parameter = parameter_extract.findall(message)
                        if len(parameter) > 0:
                            parameter = parameter[0]
                        if command == 'connection':
                            message = command
                        elif command == 'echo' and parameter == 'GUI':
                            message = ''
                        elif message == 'connected to server':
                            #This is sent by the local queued client and its meaning can be confusing, therefore not shown
                            message = ''
                        elif message == 'SOCacquire_z_stackEOCOKEOP':
                            message = 'Z stack acquisition complete.'
                        elif message == 'SOCacquire_z_stackEOCsaveOKEOP' and os.path.exists(self.z_stack_path):
                            time.sleep(0.1)
                            self.z_stack = matlabfile.read_z_stack(self.z_stack_path)
                            self.read_stage(display_coords = False)
                            self.z_stack['stage_position'] = utils.pack_position(self.stage_position-self.stage_origin, 0)
                            self.z_stack['add_date'] = utils.datetime_string().replace('_', ' ')
                            hdf5io.save_item(self.mouse_file.replace('.hdf5', '_z_stack.hdf5'), 'z_stack', self.z_stack, filelocking = self.config.ENABLE_HDF5_FILELOCKING)
                            self.printc('Z stack is saved to {0}' .format(z_stack_file_path))
                            os.remove(self.z_stack_path)
                        elif command == 'measurement_started':
                            self.measurement_running = True
                            self.measurement_starttime = time.time()
                            try:
                                self.measurement_duration = int(numpy.ceil(float(parameter)))
                            except:
                                self.measurement_duration = 0
                            self.parent.main_widget.experiment_control_groupbox.experiment_progress.setRange(0, self.measurement_duration)
                            self.parent.main_widget.experiment_control_groupbox.start_experiment_button.setEnabled(False)
#                            if self.experiment_parameters['enable_intrinsic']:
#                                import threading
#                                from visexpman.engine.hardware_interface import camera_interface
#                                p = os.path.join(self.config.EXPERIMENT_DATA_PATH, self.experiment_parameters['id']+'_intrinsic.hdf5')
#                                self.printc('camera data will be saved to '+p)
#                                self.camera_runner = threading.Thread(target =camera_interface.opencv_camera_runner, args = (p, self.measurement_duration+3.0, self.config))
#                                self.camera_runner.start()
                        elif command == 'measurement_finished':
                            self.measurement_running = False
                            self.parent.main_widget.experiment_control_groupbox.start_experiment_button.setEnabled(True)
                        elif command == 'measurement_ready':
                            if self.experiment_parameters['enable_intrinsic']:
                                self.printc('Camera data is being saved...')
                                self.camera_runner.join()
                                self.printc('Camera recording finished')
#                            else:
                            self.add_measurement_id(parameter)
                            
                        elif command == 'fragment_check_ready':
                            #ID is saved, flag will be updated in mouse later when the measurement file is closed
                            self.fragment_check_ready_id = parameter
                        elif command == 'mesextractor_ready':
                            flags = [command]
                            if hasattr(self, 'fragment_check_ready_id') and self.fragment_check_ready_id is not None and parameter == self.fragment_check_ready_id:
                                #Assuming that by this time the measurement file is closed
                                flags.append('fragment_check_ready')
                                self.fragment_check_ready_id = None
                            else:#Not handled situation: consecutive fragment_check_ready and mesextractor_ready flags are associated to different ids
                                pass
                            self.set_analysis_status_flag(parameter, flags)
                        elif command == 'find_cells_ready':
                            if self.config.ADD_CELLS_TO_MOUSE_FILE:
                                self.add_cells_to_database(parameter)
                            else:
                                region_name, measurement_file_path, info = self.read_scan_regions(parameter)
                                id = parameter 
                                self.scan_regions[region_name]['process_status'][parameter]['find_cells_ready'] = True 
                                soma_rois = hdf5io.read_item(measurement_file_path, 'soma_rois') 
                                if soma_rois is None or len(soma_rois) == 0: 
                                    number_of_new_cells = 0 
                                else: 
                                    number_of_new_cells = len(soma_rois)
                                    if number_of_new_cells > 200: 
                                        number_of_new_cells = 50
                                    self.scan_regions[region_name]['process_status'][id]['info']['number_of_cells'] = number_of_new_cells 
                                    self.save2mouse_file(['scan_regions']) 
                                    self.parent.update_jobhandler_process_status()
                        elif command == 'job_list_file_copy':
                            if parameter == '':
                                tag = 'jobs'
                            else:
                                tag = parameter
                            if self.generate_job_list(tag = tag):
                                self.queues['analysis']['out'].put('SOCjob_list_file_copiedEOCfilename={0}EOP'.format(os.path.split(self.mouse_file)[1].replace('.hdf5', '_{0}.hdf5'.format(tag))))
                        else:
                            self.printc(utils.timestamp2hm(time.time()) + ' ' + k.upper() + ' '  +  message)
        except:
            self.printc(traceback.format_exc())

    def mouse_file_changed(self):
        self.save_cells()
        self.wait_mouse_file_save()
        self.mouse_file = os.path.join(self.config.EXPERIMENT_DATA_PATH, str(self.parent.main_widget.scan_region_groupbox.select_mouse_file.currentText()))
        self.load_mouse_file()
        self.reset_jobhandler()
        self.emit(QtCore.SIGNAL('update_widgets_when_mouse_file_changed'))

    def pass_signal(self, signal_id):
        self.signal_id_queue.put(str(signal_id))

    ########## Manage context ###############
    def init_variables(self):
        self.files_to_delete = []
        self.jobhandler_reset_issued = False
        self.prev_date_updated = 0.0
        self.widget_context_fields = ['self.parent.main_widget.scan_region_groupbox.select_mouse_file',
                                        'self.parent.main_widget.scan_region_groupbox.scan_regions_combobox',
                                        'self.parent.main_widget.experiment_control_groupbox.experiment_name',
                                        #'self.parent.roi_widget.select_cell_combobox',
                                        'self.parent.roi_widget.xz_line_length_combobox',
                                        'self.parent.roi_widget.roi_pattern_parameters_lineedit',
                                        'self.parent.roi_widget.cell_merge_distance_combobox',
                                        'self.parent.roi_widget.cell_group_combobox',
                                        'self.parent.common_widget.registration_subimage_combobox',
                                        'self.parent.animal_parameters_groupbox.anesthesia_history_groupbox.substance_combobox',
                                        'self.parent.animal_parameters_groupbox.anesthesia_history_groupbox.amount_combobox',
                                        'self.parent.animal_parameters_groupbox.anesthesia_history_groupbox.comment_combobox']
        self.measurement_running = False

    def initialize_mouse_file(self):
        '''
        Finds out which mouse file to load and loadds data from it
        '''
        are_new_files, self.mouse_files = update_mouse_files_list(self.config)
        if len(self.mouse_files)>0:
            if hasattr(self, 'last_mouse_file_name') and self.last_mouse_file_name in self.mouse_files:
                mouse_file = self.last_mouse_file_name
            else:
                mouse_file = self.mouse_files[0]
                self.last_mouse_file_name = mouse_file
            self.mouse_file = os.path.join(self.config.EXPERIMENT_DATA_PATH, mouse_file)
            self.load_mouse_file()

    def load_mouse_file(self):
        '''
        Loads scan region, cell and meanimage data from mouse file
        '''
        if os.path.isfile(self.mouse_file):
            #clean out attributes
            attributes = ['scan_regions', 'cells', 'images', 'animal_parameters']
            for attribute in attributes:
                if hasattr(self, attribute):
                    setattr(self, attribute,  {})
            h = hdf5io.Hdf5io(self.mouse_file, filelocking=self.config.ENABLE_HDF5_FILELOCKING)
            varname = h.find_variable_in_h5f('animal_parameters', regexp=True)[0]
            h.load(varname)
            self.animal_parameters = getattr(h, varname)
            scan_regions = h.findvar('scan_regions')
            if scan_regions is None:
                self.scan_regions = {}
            else:
                self.scan_regions = copy.deepcopy(scan_regions)
            analysis_status = h.findvar('analysis_status')
            if analysis_status is None:
                #generate it from scan regions
                self.analysis_status = {}
                for region_name, scan_region in self.scan_regions.items():
                    if scan_region.has_key('process_status'):
                        self.analysis_status[region_name] = scan_region['process_status']
                        del scan_region['process_status']
                #Save scan regions without process status to file
                h.scan_regions = copy.deepcopy(self.scan_regions)
                h.analysis_status = copy.deepcopy(self.analysis_status)
                h.save(['scan_regions','analysis_status'], overwrite = True)
            else:
                self.analysis_status = copy.deepcopy(analysis_status)
            self.printc('Loading cells')
            region_names = self.scan_regions.keys()
            self.cells = {}
            for region_name in region_names:
                cells  = copy.deepcopy(h.findvar('cells_' + region_name))
                if cells is not None and hasattr(cells, 'dtype'):
                    self.cells[region_name] = utils.array2object(cells)
            if self.cells == {}:
                cells  = copy.deepcopy(h.findvar('cells'))#Takes long to load cells
                if cells is not None:
                    if hasattr(cells, 'dtype'):
                        self.cells = utils.array2object(cells)
                    else:
                        self.cells = cells
            self.printc('Loading mean images')
            images  = copy.deepcopy(h.findvar('images'))#Takes long to load images
            if images is not None:
                self.images = images
            anesthesia_history = copy.deepcopy(h.findvar('anesthesia_history'))#Takes long to load images
            if anesthesia_history is not None:
                self.anesthesia_history = copy.deepcopy(anesthesia_history)
            h.close()

    def load_context(self):
        context_hdf5 = hdf5io.Hdf5io(self.config.CONTEXT_FILE, filelocking=self.config.ENABLE_HDF5_FILELOCKING)
        context_hdf5.load('stage_origin')
        context_hdf5.load('stage_position')
        if hasattr(context_hdf5, 'stage_position') and hasattr(context_hdf5, 'stage_origin') :
            self.stage_origin = context_hdf5.stage_origin
            self.stage_position = context_hdf5.stage_position
        else:
            self.stage_position = numpy.zeros(3)
            self.stage_origin = numpy.zeros(3)
        self.xy_scan = context_hdf5.findvar('xy_scan')
        self.xz_scan = context_hdf5.findvar('xz_scan')
        self.load_widget_context(context_hdf5)
        context_hdf5.close()
        self.stage_position_valid = False
        self.scan_regions = {}

    def save_context(self):
        try:
            context_hdf5 = hdf5io.Hdf5io(self.config.CONTEXT_FILE, filelocking=self.config.ENABLE_HDF5_FILELOCKING)
            context_hdf5.stage_origin = copy.deepcopy(self.stage_origin)
            context_hdf5.stage_position = copy.deepcopy(self.stage_position)
            context_hdf5.save('stage_origin',overwrite = True)
            context_hdf5.save('stage_position', overwrite = True)
            if hasattr(self,  'xy_scan'):
                context_hdf5.xy_scan = copy.deepcopy(self.xy_scan)
                context_hdf5.save('xy_scan', overwrite = True)
            if hasattr(self, 'xz_scan'):
                context_hdf5.xz_scan = copy.deepcopy(self.xz_scan)
                context_hdf5.save('xz_scan', overwrite = True)
            context_hdf5.close()
        except:
            self.printc('Context file NOT updated')

    def save_widget_context(self, hdfhandler):
        if hasattr(self,'widget_context_fields'):
            hdfhandler.widget_context = {}
            for widget_field in self.widget_context_fields:
                ref = introspect.string2objectreference(self, widget_field)
                if hasattr(ref,'currentText'):
                    hdfhandler.widget_context[widget_field] = str(ref.currentText())
            hdfhandler.save('widget_context',overwrite = True)

    def load_widget_context(self,hdfhandler):
        hdfhandler.load('widget_context')
        if hasattr(hdfhandler, 'widget_context'):
            self.widget_context_values = copy.deepcopy(hdfhandler.widget_context)
            for k in self.widget_context_values.keys():
                if 'mouse_file' in k:
                    self.last_mouse_file_name = self.widget_context_values[k]
                if 'scan_region' in k: 
                    self.last_region_name = self.widget_context_values[k]
                if hasattr(self,'last_mouse_file_name') and hasattr(self, 'last_region_name'):
                    break

    ############## Measurement file handling ########################
    def add_cells_to_database(self, id, update_gui = True):
        region_name, measurement_file_path, info = self.read_scan_regions(id)
        #read cell info from measurement file
        h_measurement = hdf5io.Hdf5io(measurement_file_path, filelocking=self.config.ENABLE_HDF5_FILELOCKING)
        scan_mode = h_measurement.findvar('call_parameters')['scan_mode']
        self.analysis_status[region_name][id]['find_cells_ready'] = True
        if scan_mode == 'xz':
            soma_rois = h_measurement.findvar('soma_rois')
            if soma_rois is not None:
                number_of_new_cells = len(soma_rois)
            else:
                number_of_new_cells = 0
            self.analysis_status[region_name][id]['info']['number_of_cells'] = number_of_new_cells
            h_measurement.close()
            #Save changes
            self.save2mouse_file('scan_regions')
            self.printc('{1} cells found in {0} but not added to database because it is an xz scan'.format(id, number_of_new_cells))
            if update_gui:
                self.parent.update_cell_list()
                self.parent.update_cell_filter_list()
                self.update_analysis_status()
            return
        if not hasattr(self,  'images'):
            self.images = {}
        self.images[id] = {}
        self.images[id]['meanimage'] = h_measurement.findvar('meanimage')
        scale = h_measurement.findvar('image_scale')
        self.images[id]['scale'] = scale
        origin = h_measurement.findvar('image_origin')
        self.images[id]['origin'] = origin
        self.images = copy.deepcopy(self.images)
        if not hasattr(self,  'cells'):
            self.cells = {}
        if not self.cells.has_key(region_name):
            self.cells[region_name] = {}
        soma_rois = h_measurement.findvar('soma_rois')
        roi_centers = h_measurement.findvar('roi_centers')
        roi_plots = h_measurement.findvar('roi_plots')
        depth = int(numpy.round(h_measurement.findvar('position')['z'][0], 0))
        stimulus = h_measurement.findvar('stimulus_class')
        if soma_rois is None or len(soma_rois) == 0:
            number_of_new_cells = 0
        else:
            number_of_new_cells = len(soma_rois)
            if number_of_new_cells > 250:
                number_of_new_cells = 50
        self.analysis_status[region_name][id]['info']['number_of_cells'] = number_of_new_cells
        from visexpA.engine.datahandlers.datatypes import cell_signature
        for i in range(number_of_new_cells):
            cell_id = cell_signature('r0c0', handler=h_measurement, index = i, return_string = True)
            self.cells[region_name][cell_id] = {}
            self.cells[region_name][cell_id]['depth'] = depth
            self.cells[region_name][cell_id]['id'] = id
            self.cells[region_name][cell_id]['soma_roi'] = soma_rois[i]
            self.cells[region_name][cell_id]['roi_center'] = roi_centers[i]
            self.cells[region_name][cell_id]['accepted'] = False
            self.cells[region_name][cell_id]['group'] = 'none'
            self.cells[region_name][cell_id]['add_date'] = utils.datetime_string().replace('_', ' ')
            self.cells[region_name][cell_id]['stimulus'] = stimulus
            self.cells[region_name][cell_id]['scale'] = scale
            self.cells[region_name][cell_id]['origin'] = origin
            self.cells[region_name][cell_id]['roi_plot'] = roi_plots[i]
            self.cells[region_name][cell_id]['cell_id'] = copy.deepcopy(cell_id)
#        import pdb
#        pdb.set_trace()
        h_measurement.close()
        #Save changes
        self.save2mouse_file(['cells', 'scan_regions', 'images', 'analysis_status'],region_name = self.parent.get_current_region_name())
        self.printc('{1} cells added from {0}'.format(id, number_of_new_cells))
        if update_gui:
            self.parent.update_cell_list()
            self.parent.update_cell_filter_list()
            self.update_analysis_status()

    def set_analysis_status_flag(self, id, flag_names):
        region_name, measurement_file_path, info = self.read_scan_regions(id)
        id_not_found = False
        for flag_name in flag_names:
            if self.analysis_status[region_name].has_key(id):
                self.analysis_status[region_name][id][flag_name] = True
            else:
                id_not_found = True
        self.save2mouse_file('scan_regions')
        if id_not_found:
            self.printc('Unknown id ({0}), probably mouse file is changed', format(id))
        else:
            self.printc('Process status flag set: {1} -> {0}'.format(flag_names[0],  id))
        self.update_analysis_status()

    def add_measurement_id(self, id):
        region_name, measurement_file_path, info = self.read_scan_regions(id)
        if not hasattr(self, 'analysis_status'):
            self.analysis_status = {}
        if not self.analysis_status.has_key(region_name):
            self.analysis_status[region_name] = {}
        if self.analysis_status[region_name].has_key(id):
            if not self.ask4confirmation('ID ({0} already exists, do you want to reimport this measurement?' .format(id)):
                return
        self.analysis_status[region_name][id] = {}
        self.analysis_status[region_name][id]['fragment_check_ready'] = False
        self.analysis_status[region_name][id]['mesextractor_ready'] = False
        self.analysis_status[region_name][id]['find_cells_ready'] = False
        self.analysis_status[region_name][id]['info'] = {}
        self.analysis_status[region_name][id]['info'] = info
        self.save2mouse_file('analysis_status')
        self.printc('Measurement ID added: {0}'.format(id))
        self.update_analysis_status()
        self.parent.update_file_id_combobox()

    def add_id(self):
        self.add_measurement_id(self.parent.get_current_file_id())

    def read_scan_regions(self, id):
        #read call parameters
        measurement_file_path = fileop.get_measurement_file_path_from_id(id, self.config)
        if measurement_file_path is None or not os.path.exists(measurement_file_path):
            self.printc('Measurement file not found: {0}, {1}' .format(measurement_file_path,  id))
            return 3*[None]
        measurement_hdfhandler = hdf5io.Hdf5io(measurement_file_path, filelocking=self.config.ENABLE_HDF5_FILELOCKING)
        fromfile = measurement_hdfhandler.findvar(['call_parameters', 'position', 'experiment_config_name'])
        call_parameters = fromfile[0]
        if not hasattr(self, 'mouse_file') or not call_parameters.has_key('region_name'):
            self.printc('Online analysis of measurements without mouse file or scan region is not supported')
            return 3*[None]
        if not call_parameters.has_key('scan_mode'):
            self.printc('Scan mode does not exists')
            measurement_hdfhandler.close()
            return 3*[None]
        laser_intensity = measurement_hdfhandler.findvar('laser_intensity', path = 'root.'+ '_'.join(cg.get_mes_name_timestamp(measurement_hdfhandler)))
        measurement_hdfhandler.close()
        info = {'depth': fromfile[1]['z'][0], 'stimulus':fromfile[2], 'scan_mode':call_parameters['scan_mode'], 'laser_intensity': laser_intensity}
        #Read the database from the mouse file pointed by the measurement file
        mouse_file = os.path.join(self.config.EXPERIMENT_DATA_PATH, call_parameters['mouse_file'])
        if not os.path.exists(mouse_file):
            self.printc('Mouse file ({0}) assigned to measurement ({1}) is missing' .format(mouse_file,  id))
            return 3*[None]
        if self.scan_regions[call_parameters['region_name']].has_key(id):
            self.printc('ID already exists: {0}'.format(id))
            return 3*[None]
        return call_parameters['region_name'], measurement_file_path, info

    def rebuild_cell_database(self):
        self.clear_analysis_status()
        measurement_file_paths = fileop.filtered_file_list(self.config.EXPERIMENT_DATA_PATH, ['fragment','hdf5'], fullpath = True,filter_condition='and')
        for measurement_path in measurement_file_paths:
            id = fileop.parse_fragment_filename(measurement_path)['id']
            flags = ['fragment_check_ready', 'mesextractor_ready']
            self.add_measurement_id(id)
            self.set_analysis_status_flag(id, flags)
            self.add_cells_to_database(id, update_gui = (measurement_file_paths[-1] == measurement_path))

    def clear_analysis_status(self):
        self.cells = {}
        for region_name in self.analysis_status.keys():
            self.analysis_status[region_name] = {}
        self.save2mouse_file(['analysis_status', 'cells'])

    def remove_measurement_file_from_database(self, id_to_remove = None, process_status_update = False):
        self.printc('Removing measurement id...')
        fields_to_save = []
        if id_to_remove is None:
            id_to_remove = self.parent.get_current_file_id()
        if not self.ask4confirmation('Do you want to remove {0} measurement?' .format(id_to_remove)):
            return
        region_name = self.parent.get_current_region_name()
        if utils.safe_has_key(self.scan_regions, region_name) and not process_status_update and self.analysis_status[region_name].has_key(id_to_remove):
            del self.analysis_status[region_name][id_to_remove]
            fields_to_save.append('analysis_status')
            self.printc('Process status updated')
        if hasattr(self, 'images') and utils.safe_has_key(self.images, id_to_remove):
            del self.images[id_to_remove]
            fields_to_save.append('images')
            self.printc('Meanimages updated')
        if hasattr(self, 'cells') and utils.safe_has_key(self.cells, region_name):
            for cell_id in self.cells[region_name].keys():
                if id_to_remove in cell_id:
                    del self.cells[region_name][cell_id]
            fields_to_save.append('cells')
            self.printc('Cells updated')
        self.save2mouse_file(fields_to_save)
        if not process_status_update:
            self.update_analysis_status()
            self.parent.update_file_id_combobox()
            self.parent.update_cell_list()
            self.parent.update_cell_filter_list()
            self.parent.update_meanimage()
            self.parent.update_cell_group_combobox()
            self.printc('{0} measurement is removed'.format(id_to_remove))

    def set_measurement_file_process_state(self):
        self.printc('Setting state of measurement id...')
        selected_id = self.parent.get_current_file_id()
        target_state = str(self.parent.main_widget.measurement_datafile_status_groupbox.set_to_state_combobox.currentText())
        region_name = self.parent.get_current_region_name()
        if target_state == any(['not processed', 'mesextractor_ready']):#remove cells, mean images and roi curves
            self.remove_measurement_file_from_database(id_to_remove = selected_id, keep_analysis_status_entry = True)
        #Modify process status
        if utils.safe_has_key(self.analysis_status, region_name) and self.analysis_status[region_name].has_key(selected_id):
            if target_state == 'not processed':
                self.analysis_status[region_name][selected_id]['mesextractor_ready'] = False
                self.analysis_status[region_name][selected_id]['fragment_check_ready'] = False
                self.analysis_status[region_name][selected_id]['find_cells_ready'] = False
            elif target_state == 'mesextractor_ready':
                self.analysis_status[region_name][selected_id]['find_cells_ready'] = False
            elif target_state == 'find_cells_ready':
                self.analysis_status[region_name][selected_id]['find_cells_ready'] = True
        self.save2mouse_file('analysis_status', wait_save = True)
        self.update_analysis_status()
        self.parent.update_file_id_combobox()
        self.queues['analysis']['out'].put('SOCclear_joblistEOCEOP')
        self.printc('Measurement file status is updated')

    def next_cell(self):
        current_index = self.parent.roi_widget.select_cell_combobox.currentIndex()
        current_index += 1
        if current_index >= len(self.cell_ids):
            current_index = len(self.cell_ids)-1
            self.emit(QtCore.SIGNAL('select_cell_changed'))
        else:
            self.parent.roi_widget.select_cell_combobox.setCurrentIndex(current_index)

    def previous_cell(self):
        current_index = self.parent.roi_widget.select_cell_combobox.currentIndex()
        current_index -= 1
        if current_index < 0:
            current_index = len(self.cell_ids)-1
        self.parent.roi_widget.select_cell_combobox.setCurrentIndex(current_index)

    def accept_cell(self):
        self.select_cell(True)

    def ignore_cell(self):
        self.select_cell(False)

    def select_cell(self, selection):
        self.cells[self.parent.get_current_region_name()][self.parent.get_current_cell_id()]['accepted'] = selection
        if selection:
            cell_group_name = str(self.parent.roi_widget.cell_group_combobox.currentText())
            if cell_group_name == '':
                self.printc('No cell group name provided')
                return
            self.cells[self.parent.get_current_region_name()][self.parent.get_current_cell_id()]['group'] = cell_group_name
        self.next_cell()
        self.cell_status_changed_in_cache = True

    def calculate_suggested_depth(self):
        current_group = str(self.parent.roi_widget.cell_group_combobox.currentText())
        region_name = self.parent.get_current_region_name()
        if current_group != '' and self.cells.has_key(region_name):
            depths = [cell['depth'] for cell in self.cells[region_name].values() if cell['group'] == current_group]
            self.suggested_depth = numpy.round(numpy.array(list(set(depths))).mean(), 0)
        else:
            self.suggested_depth = numpy.nan

    def save_cells(self,region_name = None):
        if hasattr(self, 'cells') and self.cell_status_changed_in_cache:
            self.save2mouse_file('cells',region_name = region_name)
            self.parent.update_cell_group_combobox()
            self.cell_status_changed_in_cache = False
            self.printc('Cells saved')

################### Stage #######################
    def read_stage(self, display_coords = False):
        self.printc('Reading stage and objective position, please wait')
        result = False
        utils.empty_queue(self.queues['stim']['in'])
        self.queues['stim']['out'].put('SOCstageEOCreadEOP')
        if utils.wait_data_appear_in_queue(self.queues['stim']['in'], self.config.GUI_STAGE_TIMEOUT):
            while not self.queues['stim']['in'].empty():
                response = self.queues['stim']['in'].get()
                if 'SOCstageEOC' in response:
                    self.stage_position = self.parse_list_response(response)
                    result, self.objective_position = self.mes_interface.read_objective_position(timeout = self.config.MES_TIMEOUT)
                    if not result:
                        self.printc('MES does not respond')
                    if display_coords:
                        self.printc('rel: {0}, abs: {1}'.format(self.stage_position - self.stage_origin, self.stage_position))
                    else:
                        self.printc('Read stage ready')
                    self.save_context()
                    self.parent.update_position_display()
                    result = True
        else:
            self.printc('stage is not accessible')
        return result

    def set_stage_origin(self):
        if not self.ask4confirmation('Setting stage origin. Are you sure?'):
            return
        result = False
        if not self.mes_interface.overwrite_relative_position(0, self.config.MES_TIMEOUT):
            self.printc('Setting objective to 0 did not succeed')
            return result
        if not self.stage_position_valid:
            self.read_stage(display_coords = False)
            self.stage_position_valid = True
        self.stage_origin = self.stage_position
        self.save_context()
        utils.empty_queue(self.queues['stim']['in'])
        self.queues['stim']['out'].put('SOCstageEOCoriginEOP')
        if utils.wait_data_appear_in_queue(self.queues['stim']['in'], 10.0):
            while not self.queues['stim']['in'].empty():
                response = self.queues['stim']['in'].get()
                if 'SOCstageEOC' in response:
                    self.printc('Origin set')
                    self.stage_origin_set = True
                    result = True
        self.origin_set = True
        self.parent.update_position_display()
        return result

    def tilt_brain_surface(self):
        if self.parent.common_widget.enable_tilting_checkbox.checkState() != 2:
            self.printc('Tilting NOT enabled')
            return
        self.parent.common_widget.enable_tilting_checkbox.setCheckState(0)
        movement = map(float, self.parent.scanc().split(','))
        if len(movement) != 2:
            self.printc('Invalid coordinates')
            return
        if abs(movement[0]) > self.config.TILTING_LIMIT or abs(movement[1]) > self.config.TILTING_LIMIT:
            self.printc('Requested tilting is too big')
            return
        if not self.ask4confirmation('Make surre that anesthesia tube not touching mouse nose'):
            return
        mg = stage_control.MotorizedGoniometer(self.config, id = 1)
        speed = 150#IDEA: speed may depend on movement
        if mg.set_speed(speed):
            time.sleep(1.0)
            result = mg.move(numpy.array(movement))
            if not result:
                self.printc('Tilting was NOT successful')
            else:
                self.printc('Tilting mouse successful')
                position, result = mg.read_position()
                if not result:
                    self.printc('New position is unknown')
                else:
                    self.printc('{0} degree'.format(position))
        else:
            self.printc('Setting goniometer speed was NOT successful')
        mg.release_instrument()

    def move_stage(self):
        movement = self.parent.scanc().split(',')
        if len(movement) == 2:
            #Only two values are accepted
            movement.append('0')
        else:
            self.printc('invalid coordinates')
            return
        #Disbaled: self.parent.main_widget.scan_region_groupbox.scan_regions_combobox.setEditText('')
        self.move_stage_relative(movement)
        if self.parent.common_widget.enable_xy_scan_with_move_checkbox.checkState() != 0:
            self.acquire_xy_scan()

    def move_stage_relative(self, movement):
        if hasattr(self, 'xy_scan'): #to avoid saving false data at saving regions
            del self.xy_scan
        if hasattr(self, 'xz_scan'):
            del self.xz_scan
        utils.empty_queue(self.queues['stim']['in'])
        self.queues['stim']['out'].put('SOCstageEOCset,{0},{1},{2}EOP'.format(movement[0], movement[1], movement[2]))
        self.printc('movement {0}, {1}'.format(movement[0], movement[1]))
        if not utils.wait_data_appear_in_queue(self.queues['stim']['in'], self.config.GUI_STAGE_TIMEOUT):
            self.printc('Stage does not respond')
            return False
        while not self.queues['stim']['in'].empty():
            response = self.queues['stim']['in'].get()
            if 'SOCstageEOC' in response:
                self.stage_position = self.parse_list_response(response)
                self.save_context()
                self.parent.update_position_display()
                self.printc('New position rel: {0}, abs: {1}'.format(self.stage_position - self.stage_origin, self.stage_position))
                return True
        self.printc('Stage does not respond')
        return False

    def stop_stage(self):
        utils.empty_queue(self.queues['stim']['in'])
        self.queues['stim']['out'].put('SOCstageEOCstopEOP')
        self.printc('Stage stopped')

################### MES #######################
    def set_objective(self):
        try:
            position = float(self.parent.scanc())
        except ValueError:
            self.printc('No position is given')
            return
        if self.mes_interface.set_objective(position, self.config.MES_TIMEOUT):
            self.objective_position = position
            if self.parent.common_widget.enable_set_objective_origin_after_moving_checkbox.checkState() != 0:
                self.parent.common_widget.enable_set_objective_origin_after_moving_checkbox.setCheckState(0) 
                if not self.mes_interface.overwrite_relative_position(0, self.config.MES_TIMEOUT):
                    self.printc('Setting objective to 0 did not succeed')
                else:
                    self.objective_position = 0.0
            if self.parent.common_widget.enable_laser_adjust_checkbox.checkState() != 0 and position == 0:
                #Adjust laser to saved value
                result, adjusted_laser_intensity = self.mes_interface.set_laser_intensity(self.scan_regions[self.parent.get_current_region_name()]['laser_intensity'])
                if not result:
                    self.printc('Laser cannot be set')
            self.parent.update_position_display()
            self.printc('Objective is set to {0} um'.format(position))
        else:
            self.printc('MES did not respond')

    def set_objective_relative_value(self):
        try:
            position = float(self.parent.scanc())
        except ValueError:
            self.printc('No position is given')
            return
        if self.mes_interface.overwrite_relative_position(position, self.config.MES_TIMEOUT):
            self.printc('Objective relative value is set to {0} um'.format(position))
        else:
            self.printc('MES did not respond')
            
    def start_tile_scan(self):
        parameters = {}
        parameter_names = ['overlap', 'ncols', 'nrows']
        for pn in parameter_names:
            parameters[pn] = str(getattr(self.parent.z_stack_widget.tile_scan_groupbox, pn).overlap.input.text())
            try:
                parameters[pn] = float(parameters[pn])
            except:
                self.printc('{0} parameter is in incorrect format', format(pn))
        #somehow the size of scan window has to be known
        window_size = utils.rc((700, 700))
        if self.read_stage():
            self.tile_scan_positions = []
            for row in parameters['nrows']:
                for col in parameters['ncols']:
                    pos = [row * window_size['row'] - parameters['overlap'] + self.stage_position['row'], 
                           col * window_size['col'] - parameters['overlap'] + self.stage_position['col'], 0]
                    self.tile_scan_positions.append(pos)
        self.tile_scan_positions = utils.rcd(numpy.array(self.tile_scan_positions))
        self.tile_scan_position_index = 0
        #TODO: message to start tile scan
        
    def tile_scan(self):
        if hasattr(self, 'tile_scan_position_index') and self.move_stage_relative(self.tile_scan_positions[self.tile_scan_position_index]):
            zstack, result = self.mes_interface.acquire_z_stack(timeout = self.config.MES_TIMEOUT)
            zstack['position'] = self.tile_scan_positions[self.tile_scan_position_index]
            #TODO: save tile scan fragment
            self.tile_scan_position_index += 1
            if self.tile_scan_positions.shape[0] >= self.tile_scan_position_index:#End of tile scan
                pass#Message to end tilescan
            else:
                pass#Message to continue tile scan
                
    def finish_tile_scan(self):
        pass

    def acquire_z_stack(self):
        self.printc('Starting z stack, please wait')
        try:
            self.z_stack_path, results = self.mes_interface.start_z_stack(self.config.MES_TIMEOUT)
            self.printc((self.z_stack_path, results))
        except:
            self.printc(traceback.format_exc())

    def acquire_xy_scan(self, use_region_parameters = False):
        self.printc('Acquire two photon image')
        if self.parent.main_widget.scan_region_groupbox.use_saved_scan_settings_settings_checkbox.checkState() != 0 or use_region_parameters:
            #Load scan settings from parameter file
            parameter_file_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, 'scan_region_parameters.mat')
            if self.create_parameterfile_from_region_info(parameter_file_path, 'xy'):
                self.xy_scan, result = self.mes_interface.acquire_xy_scan(self.config.MES_TIMEOUT, parameter_file = parameter_file_path)
            else:
                self.xy_scan = {}
                result = False
        elif self.parent.main_widget.scan_region_groupbox.use_saved_scan_settings_settings_checkbox.checkState() == 0:
            self.xy_scan, result = self.mes_interface.acquire_xy_scan(self.config.MES_TIMEOUT)
        if hasattr(self.xy_scan, 'has_key'):
            if self.xy_scan.has_key('path'):#For unknown reason this key is not found sometimes
                self.files_to_delete.append(self.xy_scan['path'])
        if result:
            if self.xy_scan.has_key(self.config.DEFAULT_PMT_CHANNEL):
                self.show_image(self.xy_scan[self.config.DEFAULT_PMT_CHANNEL], 0, self.xy_scan['scale'], origin = self.xy_scan['origin'])
            elif self.xy_scan.has_key('pmtURraw'):
                self.show_image(self.xy_scan['pmtURraw'], 0, self.xy_scan['scale'], origin = self.xy_scan['origin'])
            self.save_context()
            #Update objective position to ensure synchronzation with manual control of objective
            self.objective_position = self.xy_scan['objective_position'] 
            self.parent.update_position_display()
            self.printc('Image acquiring ready')
            return True
        else:
                self.printc('No image acquired')
        return False

    def acquire_xz_scan(self, use_region_parameters = False):
        '''
        The correct scan time needs to be defined by the user
        '''
        self.printc('Acquire vertical scan')
        if self.parent.main_widget.scan_region_groupbox.use_saved_scan_settings_settings_checkbox.checkState() != 0 or use_region_parameters:
            parameter_file_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, 'xz_scan_region_parameters.mat')
            if not self.create_parameterfile_from_region_info(parameter_file_path, 'xz'):
                return False
            self.xz_scan, result = self.mes_interface.vertical_line_scan(parameter_file = parameter_file_path)
            self.files_to_delete.append(parameter_file_path)
        else:
            self.xz_scan, result = self.mes_interface.vertical_line_scan()
        if not result:
            self.printc('Vertical scan did not succeed')
            return result
        if hasattr(self.xz_scan, 'has_key'):
            if self.xz_scan.has_key('path'):#For unknown reason this key is not found sometimes
                self.files_to_delete.append(self.xz_scan['path'])
        #Update objective position to ensure synchronzation with manual control of objective
        self.objective_position = self.xz_scan['objective_position']
        objective_position_marker = [[0, self.objective_position, 
                                      0.04*self.xz_scan['scaled_image'].shape[0] * self.xz_scan['scaled_scale']['col'], self.objective_position]]

        self.parent.update_position_display()
        if self.xy_scan.has_key('scaled_image_red'):
            self.show_image(self.xz_scan['scaled_image_red'], 2, self.xz_scan['scaled_scale'], line = objective_position_marker, origin = self.xz_scan['origin'])
        else:
            self.show_image(self.xz_scan['scaled_image'], 2, self.xz_scan['scaled_scale'], line = objective_position_marker, origin = self.xz_scan['origin'])
        self.save_context()       
        self.xz_scan_acquired = True
        return result

    def create_xz_lines(self):
        self.printc('Saving cell settings...')
        self.save_cells(region_name = self.parent.get_current_region_name())
        self.printc('Creating xz lines,  please wait...')
        if not hasattr(self, 'animal_parameters'):
            self.printc('Animal parameters are not available, roi filename is unknown')
            return
        region_name = self.parent.get_current_region_name()
        result,  self.objective_position, self.objective_origin = self.mes_interface.read_objective_position(timeout = self.config.MES_TIMEOUT, with_origin = True)
        if not result:
            self.printc('Objective position is not available')
            return
        if os.path.exists(self.mouse_file):
            merge_distance = str(self.parent.roi_widget.cell_merge_distance_combobox.currentText())
            if merge_distance =='':
                merge_distance = self.config.CELL_MERGE_DISTANCE
            else:
                merge_distance = float(merge_distance)
            self.xz_config = {}
            self.xz_config['merge_distance'] = merge_distance
            self.xz_config['cell_group'] = self.parent.get_current_cell_group()
            self.roi_locations, self.rois = experiment_data.read_merge_rois(self.cells, 
                                cell_group = self.xz_config['cell_group'],
                                region_name =  region_name, 
                                objective_position = self.objective_position, 
                                objective_origin = self.objective_origin, 
                                z_range = self.config.XZ_SCAN_CONFIG['Z_RANGE'], 
                                merge_distance = merge_distance)
            if self.rois is None:
                self.printc('No rois found, check objective position')
                return
            params = str(self.parent.roi_widget.roi_pattern_parameters_lineedit.currentText()).replace(' ', '')
            if len(params)==0:
                roi_pattern_size = 0
                aux_roi_distance = 0
            else:
                roi_pattern_size = int(params.split(',')[0])
                aux_roi_distance = float(params.split(',')[1])
            self.xz_config['roi_pattern_size'] = roi_pattern_size
            self.xz_config['aux_roi_distance'] = aux_roi_distance
            if roi_pattern_size > 1:
                self.roi_locations, self.rois = experiment_data.add_auxiliary_rois(self.rois, roi_pattern_size, self.objective_position, self.objective_origin, 
                                                                     aux_roi_distance = aux_roi_distance, soma_size_ratio = None)
            if self.roi_locations is not None:
                line_length = str(self.parent.roi_widget.xz_line_length_combobox.currentText())
                self.xz_config = dict(self.xz_config.items() + copy.deepcopy(self.config.XZ_SCAN_CONFIG).items())
                if line_length != '':
                    self.xz_config['LINE_LENGTH'] = float(line_length)
                if not self.mes_interface.create_XZline_from_points(self.roi_locations, self.xz_config, True):
                        selfprintc('Creating xz lines did not succeed')
                else:
                    self.printc('{0} xz lines created'.format(self.roi_locations.shape[0]))
            else:
                self.printc('No rois loaded')

    ##############################Animal parameters##############################################    
    def save_animal_parameters(self):
        '''
        Saves the following parameters of a mouse:
        - birth date
        - gcamp injection date
        - anesthesia protocol
        - ear punch infos
        - strain
        - user comments

        The hdf5 file is closed.
        '''
        mouse_birth_date = self.parent.animal_parameters_groupbox.mouse_birth_date.date()
        mouse_birth_date = '{0}-{1}-{2}'.format(mouse_birth_date.day(),  mouse_birth_date.month(),  mouse_birth_date.year())
        gcamp_injection_date = self.parent.animal_parameters_groupbox.gcamp_injection_date.date()
        gcamp_injection_date = '{0}-{1}-{2}'.format(gcamp_injection_date.day(),  gcamp_injection_date.month(),  gcamp_injection_date.year())                

        id_text = str(self.parent.animal_parameters_groupbox.id.currentText())
        if id_text == '':
            self.printc('Providing ID is mandatory')
            return
        self.animal_parameters = {
            'mouse_birth_date' : mouse_birth_date,
            'gcamp_injection_date' : gcamp_injection_date,
            'id' : id_text,
            'gender' : str(self.parent.animal_parameters_groupbox.gender.currentText()),
            'ear_punch_l' : str(self.parent.animal_parameters_groupbox.ear_punch_l.currentText()), 
            'ear_punch_r' : str(self.parent.animal_parameters_groupbox.ear_punch_r.currentText()),
            'strain' : str(self.parent.animal_parameters_groupbox.mouse_strain.currentText()),
            'green_labeling' : str(self.parent.animal_parameters_groupbox.green_labeling.currentText()),
            'red_labeling' : str(self.parent.animal_parameters_groupbox.red_labeling.currentText()),
            'comments' : str(self.parent.animal_parameters_groupbox.comments.currentText()),
            'add_date' : utils.datetime_string().replace('_', ' ')
        }        
        name = '{0}_{1}_{2}_{3}_{4}_{5}' .format(self.animal_parameters['id'], self.animal_parameters['strain'], self.animal_parameters['mouse_birth_date'] , self.animal_parameters['gcamp_injection_date'], \
                                         self.animal_parameters['ear_punch_l'], self.animal_parameters['ear_punch_r'])
        #TODO use component_guesser.generate_filename
        self.mouse_file = os.path.join(self.config.EXPERIMENT_DATA_PATH, self.generate_animal_filename('mouse', self.animal_parameters))

        if os.path.exists(self.mouse_file):
            self.printc('Animal parameter file already exists')
        else:
            variable_name = 'animal_parameters_{0}'.format(int(time.time()))
            hdf5io.save_item(self.mouse_file, variable_name, self.animal_parameters, filelocking = self.config.ENABLE_HDF5_FILELOCKING)
            are_new_file, self.mouse_files = update_mouse_files_list(self.config, self.mouse_files)
            time.sleep(0.1)#Wait till file is created
            #set selected mouse file to this one
            self.parent.update_mouse_files_combobox(set_to_value = os.path.split(self.mouse_file)[-1])
            self.parent.update_cell_group_combobox()
            #Clear image displays showing regions
            self.emit(QtCore.SIGNAL('clear_image_display'), 1)
            self.emit(QtCore.SIGNAL('clear_image_display'), 3)
            self.parent.main_widget.scan_region_groupbox.use_saved_scan_settings_settings_checkbox.setCheckState(0)
            #Initialize anesthesi history
            self.anesthesia_history = []
            self.save2mouse_file('anesthesia_history')
            self.update_anesthesia_history()
            self.printc('Animal parameter file saved')

    def add_to_anesthesia_history(self):
        if hasattr(self, 'mouse_file') and os.path.exists(self.mouse_file):
            if not hasattr(self, 'anesthesia_history'):
                self.anesthesia_history = []
            entry = {}
            date = self.parent.animal_parameters_groupbox.anesthesia_history_groupbox.date.date()
            tme = self.parent.animal_parameters_groupbox.anesthesia_history_groupbox.date.time()
            timestamp = time.mktime(time.struct_time((date.year(),date.month(),date.day(),tme.hour(),tme.minute(),0,0,0,-1)))
#        mouse_birth_date = '{0}-{1}-{2}'.format(mouse_birth_date.day(),  mouse_birth_date.month(),  mouse_birth_date.year())
            entry['timestamp'] = timestamp
            entry['substance'] = str(self.parent.animal_parameters_groupbox.anesthesia_history_groupbox.substance_combobox.currentText())
            entry['amount'] = str(self.parent.animal_parameters_groupbox.anesthesia_history_groupbox.amount_combobox.currentText())
            entry['comment'] = str(self.parent.animal_parameters_groupbox.anesthesia_history_groupbox.comment_combobox.currentText())
            self.anesthesia_history.append(entry)
            import operator
            self.anesthesia_history.sort(key = operator.itemgetter('timestamp'))
            self.save2mouse_file('anesthesia_history')
            self.update_anesthesia_history()

    def remove_last_from_anesthesia_history(self):
        if hasattr(self, 'mouse_file') and os.path.exists(self.mouse_file):
            if not hasattr(self, 'anesthesia_history'):
                self.anesthesia_history = []
            elif len(self.anesthesia_history) > 0:
                self.anesthesia_history.pop()
                self.save2mouse_file('anesthesia_history')
            self.update_anesthesia_history()

    ################### Regions #######################
    def add_scan_region(self):
        '''
        The following data are saved:
        -two photon image of the brain surface
        -mes parameter file of two photon acquisition so that later the very same image could be taken to help realignment
        -objective positon where the data acquisition shall take place. This is below the brain surface
        -stage position. If master position is saved, the current position is set to origin. The origin of stimulation software is also 
        '''
        if not self.xz_scan_acquired and hasattr(self, 'xz_scan'):
            del self.xz_scan
        if not hasattr(self, 'xy_scan'):
            self.printc('No brain surface image is acquired')
            return
        if self.xy_scan['averaging'] < self.config.MIN_SCAN_REGION_AVERAGING:
            self.printc('Brain surface image averaging is only {0}' .format(self.xy_scan['averaging'], self.config.MIN_SCAN_REGION_AVERAGING))
        if hasattr(self, 'xz_scan') and self.xz_scan['averaging'] < self.config.MIN_SCAN_REGION_AVERAGING:
            self.printc('Number of xz frames is only {0}' .format(self.xz_scan['averaging']))
        if not (os.path.exists(self.mouse_file) and '.hdf5' in self.mouse_file):
            self.printc('mouse file not found')
            return
        result, self.objective_position = self.mes_interface.read_objective_position(timeout = self.config.MES_TIMEOUT)
        if not result:
            self.printc('MES does not respond')
            return
        result, laser_intensity = self.mes_interface.read_laser_intensity()
        if not result:
            self.printc('MES does not respond')
            return
        if not self.read_stage(display_coords = False):
            self.printc('Stage cannot be accessed')
            return
        if self.scan_regions == None:
            self.scan_regions = {}
        region_name = self.parent.get_current_region_name()
        if region_name == '':
            region_name = 'r'
        if self.scan_regions.has_key(region_name):
            #Ask for confirmation to overwrite if region name already exists
            self.emit(QtCore.SIGNAL('show_overwrite_region_messagebox'))
            while self.gui_thread_queue.empty() :
                time.sleep(0.1) 
            if not self.gui_thread_queue.get():
                self.printc('Region not saved')
                return
        else:
            relative_position = numpy.round(self.stage_position-self.stage_origin, 0)
            region_name_tag = '_{0}_{1}'.format(int(relative_position[0]),int(relative_position[1]))
            region_name = region_name + region_name_tag
            region_name = region_name.replace(' ', '_')
            #Ask for confirmation to overwrite if region name already exists
            if self.scan_regions.has_key(region_name) and not self.ask4confirmation('Overwriting scan region'):
                self.printc('Region not saved')
                return
        if not('master' in region_name or '0_0' in region_name or self.has_master_position(self.scan_regions)):
            self.printc('Master position has to be defined')
            return
        if 'master' == region_name.replace(region_name_tag, ''):
           if not self.set_stage_origin():
                self.printc('Setting origin did not succeed')
                return
           else:
                relative_position = numpy.round(self.stage_position-self.stage_origin, 0)
                region_name = 'master_{0}_{1}'.format(int(relative_position[0]),int(relative_position[1]))
        scan_region = {}
        scan_region['add_date'] = utils.datetime_string().replace('_', ' ')
        scan_region['position'] = utils.pack_position(self.stage_position-self.stage_origin, self.objective_position)
        scan_region['laser_intensity'] = laser_intensity
        scan_region['xy'] = {}
        if self.xy_scan.has_key(self.config.DEFAULT_PMT_CHANNEL):
            scan_region['xy']['image'] = self.xy_scan[self.config.DEFAULT_PMT_CHANNEL]
        elif self.xy_scan.has_key('pmtURraw'):
            scan_region['xy']['image'] = self.xy_scan['pmtURraw']
        scan_region['xy']['scale'] = self.xy_scan['scale']
        scan_region['xy']['origin'] = self.xy_scan['origin']
        scan_region['xy']['mes_parameters']  = self.xy_scan['mes_parameters']
        #Save xy line scan parameters
        result, line_scan_path, line_scan_path_on_mes = self.mes_interface.get_line_scan_parameters()
        if result and os.path.exists(line_scan_path):
            scan_region['xy_scan_parameters'] = utils.file_to_binary_array(line_scan_path)
            os.remove(line_scan_path)
        #Vertical section
        if hasattr(self, 'xz_scan'):
            if self.xz_scan !=  None:
                scan_region['xz'] = self.xz_scan
                scan_region['xz']['mes_parameters'] = utils.file_to_binary_array(self.xz_scan['path'])
            else:
                self.printc('Vertical scan is not available')
        else:
            self.printc('Vertical scan is not available')
        #Save new scan region to hdf5 file
        self.scan_regions[region_name] = scan_region
        self.save2mouse_file('scan_regions')
        self.parent.update_region_names_combobox(region_name)
        self.update_scan_regions()#This is probably redundant
        self.printc('{0} scan region saved'.format(region_name))

    def save_xy_scan(self):
        if not self.ask4confirmation('XY scan config will be overwritten'):
            return
        region_name = self.parent.get_current_region_name()
        if not self.xy_scan is None:
            if self.xy_scan.has_key(self.config.DEFAULT_PMT_CHANNEL):
                self.scan_regions[region_name]['xy']['image'] = self.xy_scan[self.config.DEFAULT_PMT_CHANNEL]
            elif self.xy_scan.has_key('pmtURraw'):
                self.scan_regions[region_name]['xy']['image'] = self.xy_scan['pmtURraw']
            self.scan_regions[region_name]['xy']['scale'] = self.xy_scan['scale']
            self.scan_regions[region_name]['xy']['origin'] = self.xy_scan['origin']
            self.save2mouse_file('scan_regions')
            self.update_scan_regions()#This is probably redundant
            self.printc('XY scan updated')

    def save_xz_scan(self):
        if not self.ask4confirmation('XZ scan config will be overwritten'):
            return
        region_name = self.parent.get_current_region_name()
        if not self.xz_scan is None:
            self.scan_regions[region_name]['xz'] = self.xz_scan
            self.scan_regions[region_name]['xz']['mes_parameters'] = utils.file_to_binary_array(self.xz_scan['path'])
            self.save2mouse_file('scan_regions')
            self.update_scan_regions()#This is probably redundant
            self.printc('XZ scan updated')

    def save_xyt_scan(self):
        if not self.ask4confirmation('XYT scan config will be overwritten'):
            return
        region_name = self.parent.get_current_region_name()
        if not self.xy_scan is None:
            self.printc('Reading XYT line scan parameters')
            result, line_scan_path, line_scan_path_on_mes = self.mes_interface.get_line_scan_parameters()
            if result and os.path.exists(line_scan_path):
                self.scan_regions[region_name]['xy_scan_parameters'] = utils.file_to_binary_array(line_scan_path)
                self.save2mouse_file('scan_regions')
                os.remove(line_scan_path)
                self.update_scan_regions()#This is probably redundant
                self.printc('XYT scan updated')
            else:
                self.printl('XYT scan parameters cannot be read')

    def remove_scan_region(self):
        selected_region = self.parent.get_current_region_name()
        if not self.ask4confirmation('Do you want to remove {0} scan region?' .format(selected_region)):
            return
        if selected_region != 'master' and 'r_0_0' not in selected_region:
            if self.scan_regions.has_key(selected_region):
                del self.scan_regions[selected_region]
            self.save2mouse_file('scan_regions')
            self.parent.main_widget.scan_region_groupbox.scan_regions_combobox.setCurrentIndex(0)
            self.parent.update_region_names_combobox()
            self.update_scan_regions()
            self.printc('{0} region removed'.format(selected_region))
        else:
            self.printc('Master region cannot be removed')

    def move_to_region(self):
        '''
        Use cases:
        1. move stage and objective without realignment
        2. move stage and objective and realign both vertically and in xy
        (3. Realign objective at experiment batches - will be implemented in stimulation sw)
        '''
        selected_region = self.parent.get_current_region_name()
        if self.parent.helpers_widget.override_enforcing_set_stage_origin_checkbox.checkState() != 0:
            self.stage_origin_set = True
        if not self.stage_origin_set:
            self.printc('WARNING: origin not set')
            #return When origin is not set, only a notification will be shown, but stage is moved to region
        if self.parent.main_widget.scan_region_groupbox.move_to_region_options['checkboxes']['objective_move'] .checkState() != 0:
            self.printc('Move objective to saved position')
            if abs(self.scan_regions[selected_region]['position']['z']) > self.config.OBJECTIVE_POSITION_LIMIT:
                self.printc('Objective position is not correct')
                return
            if not self.mes_interface.set_objective(self.scan_regions[selected_region]['position']['z'], self.config.MES_TIMEOUT):
                self.printc('Setting objective did not succeed')
                return
            self.printc('Objective set to {0} um'.format(self.scan_regions[selected_region]['position']['z']))
        if self.parent.main_widget.scan_region_groupbox.move_to_region_options['checkboxes']['stage_move'] .checkState() != 0:
            if not (self.has_master_position(self.scan_regions) and self.scan_regions.has_key(selected_region)):
                self.printc('Master position is not defined')
                return
            self.printc('Move stage to saved region position')
            master_position_name = self.get_master_position_name(self.scan_regions)
            current_relative_position = self.stage_position - self.stage_origin
            master_position = numpy.array([self.scan_regions[master_position_name]['position']['x'][0], self.scan_regions[master_position_name]['position']['y'][0], current_relative_position[-1]])
            target_relative_position = numpy.array([self.scan_regions[selected_region]['position']['x'][0], self.scan_regions[selected_region]['position']['y'][0], current_relative_position[-1]])
            movement = target_relative_position - current_relative_position
            if not self.move_stage_relative(movement):
                return
        if self.parent.main_widget.scan_region_groupbox.move_to_region_options['checkboxes']['stage_realign'] .checkState() != 0:
            self.printc('Realign stage')
            if not self.acquire_xy_scan(use_region_parameters = True):
                return
            self.printc('Register with saved image.')
            #calculate translation between current and saved brain surface image
            if not self.register_images(self.xy_scan[self.config.DEFAULT_PMT_CHANNEL], self.scan_regions[selected_region]['xy']['image'], self.xy_scan['scale'], self.xy_scan['origin']):
                return
            if abs(self.suggested_translation['col'])  > self.config.MAX_REALIGNMENT_OFFSET or abs(self.suggested_translation['row']) > self.config.MAX_REALIGNMENT_OFFSET:
                self.printc('Suggested translation is not plausible')
                return
            #Translate stage with suggested values
            stage_translation = -numpy.round(numpy.array([self.suggested_translation['col'][0], self.suggested_translation['row'][0], 0.0]), 2)
            if abs(self.suggested_translation['col'])  > self.config.REALIGNMENT_XY_THRESHOLD or abs(self.suggested_translation['row']) > self.config.REALIGNMENT_XY_THRESHOLD:
                self.move_stage_relative(stage_translation)
            else:
                self.printc('Suggested translation is small, stage is not moved')
            if self.parent.main_widget.scan_region_groupbox.move_to_region_options['checkboxes']['stage_origin_adjust'] .checkState() != 0:
                self.printc('Stage origin was corrected with detected offset')
                self.stage_origin = self.stage_origin + stage_translation
            #Get a two photon image and register again, to see whether realignment was successful
            if not self.acquire_xy_scan(use_region_parameters = True):
                return
            if not self.register_images(self.xy_scan[self.config.DEFAULT_PMT_CHANNEL], self.scan_regions[selected_region]['xy']['image'], self.xy_scan['scale'], self.xy_scan['origin']):
                return
            if abs(self.suggested_translation['col']) > self.config.ACCEPTABLE_REALIGNMENT_OFFSET or abs(self.suggested_translation['row']) > self.config.ACCEPTABLE_REALIGNMENT_OFFSET:
                self.printc('Realignment was not successful {0}' .format(self.suggested_translation)) #Process not interrupted, but moves to vertical realignment
            self.printc('XY offset {0}' .format(self.suggested_translation))
        if self.parent.main_widget.scan_region_groupbox.move_to_region_options['checkboxes']['objective_realign'] .checkState() != 0 and\
                self.scan_regions[selected_region].has_key('xz'):
            self.printc('Realign objective')
            result, self.objective_position = self.mes_interface.read_objective_position(timeout = self.config.MES_TIMEOUT)
            if not result:
                self.printc('MES does not respond')
                return
            if not self.acquire_xz_scan(use_region_parameters = True):
                self.printc('Vertical scan was not successful')
                return
            #calculate z offset between currently acquired vertical scan and reference data
            if not self.register_images(self.xz_scan['scaled_image'], self.scan_regions[selected_region]['xz']['scaled_image'], self.xz_scan['scaled_scale']):
                return
            vertical_offset = self.suggested_translation['row']
            if abs(vertical_offset)  > self.config.MAX_REALIGNMENT_OFFSET:
                self.printc('Suggested movement is not plausible')
                return
            new_objective_position = self.objective_position + vertical_offset#self.objective_position was updated by vertical scan
            #Move objective
            if abs(vertical_offset)  > self.config.REALIGNMENT_Z_THRESHOLD:
                if not self.mes_interface.set_objective(new_objective_position, self.config.MES_TIMEOUT):
                    self.printc('Setting objective did not succeed')
                    return
                else:
                    self.printc('Objective moved to {0}'.format(new_objective_position))
                    #Change origin when full realignment is done with moving both objective and stage and realign both devices
                    if self.parent.main_widget.scan_region_groupbox.move_to_region_options['checkboxes']['objective_origin_adjust'] .checkState() != 0:
                        if not self.mes_interface.overwrite_relative_position(self.objective_position, self.config.MES_TIMEOUT):
                            self.printc('Setting objective relative value did not succeed')
                            return
                        else:
                            self.printc('Objective relative origin was corrected with detected offset')
                    result, self.objective_position = self.mes_interface.read_objective_position(timeout = self.config.MES_TIMEOUT)
                    if not result:
                        self.printc('MES did not respond')
                        return
            else:
                self.printc('Suggested translation is small, objective is not moved.')
            #Verify vertical realignment
            if not self.acquire_xz_scan(use_region_parameters = True):
                self.printc('Vertical scan was not successful')
                return
            if not self.register_images(self.xz_scan['scaled_image'], self.scan_regions[selected_region]['xz']['scaled_image'], self.xz_scan['scaled_scale']):
                return
            vertical_offset = self.suggested_translation['row']
            if abs(vertical_offset) > self.config.ACCEPTABLE_REALIGNMENT_OFFSET:
                self.printc('Realignment was not successful {0}'.format(vertical_offset))
                return
            self.printc('Vertical offset {0}' .format(vertical_offset))
        self.parent.update_position_display()
        self.suggested_translation = utils.cr((0, 0))
        self.printc('Move to region complete')

    ################## Experiment control ####################
    def identify_flourescence_intensity_distribution(self):
        '''
        Input parameters:
        - z range
        - max laser power at min/max z
        Performs z linescans at different depths with different laser intensities
        '''
        self.abort_calib = False
        laser_step = 10.0
        #Gather parameters from GUI
        try:
            z_overlap = float(self.parent.scanc())
        except ValueError:
            z_overlap = self.config.DEFAULT_Z_SCAN_OVERLAP
        try:
            z_top, z_bottom = map(float, str(self.parent.main_widget.experiment_control_groupbox.objective_positions_combobox.currentText()).split(','))
        except ValueError:
            z_top = 0
            z_bottom = float(str(self.parent.main_widget.experiment_control_groupbox.objective_positions_combobox.currentText()))
        if z_top < z_bottom:
            self.printc('z bottom must be deeper than z top')
            return
        try:
            max_laser_z_top, max_laser_z_bottom =  map(float, str(self.parent.main_widget.experiment_control_groupbox.laser_intensities_combobox.currentText()).split(','))
        except ValueError:
            max_laser_z_top, max_laser_z_bottom = (30, 50)
        if max_laser_z_top > max_laser_z_bottom:
            self.printc('Laser intensity shall increase with depth')
            return
        tag = int(time.time())
        image_dir = os.path.join(self.config.EXPERIMENT_DATA_PATH, 'vs{0}'.format(tag))
        os.mkdir(image_dir)
        #Calculate objective positions and laser intensities
        z_step = self.config.MES_Z_SCAN_SCOPE - z_overlap
        objective_positions = (z_top - 0.5 * self.config.MES_Z_SCAN_SCOPE - numpy.arange((z_top - z_bottom) / z_step) * z_step).tolist()
        max_laser_intensities = numpy.linspace(max_laser_z_top, max_laser_z_bottom, len(objective_positions))
        calibration_parameters = []
        for i in range(len(objective_positions)):
            max_laser_value_index =  int(max_laser_intensities[i]/laser_step)+1
            min_laser_value_index = max_laser_value_index - 2
            if min_laser_value_index <= 0:
                min_laser_value_index = 1
            calibration_parameters.append({'objective_position' : objective_positions[i], 'laser_intensity': numpy.arange(min_laser_value_index,max_laser_value_index) * laser_step})

        #Execute calibration process
        xz_scans = []
        for i1 in range(len(calibration_parameters)):
            if self.abort_calib:
                break
            if not self.mes_interface.set_objective(calibration_parameters[i1]['objective_position'], self.config.MES_TIMEOUT):
                self.printc('MES does not respond')
                return
            else:
                for laser_intensity in calibration_parameters[i1]['laser_intensity']:
                    if self.abort_calib:
                        break
                    #Adjust laser
                    result, adjusted_laser_intensity = self.mes_interface.set_laser_intensity(laser_intensity)
                    if not result:
                        self.printc('Setting laser intensity did not succeed')
                        return
                    self.printc('Objective: {0} um, laser: {1} %'.format(calibration_parameters[i1]['objective_position'], laser_intensity))
                    #Vertical scan
                    xz_scan,  result = self.mes_interface.vertical_line_scan()
                    if not result:
                        self.printc('Vertical scan did not succeed')
                        return
                    xz_scan['laser_intensity'] = laser_intensity
                    xz_scan['objective_position'] = calibration_parameters[i1]['objective_position']
                    xz_scans.append(xz_scan)
                    self.files_to_delete.append(xz_scan['path'])
                    self.show_image(xz_scan['scaled_image'], 2, xz_scan['scaled_scale'], origin = xz_scan['origin'])
                    imaged.imshow(xz_scan['scaled_image'], save=os.path.join(image_dir, 'xz_scan-{2}-{0}-{1}.png'.format(int(laser_intensity), int(calibration_parameters[i1]['objective_position']), tag)))
        self.save_context()
        #Save results to mouse file
        mouse_file_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, str(self.parent.main_widget.scan_region_groupbox.select_mouse_file.currentText()))
        #TMP:
        mouse_file_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, 'xz_scans-{0}.hdf5'.format(tag))
        self.save2mouse_file('intensity_calibration_data')
        self.printc('Done')

    def stop_experiment(self):
        command = 'SOCabort_experimentEOCguiEOP'
        self.queues['stim']['out'].put(command)
        self.printc('Stopping experiment requested, please wait')
        self.parent.main_widget.experiment_control_groupbox.start_experiment_button.setEnabled(True)
        self.parent.main_widget.experiment_control_groupbox.experiment_progress.setValue(0)

    def graceful_stop_experiment(self):
        command = 'SOCgraceful_stop_experimentEOCguiEOP'
        self.queues['stim']['out'].put(command)
        self.printc('Graceful stop requested, please wait')

    def start_experiment(self):
        self.printc('Experiment started, please wait')
        self.experiment_parameters = {}
        if hasattr(self, 'mouse_file'):
            self.experiment_parameters['mouse_file'] = os.path.split(self.mouse_file)[1]
        region_name = self.parent.get_current_region_name()
        if len(region_name)>0:
            self.experiment_parameters['region_name'] = region_name
        objective_range_string = str(self.parent.main_widget.experiment_control_groupbox.objective_positions_combobox.currentText())
        if len(objective_range_string)>0:
            objective_positions = map(float, objective_range_string.split(','))
            if len(objective_positions) != 3:
                self.printc('Objective range is not in correct format')
                return
            if objective_positions[0] > objective_positions[1]:
                reverse = True
                tmp = objective_positions[0]
                objective_positions[0] = objective_positions[1]
                objective_positions[1] = tmp
            else:
                reverse = False
            objective_positions[1] += objective_positions[2]
            self.experiment_parameters['objective_positions'] = numpy.arange(*objective_positions)
            self.experiment_parameters['number_of_depths'] = self.experiment_parameters['objective_positions'].shape[0]
            if reverse:
                self.experiment_parameters['objective_positions'] = self.experiment_parameters['objective_positions'].tolist()
                self.experiment_parameters['objective_positions'].reverse()
                self.experiment_parameters['objective_positions'] = numpy.array(self.experiment_parameters['objective_positions'])
            self.experiment_parameters['current_objective_position_index'] = 0
        laser_intensities_string =  str(self.parent.main_widget.experiment_control_groupbox.laser_intensities_combobox.currentText())
        if len(laser_intensities_string) > 0:
            self.experiment_parameters['laser_intensities'] = map(float, laser_intensities_string.replace(' ', '').split(','))
            if len(self.experiment_parameters['laser_intensities']) != 2:
                self.printc('Laser intensity range is not in correct format')
                return
            self.experiment_parameters['laser_intensities'] = numpy.linspace(self.experiment_parameters['laser_intensities'][0],
                                                                                            self.experiment_parameters['laser_intensities'][1], 
                                                                                            self.experiment_parameters['number_of_depths'])
            #generic.expspace(self.experiment_parameters['laser_intensities'][0], self.experiment_parameters['laser_intensities'][1],  self.experiment_parameters['objective_positions'].shape[0])
        if self.parent.main_widget.experiment_control_groupbox.enable_intrinsic.input.checkState() ==2:
            self.experiment_parameters['enable_intrinsic'] = True
        else:
            self.experiment_parameters['enable_intrinsic'] = False
        #Set back next/prev/redo button texts
        self.parent.main_widget.experiment_control_groupbox.next_depth_button.setText('Next')
        self.parent.main_widget.experiment_control_groupbox.previous_depth_button.setText('Prev')
        self.parent.main_widget.experiment_control_groupbox.redo_depth_button.setText('Redo')
        #Start experiment batch
        self.generate_experiment_start_command()

    def generate_experiment_start_command(self):
        #Ensure that user can switch between different stimulations during the experiment batch
        self.experiment_parameters['experiment_config'] = str(self.parent.main_widget.experiment_control_groupbox.experiment_name.currentText())
        self.experiment_parameters['scan_mode'] = str(self.parent.main_widget.experiment_control_groupbox.scan_mode.currentText())
        self.experiment_parameters['id'] = str(int(time.time()))
        if self.experiment_parameters.has_key('current_objective_position_index') and self.experiment_parameters.has_key('objective_positions'):
            self.experiment_parameters['objective_position'] = self.experiment_parameters['objective_positions'][self.experiment_parameters['current_objective_position_index']]
            objective_position = self.experiment_parameters['objective_position']
            self.parent.main_widget.experiment_control_groupbox.redo_depth_button.setText('Redo {0} um'.format(objective_position))
            #Update redo and next buttons
            time.sleep(0.2)
            if self.experiment_parameters['current_objective_position_index']+1 < self.experiment_parameters['objective_positions'].shape[0]:
                objective_position = self.experiment_parameters['objective_positions'][self.experiment_parameters['current_objective_position_index']+1]
                self.parent.main_widget.experiment_control_groupbox.next_depth_button.setText('Next {0} um'.format(objective_position))
            if self.experiment_parameters['current_objective_position_index'] > 0:
                objective_position = self.experiment_parameters['objective_positions'][self.experiment_parameters['current_objective_position_index']-1]
                self.parent.main_widget.experiment_control_groupbox.previous_depth_button.setText('Prev {0} um'.format(objective_position))
        if self.experiment_parameters.has_key('current_objective_position_index') and self.experiment_parameters.has_key('laser_intensities'):
            self.experiment_parameters['laser_intensity'] = self.experiment_parameters['laser_intensities'][self.experiment_parameters['current_objective_position_index']]
        #generate parameter file
        parameter_file = os.path.join(self.config.EXPERIMENT_DATA_PATH, self.experiment_parameters['id']+'.hdf5')
        if os.path.exists(parameter_file):
            time.sleep(1.1)
            self.experiment_parameters['id'] = str(int(time.time()))
            parameter_file = os.path.join(self.config.EXPERIMENT_DATA_PATH, self.experiment_parameters['id']+'.hdf5')
            if os.path.exists(parameter_file):
                self.printc('Experiment ID already exists')
                return
        tmp_path = fileop.get_tmp_file('hdf5', 0.3)
        h = hdf5io.Hdf5io(tmp_path, filelocking=self.config.ENABLE_HDF5_FILELOCKING)
        fields_to_save = ['parameters']
        h.parameters = copy.deepcopy(self.experiment_parameters)
        if h.parameters.has_key('laser_intensities'):
            del h.parameters['laser_intensities']
        if h.parameters.has_key('objective_positions'):
            del h.parameters['objective_positions']
        if self.experiment_parameters.has_key('region_name') and not self.experiment_parameters['enable_intrinsic']:
            h.xy_scan_parameters = copy.deepcopy(self.scan_regions[self.experiment_parameters['region_name']]['xy_scan_parameters'])
            fields_to_save.append('xy_scan_parameters')
        if hasattr(self, 'animal_parameters'):
            h.animal_parameters = copy.deepcopy(self.animal_parameters)
            fields_to_save.append('animal_parameters')
        if hasattr(self, 'anesthesia_history'):
            h.anesthesia_history = copy.deepcopy(self.anesthesia_history)
            fields_to_save.append('anesthesia_history')
        if self.experiment_parameters['scan_mode'] == 'xz':
            h.xz_config = copy.deepcopy(self.xz_config)
            h.rois = copy.deepcopy(self.rois)
            h.roi_locations = copy.deepcopy(self.roi_locations)
            fields_to_save += ['xz_config', 'rois', 'roi_locations']
        h.save(fields_to_save)
        h.close()
        time.sleep(0.3)
        shutil.copy(tmp_path, parameter_file)
        self.printc('{0} parameter file generated'.format(self.experiment_parameters['id']))
        command = 'SOCexecute_experimentEOCid={0},experiment_config={1}EOP' .format(self.experiment_parameters['id'], self.experiment_parameters['experiment_config'])
        self.queues['stim']['out'].put(command)
        os.remove(tmp_path)

    def previous_experiment(self):
        if self.experiment_parameters.has_key('current_objective_position_index') and \
            self.experiment_parameters['current_objective_position_index'] > 0:
            self.experiment_parameters['current_objective_position_index'] -= 1
            self.generate_experiment_start_command()

    def redo_experiment(self):
        self.generate_experiment_start_command()

    def next_experiment(self):
        if self.experiment_parameters.has_key('current_objective_position_index'):
            self.experiment_parameters['current_objective_position_index'] += 1
            if self.experiment_parameters['current_objective_position_index'] < self.experiment_parameters['objective_positions'].shape[0]:
                self.generate_experiment_start_command()

    ############ 3d scan test ###############
    def show_rc_scan_results(self):
        import pylab as p
        import mpl_toolkits.mplot3d.axes3d as p3
        if hasattr(self, 'scanned_trajectory'):
            scanned_trajectory = self.scanned_trajectory[-1]
            undersample = 10
            x = scanned_trajectory['x'][::undersample]
            y = scanned_trajectory['y'][::undersample]
            z = scanned_trajectory['z'][::undersample]
            fig=p.figure(1)
            ax = p3.Axes3D(fig)
            ax.scatter(x, y, z,  s=4)
            p.figure(2)
            p.plot(scanned_trajectory['masked_line'][::undersample])
            p.plot(scanned_trajectory['roi'][::undersample])
            p.show()
            
    def camera_test(self):
        self.mes_interface.acquire_video(float(str(self.parent.scanc())), 5)

    ########### Network debugger tools #################
    def send_command(self):
        connection = str(self.parent.helpers_widget.select_connection_list.currentText())
        if self.queues.has_key(connection):
            self.queues[connection]['out'].put(self.parent.scanc())
        else:
            self.printc('Connection not selected')

    def show_connected_clients(self):
        connection_status = self.command_relay_server.get_connection_status()
        connected = []
        for k, v in connection_status.items():
            if v:
                connected.append(k)
        connected.sort()
        connected = str(connected).replace('[','').replace(']', '').replace('\'','').replace(',','\n')
        self.printc(connected)
        self.printc('\n')

    def show_network_messages(self):
        network_messages = self.command_relay_server.get_debug_info()
        for network_message in network_messages:
            endpoint_name = network_message[1].split(' ')
            endpoint_name = (endpoint_name[1] + '/' + endpoint_name[3]).replace(',','')
            message = network_message[1].split('port')[1].split(': ', 1)[1]
            displayable_message = network_message[0] + ' ' + endpoint_name + '>> ' + message
            self.printc(displayable_message)
        self.printc('\n')

    def update_network_connection_status(self):
        #Check for network connection status
        if hasattr(self.parent, 'common_widget') and hasattr(self.command_relay_server, 'servers'):
            connection_status = self.command_relay_server.get_connection_status()
            connected = ''
            n_connected = 0
            if connection_status['STIM_MES/MES'] and connection_status['STIM_MES/STIM']:
                connected += 'STIM-MES  '
                n_connected += 1
            if connection_status['GUI_MES/MES'] and connection_status['GUI_MES/GUI']:
                connected += 'MES  '
                n_connected += 1
            if connection_status['GUI_STIM/STIM'] and connection_status['GUI_STIM/GUI']:
                connected += 'STIM  '
                n_connected += 1
            if connection_status['GUI_ANALYSIS/ANALYSIS'] and connection_status['GUI_ANALYSIS/GUI']:
                connected += 'ANALYSIS  '
                n_connected += 1
            n_connections = len(self.config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'].keys())
            connected = 'Alive connections ({0}/{1}): '.format(n_connected, n_connections) + connected
            self.parent.common_widget.connected_clients_label.setText(connected)

    ################ Helper functions ###################
    def show_help(self):
        if webbrowser.open_new_tab(self.config.MANUAL_URL):
            self.printc('Shown in default webbrowser')

    def add_simulated_measurement_file(self):
        self.clear_analysis_status()
        commands = []
        for path in fileop.listdir_fullpath(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'simulated_data')):
            if '.hdf5' in path:
                h = hdf5io.Hdf5io(path, filelocking=self.config.ENABLE_HDF5_FILELOCKING)
                h.load('call_parameters')
                h.call_parameters['mouse_file'] = os.path.split(self.mouse_file)[1]
                h.save('call_parameters', overwrite = True)
                h.close()
            target_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, os.path.split(path)[1])
            if os.path.exists(target_path):
                os.remove(target_path)
            shutil.copyfile(path, target_path)
            if '.hdf5' in path:
                commands.append('SOCmeasurement_readyEOC{0}EOP'.format(fileop.parse_fragment_filename(path)['id']))
                self.printc('Simulated file copied: {0}'.format(path))
        time.sleep(1.0)
        for command in commands:
            self.queues['stim']['in'].put(command)
        self.queues['analysis']['out'].put('SOCclear_joblistEOCEOP')
        self.printc('Done')

    def save_xy_scan_to_file(self):
        hdf5_handler = hdf5io.Hdf5io(fileop.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'xy_scan.hdf5')), filelocking=self.config.ENABLE_HDF5_FILELOCKING)
        hdf5_handler.xy_scan = self.xy_scan
        hdf5_handler.stage_position = self.stage_position
        hdf5_handler.save(['xy_scan', 'stage_position'])
        hdf5_handler.close()

    ############# Helpers #############
    def generate_job_list(self, mouse_file = None, tag = None):
        result = False
        if not hasattr(self, 'mouse_file'):
            return result
        if mouse_file is None:
            mouse_file = self.mouse_file
        if tag is None:
            tag = 'copy'
        copy_path = mouse_file.replace('.hdf5', '_' +tag+'.hdf5')
        try:
            if os.path.exists(mouse_file) and os.path.isfile(mouse_file):
                if 'jobhandler' in tag:#Stim uses other nodes of mouse file
                    h1=hdf5io.Hdf5io(copy_path, filelocking=self.config.ENABLE_HDF5_FILELOCKING)
                    h1.scan_regions = {}
                    region_name = self.parent.get_current_region_name()
                    sr = copy.deepcopy(self.scan_regions)
                    #Wipe out unnecessary data
                    h1.process_list = {}
                    for region_name, analysis_status_list_in_region in self.analysis_status.items():
                            for id, measurement in analysis_status_list_in_region.items():
                                if not measurement['fragment_check_ready'] or not measurement['mesextractor_ready'] or not measurement['find_cells_ready']:
                                    entry = copy.deepcopy(measurement)
                                    del entry['info']
                                    h1.process_list[id] = entry
                    h1.save('process_list', overwrite=True)
                    h1.close()
                result = True
        except:
            self.printc(traceback.format_exc())
        time.sleep(0.2)#Wait to make sure that file is completely copied
        return result

    def create_parameterfile_from_region_info(self, parameter_file_path, scan_type):
        selected_region = self.parent.get_current_region_name()
        if not self.scan_regions.has_key(selected_region):
            self.printc('Selected region does not exists')
            return False
        if not self.scan_regions[selected_region].has_key(scan_type):
            self.printc('Parameters for {0} does not exists' .format(scan_type))
            return False
        self.scan_regions[selected_region][scan_type]['mes_parameters'].tofile(parameter_file_path)
        if not os.path.exists(parameter_file_path):
            self.printc('Parameter file not created')
            return False
        else:
            return True

    def create_image_registration_data_file(self, f1, f2):
        image_hdf5_handler = hdf5io.Hdf5io(os.path.join(self.config.CONTEXT_PATH, 'image.hdf5'), filelocking=self.config.ENABLE_HDF5_FILELOCKING)
        image_hdf5_handler.f1 = f1
        image_hdf5_handler.f2 = f2
        image_hdf5_handler.save(['f1', 'f2'], overwrite = True)
        image_hdf5_handler.close()

    def cutout_subimage(self, image, box, scale, origin):
        upper_leftx = int((box[0] - origin['col'])/scale['col'])
        upper_lefty = int((box[1] - origin['row'])/scale['row'])
        bottom_rightx = int((box[2] - origin['col'])/scale['col'])
        bottom_righty = int((box[3] - origin['row'])/scale['row'])
        subimage = image[upper_lefty:bottom_righty, upper_leftx:bottom_rightx]
        if any(subimage.shape) < 128:
            new_size = []
            for i in range(2):
                if subimage.shape[i] < 128:
                    s = 128
                else:
                    s = subimage.shape[i]
                new_size.append(s)
            extended_image = numpy.zeros(new_size, dtype = subimage.dtype)
            extended_image[0:subimage.shape[0], 0: subimage.shape[1]]= subimage
            subimage = extended_image
        return subimage

    def register(self):
        self.register_images(self.xy_scan[self.config.DEFAULT_PMT_CHANNEL], self.scan_regions[self.parent.get_current_region_name()]['xy']['image'], self.xy_scan['scale'], self.xy_scan['origin'])

    def register_images(self, f1, f2, scale, origin = None, print_result = True):
        box = self.parent.get_subimage_box()
        if not origin is None and len(box) ==4:
            f1 = self.cutout_subimage(f1, box, scale, origin)
            f2 = self.cutout_subimage(f2, box, scale, origin)
            if False:
                try:
                    import Image
                except ImportError:
                    from PIL import Image
                from visexpA.engine.dataprocessors import generic
                Image.fromarray(generic.normalize(f1,  numpy.uint8)).save(fileop.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'f1.png')))
                Image.fromarray(generic.normalize(f2,  numpy.uint8)).save(fileop.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'f2.png')))
        self.create_image_registration_data_file(f1, f2)
        utils.empty_queue(self.queues['analysis']['in'])
        arguments = ''
        self.queues['analysis']['out'].put('SOCregisterEOC' + arguments + 'EOP')
        if not utils.wait_data_appear_in_queue(self.queues['analysis']['in'], 15.0):
            self.printc('Analysis not connected')
            return False
        messages_to_put_back = []
        p = self.queues['analysis']['in'].get()
        if 'SOCregisterEOCstartedEOP' not in p:
            self.printc('Image registration did not start,{0}'.format(p))
            messages_to_put_back.append(p)
            return False
        mouse_file_copy_requested = False
        if utils.wait_data_appear_in_queue(self.queues['analysis']['in'], timeout = self.config.MAX_REGISTRATION_TIME):#TODO: the content of the queue also need to be checked
            while not self.queues['analysis']['in'].empty():
                    response = self.queues['analysis']['in'].get()
                    if 'SOCmouse_file_copyEOCjobhandlerEOP' in response:
                        response = response.replace('SOCmouse_file_copyEOCjobhandlerEOP', '')
                        mouse_file_copy_requested = True
                    if 'error' in response:
                        self.printc('Image registration resulted error')
                        return False
                    elif 'register' in response and not 'started' in response:
                        self.registration_result = self.parse_list_response(response) #rotation in angle, center or rotation, translation
                        self.suggested_translation = utils.cr(utils.nd(scale) * self.registration_result[-2:]*numpy.array([-1, 1]))
                        if print_result:
                            self.printc('Suggested translation: {0:.2f}, {1:.2f}'.format(-self.suggested_translation['row'][0], -self.suggested_translation['col'][0]))
                        return True
                    else:
                        messages_to_put_back.append(response)
            for msg in messages_to_put_back:
                self.queues['analysis']['in'].put(msg)
        else:
            self.printc('Analysis does not respond')
        if mouse_file_copy_requested:
            self.queues['analysis']['in'].put('SOCmouse_file_copyEOCjobhandlerEOP')
        return False

    def parse_list_response(self, response):
        return numpy.array(map(float,parameter_extract.findall( response)[0].split(',')))

    def has_master_position(self, scan_regions):
        master_position_exists = False
        for saved_region_name in scan_regions.keys():
            if 'master' in saved_region_name or '0_0' in saved_region_name:
                master_position_exists = True
                break
        return master_position_exists

    def get_master_position_name(self, scan_regions):
        master_position_name = ''
        for saved_region_name in scan_regions.keys():
            if 'master' in saved_region_name or '0_0' in saved_region_name:
                master_position_name = saved_region_name
                break
        return master_position_name

    def generate_animal_filename(self, tag, animal_parameters, extension = 'hdf5'):
        name = '{5}_{7}_{0}_{1}_{2}_{3}_{4}.{6}' .format(animal_parameters['strain'], animal_parameters['mouse_birth_date'] , animal_parameters['gcamp_injection_date'], \
                                         animal_parameters['ear_punch_l'], animal_parameters['ear_punch_r'], tag, extension, animal_parameters['id'])
        return name

    def ask4confirmation(self, action2confirm):
        self.emit(QtCore.SIGNAL('ask4confirmation'), action2confirm)
        while self.gui_thread_queue.empty() :
            time.sleep(0.1) 
        return self.gui_thread_queue.get()

    def save2mouse_file(self, fields, wait_save = False, region_name = None):
#        #Wait till mouse file handler finishes with copying data fields
#        while self.parent.mouse_file_handler.lock:
#            pass
        if not isinstance(fields, list):
            fields = [fields]
        #create copy of saveable data in mouse file handler
        for field in fields:
            field_value = copy.deepcopy(getattr(self, field))
            if field == 'cells':
                cells_pickled_ready = self.cells2pickled_ready(field_value)
                if region_name is None:
                    for k,v in cells_pickled_ready.items():
                        self.queues['mouse_file_handler'].put(['cells_' + k, utils.object2array(v)])
                else:
                    self.queues['mouse_file_handler'].put(['cells_' + region_name, utils.object2array(cells_pickled_ready[region_name])])
            else:
                self.queues['mouse_file_handler'].put([field, field_value])
        self.mouse_file_saver()
        if wait_save:
            self.wait_mouse_file_save()

    def wait_mouse_file_save(self):
        if hasattr(self.parent, 'mouse_file_handler'):
            while self.parent.mouse_file_handler.running:
                    time.sleep(0.1)

    def mouse_file_saver(self):
        if hasattr(self, 'mouse_file') and os.path.exists(self.mouse_file) and utils.safe_has_key(self.queues, 'mouse_file_handler') and not self.queues['mouse_file_handler'].empty():
            self.running = True
            h = hdf5io.Hdf5io(self.mouse_file, filelocking=self.config.ENABLE_HDF5_FILELOCKING)
            field_names_to_save = []
#            with introspect.Timer('save time'):
            if True:
                while not self.queues['mouse_file_handler'].empty():
                    field_name, field_value = self.queues['mouse_file_handler'].get()
                    setattr(h, field_name, field_value)
                    if not field_name in field_names_to_save:
                        field_names_to_save.append(field_name)
                h.save(field_names_to_save, overwrite = True)
            h.close()
            self.running = False
            self.printc('{0} saved to mouse file'.format(', '.join(field_names_to_save)))

    def cells2pickled_ready(self, cells):
        '''
        This is a workaround for a couple of compatibility problems between pickle and hdf5io
        '''
        for sr in cells.values():
            for cell in sr.values():
                if cell['group'] == '':
                    cell['group'] = 'none'
                cell['roi_center'] = utils.rcd((cell['roi_center']['row'], cell['roi_center']['col'], cell['roi_center']['depth']))
        return cells

class MouseFileHandler(Poller):
    '''
    Performs all write operations to the moouse file, ensuring that this time consuming procedure does not increase
    main poller's response time.
    '''
    def __init__(self, parent):
        Poller.__init__(self, parent)
        self.running = False

    def handle_commands(self):
        '''
        Receives commands from main poller to save data to mouse file
        '''
        if hasattr(self.parent.poller, 'mouse_file') and os.path.exists(self.parent.poller.mouse_file) and utils.safe_has_key(self.parent.queues, 'mouse_file_handler') and not self.parent.queues['mouse_file_handler'].empty():
            self.running = True
            h = hdf5io.Hdf5io(self.parent.poller.mouse_file, filelocking=self.config.ENABLE_HDF5_FILELOCKING)
            field_names_to_save = []
            while not self.parent.queues['mouse_file_handler'].empty():
                field_name, field_value = self.parent.queues['mouse_file_handler'].get()
                if field_name == 'animal_parameters':
                    field_name += str(int(time.time()))
#                if field_name == 'cells':
#                    field_value = utils.object2array(self.cells2pickled_ready(field_value))
                setattr(h, field_name, field_value)
                if not field_name in field_names_to_save:
                    field_names_to_save.append(field_name)
#            try:
#                field_names_to_save.remove('roi_curves')
#            except:
#                pass
            for f in field_names_to_save:
                print f
                h.save(f, overwrite = True)
            h.close()
            self.running = False
            self.printc('{0} saved to mouse file'.format(', '.join(field_names_to_save)))
        else:
            time.sleep(1.0)

    def cells2pickled_ready(self, cells):
        '''
        This is a workaround for a couple of compatibility problems between pickle and hdf5io
        '''
        for sr in cells.values():
            for cell in sr.values():
                if cell['group'] == '':
                    cell['group'] = 'none'
                cell['roi_center'] = utils.rcd((cell['roi_center']['row'], cell['roi_center']['col'], cell['roi_center']['depth']))
        return cells

def update_mouse_files_list(config, current_mouse_files = []):
    new_mouse_files = fileop.filtered_file_list(config.EXPERIMENT_DATA_PATH,  ['mouse', 'hdf5'], filter_condition = 'and')
    new_mouse_files = [mouse_file for mouse_file in new_mouse_files if '_jobhandler' not in mouse_file and '_stim' not in mouse_file and '_copy' not in mouse_file and os.path.isfile(os.path.join(config.EXPERIMENT_DATA_PATH,mouse_file))]
    if current_mouse_files != new_mouse_files:
        are_new_files = True
    else:
        are_new_files = False
    return are_new_files, new_mouse_files
    
class BehavioralTesterPoller(Poller):
    def __init__(self, parent, config):
        from visexpman.engine.hardware_interface import digital_io
        Poller.__init__(self, parent)
        self.recording = []
        self.timeseries = []
        self.path = fileop.generate_filename(os.path.join(self.config.LOG_PATH, 'recording.txt'))
        try:
            self.pi = digital_io.Photointerrupter(config)
            self.pi.start()
        except:
            pass
        if hasattr(self.config, 'VALVE_COMPORT'):
            import serial
            self.valve_serialport = serial.Serial(self.config.VALVE_COMPORT)
            self.close_valve()

    def periodic(self):
        if hasattr(self, 'pi') and not self.pi.queues['0'].empty():
            self.printc('{0}'.format(self.pi.queues['0'].get()))
    
    def open_valve_for_a_time(self):
        try:
            open_time = float(self.parent.open_valve_for_a_time.input.input.text())
            self.open_valve()
            time.sleep(1e-3*open_time)
            self.close_valve()
            self.printc('Valve opened for {} ms'.format(open_time))
        except ValueError:
            self.printc('Provide numeric value as value open time')
        
        
            
    def open_valve(self):
        self.valve_serialport.setRTS(True)
        self.printc('Valve opened')
        
    def close_valve(self):
        self.valve_serialport.setRTS(False)
        self.printc('Valve closed')

    def close(self):
        if hasattr(self, 'valve_serialport'):
            self.valve_serialport.close()
        if hasattr(self, 'pi'):
            self.pi.command_queue.put('TERMINATE')
            self.pi.join()

class FlowmeterPoller(flowmeter.Flowmeter, Poller):
    def __init__(self, parent, config):
        Poller.__init__(self, parent)
        flowmeter.Flowmeter.__init__(self, config)
        self.recording = []
        self.timeseries = []
        self.path = fileop.generate_filename(os.path.join(self.config.LOG_PATH, 'recording.txt'))
        self.file = open(self.path, 'at')
        self.file.write('time[s]\tflow rate[ul/min\n')
        self.last_file_write = time.time()
        self.last_flowrate_check = time.time()

    def periodic(self):
        #Update status
        if self.running:
            status = 'running'
        elif self.init_ready:
            status = 'initialized'
        else:
            status = 'not initialized' 
        data = self.read(self.config.GUI['GUI_REFRESH_PERIOD'] * 7)
        if not data[0]:
            self.parent.update_status(status)
        else:
            self.parent.update_status(status, data[1][0])
            recording_chunk = data[1]
            timeseries_chunk = numpy.arange(len(self.recording), len(self.recording) + data[1].shape[0], dtype = numpy.float) / self.config.FLOWMETER['SAMPLING_RATE']
            rec_str = ''
            for i in range(recording_chunk.shape[0]):
                rec_str += '{0}\t{1:2.2f}\n'.format(timeseries_chunk[i], recording_chunk[i])
            self.file.write(rec_str)
            now = time.time()
            if now - self.last_file_write > self.config.FILEWRITE_PERIOD:
                self.file.flush()
                self.last_file_write = now
            self.recording.extend(data[1].tolist())
            if now - self.last_flowrate_check > self.config.FLOW_STUCKED_CHECK_PERIOD:
                self.last_flowrate_check = now
                if abs(data[1]).mean() < self.config.FLOW_STUCKED_LIMIT:
                    self.printc('Low flowrate')
                if hasattr(winsound, 'PlaySound'):
                    #Sound alarm
                    winsound.PlaySound('SystemHand',winsound.SND_ALIAS)

    def close(self):
        self.stop_measurement()
        self.file.close()
        
class CaImagingPoller(Poller):
    def __init__(self, parent):
        Poller.__init__(self, parent)
        self.config = parent.config
        from multiprocessing import Queue, Process
        self.queues = {'in':Queue(), 'out':Queue(), 'parameters': Queue(), 'data': Queue(), 'frame': Queue(),  'udp': Queue()}
        self.process = Process(target=scanner_control.two_photon_scanner_process,  args = (self.config, self.queues))
        self.process.start()
        self.init_variables()
        self.load_context()
        self.init_network()
                
    def init_network(self):
        self.connections = {}
        self.queues['gui'] = {}
        self.queues['gui']['out'] = Queue.Queue()
        self.queues['gui']['in'] = Queue.Queue()
        self.connections['gui'] = network_interface.start_client(self.config, 'IMAGING', 'GUI_IMAGING', self.queues['gui']['in'], self.queues['gui']['out'])
        self.queues['stim'] = {}
        self.queues['stim']['out'] = Queue.Queue()
        self.queues['stim']['in'] = Queue.Queue()
        self.connections['stim'] = network_interface.start_client(self.config, 'IMAGING', 'STIM_IMAGING', self.queues['stim']['in'], self.queues['stim']['out'])

    def periodic(self):
        if self.scan_run and self.scan_start_time is not None:
            self.update_status(scan_is_running_for = (numpy.round(time.time() - self.scan_start_time),  's'))
        else:
            self.update_status(scan_is_running_for = (0,  's'))
        
    def run_in_all_iterations(self):
        self.udp_handler()
        try:
            self.frame_update()
        except:
            self.printc(traceback.format_exc())
            
    def handle_commands(self):
        if not self.queues['in'].empty():
            message_raw = self.queues['in'].get()
            message = message_raw.split(',')
            method = message[0]
            if len(message)>0:
                arguments = message[1:]
            else:
                arguments = []
            if hasattr(self, method) and callable(getattr(self, method)) and not hasattr(getattr(self, method), 'emit'):
                try:
                    getattr(self, method)()
                except:
                    self.printc(traceback.format_exc())
            else:
                self.printc(message_raw)
        try:
            for k, queue in self.queues.items():                
                if hasattr(queue, 'has_key') and queue.has_key('in') and not queue['in'].empty():
                    messages = queue['in'].get()
                    if 'EOPSOC' in messages:
                        messages = messages.replace('EOPSOC','EOP@@@SOC').split('@@@')
                    else:
                        messages = [messages]
                    for message in messages:
                        command = command_extract.findall(message)
                        if len(command) > 0:
                            command = command[0]
                        parameter = parameter_extract.findall(message)
                        if len(parameter) > 0:
                            parameter = parameter[0]
                        if command == 'connection':
                            message = command
                        elif command == 'start_experiment':
                            self.start_experiment(id = parameter.split('=')[1])
                        elif message == 'connected to server':
                            #This is sent by the local queued client and its meaning can be confusing, therefore not shown
                            message = ''
                        elif isinstance(command, str) and hasattr(self, command):
                            getattr(self, command)()
#                        else:
#                            self.printc(k.upper() + ' '  +  message)
        except:
            self.printc(traceback.format_exc())

    def connect_signals(self):
        Poller.connect_signals(self)
        self.parent.connect(self, QtCore.SIGNAL('show_image'), self.parent.show_image)
        self.parent.connect(self, QtCore.SIGNAL('update_scan_run_status'), self.parent.update_scan_run_status)
        self.parent.connect(self, QtCore.SIGNAL('plot_calibdata'), self.parent.plot_calibdata)
        self.parent.connect(self, QtCore.SIGNAL('plot_histogram'), self.parent.plot_histogram)
                
    def load_context(self):
        if os.path.exists(self.config.CONTEXT_FILE):
            context_hdf5 = hdf5io.Hdf5io(self.config.CONTEXT_FILE, filelocking=self.config.ENABLE_HDF5_FILELOCKING)
            self.load_widget_context(context_hdf5)
            for node in self.context_nodes:
                context_hdf5.load(node)
                if hasattr(context_hdf5, node):
                    setattr(self,  node, copy.deepcopy(getattr(context_hdf5, node)))
            context_hdf5.close()
        
    def load_widget_context(self,hdfhandler):
        hdfhandler.load('widget_context')
        if hasattr(hdfhandler, 'widget_context'):
            self.widget_context_values = copy.deepcopy(hdfhandler.widget_context)
            
    def save_context(self):
        h = hdf5io.Hdf5io(self.config.CONTEXT_FILE, filelocking=self.config.ENABLE_HDF5_FILELOCKING)
        for node in self.context_nodes:
            if hasattr(self, node):
                setattr(h,  node, copy.deepcopy(getattr(self, node)))
                h.save(node)
        self.save_widget_context(h)
        h.close()
            
    def save_widget_context(self, hdfhandler):
        if hasattr(self,'widget_context_fields'):
            hdfhandler.widget_context = {}
            for widget_field in self.widget_context_fields:
                ref = introspect.string2objectreference(self, widget_field)
                if hasattr(ref,'checkState'):
                    hdfhandler.widget_context[widget_field] = ref.checkState()
                elif hasattr(ref,'currentText'):
                    hdfhandler.widget_context[widget_field] = str(ref.currentText())
                elif hasattr(ref,'text'):
                    hdfhandler.widget_context[widget_field] = str(ref.text())
                
            hdfhandler.save('widget_context',overwrite = True)
            
    def init_variables(self):
        self.scan_run = False
        self.status = {}
        self.objective_position = 0
        self.scan_start_time = None
        self.widget_context_fields = ['self.parent.central_widget.main_widget.background_scan_parameters.inputs[\'scan_area_size_xy\'].input', 
                                        'self.parent.central_widget.main_widget.background_scan_parameters.inputs[\'scan_area_center_xy\'].input', 
                                        'self.parent.central_widget.main_widget.background_scan_parameters.inputs[\'resolution\'].input', 
                                        'self.parent.central_widget.main_widget.measurement_files.cell_name.input', 
                                        'self.parent.central_widget.main_widget.experiment_control_groupbox.experiment_name', 
                                        'self.parent.central_widget.image_analysis.histogram_range.input', 
                                        'self.parent.central_widget.main_widget.use_user_parameters.input', 
                                        'self.parent.central_widget.main_widget.beamer_control.trigger_delay.input', 
                                        'self.parent.central_widget.main_widget.beamer_control.trigger_pulse_width.input', 
                                        'self.parent.central_widget.main_widget.beamer_control.enable_beamer.input', 
                                        'self.parent.central_widget.calibration_widget.calib_scan_pattern.pattern', 
                                      ]
        for pn in self.parent.central_widget.calibration_widget.parameter_names:
            self.widget_context_fields.append('self.parent.central_widget.calibration_widget.scanner_parameters[\'{0}\'].input'.format(pn))
        for pn in self.parent.central_widget.calibration_widget.calib_scan_pattern.widgets.keys():
            if hasattr(self.parent.central_widget.calibration_widget.calib_scan_pattern.widgets[pn], 'input'):
                self.widget_context_fields.append('self.parent.central_widget.calibration_widget.calib_scan_pattern.widgets[\'{0}\'].input'.format(pn))
        self.context_nodes = ['main_image']
        
    def init_debug(self):
        #Load data from test file
        if os.name != 'nt' and not hasattr(self, 'main_image'):
            return
            from visexpman.users.test import unittest_aggregator
            h = hdf5io.Hdf5io(fileop.filtered_file_list(unittest_aggregator.prepare_test_data('caimaging'), 'hdf5', fullpath = True)[0], filelocking=False)
            img = h.findvar('data')
            img = img.mean(axis=0)
            scan_parameters = h.findvar('scan_parameters')
            h.close()
            if not scan_parameters.has_key('scan_center'):
                scan_parameters['scan_center'] = utils.rc((0,0))
                scan_parameters['resolution'] = 1
            self.main_image = {}
            self.main_image['image'] = img
            self.main_image['resolution'] = utils.rc((scan_parameters['resolution'],  )*2)
            self.main_image['center'] = scan_parameters['scan_center']
            self.update_main_image()
            
    def udp_handler(self):
        if not self.queues['udp'].empty():
            message = self.queues['udp'].get()
            #sec 31.333333 filename 20130423_C1#011_1978KeisukeDS_4dir_S100_C0%speed_300_range_500%_ND0_Ch1W0.phys
            message_chunks = message.split(' ')
            if message_chunks[0] == 'sec' and message_chunks[2] == 'filename':
                duration = float(message_chunks[1])
                measurement_name = message_chunks[3].split('.')[0]
                self.scan(duration=duration, name = measurement_name)

    def update_main_image(self):
        aichannel, self.enabled_channels = self._select_ai_channel()
        if hasattr(self, 'main_image') and self.main_image.has_key('image'):
            self.show_image(self.process_images(self.main_image['image']), self.main_image['resolution'], self.main_image['center'])

    def update_status(self, **kwargs):
        for k,  v in kwargs.items():
            self.status[k] = v
        text = ''
        param_per_line = 4
        ct = 0
        for k, v in self.status.items():
            text += '{0}: {1} {2}\t'.format(k.replace('_', ' ').capitalize(), v[0],  v[1])
            ct += 1
            if ct%param_per_line==0 and  ct != 0:
                text+= '\n'
        self.parent.central_widget.status.setText(text)

    def update_scan_run_status(self, status):
        self.emit(QtCore.SIGNAL('update_scan_run_status'), status)
        
    def show_image(self, image, scale, origin):
        self.emit(QtCore.SIGNAL('show_image'), image, scale, origin)

    def close(self):
        self.queues['out'].put('SOCquitEOCEOP')
#        if self.config.__class__.__name__ == 'CaImagingTestConfig':
#            self.queues['stim']['out'].put('SOCexitEOCEOP')
        for conn_name in self.queues.keys():
            if hasattr(self.queues[conn_name], 'has_key') and self.queues[conn_name].has_key('out'):
                self.queues[conn_name]['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.save_context()
        self.process.join()
        
    ########### Commands #################
    def start_experiment(self,id = None):
        if self.scan_run:
            self.printc('Experiment already running')
            return
        if id is None:
            return
        #Load parameter file
        parameter_file = os.path.join(self.config.EXPERIMENT_DATA_PATH, id+'.hdf5')
        if not os.path.exists(parameter_file):
            self.printc('Parameter file does not exists: {0}'.format(parameter_file))
            return
        h = hdf5io.Hdf5io(parameter_file, filelocking=self.config.ENABLE_HDF5_FILELOCKING)
        h.load('parameters')
        h.close()
        if h.parameters['enable_ca_recording']:
            self.scan(duration = h.parameters['measurement_duration'], id = id, enable_record = True)
        else:
            self.printc('Ca signal recording is disabled')

    def stop_experiment(self):
        if self.scan_run:
            self.printc('Stopping experiment requested, please wait')
            self.queues['out'].put('stop_scan')
            
    def abort_experiment(self):
        self.stop_experiment()
    
    def scan(self, duration=None, nframes=None, name = '', id = None, enable_record = None):
        if self.scan_run:
            self.queues['out'].put('stop_scan')
            self.printc('Scan stop requested')
        else:
            self.update_scan_run_status('prepare')
            self.parameters = {}
            if duration is not None:
                self.parameters['duration'] = duration
            if nframes is not None:
                self.parameters['nframes'] = nframes
            try:
                self.parameters['scan_size'] = utils.cr(stringop.str2params(self.parent.central_widget.main_widget.background_scan_parameters.inputs['scan_area_size_xy'].input.text()))
                self.parameters['scan_center'] = utils.cr(stringop.str2params(self.parent.central_widget.main_widget.background_scan_parameters.inputs['scan_area_center_xy'].input.text()))
                self.parameters['resolution'] = 1.0/float(str(self.parent.central_widget.main_widget.background_scan_parameters.inputs['resolution'].input.text()))
            except:
                self.update_scan_run_status('ready')
                return
            if self.parent.central_widget.main_widget.use_user_parameters.input.checkState() == 2:
                try:
                    self.parameters['SCANNER_SETTING_TIME'] = stringop.str2params(self.parent.central_widget.calibration_widget.scanner_parameters['SCANNER_SETTING_TIME'].input.text())
                    if len(self.parameters['SCANNER_SETTING_TIME']) == 1:
                        self.parameters['SCANNER_SETTING_TIME'] = self.parameters['SCANNER_SETTING_TIME'][0]
                    elif len(self.parameters['SCANNER_SETTING_TIME']) == 0:
                        del self.parameters['SCANNER_SETTING_TIME']
                except ValueError:
                    pass#value from machine config will be used
                for pn in ['SCANNER_START_STOP_TIME', 'AO_SAMPLE_RATE', 'AI_SAMPLE_RATE']:
                    try:
                        self.parameters[pn] = float(str(self.parent.central_widget.calibration_widget.scanner_parameters[pn].input.text()))
                    except ValueError:
                        pass#value from machine config will be used
            if enable_record is None:
                self.parameters['enable_recording'] = False
            else:
                self.parameters['enable_recording'] = enable_record
            #figure out which analog channels need to be sampled
            self.parameters['AI_CHANNEL'], self.enabled_channels = self._select_ai_channel()
            #Read projector trigger config
            if self.parent.central_widget.main_widget.beamer_control.enable_beamer.input.checkState() == 2:
                try:
                    self.parameters['SCANNER_TRIGGER_CONFIG'] = {}
                    self.parameters['SCANNER_TRIGGER_CONFIG']['offset'] = float(str(self.parent.central_widget.main_widget.beamer_control.trigger_delay.input.text()))*1e-6
                    self.parameters['SCANNER_TRIGGER_CONFIG']['width'] = float(str(self.parent.central_widget.main_widget.beamer_control.trigger_pulse_width.input.text()))*1e-6
                    self.parameters['SCANNER_TRIGGER_CONFIG']['amplitude'] = self.config.SCANNER_TRIGGER_CONFIG['amplitude']
                    self.parameters['SCANNER_TRIGGER_CONFIG']['enable'] = True
                except ValueError:
                    pass
            #generate filename/create dirs
            if False:
                folder = os.path.join(self.config.EXPERIMENT_DATA_PATH,  utils.date_string())
                fileop.mkdir_notexists(folder)
            else:
                folder = self.config.EXPERIMENT_DATA_PATH
            if id == None:
                self.id = str(int(time.time()))
            else:
                self.id = id
            filenames = experiment_data.generate_filename(self.config, 
                                                                            self.id, 
                                                                            name.replace('Config', '').replace('config', ''),  
                                                                            end_tag = '_ca',
                                                                            user_extensions = ['tiff'], output_folder = folder)
            self.parameters['filenames'] = filenames
            self.queues['parameters'].put(self.parameters)
            self.queues['out'].put('start_scan')
            self.printc('Scan start requested')
        
    def scan_started(self):
        self.scan_parameters = self.queues['data'].get()
        self.update_status(frame_rate = (numpy.round(self.scan_parameters['frame_rate'], 2),  'Hz'))
        self.printc('Scanner max speeds (x, y): {0}, {1} um/s, scanning speed x axis: {2} um/s,overshoot: {3} um\nimage offset {4}'
                    .format(self.scan_parameters['speeds']['x']['max'], self.scan_parameters['speeds']['y']['max'], self.scan_parameters['speeds']['x']['scan'], self.scan_parameters['overshoot'],
                            self.scan_parameters['image_offset'])
                                                                          )
        self.scan_start_time = time.time()
        self.printc('Scan started')
        self.queues['stim']['out'].put('SOCimaging_startedEOCEOP')
        self.update_scan_run_status('started')
        
    def scan_ready(self):
        self.update_scan_run_status('ready')
        self.scan_parameters = {}
        self.scan_start_time = None
        self.printc('Scan ready')
        self.queues['gui']['out'].put('SOCimaging_finishedEOC{0}EOP'.format(self.id))
        
    def saving_data(self):
        self.printc('Saving data')
        self.update_scan_run_status('saving')
        
    def frame_update(self):
        if not self.queues['frame'].empty() and self.scan_run:
            rawframe = self.queues['frame'].get()
            if self.parent.central_widget.main_widget.enable_image_offset.input.checkState() == 0:
                self.scan_parameters['image_offset'] = 0
            self.current_frame = scanner_control.raw2frame(rawframe, 
                                                                            self.scan_parameters['binning_factor'], 
                                                                            self.scan_parameters['boundaries'], 
                                                                            self.scan_parameters['image_offset'])
            if not hasattr(self, 'main_image'):
                self.main_image={}
            self.main_image['image'] = self.current_frame
            self.main_image['resolution'] = utils.rc((self.parameters['resolution'],  )*2)
            self.main_image['center'] =  self.parameters['scan_center']
            self.update_main_image()
            #Get items from queue to make queue empty
            while not self.queues['frame'].empty():
                self.queues['frame'].get()

    def process_images(self, image):
        '''
        Colors image according to image channels, filtering and histogram transformation applied and sidebar is drawn
        '''
        from visexpA.engine.dataprocessors import generic
        try:
            imout = numpy.zeros((image.shape[0],  image.shape[1],  3))
        except:#TMP, at high frame rates, empty images are tried to display
            self.printc(image.shape)
#            self.printc(image)
            
        for i in range(len(self.enabled_channels)):
            channel_color = [self.config.PMTS[pmtch]['COLOR'] for pmtch in self.config.PMTS.keys() if self.config.PMTS[pmtch]['AI'] == self.enabled_channels[i]][0]
            if len(self.enabled_channels) == 1:
                channel_index = 0
            elif len(self.enabled_channels) == 2:
                channel_index = self.enabled_channels[i]
            if channel_color == 'RED':
                imout[:, :, 0] = self.apply_histogram(self.apply_filters(self.scale_image(image[:, :, channel_index])))
            elif channel_color == 'GREEN':
                imout[:, :, 1] = self.apply_histogram(self.apply_filters(self.scale_image(image[:, :, channel_index])))
                
                channel_index += 1
        imout = numpy.cast['uint8'](255*imout)
        #convert to PIL image
        imout = Image.fromarray(imout)
        #Flip image
        if self.config.CAIMAGE_DISPLAY['VERTICAL_FLIP']:
            imout = imout.transpose(Image.FLIP_TOP_BOTTOM)
        if self.config.CAIMAGE_DISPLAY['HORIZONTAL_FLIP']:
            imout = imout.transpose(Image.FLIP_LEFT_RIGHT)
        imout = numpy.asarray(imout)
        #Draw scalebar
        return imout
        
    def scale_image(self, image):
        '''
        The pmt voltage values are scaled between 0 and self.config.MAX_PMT_VOLTAGE
        '''
        image_scaled = numpy.where(image < 0,  0,  image)
        image_scaled = numpy.where(image_scaled > self.config.MAX_PMT_VOLTAGE, self.config.MAX_PMT_VOLTAGE,  image_scaled)
        image_scaled /= self.config.MAX_PMT_VOLTAGE
        return image_scaled

    def apply_histogram(self, image):
        '''
        Pixels of input image are in the 0...1 range
        '''
        histogram_resolution = 0.01
        histogram_parameters = stringop.str2params(self.parent.central_widget.image_analysis.histogram_range.input.text())
        image_out = image
        if len(histogram_parameters)==3:#Apply histogram
            min,  max,  gamma = histogram_parameters
            try:
#                from visexpman.engine.generic.introspect import Timer
#                with Timer('rt'):
                x = numpy.arange(0.0, 1.0, histogram_resolution)
                lut = utils.generate_lut(x, min, max, gamma)
                apply_lut = scipy.interpolate.interp1d(x, lut, bounds_error  = False, fill_value  = 0.0)
                image_out = apply_lut(image)
            except:
                lut = None
                self.printc(traceback.format_exc())
        else:
            lut = None
        
        #Generate and display hisogram
        hist, bins = numpy.histogram(image,  bins = 1/histogram_resolution)
        #Normalize histogram
        hist = hist/float(image.shape[0]*image.shape[1])
        t = numpy.arange(0.0, 1.0, 1.0/hist.shape[0])
        self.emit(QtCore.SIGNAL('plot_histogram'), t, hist, lut)
        return image_out
        
    def apply_filters(self, image):
        return image
        
    ######### Snap one image ################
    def snap(self):
        self.scan(nframes=1)
        
    def snap1(self):#For calibration purposes
        self.scan(nframes=10)
        
    ######### Calibration related #############
    def calib(self):
        if self.scan_run:
            self.queues['out'].put('stop_scan')
            self.printc('Scan stop requested')
        else:
            self.update_scan_run_status('prepare')
            self.parameters = {}
            self.parameters['AI_CHANNEL'], self.enabled_channels = self._select_ai_channel()
            for pn in self.parent.central_widget.calibration_widget.parameter_names:
                par_value = str(self.parent.central_widget.calibration_widget.scanner_parameters[pn].input.text())
                if par_value != '':
                    par_value = stringop.str2params(par_value)
                    if len(par_value) == 1:
                        par_value = par_value[0]
                    self.parameters[pn] = par_value
            self.parameters['pattern'] = str(self.parent.central_widget.calibration_widget.calib_scan_pattern.pattern.currentText())
            for pn, widget in self.parent.central_widget.calibration_widget.calib_scan_pattern.widgets.items():
                if hasattr(widget, 'input'):
                    try:
                        if hasattr(getattr(widget, 'input'), 'checkState'):
                            self.parameters[pn] = (widget.input.checkState()==2)
                        elif hasattr(getattr(widget, 'input'), 'text'):
                            self.parameters[pn] = float(str(widget.input.text()))
                    except ValueError:
                        pass
            self.queues['parameters'].put(self.parameters)
            self.queues['out'].put('start_calibration')
            self.printc('Calibration start requested')
            
    def calib_started(self):
        self.printc('Calibration started')
        self.update_scan_run_status('started')
        
    def calib_ready(self):
        self.printc('Calibration ready')
        self.update_scan_run_status('ready')
        while True:
            if not self.queues['data'].empty():
                self.emit(QtCore.SIGNAL('plot_calibdata'))
                break
    ####### Helpers ###########
    def _select_ai_channel(self):
        #figure out which analog channels need to be sampled
        ai_channel = self.config.DAQ_CONFIG[0]['AI_CHANNEL']
        enabled_channels = []
        for channel in self.config.PMTS.keys():
            if getattr(getattr(getattr(self.parent.central_widget.control_widget, channel + '_enable'), 'input'),  'checkState')() == 2:
                enabled_channels.append(self.config.PMTS[channel]['AI'])
        if len(enabled_channels) == 0:
            self.printc('No channels enabled, scan does not start')
        elif len(enabled_channels) == 1:
            ai_channel = '{0}/ai{1}'.format(ai_channel.split('/')[0], enabled_channels[0])
        return ai_channel, enabled_channels
        
class VisexpGuiPoller(Poller):
    def __init__(self, parent):
        Poller.__init__(self, parent)
        self.config = parent.config
        self.init_variables()
        self.load_context()
        self.init_widget_handlers()#Depends on context values
        
    def init_variables(self):
        self.queues = {}
        self.gui_thread_queue = Queue.Queue()
        self.stimulation_finished = False
        self.imaging_finished = False
        self.analog_recording_started=False
        self.connected_nodes = ''
        self.sync_samples = {'ca_imaging':[], 'stim':[]}
        self.tdiff = {'ca_imaging':0, 'stim':0}
        self.measurement_loaded = False
        self.plotdata = {}
        self.context_paths = {}
        self.unittest_context_paths = ['self.parent.central_widget.main_widget.experiment_parameters.values.rowCount',#only used by unittest
                                     'self.experiment_control.user_selected_stimulation_module',
                                     'self.animal_file.animal_files.keys',
                                     'self.parent.log.filename', 
                                     'self.animal_file.recordings']
        self.context_paths['variables'] = ['self.experiment_control.experiment_config_classes.keys', 
                                     'self.animal_file.filename', 
                                     'self.parent.log.filename', 
                                     'self.parent.central_widget.parameters_groupbox.machine_parameters', 
                                     'self.current_datafile'
                                     ]
        self.context_paths['variables'].extend(self.unittest_context_paths)
        self.optional_context_paths = ['self.animal_file.filename',]#If these items not found in context file, no warning is given
        self.optional_context_paths.extend(self.unittest_context_paths)
        self.context_paths['widgets'] = [
                                          'self.parent.central_widget.main_widget.experiment_control_groupbox.experiment_name.currentText',
                                          'self.parent.central_widget.main_widget.experiment_options_groupbox.cell_name.input.text', 
                                          'self.parent.central_widget.main_widget.experiment_options_groupbox.recording_channel.list.selectedIndexes', 
                                          'self.parent.central_widget.main_widget.experiment_options_groupbox.scanning_range.input.text', 
                                          'self.parent.central_widget.main_widget.experiment_options_groupbox.pixel_size.text', 
                                          'self.parent.central_widget.main_widget.experiment_options_groupbox.resolution_unit.currentIndex', 
                                          'self.parent.central_widget.averaging.input.text',
                                          'self.parent.central_widget.main_widget.toolbox.bullseye_type.currentIndex',
                                          'self.parent.central_widget.main_widget.toolbox.bullseye_size.input.text',
                                          'self.parent.central_widget.analysis.ta.baseline_start.input.text',
                                          'self.parent.central_widget.analysis.ta.baseline_end.input.text',
                                          'self.parent.central_widget.analysis.ta.post_response_duration.input.text',
                                          'self.parent.central_widget.analysis.ta.initial_drop_duration.input.text',
                                          'self.parent.central_widget.analysis.roi.min_roi_size.input.text',
                                          'self.parent.central_widget.analysis.roi.max_roi_size.input.text',
                                          'self.parent.central_widget.analysis.roi.sigma.input.text',
                                          'self.parent.central_widget.analysis.roi.threshold_factor.input.text',
                                          
                                          ]
        for i in range(self.config.MAX_CA_IMAGE_DISPLAYS):
            self.context_paths['widgets'].append('self.parent.central_widget.ca_displays.display_configs[{0}].enable.checkState'.format(i))
            self.context_paths['widgets'].append('self.parent.central_widget.ca_displays.display_configs[{0}].name.input.text'.format(i))
            self.context_paths['widgets'].append('self.parent.central_widget.ca_displays.display_configs[{0}].channel_select.input.currentIndex'.format(i))
            self.context_paths['widgets'].append('self.parent.central_widget.ca_displays.display_configs[{0}].exploring_mode_options.input.currentIndex'.format(i))
            self.context_paths['widgets'].append('self.parent.central_widget.ca_displays.display_configs[{0}].recording_mode_options.input.currentIndex'.format(i))
            self.context_paths['widgets'].append('self.parent.central_widget.ca_displays.display_configs[{0}].gridline_select.input.currentIndex'.format(i))
                                          
    def load_context(self):
        self.context = {}
        for k in self.context_paths.keys():
            self.context[k] = {}
        if not os.path.exists(fileop.get_context_filename(self.config)):
            return
        self.context = utils.array2object(hdf5io.read_item(fileop.get_context_filename(self.config), 'context', self.config,filelocking=False))
        #check if context has the expected keys.
        for k in self.context_paths.keys():
            for expected_key in self.context_paths[k]:
                if expected_key not in self.context[k].keys() and expected_key not in self.optional_context_paths:
                    self.context[k][expected_key] = None
                    warning_msg = '{0}/{1} not found in context file.' .format(k, expected_key) 
                    warnings.warn(warning_msg)
                    self.printc('WARNING: '+warning_msg)
                    break

    def save_context(self):
        context = {}
        context['variables'] = {}
        for varname in self.context_paths['variables']:
            try:
                context['variables'][varname] = introspect.string2objectreference(self,varname)
            except AttributeError:#Continue if variable name does not exists
                continue
            if hasattr(context['variables'][varname], '__call__'):
                context['variables'][varname] = context['variables'][varname]()
        context['widgets'] = {}
        for varname in self.context_paths['widgets']:
            context['widgets'][varname] = introspect.string2objectreference(self,varname)
            if hasattr(context['widgets'][varname], '__call__'):
                context['widgets'][varname] = context['widgets'][varname]()
                if hasattr(context['widgets'][varname], 'isSimpleText'):
                    context['widgets'][varname] = str(context['widgets'][varname])
                elif isinstance(context['widgets'][varname], list):#Qlistwidget selected rows
                    context['widgets'][varname] = [s.row() for s in context['widgets'][varname]]
        hdf5io.save_item(fileop.get_context_filename(self.config), 'context', utils.object2array(context), self.config, overwrite = True,filelocking=False)
                                 
    def init_widget_handlers(self):
        '''
        Widget related classes
        '''
        context_experiment_config_file = None
        if self.context['widgets'].has_key('self.parent.central_widget.main_widget.experiment_control_groupbox.experiment_name.currentText'):
            expname = self.context['widgets']['self.parent.central_widget.main_widget.experiment_control_groupbox.experiment_name.currentText']
            if os.path.exists(os.path.split(expname)[0]):
                context_experiment_config_file = os.path.split(expname)[0]
        self.experiment_control = gui.ExperimentControl(self, self.config, 
                                                        self.parent.central_widget.main_widget.experiment_control_groupbox, 
                                                        self.parent.central_widget.main_widget.experiment_parameters, 
                                                        self.parent.central_widget.main_widget.recording_status, 
                                                        context_experiment_config_file = context_experiment_config_file)
        context_animal_file = utils.get_key( self.context['variables'], 'self.animal_file.filename')
        if context_animal_file is not None and not os.path.exists(context_animal_file):
            context_animal_file = None
        self.animal_file = gui.AnimalFile(self, self.config, self.parent.central_widget.animal_parameters_groupbox, 
                                                      context_animal_file = context_animal_file)
        self.experiment_log = gui.ExperimentLog(self, self.config, self.parent.central_widget.experiment_log_groupbox)
        #Init machine parameters
        if self.context['variables'].has_key('self.parent.central_widget.parameters_groupbox.machine_parameters'):
            self.parent.central_widget.parameters_groupbox.machine_parameters = self.context['variables']['self.parent.central_widget.parameters_groupbox.machine_parameters']
        self.visualisation_control = gui.CaImagingVisualisationControl(self, self.config, self.parent.central_widget.ca_displays)
        self.toolbox = gui.RetinaTools(self, self.config, self.parent.central_widget.main_widget.toolbox)
        if self.context['variables'].has_key('self.current_datafile'):
            self.current_datafile = self.context['variables']['self.current_datafile']                

    def connect_signals(self):
        self.connect(self, QtCore.SIGNAL('printc'), self.parent.printc)
        self.connect(self, QtCore.SIGNAL('ask4confirmation'), self.parent.ask4confirmation)
        self.connect(self, QtCore.SIGNAL('ask4filename'), self.parent.ask4filename)
        self.connect(self, QtCore.SIGNAL('notify_user'), self.parent.notify_user)
        self.connect(self, QtCore.SIGNAL('update_curve'), self.parent.update_curve)
        self.connect(self, QtCore.SIGNAL('update_image'), self.parent.update_image)
        self.connect(self, QtCore.SIGNAL('load_rois'), self.parent.central_widget.image.load_rois)
        self.connect(self, QtCore.SIGNAL('set_experiment_progressbar'), self.parent.set_experiment_progressbar)
        self.connect(self, QtCore.SIGNAL('set_experiment_progressbar_range'), self.parent.set_experiment_progressbar_range)
        self.connect(self, QtCore.SIGNAL('set_experiment_names'), self.parent.set_experiment_names)
        self.connect(self, QtCore.SIGNAL('update_experiment_parameter_table'), self.parent.update_experiment_parameter_table)
        self.connect(self, QtCore.SIGNAL('update_animal_parameters_table'), self.parent.update_animal_parameters_table)
        self.connect(self, QtCore.SIGNAL('update_animal_file_list'), self.parent.update_animal_file_list)
        self.connect(self, QtCore.SIGNAL('update_experiment_log_suggested_date'), self.parent.update_experiment_log_suggested_date)
        self.connect(self, QtCore.SIGNAL('update_experiment_log'), self.parent.update_experiment_log)
        self.connect(self, QtCore.SIGNAL('update_recording_status'), self.parent.update_recording_status)
        self.connect(self, QtCore.SIGNAL('close_app'), self.parent.close_app)
        self.connect(self, QtCore.SIGNAL('select_recording_item'), self.parent.select_recording_item)
        self.connect(self, QtCore.SIGNAL('select_experiment_log_entry'), self.parent.select_experiment_log_entry)
        
    def update_network_connection_status(self):
        #Check for network connection status
        self.connected_nodes = ''
        n_connected = 0
        n_connections = len(self.socket_queues.keys())
        for remote_node_name, socket in self.socket_queues.items():
            if self.ping(timeout=1.0, connection=remote_node_name):
                self.connected_nodes += remote_node_name + ' '
                n_connected += 1
        self.parent.central_widget.network_status.setText('Network connections: {2} {0}/{1}'.format(n_connected, n_connections, self.connected_nodes))
            
    def _update_plot(self, msg, connection_name):
        if not self.plotdata.has_key(connection_name):
            self.plotdata[connection_name] = []
        if len(numpy.array(msg['plot']).shape) == 1:
            self.plotdata[connection_name].append(msg['plot'])
        else:
            self.plotdata[connection_name].extend(msg['plot'])
        curves = [[], [], []]
        for c in self.plotdata.keys():#TODO: this is a messy solution
            if len(self.plotdata[c])==0:
                continue
            plotdata = numpy.array(self.plotdata[c])
            if not hasattr(self.experiment_control, 'current_stimulus_start_time'):
                return
            t=plotdata[:,0]-self.tdiff[c]-self.experiment_control.current_stimulus_start_time#time 0 is when stim started
#            t -= t[0]
            plotdata = plotdata[:,1:]
            if c=='stim' and self.plotdata.has_key('ca_imaging'):#TEST0206
                #Specific for block trigger
                #insert values to visualize block trigger better
#                t=numpy.repeat(t,2)
#                plotdata=numpy.repeat(numpy.cast['bool'](plotdata),2)
#                plotdata[0::2] = numpy.invert(plotdata[0::2])
                ca_values = numpy.array(self.plotdata['ca_imaging'])[:,1:]
                plotdata = signal.scale(plotdata, ca_values.min(), ca_values.max())
                curves[0] = (t, plotdata)
            else:
                for i in range(plotdata.shape[1]):
                    curves[1] = [t, plotdata[:,i]]
        self.emit(QtCore.SIGNAL('update_curve'), curves)        
        
    def clear_curves(self):
        self.plotdata = {}
        self.emit(QtCore.SIGNAL('update_curve'),  None)

    def _calculate_tdiff(self, msg, connection):
        self.sync_samples[connection].append(msg)
        for c in ['stim', 'ca_imaging']:
            if len(self.sync_samples[c]) == self.config.SYNC_SAMPLE_SIZE:
                latency = numpy.array([sample['sync']['t1*']-sample['sync']['t1'] for sample in self.sync_samples[c]]).mean()
                self.tdiff[c] = self.sync_samples[c][-1]['sync']['t1'] + 0.5 * latency - self.sync_samples[c][-1]['sync']['t2']
                self.printc(self.tdiff)
                self.sync_samples[c] = []

    def display_datafile(self,datafile = None):
        if datafile is None:
            folder = os.path.split(self.current_datafile)[0] if hasattr(self, 'current_datafile') and self.current_datafile is not None and os.path.exists(os.path.split(self.current_datafile)[0]) else fileop.get_user_experiment_data_folder(self.config)
            self.printc(folder)
            if hasattr(self, 'current_datafile'):
                self.printc(self.current_datafile)
            datafile = self.ask4filename('Select datafile', folder,  '*.hdf5')
#            datafile = self.gui_thread_queue.get()
        if not os.path.exists(datafile):
            return
        if fileop.parse_recording_filename(datafile)['type'] != 'data':
            self.printc('This file cannot be displayed')
            return
        ts, ti, a = experiment_data.get_activity_plotdata(datafile)
        rect_heights = numpy.ones_like(ts)
        rect_heights[0::2] = a.min()
        rect_heights[1::2] = a.max()
        curves = [[ts, rect_heights]]
        curves.append([ti,a])
        self.emit(QtCore.SIGNAL('update_curve'), curves)
        #Display meanimage
        meanimage,rawdata,scale=experiment_data.get_imagedata(datafile)
        mi=numpy.zeros((meanimage.shape[0],meanimage.shape[1],3))
        mi[:,:,1]=meanimage
        self.emit(QtCore.SIGNAL('update_image'), mi,scale)
        self.rawdata = rawdata
        self.ts = ts
        self.ti = ti
        self.meanimage = meanimage
        self.scale = scale
        self.measurement_loaded = True
        self.printc(datafile)
        self.current_datafile = datafile
        #Load rois
        roi_info = hdf5io.read_item(datafile, 'rois', filelocking=False)
        if roi_info is not None:
            self.emit(QtCore.SIGNAL('load_rois'), roi_info)
        else:
            self.emit(QtCore.SIGNAL('load_rois'), [])

    def run_in_all_iterations(self):
        #### Calling functions all the time #### 
        self.experiment_control.prepare_next_experiment()
        #### Calling functions at lower repetition rate #### 
        if not hasattr(self, 'phase'):
            self.phase = 0
        if not hasattr(self, 'last_second'):
            self.last_second = 0
        now = time.time()
        if now - self.last_second>1.0:
            self.last_second = now
            if not self.phase%2:
                self.test()#Call tester
                #update progress bar
                self.emit(QtCore.SIGNAL('set_experiment_progressbar'), time.time()-self.experiment_control.current_stimulus_start_time if self.experiment_control.isstimulus_started else 0)
            if not self.phase%5:
                self.animal_file.chec4new_animal_file()
                self.update_network_connection_status()
            if not self.phase%15:
                self.experiment_log.update_suggested_date()
            if not self.phase%7:
                pass
            if not self.phase%9:
                self.experiment_control.check_stimulus_and_imaging_start_timeout()
                self.experiment_control.check_data_ready_timeout()
            if not self.phase%21:
                self.printc('poller alive')
                if not self.experiment_control.check_recording_state(['queued', 'preparing',  'running']):
                    for i in range(self.config.SYNC_SAMPLE_SIZE):
                        for c in ['stim', 'ca_imaging']:
                            if c in self.connected_nodes:
                                self.send('sync', connection=c)
                        time.sleep(0.1)
            self.phase+= 1
            
    def periodic(self):
        pass

    def handle_commands(self):
        '''
        Reads and relays data from network queues
        '''
        try:
            for connection_name in self.socket_queues.keys():
                q = self.socket_queues[connection_name]['fromsocket']
                msgs=[]
                while True:
    #            if connection_name == 'ca_imaging':
    #                status = self.socket_queues[connection_name]['in'].empty(),self.socket_queues[connection_name]['out'].empty()
    #                if not status[0] or not status[1]:
    #                    self.printc([self.queues[connection_name]['in'].empty(),self.queues[connection_name]['out'].empty()])
                    if q.empty():
    #                    continue
                        break
                    msgs.append(q.get())
                for msg in msgs:
                    if isinstance(msg,str) and 'ping' not in msg and 'pong' not in msg:
                        self.printc('{0}: {1}'.format(connection_name.upper(),msg))
                    elif hasattr(msg, 'has_key') and msg.has_key('trigger'):
                        trigger_name = msg['trigger']
                        arg = msg.get('arg', None)
                        if trigger_name=='imaging started' and arg=='started':
                            self.clear_curves()
                            res = self.experiment_control.start_stimulation()
                        elif trigger_name == 'stim started':
                            res = self.experiment_control.stimulation_started()
                            self.emit(QtCore.SIGNAL('set_experiment_progressbar_range'), self.experiment_control.current_stimulus_duration)
                            self.emit(QtCore.SIGNAL('set_experiment_progressbar'), 0)
                        elif trigger_name == 'stim done':
                            res = self.experiment_control.stop_image_acquisition()
                        elif trigger_name == 'stim data ready' or trigger_name  == 'imaging data ready':
                            res = self.experiment_control.finish_experiment(trigger_name)
                        if res != True:#Put trigger back to network queue if could not be processed
                            q.put(msg)
                    elif hasattr(msg, 'has_key') and msg.has_key('sync'):
                        self._calculate_tdiff(msg, connection_name)
                    elif hasattr(msg, 'has_key') and msg.has_key('plot'):
                        self._update_plot(msg, connection_name)
                    elif hasattr(msg, 'has_key') and msg.has_key('function'):
                        function_name = msg['function']
                        args = msg['args']
                        if function_name == 'remote_call':
                            introspect.string2objectreference(self, args[0])(*args[1])
                        elif function_name == 'read_variable':#NOT TESTED
                            function_call = {'function': 'set_variable', 'args': [args[0], introspect.string2objectreference(self,args[0])]}
                            self.send(function_call,connection='ca_imaging')
        except:
            self.printc(traceback.format_exc())
                                
    def close(self):
        self.printc('phase counter: {0}'.format(self.phase))
        for conn_name in self.queues.keys():
            self.queues[conn_name]['out'].put('SOCclose_connectionEOCstop_clientEOP')
        time.sleep(0.5)
        self.save_context()
        time.sleep(3.0)
        
    def test(self):
        if (hasattr(self, 'test_run') and self.testmode!=1 and self.testmode != 11)\
                    or self.testmode is None:
            return
        self.test_run=True
        wait=0.1
        animal_param_table = self.parent.central_widget.animal_parameters_groupbox.table
        import PyQt4.QtGui as QtGui
        self.printc('Test {0}'.format(self.testmode))
        if self.testmode==0:#Just for creating context file/quickly starting up the gui
            self.parent.central_widget.main_widget.experiment_control_groupbox.experiment_name.setCurrentIndex(2)
            time.sleep(1)
            self.emit(QtCore.SIGNAL('close_app'))
        elif self.testmode==1:
            if not hasattr(self, 'test_phase'):
                self.test_phase = 1
                self.printc('Select test_stimulus.py module.')
                self.signal_id_queue.put('experiment_control.browse')
            elif self.test_phase == 1:
                self.test_phase = 2
                widget = self.parent.central_widget.main_widget.experiment_control_groupbox.experiment_name
                items = gui_generic.get_combobox_items(widget)
                widget.setCurrentIndex(items.index(stringop.string_in_list(items, 'GUITestExperimentConfig', return_match=True)))
                time.sleep(1)
                expparam_table = self.parent.central_widget.main_widget.experiment_parameters.values
                for i in range(expparam_table.rowCount()):
                    if 'PAR1' in str(expparam_table.item(i, 0).text()):
                        comment = expparam_table.item(i, 1).toolTip()
                        item = QtGui.QTableWidgetItem('100')
                        item.setToolTip(comment)
                        expparam_table.setItem(i, 1, item)
                time.sleep(1.0)
                self.experiment_control.save_experiment_parameters()
                for i in range(expparam_table.rowCount()):
                    if 'PAR1' in str(expparam_table.item(i, 0).text()):
                        comment = expparam_table.item(i, 1).toolTip()
                        item = QtGui.QTableWidgetItem('1.0')
                        item.setToolTip(comment)
                        expparam_table.setItem(i, 1, item)
                time.sleep(1.0)
                self.experiment_control.save_experiment_parameters()
                time.sleep(1.0)
                self.emit(QtCore.SIGNAL('close_app'))
        elif self.testmode==2 or self.testmode==3:
            self.parent.central_widget.main_tab.setCurrentIndex(2)
            animal_param_table.setItem(0, 1, QtGui.QTableWidgetItem('test'))
            time.sleep(wait)
            animal_param_table.cellWidget(1, 1).setDate(QtCore.QDate(2013, 1, 1))
            time.sleep(wait)
            animal_param_table.cellWidget(2, 1).setDate(QtCore.QDate(2013, 5, 1))
            time.sleep(wait)
            animal_param_table.cellWidget(3, 1).setCurrentIndex(1)
            time.sleep(wait)
            animal_param_table.cellWidget(4, 1).setCurrentIndex(2)
            time.sleep(wait)
            animal_param_table.cellWidget(5, 1).setCurrentIndex(1)
            time.sleep(wait)
            animal_param_table.cellWidget(6, 1).setEditText('strain')
            if self.testmode==2:
                animal_param_table.cellWidget(7, 1).setEditText('label')
            self.animal_file.save_animal_parameters()
            self.emit(QtCore.SIGNAL('close_app'))
        elif self.testmode ==4 or self.testmode ==5:
            for fn in os.listdir(tempfile.gettempdir()):
                if 'animal_' in fn and '.hdf5' in fn:
                    self.printc(fn)
                    shutil.move(os.path.join(tempfile.gettempdir(), fn), self.config.DATA_STORAGE_PATH)
            self.parent.central_widget.main_tab.setCurrentIndex(2)
            time.sleep(wait)
            self.animal_file.search_data_storage()
            time.sleep(1)
            self.parent.central_widget.animal_parameters_groupbox.animal_filename.input.setCurrentIndex(1)
            time.sleep(1)
            if self.testmode ==5:
                self.animal_file.copy()
                time.sleep(1)
                self.parent.central_widget.animal_parameters_groupbox.animal_filename.input.setCurrentIndex(2)
                time.sleep(1)
            animal_param_table.cellWidget(1, 1).setDate(QtCore.QDate(2015, 1, 1))
            time.sleep(1)
            self.animal_file.reload_animal_parameters()
            time.sleep(1)
            animal_param_table.cellWidget(7, 1).setEditText('modified_label')
            time.sleep(wait)
            animal_param_table.cellWidget(8, 1).setEditText('yes')
            time.sleep(1)
            self.animal_file.update()
            time.sleep(1)
            if self.testmode ==5:
                animal_param_table.setItem(0, 1, QtGui.QTableWidgetItem('second_one'))
                time.sleep(wait)
                animal_param_table.cellWidget(1, 1).setDate(QtCore.QDate(2012, 1, 1))
                time.sleep(wait)
                animal_param_table.cellWidget(2, 1).setDate(QtCore.QDate(2012, 1, 1))
                time.sleep(wait)
                animal_param_table.cellWidget(6, 1).setEditText('secondstrain')
                time.sleep(wait)
                self.animal_file.save_animal_parameters()
            time.sleep(1)
            self.emit(QtCore.SIGNAL('close_app'))
        elif self.testmode == 6:
            self.parent.central_widget.main_tab.setCurrentIndex(2)
            time.sleep(wait)
            animal_param_table.setItem(0, 1, QtGui.QTableWidgetItem('test'))
            time.sleep(wait)
            animal_param_table.cellWidget(1, 1).setDate(QtCore.QDate(2010, 1, 1))
            time.sleep(wait)
            animal_param_table.cellWidget(2, 1).setDate(QtCore.QDate(2010, 1, 1))
            time.sleep(wait)
            animal_param_table.cellWidget(3, 1).setCurrentIndex(1)
            time.sleep(wait)
            animal_param_table.cellWidget(4, 1).setCurrentIndex(1)
            time.sleep(wait)
            animal_param_table.cellWidget(5, 1).setCurrentIndex(1)
            time.sleep(wait)
            animal_param_table.cellWidget(6, 1).setEditText('strain')
            time.sleep(wait)
            animal_param_table.cellWidget(7, 1).setEditText('label')
            time.sleep(wait)
            self.animal_file.save_animal_parameters()
            time.sleep(1)
            animal_param_table.setItem(0, 1, QtGui.QTableWidgetItem('test1'))
            animal_param_table.cellWidget(7, 1).setEditText('label1')
            self.animal_file.update()
            time.sleep(1)
            self.emit(QtCore.SIGNAL('close_app'))
        elif self.testmode == 7 or self.testmode == 8 or self.testmode ==  9 or self.testmode ==  10:
            if self.testmode == 9 or self.testmode ==  10:
                self.parent.central_widget.main_tab.setCurrentIndex(2)
                time.sleep(wait)
                animal_param_table.setItem(0, 1, QtGui.QTableWidgetItem('addlog1'))
                time.sleep(wait)
                animal_param_table.cellWidget(1, 1).setDate(QtCore.QDate(2009, 1, 1))
                time.sleep(wait)
                animal_param_table.cellWidget(2, 1).setDate(QtCore.QDate(2009, 1, 1))
                time.sleep(wait)
                animal_param_table.cellWidget(6, 1).setEditText('1')
                time.sleep(wait)
                animal_param_table.cellWidget(7, 1).setEditText('xy')
                time.sleep(wait)
                self.animal_file.save_animal_parameters()
                time.sleep(1)
            self.parent.central_widget.main_tab.setCurrentIndex(1)
            time.sleep(wait)
            self.parent.central_widget.experiment_log_groupbox.new_entry.comment.input.setText('1/1')
            time.sleep(wait)
            self.experiment_log.add()
            time.sleep(1)
            if  self.testmode ==  10:
                self.parent.central_widget.main_tab.setCurrentIndex(2)
                time.sleep(wait)
                animal_param_table.setItem(0, 1, QtGui.QTableWidgetItem('addlog2'))
                time.sleep(wait)
                animal_param_table.cellWidget(6, 1).setEditText('2')
                time.sleep(wait)
                self.animal_file.save_animal_parameters()
                time.sleep(1)
                self.parent.central_widget.main_tab.setCurrentIndex(1)
            self.parent.central_widget.experiment_log_groupbox.new_entry.substance.input.setEditText('isofl2')
            time.sleep(wait)
            self.parent.central_widget.experiment_log_groupbox.new_entry.amount.input.setText('22 ul')
            time.sleep(wait)
            self.parent.central_widget.experiment_log_groupbox.new_entry.comment.input.setText('2/1')
            time.sleep(wait)
            self.experiment_log.add()
            time.sleep(1)
            self.parent.central_widget.experiment_log_groupbox.new_entry.substance.input.setEditText('isofl2')
            time.sleep(wait)
            self.parent.central_widget.experiment_log_groupbox.new_entry.amount.input.setText('2 ul')
            time.sleep(wait)
            self.parent.central_widget.experiment_log_groupbox.new_entry.comment.input.setText('2/2')
            time.sleep(wait)
            self.experiment_log.add()
            time.sleep(1.5)
            if  self.testmode ==  10:
                self.parent.central_widget.animal_parameters_groupbox.animal_filename.input.setCurrentIndex(0)
                time.sleep(0.5)
                self.parent.central_widget.experiment_log_groupbox.new_entry.substance.input.setEditText('isofl1')
                time.sleep(wait)
                self.parent.central_widget.experiment_log_groupbox.new_entry.amount.input.setText('0 %')
                time.sleep(wait)
                self.parent.central_widget.experiment_log_groupbox.new_entry.comment.input.setText('1/2')
                time.sleep(wait)
                self.experiment_log.add()
                time.sleep(0.5)
                self.parent.central_widget.experiment_log_groupbox.new_entry.substance.input.setCurrentIndex(1)
                time.sleep(wait)
                self.parent.central_widget.experiment_log_groupbox.new_entry.amount.input.setText('1 % 1/3')
                time.sleep(wait)
                self.parent.central_widget.experiment_log_groupbox.new_entry.comment.input.setText('')
                time.sleep(wait)
                self.experiment_log.add()
                time.sleep(0.5)
                self.parent.central_widget.experiment_log_groupbox.new_entry.substance.input.setCurrentIndex(1)#Testing if duplicates can be added
                time.sleep(wait)
                self.parent.central_widget.experiment_log_groupbox.new_entry.amount.input.setText('1 % 1/3')
                time.sleep(wait)
                self.parent.central_widget.experiment_log_groupbox.new_entry.comment.input.setText('')
                time.sleep(wait)
                self.experiment_log.add()
                time.sleep(0.5)
                self.parent.central_widget.experiment_log_groupbox.new_entry.substance.input.setCurrentIndex(1)
                time.sleep(wait)
                self.parent.central_widget.experiment_log_groupbox.new_entry.amount.input.setText('1 %')
                time.sleep(wait)
                self.parent.central_widget.experiment_log_groupbox.new_entry.comment.input.setText('1/4')
                time.sleep(wait)
                self.experiment_log.add()
                time.sleep(0.5)
                self.emit(QtCore.SIGNAL('select_experiment_log_entry'), 1)
                time.sleep(wait)
                self.emit(QtCore.SIGNAL('select_experiment_log_entry'), 2)
                while len(self.parent.central_widget.experiment_log_groupbox.log.selectedItems()) != 2:
                    time.sleep(0.1)
                self.experiment_log.remove()
            time.sleep(1.0)
            self.emit(QtCore.SIGNAL('close_app'))
        elif self.testmode == 11:
            self.parent.central_widget.main_tab.setCurrentIndex(2)
            if not hasattr(self, 'test_phase'):
                self.test_phase = 1
                for fn in os.listdir(tempfile.gettempdir()):
                    if 'animal_' in fn and '.hdf5' in fn:
                        self.printc('{0} moved'.format(os.path.join(tempfile.gettempdir(), fn)))
                        shutil.move(os.path.join(tempfile.gettempdir(), fn), fileop.get_user_experiment_data_folder(self.config))
                self.filemovetime = time.time()
            elif self.test_phase == 1:
                APP_CLOSE_TIMEOUT = 10.0
                if time.time()-self.filemovetime>APP_CLOSE_TIMEOUT:
                    time.sleep(1)
                    self.emit(QtCore.SIGNAL('close_app'))
        elif self.testmode == 12:
            self.parent.central_widget.main_tab.setCurrentIndex(2)
            for i in range(3):
                animal_param_table.setItem(0, 1, QtGui.QTableWidgetItem('id{0}'.format(i)))
                time.sleep(wait)
                animal_param_table.cellWidget(1, 1).setDate(QtCore.QDate(2012, 12, 12))
                time.sleep(wait)
                animal_param_table.cellWidget(2, 1).setDate(QtCore.QDate(2012, 12, 12))
                time.sleep(wait)
                animal_param_table.cellWidget(6, 1).setEditText('12')
                time.sleep(wait)
                animal_param_table.cellWidget(7, 1).setEditText('xy')
                time.sleep(wait)
                self.animal_file.save_animal_parameters()
                time.sleep(1)
            self.parent.central_widget.main_tab.setCurrentIndex(0)
            time.sleep(wait)
            self.parent.central_widget.animal_parameters_groupbox.animal_filename.input.setCurrentIndex(1)
            time.sleep(wait)
            self.parent.central_widget.main_widget.experiment_options_groupbox.cell_name.input.setText('cell')
            time.sleep(wait)
            self.parent.central_widget.main_widget.experiment_options_groupbox.scanning_range.input.setText('100, 100')
            time.sleep(1)
            self.emit(QtCore.SIGNAL('close_app'))
        elif self.testmode == 13 or self.testmode == 14:
            if self.testmode == 14:
                self.parent.central_widget.main_tab.setCurrentIndex(2)
                time.sleep(wait)
                animal_param_table.setItem(0, 1, QtGui.QTableWidgetItem('id0'))
                time.sleep(wait)
                animal_param_table.cellWidget(1, 1).setDate(QtCore.QDate(2012, 12, 12))
                time.sleep(wait)
                animal_param_table.cellWidget(2, 1).setDate(QtCore.QDate(2012, 12, 12))
                time.sleep(wait)
                animal_param_table.cellWidget(6, 1).setEditText('12')
                time.sleep(wait)
                animal_param_table.cellWidget(7, 1).setEditText('xy')
                time.sleep(wait)
                self.animal_file.save_animal_parameters()
                time.sleep(1)
            self.parent.central_widget.main_tab.setCurrentIndex(0)
            time.sleep(wait)
            self.parent.central_widget.main_widget.experiment_options_groupbox.cell_name.input.setText('C1')
            time.sleep(wait)
            self.parent.central_widget.main_widget.experiment_options_groupbox.scanning_range.input.setText('200, 200')
            time.sleep(wait)
            self.parent.central_widget.main_widget.experiment_options_groupbox.pixel_size.setText('1')
            time.sleep(wait)
            self.parent.central_widget.main_widget.experiment_options_groupbox.resolution_unit.setCurrentIndex(1)
            time.sleep(wait)
            self.parent.central_widget.parameters_groupbox.machine_parameters['scanner']['Scan center'] = '10,0#'
            time.sleep(0.5)
            self.experiment_control.add_experiment()
            time.sleep(0.5)
            self.parent.central_widget.main_widget.experiment_options_groupbox.cell_name.input.setText('C2')
            self.experiment_control.add_experiment()
            time.sleep(0.5)
            self.parent.central_widget.main_widget.recording_status.new_state.setCurrentIndex(4)
            time.sleep(wait)
            self.experiment_control.set_experiment_state()
            time.sleep(0.5)
            self.emit(QtCore.SIGNAL('select_recording_item'), 0, True)
            time.sleep(0.5)
            self.experiment_control.set_experiment_state()
            time.sleep(wait)
            self.emit(QtCore.SIGNAL('select_recording_item'), 0, False)
            time.sleep(wait)
            self.emit(QtCore.SIGNAL('select_recording_item'), 1, True)
            time.sleep(1)
            self.experiment_control.remove_experiment()
            time.sleep(1)
            self.emit(QtCore.SIGNAL('close_app'))
            
    ##### Relaying signals #####
    def set_experiment_names(self, experiment_names):
        self.emit(QtCore.SIGNAL('set_experiment_names'),experiment_names)

    def update_experiment_parameter_table(self):
        self.emit(QtCore.SIGNAL('update_experiment_parameter_table'))
        
    def update_animal_parameters_table(self):
        self.emit(QtCore.SIGNAL('update_animal_parameters_table'))
        
    def update_animal_file_list(self):
        self.emit(QtCore.SIGNAL('update_animal_file_list'))
        
    def update_experiment_log_suggested_date(self):
        self.emit(QtCore.SIGNAL('update_experiment_log_suggested_date'))
        
    def update_experiment_log(self):
        self.emit(QtCore.SIGNAL('update_experiment_log'))
        
    def update_recording_status(self):
        self.emit(QtCore.SIGNAL('update_recording_status'))
        
        
if __name__ == '__main__':
    pass
