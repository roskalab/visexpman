#TODO: Load animal parameters, select ref image should come from that
#TODO: rename to visexp_gui.py
#TODO: log
#TODO:Execute experiment
#TODO: timestamp to gui.hdf5 and string_timestamp node
#TODO: string parsing: re
#TODO: string to binary array: numpy.loadtext, loadfile or struct.struct
import sys
ENABLE_NETWORK = True#not 'dev' in sys.argv[1]
SEARCH_SUBFOLDERS = True

from visexpA.engine.datadisplay import imaged
import time
import socket
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import visexpman.engine.generic.utils as utils
import visexpman.engine.visual_stimulation.configuration as configuration
import visexpman.engine.visual_stimulation.gui as gui
import visexpman.engine.hardware_interface.network_interface as network_interface
import visexpman.engine.hardware_interface.mes_interface as mes_interface
import visexpman.engine.generic.utils as utils
import visexpman.engine.generic.geometry as geometry
import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner
import Queue
import os.path
import visexpA.engine.datahandlers.hdf5io as hdf5io
try:
    import visexpA.engine.dataprocessors.itk_image_registration as itk_image_registration
    import visexpA.engine.dataprocessors.itk_versor_rigid_registration as itk_versor_rigid_registration
except:
    print 'itk not installed'
import threading
import visexpA.engine.datahandlers.matlabfile as matlabfile
import tempfile
import Image
import numpy
import shutil
import visexpman.engine.generic.log as log
from visexpman.engine.visual_stimulation import experiment_data
try:
    import visexpA.engine.dataprocessors.signal as signal
except:
    pass
import traceback

################### Main widget #######################
class VisionExperimentGui(QtGui.QWidget):
    def __init__(self, config, command_relay_server = None):
        self.config = config
        self.command_relay_server = command_relay_server
        self.console_text = ''
        self.poller = gui.Poller(self)
        self.poller.start()
        QtGui.QWidget.__init__(self)
        self.setWindowTitle('Vision Experiment Manager GUI')        
        self.resize(self.config.GUI_SIZE['col'], self.config.GUI_SIZE['row'])
        self.move(self.config.GUI_POSITION['col'], self.config.GUI_POSITION['row'])        
        self.create_gui()
        self.create_layout()
        self.connect_signals()
        self.init_network()
        self.init_files()
        self.update_gui_items()
        self.show()        
        
    def create_gui(self):
        self.new_mouse_widget = gui.NewMouseWidget(self, self.config)
        self.registered_mouse_widget = gui.RegisteredMouseWidget(self, self.config)
        self.debug_widget = gui.DebugWidget(self, self.config)
        self.realignment_tab = QtGui.QTabWidget(self)
        self.realignment_tab.addTab(self.new_mouse_widget, 'New mouse')
        self.realignment_tab.addTab(self.registered_mouse_widget, 'Registered mouse')
        self.realignment_tab.addTab(self.debug_widget, 'Debug')
        self.realignment_tab.setCurrentIndex(2)
        self.image_display = []
        for i in range(2):
            self.image_display.append(QtGui.QLabel())
        blank_image = 128*numpy.ones((self.config.IMAGE_SIZE['col'], self.config.IMAGE_SIZE['row']), dtype = numpy.uint8)
        for image in self.image_display:
            image.setPixmap(imaged.array_to_qpixmap(blank_image))
        
        self.standard_io_widget = gui.StandardIOWidget(self, self.config)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.realignment_tab, 0, 0, 1, 1)
        self.layout.addWidget(self.standard_io_widget, 1, 0, 1, 1)
        for i in range(len(self.image_display)):
            self.layout.addWidget(self.image_display[i], 0, 2 + i*2, 1, 1)
        self.layout.setRowStretch(3, 3)
        self.layout.setColumnStretch(2, 1)
        self.setLayout(self.layout)

    ############ Network, context, non-gui stuff ################
    def init_network(self):
        self.connections = {}
        self.queues = {}
        self.queues['mes'] = {}
        self.queues['mes']['out'] = Queue.Queue()
        self.queues['mes']['in'] = Queue.Queue()
        self.connections['mes'] = network_interface.start_client(self.config, 'GUI', 'GUI_MES', self.queues['mes']['in'], self.queues['mes']['out'])
        self.mes_interface = mes_interface.MesInterface(self.config, self.connections['mes'])
        self.queues['stim'] = {}
        self.queues['stim']['out'] = Queue.Queue()
        self.queues['stim']['in'] = Queue.Queue()
        self.connections['stim'] = network_interface.start_client(self.config, 'GUI', 'GUI_STIM', self.queues['stim']['in'], self.queues['stim']['out'])
        self.queues['analysis'] = {}
        self.queues['analysis']['out'] = Queue.Queue()
        self.queues['analysis']['in'] = Queue.Queue()
        self.connections['analysis'] = network_interface.start_client(self.config, 'GUI', 'GUI_ANALYSIS', self.queues['analysis']['in'], self.queues['analysis']['out'])
            
    def init_files(self):
        self.log = log.Log('gui log', utils.generate_filename(os.path.join(self.config.LOG_PATH, 'gui_log.txt'))) 
        # create folder if not exists
        self.context_file_path = os.path.join(self.config.CONTEXT_PATH, self.config.CONTEXT_NAME)
        context_hdf5 = hdf5io.Hdf5io(self.context_file_path)
        context_hdf5.load('stage_origin')
        context_hdf5.load('stage_position')
        if hasattr(context_hdf5, 'stage_position') and hasattr(context_hdf5, 'stage_origin') :
            self.stage_origin = context_hdf5.stage_origin
            self.stage_position = context_hdf5.stage_position
        else:
            self.stage_position = numpy.zeros(3)
            self.stage_origin = numpy.zeros(3)
        context_hdf5.close()
        self.stage_position_valid = False
        self.mouse_files = []
        self.selected_mouse_file = ''
        
    def save_context(self):        
        context_hdf5 = hdf5io.Hdf5io(self.context_file_path)
        context_hdf5.stage_origin = self.stage_origin
        context_hdf5.stage_position = self.stage_position
        context_hdf5.save('stage_origin',overwrite = True)
        context_hdf5.save('stage_position', overwrite = True)
        context_hdf5.close()
        
    ####### Signals/functions ###############
    def connect_signals(self):
        self.connect(self.standard_io_widget.execute_python_button, QtCore.SIGNAL('clicked()'),  self.execute_python)
        self.connect(self.standard_io_widget.clear_console_button, QtCore.SIGNAL('clicked()'),  self.clear_console)
        self.connect(self.new_mouse_widget.animal_parameters_groupbox.new_mouse_file_button, QtCore.SIGNAL('clicked()'),  self.save_animal_parameters)
        self.connect(self.debug_widget.animal_parameters_groupbox.new_mouse_file_button, QtCore.SIGNAL('clicked()'),  self.save_animal_parameters)
        self.connect(self.debug_widget.show_connected_clients_button, QtCore.SIGNAL('clicked()'),  self.show_connected_clients)
        self.connect(self.debug_widget.show_network_messages_button, QtCore.SIGNAL('clicked()'),  self.show_network_messages)
        self.connect(self.debug_widget.z_stack_button, QtCore.SIGNAL('clicked()'),  self.acquire_z_stack)
        self.connect(self.debug_widget.stop_experiment_button, QtCore.SIGNAL('clicked()'),  self.stop_experiment)
        self.connect(self.debug_widget.start_experiment_button, QtCore.SIGNAL('clicked()'),  self.start_experiment)
        self.connect(self.debug_widget.set_stage_origin_button, QtCore.SIGNAL('clicked()'),  self.set_stage_origin)
        self.connect(self.debug_widget.read_stage_button, QtCore.SIGNAL('clicked()'),  self.read_stage)
        self.connect(self.debug_widget.move_stage_button, QtCore.SIGNAL('clicked()'),  self.move_stage)
        self.connect(self.debug_widget.master_position_groupbox.get_two_photon_image_button, QtCore.SIGNAL('clicked()'),  self.acquire_two_photon_image)
        self.connect(self.debug_widget.master_position_groupbox.save_master_position_button, QtCore.SIGNAL('clicked()'),  self.save_master_position)
        self.connect(self.debug_widget.send_command_button, QtCore.SIGNAL('clicked()'),  self.send_command)
        
        
        self.connect(self, QtCore.SIGNAL('abort'), self.poller.abort_poller)
    
    def acquire_z_stack(self):
        try:
            self.z_stack, results = self.mes_interface.acquire_z_stack(self.config.MES_TIMEOUT)
            self.printc((self.z_stack, results))
        except:
            self.printc(traceback.format_exc())
            
    def acquire_two_photon_image(self):
        try:
            if self.debug_widget.master_position_groupbox.use_master_position_scan_settings_checkbox.checkState() == 0:
                self.two_photon_image,  result = self.mes_interface.acquire_two_photon_image(self.config.MES_TIMEOUT)
            else:
                #Load scan settings from parameter file
                parameter_file_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, 'master_position_parameters.mat')
                self.master_position['mes_parameters'].tofile(parameter_file_path)
                self.two_photon_image,  result = self.mes_interface.acquire_two_photon_image(self.config.MES_TIMEOUT, parameter_file = parameter_file_path)
            if result:
                self.show_image(self.two_photon_image[self.config.DEFAULT_PMT_CHANNEL], 0)
            else:
                self.printc('No image acquired')
        except:
            self.printc(traceback.format_exc())
            
    def save_master_position(self, widget = None):
        if widget == None:
            widget = self.debug_widget
        if self.read_stage() and hasattr(self, 'two_photon_image'):
            #Prepare data
            node_name = 'master_position'
            master_position_info = {}            
            master_position_info['image'] = self.two_photon_image[self.config.DEFAULT_PMT_CHANNEL]
            master_position_info['scale'] = self.two_photon_image['scale']
            master_position_info['position'] = utils.pack_position(self.stage_position, self.two_photon_image['objective_relative_position'])
            master_position_info['mes_parameters']  = utils.file_to_binary_array(self.two_photon_image['path'])
            #save to mouse file
            mouse_file_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, str(widget.master_position_groupbox.select_mouse_file.currentText()))
            if os.path.exists(mouse_file_path) and '.hdf5' in mouse_file_path:
                hdf5_handler = hdf5io.Hdf5io(mouse_file_path)
                setattr(hdf5_handler, node_name, master_position_info)
                hdf5_handler.save(node_name, overwrite = True)
                hdf5_handler.close()
                self.printc('Master position saved')
            else:
                self.printc('mouse file not found')
#            self.printc(master_position_info)
        
        
    def stop_experiment(self):
        command = 'SOCabort_experimentEOCguiEOP'
        self.queues['stim']['out'].put(command)
        self.printc(command)
        
    def start_experiment(self):
        command = 'SOCexecute_experimentEOCguiEOP'
        self.queues['stim']['out'].put(command)
        self.printc(command)

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
        if self.realignment_tab.currentIndex() == 2:
            widget = self.debug_widget
        else:
            widget = self.new_mouse_widget        
        mouse_birth_date = widget.animal_parameters_groupbox.mouse_birth_date.date()
        mouse_birth_date = '{0}-{1}-{2}'.format(mouse_birth_date.day(),  mouse_birth_date.month(),  mouse_birth_date.year())
        gcamp_injection_date = widget.animal_parameters_groupbox.gcamp_injection_date.date()
        gcamp_injection_date = '{0}-{1}-{2}'.format(gcamp_injection_date.day(),  gcamp_injection_date.month(),  gcamp_injection_date.year())                

        animal_parameters = {
            'mouse_birth_date' : mouse_birth_date,
            'gcamp_injection_date' : gcamp_injection_date,
            'anesthesia_protocol' : str(widget.animal_parameters_groupbox.anesthesia_protocol.currentText()),
            'gender' : str(widget.animal_parameters_groupbox.gender.currentText()),
            'ear_punch_l' : str(widget.animal_parameters_groupbox.ear_punch_l.currentText()), 
            'ear_punch_r' : str(widget.animal_parameters_groupbox.ear_punch_r.currentText()),
            'strain' : str(widget.animal_parameters_groupbox.mouse_strain.currentText()),
            'comments' : str(widget.animal_parameters_groupbox.comments.currentText()),
        }        
        name = '{0}_{1}_{2}_{3}_{4}' .format(animal_parameters['strain'], animal_parameters['mouse_birth_date'] , animal_parameters['gcamp_injection_date'], \
                                         animal_parameters['ear_punch_l'], animal_parameters['ear_punch_r'])

        mouse_file_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, 'mouse_{0}.hdf5'\
                                            .format(name))
        
        if os.path.exists(mouse_file_path):
            self.printc('Animal parameter file already exists')
        else:        
            self.hdf5_handler = hdf5io.Hdf5io(mouse_file_path)
            variable_name = 'animal_parameters_{0}'.format(int(time.time()))        
            setattr(self.hdf5_handler,  variable_name, animal_parameters)
            self.hdf5_handler.save(variable_name)
            self.printc('Animal parameters saved')
            self.hdf5_handler.close()
            
    def update_gui_items(self):
        '''
        Update comboboxes with file lists
        '''
        new_mouse_files = utils.filtered_file_list(self.config.EXPERIMENT_DATA_PATH,  'mouse')
        if self.mouse_files != new_mouse_files:
            self.mouse_files = new_mouse_files
            self.update_combo_box_list(self.debug_widget.master_position_groupbox.select_mouse_file, self.mouse_files)
        
        selected_mouse_file  = str(self.debug_widget.master_position_groupbox.select_mouse_file.currentText())
        if self.selected_mouse_file != selected_mouse_file:
            self.master_position = experiment_data.read_master_position(os.path.join(self.config.EXPERIMENT_DATA_PATH, selected_mouse_file))
            if self.master_position.has_key('image'):
                self.show_image(self.master_position['image'], 1)
        
    def set_stage_origin(self):
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
                    self.printc('origin set')
        self.origin_set = True

    def read_stage(self, display_coords = True):
        result = False
        utils.empty_queue(self.queues['stim']['in'])
        self.queues['stim']['out'].put('SOCstageEOCreadEOP')
        if utils.wait_data_appear_in_queue(self.queues['stim']['in'], 10.0):
            while not self.queues['stim']['in'].empty():
                response = self.queues['stim']['in'].get()            
                if 'SOCstageEOC' in response:
                    position = response.split('EOC')[-1].replace('EOP', '')
                    self.stage_position = numpy.array(map(float, position.split(',')))
                    if display_coords:
                        self.printc('abs: ' + str(self.stage_position))
                        self.printc('rel: ' + str(self.stage_position - self.stage_origin))
                    self.save_context()
                    result = True
        else:
            self.printc('stage is not accessible')
        return result

    def move_stage(self):
        movement = self.scanc().split(',')
        if len(movement) == 2:
            movement.append('0')
        elif len(movement) != 3:
            self.printc('invalid coordinates')
            return
        utils.empty_queue(self.queues['stim']['in'])
        self.queues['stim']['out'].put('SOCstageEOCset,{0},{1},{2}EOP'.format(movement[0], movement[1], movement[2]))
        self.printc('moves to {0}'.format(movement))
        if utils.wait_data_appear_in_queue(self.queues['stim']['in'], 10.0):
            while not self.queues['stim']['in'].empty():
                response = self.queues['stim']['in'].get()            
                if 'SOCstageEOC' in response:
                    self.read_stage()

    def execute_python(self):
        try:
            exec(str(self.scanc()))
        except:
            self.printc(traceback.format_exc())

    def clear_console(self):
        self.console_text  = ''
        self.standard_io_widget.text_out.setPlainText(self.console_text)

    ####### Helpers ###############
    
    def show_image(self, image, channel):        
        self.image_display[channel].setPixmap(imaged.array_to_qpixmap(image, self.config.IMAGE_SIZE))
        
    def send_command(self):
        connection = str(self.debug_widget.select_connection_list.currentText())
        self.queues[connection]['out'].put(self.scanc())
        
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
        if hasattr(self, 'network_messages'):
            for info in self.command_relay_server.get_debug_info():
                self.network_messages.append(info)
        else:
            self.network_messages = self.command_relay_server.get_debug_info()
        self.network_messages = self.network_messages[-500:] #limit the number of displayed messages
        for network_message in self.network_messages:
            endpoint_name = network_message[1].split(' ')
            endpoint_name = (endpoint_name[1] + '/' + endpoint_name[3]).replace(',','')
            message = network_message[1].split('port')[1].split(': ', 1)[1]
            displayable_message = network_message[0] + ' ' + endpoint_name + '>> ' + message
            self.printc(displayable_message)
        self.printc('\n')
            
    def printc(self, text):       
        if not isinstance(text, str):
            text = str(text)
        self.console_text  += text + '\n'
        self.standard_io_widget.text_out.setPlainText(self.console_text)
        self.standard_io_widget.text_out.moveCursor(QtGui.QTextCursor.End)
        self.log.info(text)

    def scanc(self):
        return str(self.standard_io_widget.text_in.toPlainText())
        
    def update_combo_box_list(self, widget, new_list):
        current_value = widget.currentText()
        if current_value in new_list:
            current_index = new_list.index(current_value)
        else:
            current_index = 0
        items_list = QtCore.QStringList(new_list)
        widget.clear()
        widget.addItems(QtCore.QStringList(new_list))
        widget.setCurrentIndex(current_index)

    def closeEvent(self, e):
        e.accept()
        self.printc('Wait till server is closed')
        self.queues['mes']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.queues['stim']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.queues['analysis']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.emit(QtCore.SIGNAL('abort'))
        if ENABLE_NETWORK:
            self.command_relay_server.shutdown_servers()            
            time.sleep(2.0) #Enough time to close network connections    
        sys.exit(0)
        
class GuiConfig(configuration.VisionExperimentConfig):
    def _set_user_parameters(self):
        COORDINATE_SYSTEM='center'

        if self.OS == 'win':
            v_drive_folder = 'V:\\'
        elif self.OS == 'linux':                        
            v_drive_folder = '/home/zoltan/visexp'
            
        if 'dev' in sys.argv[1] or 'development' in self.PACKAGE_PATH:            
            CONTEXT_NAME = 'gui_dev.hdf5'
            data_folder = os.path.join(v_drive_folder, 'data')
            MES_DATA_FOLDER = 'V:\\data'
            MES_DATA_PATH = os.path.join(v_drive_folder, 'data')            
        else:
            CONTEXT_NAME = 'gui.hdf5'
            data_folder = os.path.join(v_drive_folder, 'data')
            MES_DATA_FOLDER = 'V:\\data'
            MES_DATA_PATH = os.path.join(v_drive_folder, 'data')
        self.MES_TIMEOUT = 5.0
        LOG_PATH = os.path.join(data_folder, 'log')
        EXPERIMENT_LOG_PATH = data_folder
        EXPERIMENT_DATA_PATH = data_folder
        CONTEXT_PATH = os.path.join(v_drive_folder, 'context')
        self.GUI_REFRESH_PERIOD = 2.0
        self.COMMAND_RELAY_SERVER['ENABLE'] = ENABLE_NETWORK
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'#'172.27.26.1'#'172.27.25.220'
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = ENABLE_NETWORK
#        self.COMMAND_RELAY_SERVER['TIMEOUT'] = 60.0
        DEFAULT_PMT_CHANNEL = ['pmtUGraw',  ['pmtUGraw', 'pmtURraw',  'undefined']]
    

        #== GUI specific ==
        GUI_POSITION = utils.cr((10, 10))
        GUI_SIZE = utils.cr((1200, 800))
        IMAGE_SIZE = utils.rc((400, 400))
        self._create_parameters_from_locals(locals())

def run_gui():
    config = GuiConfig()
    if ENABLE_NETWORK:
        cr = network_interface.CommandRelayServer(config)
    else:
        cr = None
    app = Qt.QApplication(sys.argv)
    if 'dev' in sys.argv[1]:
        gui2 = VisionExperimentGui(config, cr)
    else:
        gui = Gui(config, cr)

    app.exec_()

if __name__ == '__main__':
#    m = Main()
#    m.start()    
    run_gui()
