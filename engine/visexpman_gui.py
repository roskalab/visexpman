#TODO: rename to visexp_gui.py
#TODO: timestamp to gui.hdf5 and string_timestamp node

ENABLE_NETWORK = True

import sys
import os
import time
import socket
import Queue
import os.path
import tempfile
import Image
import numpy
import shutil
import traceback
import re
import cPickle as pickle

import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

from visexpA.engine.datadisplay import imaged
import visexpman.engine.generic.utils as utils
import visexpman.engine.vision_experiment.configuration as configuration
import visexpman.engine.vision_experiment.gui as gui
from visexpman.engine.hardware_interface import network_interface
import visexpman.engine.generic.utils as utils
from visexpman.engine.generic import file
import visexpman.engine.generic as generic
import visexpman.engine.generic.geometry as geometry
import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner
import visexpA.engine.datahandlers.hdf5io as hdf5io
try:
    import visexpA.engine.dataprocessors.itk_image_registration as itk_image_registration
    import visexpA.engine.dataprocessors.itk_versor_rigid_registration as itk_versor_rigid_registration
except:
    print 'itk not installed'
from visexpman.engine.vision_experiment import experiment_data
try:
    import visexpA.engine.dataprocessors.signal as signal
except:
    pass
    
parameter_extract = re.compile('EOC(.+)EOP')

################### Main widget #######################
class VisionExperimentGui(QtGui.QWidget):
    def __init__(self, config, command_relay_server = None):
        self.config = config
        self.command_relay_server = command_relay_server
        self.console_text = ''
        self.mouse_files = []
        self.poller = gui.Poller(self)
        self.poller.start()
        self.queues = self.poller.queues
        QtGui.QWidget.__init__(self)
        self.setWindowTitle('Vision Experiment Manager GUI')
        self.resize(self.config.GUI_SIZE['col'], self.config.GUI_SIZE['row'])
        self.move(self.config.GUI_POSITION['col'], self.config.GUI_POSITION['row'])
        self.create_gui()
        self.create_layout()
        self.connect_signals()
        self.update_gui_items()
        self.show()
        
    def create_gui(self):
        self.debug_widget = gui.DebugWidget(self, self.config)
        self.regions_images_widget = gui.RegionsImagesWidget(self, self.config)
        self.overview_widget = gui.OverviewWidget(self, self.config)
        self.realignment_tab = QtGui.QTabWidget(self)
        self.realignment_tab.addTab(self.debug_widget, 'Debug')
        self.realignment_tab.setCurrentIndex(0)
        #Image tab
        self.image_tab = QtGui.QTabWidget(self)
        self.image_tab.addTab(self.regions_images_widget, 'Regions')
        self.image_tab.addTab(self.overview_widget, 'Overview')
        
        self.standard_io_widget = gui.StandardIOWidget(self, self.config)
        
        if hasattr(self.poller.two_photon_image, 'has_key'):
            if self.poller.two_photon_image.has_key(self.config.DEFAULT_PMT_CHANNEL):
                self.show_image(self.poller.two_photon_image[self.config.DEFAULT_PMT_CHANNEL], 0, 
                                self.poller.two_photon_image['scale']['row'], 
                                origin = self.poller.two_photon_image['origin'])
        if hasattr(self.poller.vertical_scan, 'has_key'):
            self.show_image(self.poller.vertical_scan['scaled_image'], 2, self.poller.vertical_scan['scale']['row'], origin = self.poller.two_photon_image['origin'])

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.realignment_tab, 0, 0, 1, 1)
        self.layout.addWidget(self.standard_io_widget, 1, 0, 1, 1)
        self.layout.addWidget(self.image_tab, 0, 1, 2, 1)
        self.layout.setRowStretch(3, 3)
        self.layout.setColumnStretch(2, 1)
        self.setLayout(self.layout)

    
    
            
    
        
    ####### Signals/functions ###############
    def connect_signals(self):
        
        self.connect(self.standard_io_widget.execute_python_button, QtCore.SIGNAL('clicked()'),  self.execute_python)
        self.connect(self.standard_io_widget.clear_console_button, QtCore.SIGNAL('clicked()'),  self.clear_console)
        self.connect(self.debug_widget.animal_parameters_groupbox.new_mouse_file_button, QtCore.SIGNAL('clicked()'),  self.save_animal_parameters)
        self.connect(self.debug_widget.show_connected_clients_button, QtCore.SIGNAL('clicked()'),  self.show_connected_clients)
        self.connect(self.debug_widget.show_network_messages_button, QtCore.SIGNAL('clicked()'),  self.show_network_messages)
        self.connect(self.debug_widget.stop_experiment_button, QtCore.SIGNAL('clicked()'),  self.stop_experiment)
        self.connect(self.debug_widget.graceful_stop_experiment_button, QtCore.SIGNAL('clicked()'),  self.graceful_stop_experiment)
        self.connect(self.debug_widget.start_experiment_button, QtCore.SIGNAL('clicked()'),  self.start_experiment)
        self.connect(self.debug_widget.send_command_button, QtCore.SIGNAL('clicked()'),  self.send_command)
        self.connect(self.debug_widget.save_two_photon_image_button, QtCore.SIGNAL('clicked()'),  self.poller.save_two_photon_image)
        self.connect(self, QtCore.SIGNAL('abort'), self.poller.abort_poller)
        self.connect(self.debug_widget.scan_region_groupbox.select_mouse_file, QtCore.SIGNAL('currentIndexChanged(int)'),  self.update_animal_parameter_display)
        self.connect(self.debug_widget.scan_region_groupbox.scan_regions_combobox, QtCore.SIGNAL('currentIndexChanged()'),  self.update_gui_items)
        
        #Blocking functions, run by poller
        self.signal_mapper = QtCore.QSignalMapper(self)
        self.connect_and_map_signal(self.debug_widget.read_stage_button, 'read_stage')
        self.connect_and_map_signal(self.debug_widget.set_stage_origin_button, 'set_stage_origin')
        self.connect_and_map_signal(self.debug_widget.move_stage_button, 'move_stage')
        self.connect_and_map_signal(self.debug_widget.move_stage_to_origin_button, 'move_stage_to_origin')
        self.connect_and_map_signal(self.debug_widget.set_objective_button, 'set_objective')
        self.connect_and_map_signal(self.debug_widget.z_stack_button, 'acquire_z_stack')
        self.connect_and_map_signal(self.debug_widget.scan_region_groupbox.get_two_photon_image_button, 'acquire_two_photon_image')
        self.connect_and_map_signal(self.debug_widget.scan_region_groupbox.snap_brain_surface_button, 'snap_brain_surface')
        self.connect_and_map_signal(self.debug_widget.scan_region_groupbox.vertical_scan_button, 'acquire_vertical_scan')
        self.connect_and_map_signal(self.debug_widget.scan_region_groupbox.add_button, 'add_scan_region')
        self.connect_and_map_signal(self.debug_widget.scan_region_groupbox.remove_button, 'remove_scan_region')
        self.connect_and_map_signal(self.debug_widget.scan_region_groupbox.register_button, 'register')
        self.connect_and_map_signal(self.debug_widget.scan_region_groupbox.realign_button, 'realign_region')
        self.connect_and_map_signal(self.debug_widget.scan_region_groupbox.move_to_button, 'move_to_region')
        #connect mapped signals to poller's pass_signal method that forwards the signal IDs.
        self.signal_mapper.mapped[str].connect(self.poller.pass_signal)
        
    def connect_and_map_signal(self, widget, mapped_signal_parameter, widget_signal_name = 'clicked'):
        self.signal_mapper.setMapping(widget, QtCore.QString(mapped_signal_parameter))
        getattr(getattr(widget, widget_signal_name), 'connect')(self.signal_mapper.map)

    def stop_experiment(self):
        command = 'SOCabort_experimentEOCguiEOP'
        self.queues['stim']['out'].put(command)
        
    def graceful_stop_experiment(self):
        command = 'SOCgraceful_stop_experimentEOCguiEOP'
        self.queues['stim']['out'].put(command)
        
    def start_experiment(self):
        params =  self.scanc()
        if len(params)>0:
            objective_positions = params.replace(',',  '<comma>')
            command = 'SOCexecute_experimentEOCobjective_positions={0}EOP' .format(objective_positions)
        else:
            command = 'SOCexecute_experimentEOCEOP'        
        self.queues['stim']['out'].put(command)

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
        if self.realignment_tab.currentIndex() == 0:
            widget = self.debug_widget
        
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
            #set selected mouse file to this one
            self.update_mouse_files_combobox(set_to_value = os.path.split(mouse_file_path)[-1])
            
    def update_mouse_files_combobox(self, set_to_value = None):
        new_mouse_files = file.filtered_file_list(self.config.EXPERIMENT_DATA_PATH,  'mouse')
        if self.mouse_files != new_mouse_files:
            self.mouse_files = new_mouse_files
            self.update_combo_box_list(self.debug_widget.scan_region_groupbox.select_mouse_file, self.mouse_files)
            if set_to_value != None:
                self.debug_widget.scan_region_groupbox.select_mouse_file.setCurrentIndex(self.mouse_files.index(set_to_value))

    def update_gui_items(self):
        '''
        Update comboboxes with file lists
        '''
        self.update_mouse_files_combobox()
        selected_mouse_file  = str(self.debug_widget.scan_region_groupbox.select_mouse_file.currentText())
        scan_regions = hdf5io.read_item(os.path.join(self.config.EXPERIMENT_DATA_PATH, selected_mouse_file), 'scan_regions')
        if scan_regions == None:
            scan_regions = {}
        #is new region added?
        if scan_regions.keys() != self.poller.scan_regions.keys():
            displayable_region_names = []
            for region in scan_regions.keys():
                if scan_regions[region].has_key('add_date'):
                    displayable_region_names.append(region + '  ' + scan_regions[region]['add_date'])
                else:
                    displayable_region_names.append(region)
            self.update_combo_box_list(self.debug_widget.scan_region_groupbox.scan_regions_combobox, displayable_region_names)
        self.poller.scan_regions = scan_regions
        #Display image of selected region
        selected_region = self.get_current_region_name()
        if hasattr(scan_regions, 'has_key'):
            if scan_regions.has_key(selected_region):
                line = None
                if scan_regions[selected_region].has_key('vertical_section'):
                    #convert line info from um to pixel
                    line = numpy.array([\
                                    scan_regions[selected_region]['vertical_section']['p1']['col'] - scan_regions[selected_region]['brain_surface']['origin']['col'],\
                                    -(scan_regions[selected_region]['vertical_section']['p1']['row'] - scan_regions[selected_region]['brain_surface']['origin']['row']),\
                                    scan_regions[selected_region]['vertical_section']['p2']['col'] - scan_regions[selected_region]['brain_surface']['origin']['col'],\
                                    -(scan_regions[selected_region]['vertical_section']['p2']['row'] - scan_regions[selected_region]['brain_surface']['origin']['row'])])
                    line /= scan_regions[selected_region]['brain_surface']['scale']['row']
                    line = line.tolist()
                    self.show_image(scan_regions[selected_region]['vertical_section']['scaled_image'], 3,
                                     scan_regions[selected_region]['vertical_section']['scale']['row'], 
                                     origin = scan_regions[selected_region]['vertical_section']['origin'])
                image_to_display = scan_regions[selected_region]['brain_surface']
                self.show_image(image_to_display['image'], 1, image_to_display['scale']['row'], line = line, origin = image_to_display['origin'])
                #update overwiew
                image, scale = experiment_data.merge_brain_regions(scan_regions, region_on_top = selected_region)
                self.show_image(image, 'overview', scale, origin = utils.rc((0, 0)))
                
        #Display coordinates of selected region
        if scan_regions.has_key(selected_region):
            if scan_regions[selected_region].has_key('add_date'):
                region_add_date = scan_regions[selected_region]['add_date']
            else:
                region_add_date = 'unknown'
            self.debug_widget.scan_region_groupbox.region_info.setText(\
                                                                           '{0:.2f}, {1:.2f}, {2:.2f}\n{3}' \
                                                                           .format(scan_regions[selected_region]['position']['x'][0], 
                                                                                   scan_regions[selected_region]['position']['y'][0], 
                                                                                   scan_regions[selected_region]['position']['z'][0], 
                                                                                   region_add_date))

    def update_animal_parameter_display(self, index):
        selected_mouse_file  = os.path.join(self.config.EXPERIMENT_DATA_PATH, str(self.debug_widget.scan_region_groupbox.select_mouse_file.currentText()))
        if os.path.exists(selected_mouse_file) and '.hdf5' in selected_mouse_file:
            h = hdf5io.Hdf5io(selected_mouse_file)
            varname = h.find_variable_in_h5f('animal_parameters')[0]
            h.load(varname)
            animal_parameters = getattr(h, varname)
            self.animal_parameters_str = '{2}, birth date: {0}, injection date: {1}, punch lr: {3},{4}, {5}, {6}'\
            .format(animal_parameters['mouse_birth_date'], animal_parameters['gcamp_injection_date'], animal_parameters['strain'], 
                    animal_parameters['ear_punch_l'], animal_parameters['ear_punch_r'], animal_parameters['gender'],  animal_parameters['anesthesia_protocol'])
            h.close()

        self.debug_widget.scan_region_groupbox.animal_parameters_label.setText(self.animal_parameters_str)

    def execute_python(self):
        try:
            exec(str(self.scanc()))
        except:
            self.printc(traceback.format_exc())

    def clear_console(self):
        self.console_text  = ''
        self.standard_io_widget.text_out.setPlainText(self.console_text)

    ####### Helpers ###############
    
    def show_image(self, image, channel, scale, line = None, origin = None):
        scale_indexed = scale
            
        if line != None:
            image_with_line = generic.draw_line_numpy_array(image, line)
        else:
            image_with_line = image
        if origin != None:
            origin_fixed = origin
            division = numpy.round(min(image_with_line.shape) *  scale_indexed/ 5.0, -1)
            image_with_sidebar = generic.draw_scalebar(image_with_line, origin_fixed, scale_indexed, division)
        else:
            image_with_sidebar = image_with_line
        if channel == 'overview':
            self.overview_widget.image_display.setPixmap(imaged.array_to_qpixmap(image_with_sidebar, self.config.OVERVIEW_IMAGE_SIZE))
            self.overview_widget.image_display.image = image_with_sidebar
            self.overview_widget.image_display.raw_image = image
            self.overview_widget.image_display.scale = scale_indexed
        else:
            self.regions_images_widget.image_display[channel].setPixmap(imaged.array_to_qpixmap(image_with_sidebar, self.config.IMAGE_SIZE))
            self.regions_images_widget.image_display[channel].image = image_with_sidebar
            self.regions_images_widget.image_display[channel].raw_image = image
            self.regions_images_widget.image_display[channel].scale = scale_indexed
        
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
        self.poller.log.info(text)

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
        
    def get_current_region_name(self):
        return str(self.debug_widget.scan_region_groupbox.scan_regions_combobox.currentText()).split(' ')[0]

    def closeEvent(self, e):
        e.accept()
        self.printc('Wait till server is closed')
        self.queues['mes']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.queues['stim']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.queues['analysis']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.emit(QtCore.SIGNAL('abort'))
        #delete files:
        for file_path in self.poller.files_to_delete:
            if os.path.exists(file_path):
                os.remove(file_path)
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
        if len(sys.argv) >1:
            arg = sys.argv[1]
        else:
            arg = ''
        if 'dev' in arg or 'development' in self.PACKAGE_PATH:
            CONTEXT_NAME = 'gui_dev.hdf5'
            data_folder = os.path.join(v_drive_folder, 'debug', 'data')
            MES_DATA_FOLDER = 'V:\\debug\\data'
            MES_DATA_PATH = os.path.join(v_drive_folder, 'debug', 'data')            
        else:
            CONTEXT_NAME = 'gui.hdf5'
            data_folder = os.path.join(v_drive_folder, 'experiment_data')
            MES_DATA_FOLDER = 'V:\\experiment_data'
            MES_DATA_PATH = os.path.join(v_drive_folder, 'experiment_data')
        self.MES_TIMEOUT = 5.0
        self.MAX_REGISTRATION_TIME = 30.0
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
        self.STAGE_TIMEOUT = 30.0

        #== GUI specific ==
        GUI_POSITION = utils.cr((10, 10))
        GUI_SIZE = utils.cr((1200, 800))
        TAB_SIZE = utils.cr((500, 800))
        IMAGE_SIZE = utils.rc((400, 400))
        OVERVIEW_IMAGE_SIZE = utils.rc((800, 800))
        self._create_parameters_from_locals(locals())

def run_gui():
    config = GuiConfig()
    if ENABLE_NETWORK:
        cr = network_interface.CommandRelayServer(config)
    else:
        cr = None
    app = Qt.QApplication(sys.argv)
    gui2 = VisionExperimentGui(config, cr)
    app.exec_()

if __name__ == '__main__':
    run_gui()
