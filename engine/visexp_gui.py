import sys
import os
import io
import time
import socket
import Queue
import os.path
import tempfile
import numpy
import shutil
import traceback
import re
import copy
import cPickle as pickle
import scipy.ndimage
import Image
import ImageDraw
import ImageFont

import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

import visexpman
from visexpA.engine.datadisplay import imaged
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import configuration
from visexpman.engine.vision_experiment import gui
from visexpman.engine.hardware_interface import network_interface
from visexpman.engine.generic import utils
from visexpman.engine.generic import file
from visexpman.engine import generic
from visexpman.engine.generic import log
from visexpman.users.zoltan.test import unit_test_runner
from visexpA.engine.datahandlers import hdf5io
from visexpA.engine.dataprocessors import generic as generic_visexpA

MAX_NUMBER_OF_DISPLAYED_MEASUREMENTS = 40
MAX_ANESTHESIA_ENTRIES = 25
parameter_extract = re.compile('EOC(.+)EOP')

ENABLE_MOUSE_FILE_HANDLER = False

################### Main widget #######################
class VisionExperimentGui(QtGui.QWidget):
    '''
    Main Qt GUI class of vision experiment manager gui.
    '''
    def __init__(self, user, config_class):
        #Fetching classes takes long time
        self.config = utils.fetch_classes('visexpman.users.'+user, classname = config_class, required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig)[0][1]()
        self.config.user = user
        self.console_text = ''
        self.log = log.Log('gui log', file.generate_filename(os.path.join(self.config.LOG_PATH, 'gui_log.txt')), local_saving = True)
        self.poller = gui.MainPoller(self)
        self.queues = self.poller.queues
        if ENABLE_MOUSE_FILE_HANDLER:
            self.mouse_file_handler = gui.MouseFileHandler(self)
        self.gui_tester = GuiTest(self)
        QtGui.QWidget.__init__(self)
        self.setWindowTitle('Vision Experiment Manager GUI - {0} - {1}' .format(user,  config_class))
        icon_path = os.path.join(os.path.split(visexpman.__file__)[0],'data','images','grabowsky.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(Qt.QIcon(icon_path))
        self.resize(self.config.GUI_SIZE['col'], self.config.GUI_SIZE['row'])
        self.move(self.config.GUI_POSITION['col'], self.config.GUI_POSITION['row'])
        self.create_gui()
        self.create_layout()
        self.block_widgets(True)
        self.connect_signals()
        self.init_variables()
        self.poller.start()
        if ENABLE_MOUSE_FILE_HANDLER:
            self.mouse_file_handler.start()
        self.show()
        self.init_widget_content()
        self.block_widgets(False)
        
    def create_gui(self):
        self.main_widget = gui.MainWidget(self, self.config)
        self.animal_parameters_widget = gui.AnimalParametersWidget(self, self.config)
        self.images_widget = gui.ImagesWidget(self, self.config)
        self.overview_widget = gui.OverviewWidget(self, self.config)
        self.roi_widget = gui.RoiWidget(self, self.config)
        self.common_widget = gui.CommonWidget(self, self.config)
        self.helpers_widget = gui.HelpersWidget(self, self.config)
        self.main_tab = QtGui.QTabWidget(self)
        self.main_tab.addTab(self.main_widget, 'Main')
        self.main_tab.addTab(self.roi_widget, 'ROI')
        self.main_tab.addTab(self.animal_parameters_widget, 'Animal parameters')
        self.main_tab.addTab(self.helpers_widget, 'Helpers')
        self.main_tab.setCurrentIndex(0)
        #Image tab
        self.image_tab = QtGui.QTabWidget(self)
        self.image_tab.addTab(self.images_widget, 'Regions')
        self.image_tab.addTab(self.overview_widget, 'Overview')
        self.standard_io_widget = gui.StandardIOWidget(self, self.config)
        experiment_config_list = utils.fetch_classes('visexpman.users.' + self.config.user,  required_ancestors = visexpman.engine.vision_experiment.experiment.ExperimentConfig, direct = False)
        experiment_config_names = []
        for experiment_config in experiment_config_list:
            experiment_config_names.append(experiment_config[1].__name__)
        experiment_config_names.sort()
        self.main_widget.experiment_control_groupbox.experiment_name.addItems(QtCore.QStringList(experiment_config_names))
        self.main_widget.experiment_control_groupbox.experiment_name.setCurrentIndex(experiment_config_names.index('ShortMovingGratingConfig'))
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.main_tab, 0, 0, 1, 1)
        self.layout.addWidget(self.common_widget, 1, 0, 1, 1)
        self.layout.addWidget(self.standard_io_widget, 2, 0, 1, 1)
        self.layout.addWidget(self.image_tab, 0, 1, 5, 1)
        self.layout.setRowStretch(3, 3)
        self.layout.setColumnStretch(2, 1)
        self.setLayout(self.layout)
        
    def init_widget_content(self):
        self.update_widgets_when_mouse_file_changed(selected_region = self.poller.last_region_name)
        if hasattr(self.poller, 'mouse_file'):
            self.update_mouse_files_combobox(os.path.split(self.poller.mouse_file)[1])#Ensuring that the filename coming from the last session is set
        if utils.safe_has_key(self.poller.xy_scan, self.config.DEFAULT_PMT_CHANNEL):
            self.show_image(self.poller.xy_scan[self.config.DEFAULT_PMT_CHANNEL], 0, self.poller.xy_scan['scale'], origin = self.poller.xy_scan['origin'])
        if utils.safe_has_key(self.poller.xz_scan, 'scaled_image'):
            self.show_image(self.poller.xz_scan['scaled_image'], 2, self.poller.xz_scan['scaled_scale'], origin = self.poller.xz_scan['origin'])

    def init_variables(self):
        self.mouse_files = []
        
    ####### Signals/functions ###############
    def block_widgets(self,  block):
        if not hasattr(self, 'blocked_widgets'):
            self.blocked_widgets =  [self.main_widget.scan_region_groupbox.select_mouse_file, self.main_tab, 
                  self.main_widget.scan_region_groupbox.scan_regions_combobox, self.animal_parameters_widget.new_mouse_file_button, 
                  self.roi_widget.select_cell_combobox, self.roi_widget.cell_filter_name_combobox,  self.roi_widget.cell_filter_combobox, 
                    self.roi_widget.show_selected_soma_rois_checkbox, self.roi_widget.show_current_soma_roi_checkbox, 
                    self.roi_widget.show_selected_roi_centers_checkbox, self.roi_widget.cell_group_combobox]
        [w.blockSignals(block) for w in self.blocked_widgets]

    def connect_signals(self):
        self.signal_mapper = QtCore.QSignalMapper(self)
        #Poller control
        self.connect(self.helpers_widget.gui_test_button, QtCore.SIGNAL('clicked()'), self.gui_tester.start_test)
        #GUI events
        self.connect(self.main_tab, QtCore.SIGNAL('currentChanged(int)'),  self.tab_changed)
#        self.connect_and_map_signal(self.main_tab, 'save_cells', 'currentChanged')
        self.connect(self.common_widget.show_gridlines_checkbox, QtCore.SIGNAL('stateChanged(int)'),  self.gridline_checkbox_changed)
        self.connect(self.common_widget.registration_subimage_combobox, QtCore.SIGNAL('editTextChanged(const QString &)'),  self.subimage_parameters_changed)
        
        self.connect_and_map_signal(self.main_widget.scan_region_groupbox.select_mouse_file, 'mouse_file_changed', 'currentIndexChanged')
        self.connect(self.main_widget.scan_region_groupbox.scan_regions_combobox, QtCore.SIGNAL('currentIndexChanged(int)'),  self.region_name_changed)

        self.connect_and_map_signal(self.animal_parameters_widget.new_mouse_file_button, 'save_animal_parameters')
        self.connect_and_map_signal(self.animal_parameters_widget.anesthesia_history_groupbox.add_button, 'add_to_anesthesia_history')
        self.connect_and_map_signal(self.animal_parameters_widget.anesthesia_history_groupbox.remove_button, 'remove_last_from_anesthesia_history')
        #Experiment control
        self.connect_and_map_signal(self.main_widget.experiment_control_groupbox.stop_experiment_button, 'stop_experiment')
        self.connect_and_map_signal(self.main_widget.experiment_control_groupbox.graceful_stop_experiment_button, 'graceful_stop_experiment')
        #Data processing
        #ROI
        self.connect_and_map_signal(self.roi_widget.accept_cell_button, 'accept_cell')
        self.connect_and_map_signal(self.roi_widget.ignore_cell_button, 'ignore_cell')
        self.connect_and_map_signal(self.roi_widget.next_button, 'next_cell')
        self.connect_and_map_signal(self.roi_widget.previous_button, 'previous_cell')
        self.connect(self.roi_widget.select_cell_combobox, QtCore.SIGNAL('currentIndexChanged(int)'),  self.select_cell_changed)
        self.connect(self.roi_widget.cell_filter_name_combobox, QtCore.SIGNAL('currentIndexChanged(int)'),  self.cell_filtername_changed)
        self.connect(self.roi_widget.cell_filter_combobox, QtCore.SIGNAL('currentIndexChanged(int)'),  self.cell_filter_changed)
        self.connect(self.roi_widget.show_selected_soma_rois_checkbox, QtCore.SIGNAL('stateChanged(int)'),  self.show_soma_roi_checkbox_changed)
        self.connect(self.roi_widget.show_current_soma_roi_checkbox, QtCore.SIGNAL('stateChanged(int)'),  self.show_soma_roi_checkbox_changed)
        self.connect(self.roi_widget.show_selected_roi_centers_checkbox, QtCore.SIGNAL('stateChanged(int)'),  self.show_soma_roi_checkbox_changed)
        self.connect(self.roi_widget.cell_group_combobox, QtCore.SIGNAL('currentIndexChanged(int)'),  self.cell_group_changed)
        
        #Network debugger tools
        self.connect_and_map_signal(self.helpers_widget.show_connected_clients_button, 'show_connected_clients')
        self.connect_and_map_signal(self.helpers_widget.show_network_messages_button, 'show_network_messages')
        self.connect_and_map_signal(self.helpers_widget.send_command_button, 'send_command')
        #Helpers
        self.connect_and_map_signal(self.helpers_widget.help_button, 'show_help')
        self.connect(self.helpers_widget.save_xy_scan_button, QtCore.SIGNAL('clicked()'),  self.poller.save_xy_scan_to_file)
        self.connect(self.standard_io_widget.execute_python_button, QtCore.SIGNAL('clicked()'),  self.execute_python)
        self.connect(self.standard_io_widget.clear_console_button, QtCore.SIGNAL('clicked()'),  self.clear_console)
        self.connect_and_map_signal(self.helpers_widget.add_simulated_measurement_file_button, 'add_simulated_measurement_file')
        self.connect_and_map_signal(self.helpers_widget.rebuild_cell_database_button, 'rebuild_cell_database')

        self.connect_and_map_signal(self.main_widget.measurement_datafile_status_groupbox.remove_measurement_button, 'remove_measurement_file_from_database')
        self.connect_and_map_signal(self.main_widget.measurement_datafile_status_groupbox.set_state_to_button, 'set_measurement_file_process_state')
        self.connect_and_map_signal(self.main_widget.measurement_datafile_status_groupbox.reset_jobhandler_button, 'reset_jobhandler')
        self.connect_and_map_signal(self.main_widget.measurement_datafile_status_groupbox.add_id_button, 'add_id')

        #Blocking functions, run by poller
        self.connect_and_map_signal(self.common_widget.read_stage_button, 'read_stage')
        self.connect_and_map_signal(self.common_widget.set_stage_origin_button, 'set_stage_origin')
        self.connect_and_map_signal(self.common_widget.move_stage_button, 'move_stage')
        self.connect_and_map_signal(self.common_widget.tilt_brain_surface_button, 'tilt_brain_surface')
        self.connect_and_map_signal(self.common_widget.stop_stage_button, 'stop_stage')
        self.connect_and_map_signal(self.common_widget.set_objective_button, 'set_objective')
        self.connect_and_map_signal(self.common_widget.register_button, 'register')
#        self.connect_and_map_signal(self.main_widget.set_objective_value_button, 'set_objective_relative_value')
        self.connect_and_map_signal(self.main_widget.z_stack_button, 'acquire_z_stack')
        self.connect_and_map_signal(self.main_widget.scan_region_groupbox.get_xy_scan_button, 'acquire_xy_scan')
        self.connect_and_map_signal(self.main_widget.scan_region_groupbox.xz_scan_button, 'acquire_xz_scan')
        self.connect_and_map_signal(self.main_widget.scan_region_groupbox.add_button, 'add_scan_region')
        self.connect_and_map_signal(self.main_widget.scan_region_groupbox.remove_button, 'remove_scan_region')
        self.connect_and_map_signal(self.main_widget.scan_region_groupbox.update_xy_button, 'save_xy_scan')
        self.connect_and_map_signal(self.main_widget.scan_region_groupbox.update_xz_button, 'save_xz_scan')
        self.connect_and_map_signal(self.main_widget.scan_region_groupbox.update_xyt_button, 'save_xyt_scan')
        self.connect_and_map_signal(self.main_widget.scan_region_groupbox.move_to_button, 'move_to_region')
        self.connect_and_map_signal(self.roi_widget.create_xz_lines_button, 'create_xz_lines')
        self.connect_and_map_signal(self.roi_widget.xy_scan_button, 'acquire_xy_scan')
        self.connect_and_map_signal(self.main_widget.experiment_control_groupbox.start_experiment_button, 'start_experiment')
        self.connect_and_map_signal(self.main_widget.experiment_control_groupbox.next_depth_button, 'next_experiment')
        self.connect_and_map_signal(self.main_widget.experiment_control_groupbox.redo_depth_button, 'redo_experiment')
        self.connect_and_map_signal(self.main_widget.experiment_control_groupbox.previous_depth_button, 'previous_experiment')
#        self.connect_and_map_signal(self.main_widget.experiment_control_groupbox.identify_flourescence_intensity_distribution_button, 'identify_flourescence_intensity_distribution')
        #connect mapped signals to poller's pass_signal method that forwards the signal IDs.
        self.signal_mapper.mapped[str].connect(self.poller.pass_signal)
        
    def connect_and_map_signal(self, widget, mapped_signal_parameter, widget_signal_name = 'clicked'):
        if hasattr(self.poller, mapped_signal_parameter):
            self.signal_mapper.setMapping(widget, QtCore.QString(mapped_signal_parameter))
            getattr(getattr(widget, widget_signal_name), 'connect')(self.signal_mapper.map)
        else:
            self.printc('{0} method does not exists'.format(mapped_signal_parameter))
            
    ############ GUI events ############
    def mouse_file_list_changed(self):
        self.update_mouse_files_combobox(set_to_value = os.path.split(self.poller.mouse_file)[1])
            
    def tab_changed(self, currentIndex):
        if currentIndex != 1:#If user switched from ROI tab, save cell selections
            self.poller.signal_id_queue.put('save_cells')
        #Load meanimages or scan region images
        image_widget = self.images_widget.image_display[0]
        if currentIndex == 0:
            self.update_scan_regions()
            self.show_image(image_widget.raw_image, 0, image_widget.scale, line = image_widget.line, origin = image_widget.origin)
        elif currentIndex == 1:
            self.update_meanimage()
            self.show_image(image_widget.raw_image, 0, image_widget.scale, line = image_widget.line, origin = image_widget.origin)
            self.update_cell_info()
            
    def gridline_checkbox_changed(self):
        self.update_gridlined_images()

    def subimage_parameters_changed(self):
        self.update_xy_images()
        
    def show_soma_roi_checkbox_changed(self):
        self.update_meanimage()
        
    def cell_group_changed(self):
        self.update_meanimage()
        self.update_suggested_depth_label()
            
    def region_name_changed(self):
        self.update_scan_regions()
        self.update_jobhandler_process_status()
        self.update_cell_list()
        self.update_cell_group_combobox()
        self.update_file_id_combobox()
        self.update_roi_curves_display()
        self.update_suggested_depth_label()
        
    def select_cell_changed(self):
        self.update_roi_curves_display()
        self.update_meanimage()
        self.update_suggested_depth_label()
        self.update_cell_info()
        self.update_cell_group_combobox()
                
    def cell_filtername_changed(self):
        self.update_cell_filter_list()
        self.update_cell_list()
        self.update_meanimage()
        self.update_roi_curves_display()
        
    def cell_filter_changed(self):
        self.update_cell_list()
        self.update_meanimage()
        self.update_roi_curves_display()

    ################### GUI updaters #################
    def update_anesthesia_history(self):
        text = 'Time\t\tsubstance\t\tamount\t\tcomment\n'
        if hasattr(self.poller, 'anesthesia_history'):
            for entry in self.poller.anesthesia_history[-MAX_ANESTHESIA_ENTRIES:]:
                text += '{0}:\t{1}\t\t{2}\t\t{3}\n' .format(utils.timestamp2ymdhm(entry['timestamp']), entry['substance'], entry['amount'], entry['comment'])
        self.animal_parameters_widget.anesthesia_history_groupbox.history_label.setText(text)
        
    def update_anesthesia_history_date_widget(self):
        now = time.localtime()
        self.animal_parameters_widget.anesthesia_history_groupbox.date.setDateTime(QtCore.QDateTime(QtCore.QDate(now.tm_year, now.tm_mon, now.tm_mday), QtCore.QTime(now.tm_hour, now.tm_min)))
        
    def update_widgets_when_mouse_file_changed(self, selected_region=None):
        self.update_animal_parameter_display()
        self.update_region_names_combobox(selected_region = selected_region)
        self.update_scan_regions()
        self.update_jobhandler_process_status()
        self.update_file_id_combobox()
        self.update_cell_list()
        self.update_roi_curves_display()
        self.update_cell_group_combobox()
        self.update_suggested_depth_label()
        self.update_anesthesia_history()
        
    def update_mouse_files_combobox(self, set_to_value = None):
            self.update_combo_box_list(self.main_widget.scan_region_groupbox.select_mouse_file, self.poller.mouse_files)
            if set_to_value != None and set_to_value in self.poller.mouse_files:
                self.main_widget.scan_region_groupbox.select_mouse_file.setCurrentIndex(self.poller.mouse_files.index(set_to_value))
            return True
                
    def update_position_display(self):
        display_position = numpy.round(self.poller.stage_position - self.poller.stage_origin, 2)
        if hasattr(self.poller, 'objective_position'):
            display_position[-1] = self.poller.objective_position
        self.common_widget.current_position_label.setText('{0:.2f}, {1:.2f}, {2:.2f}' .format(display_position[0], display_position[1], display_position[2]))
        
    def update_animal_parameter_display(self):
        if hasattr(self.poller, 'animal_parameters'):
            animal_parameters = self.poller.animal_parameters
            self.animal_parameters_str = '{6}, {2}, birth date: {0}, injection date: {1}, punch lr: {3},{4}, {5}'\
            .format(animal_parameters['mouse_birth_date'], animal_parameters['gcamp_injection_date'], animal_parameters['strain'], 
                    animal_parameters['ear_punch_l'], animal_parameters['ear_punch_r'], animal_parameters['gender'], animal_parameters['id'])
            self.main_widget.scan_region_groupbox.animal_parameters_label.setText(self.animal_parameters_str)
            
    def update_region_names_combobox(self, selected_region = None):
        #Update combobox containing scan region names
        if hasattr(self.poller.scan_regions, 'keys'):
            region_names = self.poller.scan_regions.keys()
            region_names.sort()
            self.update_combo_box_list(self.main_widget.scan_region_groupbox.scan_regions_combobox, region_names, selected_item = selected_region)
        else:
            self.update_combo_box_list(self.main_widget.scan_region_groupbox.scan_regions_combobox, [])
            
    def update_scan_regions(self, selected_region = None):
        if selected_region is None:
            selected_region = self.get_current_region_name()
        no_scale = utils.rc((1.0, 1.0))
        if utils.safe_has_key(self.poller.scan_regions, selected_region):
            scan_regions = self.poller.scan_regions
            self.roi_widget.scan_region_name_label.setText('Current scan region is {0}'.format(selected_region))
            line = []
            #Update xz image if exists and collect xy line(s)
            if scan_regions[selected_region].has_key('xz'):
                line = [[ scan_regions[selected_region]['xz']['p1']['row'] , scan_regions[selected_region]['xz']['p1']['col'], 
                             scan_regions[selected_region]['xz']['p2']['row'] , scan_regions[selected_region]['xz']['p2']['col'] ]]
                self.show_image(scan_regions[selected_region]['xz']['scaled_image'], 3,
                                     scan_regions[selected_region]['xz']['scaled_scale'], 
                                     origin = scan_regions[selected_region]['xz']['origin'])
            else:
                self.show_image(self.images_widget.blank_image, 3, no_scale)
            #Display xy image
            image_to_display = scan_regions[selected_region]['xy']
            self.xz_line = line
            self.show_image(image_to_display['image'], 1, image_to_display['scale'], line = line, origin = image_to_display['origin'])
            #update overwiew
            image, scale = imaged.merge_brain_regions(scan_regions, region_on_top = selected_region)
            self.show_image(image, 'overview', scale, origin = utils.rc((0, 0)))
            #Update region info
            if scan_regions[selected_region].has_key('add_date'):
                region_add_date = scan_regions[selected_region]['add_date']
            else:
                region_add_date = 'unknown'
            self.main_widget.scan_region_groupbox.region_info.setText('{3}\n{0:.2f}, {1:.2f}, {2:.2f}' 
                                                                      .format(scan_regions[selected_region]['position']['x'][0], scan_regions[selected_region]['position']['y'][0], 
                                                                              scan_regions[selected_region]['position']['z'][0], region_add_date))
        else:
                self.show_image(self.images_widget.blank_image, 1, no_scale, origin = utils.rc((0, 0)))
                self.show_image(self.images_widget.blank_image, 3, no_scale, origin = utils.rc((0, 0)))
                self.show_image(self.images_widget.blank_image, 'overview', no_scale, origin = utils.rc((0, 0)))
                self.main_widget.scan_region_groupbox.region_info.setText('')
                
    def update_file_id_combobox(self):
        region_name = self.get_current_region_name()
        scan_regions = self.poller.scan_regions
        if utils.safe_has_key(scan_regions, region_name) and utils.safe_has_key(scan_regions[region_name], 'process_status'):
            ids = scan_regions[region_name]['process_status'].keys()
            ids.sort()
            ids.reverse()
            self.update_combo_box_list(self.main_widget.measurement_datafile_status_groupbox.ids_combobox,ids)
        else:
            self.update_combo_box_list(self.main_widget.measurement_datafile_status_groupbox.ids_combobox,[])
                
    def update_jobhandler_process_status(self):
        scan_regions = self.poller.scan_regions
        region_name = self.get_current_region_name()
        if utils.safe_has_key(scan_regions, region_name) and scan_regions[region_name].has_key('process_status'):
            status_text = ''
            ids = scan_regions[region_name]['process_status'].keys()
            ids.sort()
            ids = ids[-MAX_NUMBER_OF_DISPLAYED_MEASUREMENTS:]
            for id in ids:
                status = scan_regions[region_name]['process_status'][id]
                if status['info'].has_key('depth'):
                    depth = int(status['info']['depth'])
                else:
                    depth = ''
                if status['info'].has_key('stimulus'):
                    stimulus = str(status['info']['stimulus']).replace('Config', '')#For unknown reason this is not always string type
                else:
                    stimulus = ''
                if status['info'].has_key('scan_mode'):
                    scan_mode = status['info']['scan_mode']
                else:
                    scan_mode = ''
                if status['info'].has_key('laser_intensity'):
                    try:
                        laser_intensity = float(status['info']['laser_intensity'])
                    except ValueError:
                        laser_intensity = 0.0
                else:
                    laser_intensity = 0.0
                if status['find_cells_ready']:
                    if status['info'].has_key('number_of_cells'):
                        status = '{0} cells' .format(status['info']['number_of_cells'])
                    else:
                        status = 'ready'
                elif status['mesextractor_ready']:
                    status = '**'
                elif status['fragment_check_ready']:
                    status = '*'
                else:
                    status = '*'
                status_text += '{0}, {1}, {2}, {3}, {4:0.1f} %: {5}\n'.format(scan_mode, stimulus, depth,  id, laser_intensity, status)
        else:
            status_text = ''
        self.main_widget.measurement_datafile_status_groupbox.process_status_label.setText(status_text)

    def update_cell_list(self):
        region_name = self.get_current_region_name()
        if region_name == '':
                self.update_combo_box_list(self.roi_widget.select_cell_combobox, [])
                return
        if hasattr(self.poller, 'cells') and utils.safe_has_key(self.poller.cells, region_name): #To handle situations when region name is being edited by user
            self.poller.cell_ids = self.poller.cells[region_name].keys()
            filter = str(self.roi_widget.cell_filter_combobox.currentText())
            filtername = str(self.roi_widget.cell_filter_name_combobox.currentText())
            if filtername != 'No filter':
                if filtername == 'date':
                    key_name = 'add_date'
                else:
                    key_name = filtername
                self.poller.cell_ids = [cell_id for cell_id, cell in self.poller.cells[region_name].items() if filter in str(cell[key_name])]
            self.poller.cell_ids.sort()
            self.update_combo_box_list(self.roi_widget.select_cell_combobox,self.poller.cell_ids)
        else:
            self.update_combo_box_list(self.roi_widget.select_cell_combobox, [])
            
    def update_cell_filter_list(self):
        if hasattr(self.poller, 'cells'):
            filtername = str(self.roi_widget.cell_filter_name_combobox.currentText())
            region_name = self.get_current_region_name()
            if region_name == '':
                return
            filter_values = []
            if filtername == 'date':
                key_name = 'add_date'
            else:
                key_name = filtername
            if utils.safe_has_key(self.poller.cells, region_name):
                for cell_id in self.poller.cells[region_name].keys():
                    if self.poller.cells[region_name][cell_id].has_key(key_name):
                        value = str(self.poller.cells[region_name][cell_id][key_name])
                        if key_name =='add_date':
                            value = value.split(' ')[0]
                        if value not in filter_values:
                            filter_values.append(value)
                filter_values.sort()
                self.update_combo_box_list(self.roi_widget.cell_filter_combobox,filter_values)
            self.update_cell_list()#This is necessary to update cell list if  'No filter' is selected but reason unknown
            
    def update_cell_info(self):
        region_name = self.get_current_region_name()
        text = ''
        if hasattr(self.poller, 'cells') and self.poller.cells.has_key(region_name) and region_name != '':
            cell_name = self.get_current_cell_id()
            if self.poller.cells[region_name].has_key(cell_name):
                if not self.poller.cells[region_name][cell_name]['accepted']:
                    info = 'not selected'
                else:
                    info = self.poller.cells[region_name][cell_name]['group']
                text = '{0}: {1}'.format(cell_name, info)
        self.roi_widget.cell_info.setText(text)
            
    def update_cell_group_combobox(self):
        region_name = self.get_current_region_name()
        if region_name == '':
                return
        if hasattr(self.poller, 'cells') and self.poller.cells.has_key(region_name):
            cell_groups = []
            for cell_id, cell_info in self.poller.cells[region_name].items():
                if cell_info['accepted'] and not cell_info['group'] in cell_groups and cell_info['group'] != 'none' and cell_info['group'] != '':
                    cell_groups.append(cell_info['group'])
            cell_groups.sort()
            self.update_combo_box_list(self.roi_widget.cell_group_combobox, cell_groups)
        else:
            self.update_combo_box_list(self.roi_widget.cell_group_combobox, [])
            
    def update_meanimage(self):
        measurement_id = self.get_current_cell_id().split('_')
        if len(measurement_id) < 2:
            return
        else:
            measurement_id = measurement_id[1]
        region_name = self.get_current_region_name()
        if hasattr(self.poller, 'images') and utils.safe_has_key(self.poller.images, measurement_id) and utils.safe_has_key(self.poller.cells, region_name) and self.main_tab.currentIndex() == 1:
            cell_group = self.get_current_cell_group()
            image_record = self.poller.images[measurement_id]
            scale = utils.cr(utils.nd(image_record['scale'])[0])
            origin = utils.rcd(utils.nd(image_record['origin'])[0])
            cells_to_display = []
            soma_rois_to_display = []
            for cell_i in self.poller.cells[region_name].values():
                if cell_i['group'] == cell_group and cell_i['accepted']:
                    if self.roi_widget.show_selected_roi_centers_checkbox.checkState() != 0:
                        cells_to_display.append(cell_i['roi_center'])
                    if self.roi_widget.show_selected_soma_rois_checkbox.checkState() != 0:
                        soma_rois_to_display.append(cell_i['soma_roi'])
            if self.roi_widget.show_current_soma_roi_checkbox.checkState() != 0:
                soma_rois_to_display.append(self.poller.cells[region_name][self.get_current_cell_id()]['soma_roi'])
            mi = numpy.take(image_record['meanimage'], [0, 0, 0], axis=2).copy()
            try:
                meanimage = imaged.draw_on_meanimage(mi, origin, scale, soma_rois = soma_rois_to_display, used_rois = cells_to_display)
            except:
                meanimage = mi
                self.printc(traceback.format_exc())
            self.show_image(scipy.ndimage.rotate(meanimage,-90), 1, scale, origin = origin)

    def update_suggested_depth_label(self):
        self.poller.calculate_suggested_depth()
        self.roi_widget.suggested_depth_label.setText('Suggested depth: {0:.0f} um'.format(self.poller.suggested_depth))

    def update_roi_curves_display(self):
        #setdata(blockplotpoints["full"], ylabel='Fluorescence', vlines = vlines, xlabel =tlabels, vlinelimits=vlinelimits, penwidth=w,  color=Qt.Qt.black,  axisscale=axislims )
        region_name = self.get_current_region_name()
        cell_id = self.get_current_cell_id()
        if cell_id != '' and utils.safe_has_key(self.poller.cells, region_name) and utils.safe_has_key(self.poller.cells[region_name], cell_id) and \
                    utils.safe_has_key(self.poller.cells[region_name][cell_id], 'roi_plot'):
            plot_info = self.poller.cells[region_name][cell_id]['roi_plot']
            self.roi_widget.roi_plot.setdata(plot_info['curve'], vlines = plot_info['vlines'], penwidth=1.5, color=Qt.Qt.black)
            self.roi_widget.roi_plot.adddata(plot_info['curve'].mean(axis=-1),color=[Qt.Qt.darkRed, Qt.Qt.darkGreen], penwidth=3)
            self.roi_widget.roi_plot.setaxisscale([0, plot_info['curve'].shape[0], plot_info['curve'].min(), plot_info['curve'].max()])
        else:
            self.roi_widget.roi_plot.clear()

    def show_image(self, image, channel, scale, line = [], origin = utils.rc((0, 0))):
        image_in = {}
        image_in['image'] = generic_visexpA.normalize(image, outtype=numpy.uint8, std_range = 10)
        image_in['scale'] = scale
        image_in['origin'] = origin
        if channel == 'overview':
            image_with_sidebar = generate_gui_image(image_in, self.config.OVERVIEW_IMAGE_SIZE, self.config, lines  = line)
            self.overview_widget.image_display.setPixmap(imaged.array_to_qpixmap(image_with_sidebar, self.config.OVERVIEW_IMAGE_SIZE))
            self.overview_widget.image_display.image = image_with_sidebar
            self.overview_widget.image_display.raw_image = image
            self.overview_widget.image_display.scale = scale
        else:
            box = self.get_subimage_box()
            gridlines = (self.common_widget.show_gridlines_checkbox.checkState() != 0)
            if gridlines:
                sidebar_fill = (100, 50, 0)
                if (channel == 0 or channel ==1) and len(box) == 4 and self.main_tab.currentIndex() != 1:
                    line = generic.box_to_lines(box)
                else:
                    line = [] #Do not  show any lines when gridlines are displayed
            else:
                sidebar_fill = (0, 0, 0)
            image_with_sidebar = generate_gui_image(image_in, self.config.IMAGE_SIZE, self.config, lines  = line, 
                                                    sidebar_fill = sidebar_fill, 
                                                    gridlines = gridlines)
            self.images_widget.image_display[channel].setPixmap(imaged.array_to_qpixmap(image_with_sidebar, self.config.IMAGE_SIZE))
            self.images_widget.image_display[channel].image = image_with_sidebar
            self.images_widget.image_display[channel].raw_image = image
            self.images_widget.image_display[channel].scale = scale
            self.images_widget.image_display[channel].origin = origin
            self.images_widget.image_display[channel].line = line
            
    def update_gridlined_images(self):
        for i in range(4):
            image_widget = self.images_widget.image_display[i]
            if hasattr(image_widget, 'raw_image'):#This check is necessary because unintialized xz images does not have raw_image attribute
                if i == 1 and (self.common_widget.show_gridlines_checkbox.checkState() == 0):
                    line = self.xz_line
                else:
                    line = image_widget.line
                self.show_image(image_widget.raw_image, i, image_widget.scale, line = line, origin = image_widget.origin)
                
    def update_xy_images(self):
        for i in range(2):
            image_widget = self.images_widget.image_display[i]
            if hasattr(image_widget, 'raw_image'):
                self.show_image(image_widget.raw_image, i, image_widget.scale, line = image_widget.line, origin = image_widget.origin)
        
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
            
    ######## GUI widget readers ###############
    def get_current_region_name(self):
        return str(self.main_widget.scan_region_groupbox.scan_regions_combobox.currentText())
        
    def get_current_cell_id(self):
        return str(self.roi_widget.select_cell_combobox.currentText())
        
    def get_current_cell_group(self):
        return str(self.roi_widget.cell_group_combobox.currentText())
        
    def get_current_file_id(self):
        return str(self.main_widget.measurement_datafile_status_groupbox.ids_combobox.currentText())
        
    def get_subimage_box(self):
        subimage_parameters = self.common_widget.registration_subimage_combobox.currentText()
        box = subimage_parameters.split(',')
        if len(box) != 4:
            box = []
        else:
            try:
                box = map(float, box)
            except:
                box = []
        return box
        
    ########## GUI utilities, misc functions #############
    def ask4confirmation(self, action2confirm):
        utils.empty_queue(self.poller.gui_thread_queue)
        reply = QtGui.QMessageBox.question(self, 'Confirm following action', action2confirm, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.No:
            self.poller.gui_thread_queue.put(False)
        else:
            self.poller.gui_thread_queue.put(True)

    def execute_python(self):
        try:
            exec(str(self.scanc()))
        except:
            self.printc(traceback.format_exc())

    def clear_console(self):
        self.console_text  = ''
        self.standard_io_widget.text_out.setPlainText(self.console_text)
        
    def printc(self, text):       
        if not isinstance(text, str):
            text = str(text)
        self.console_text  += text + '\n'
        self.standard_io_widget.text_out.setPlainText(self.console_text)
        self.standard_io_widget.text_out.moveCursor(QtGui.QTextCursor.End)
#        print text
        try:
            self.log.info(text)
        except:
            print 'gui: logging error'

    def scanc(self):
        return str(self.standard_io_widget.text_in.toPlainText())

    def closeEvent(self, e):
        e.accept()
        self.log.copy()
        self.poller.abort = True
        time.sleep(3.0)
        #TMP111self.mouse_file_handler.abort = True
        #delete files:
        for file_path in self.poller.files_to_delete:
            if os.path.exists(file_path):
                os.remove(file_path)
        time.sleep(5.0) #Enough time to close network connections
        sys.exit(0)
        
def generate_gui_image(images, size, config, lines  = [], gridlines = False, sidebar_fill = (0, 0, 0)):
    '''
    Combine images with widgets like lines, sidebars. 
    
    Inputs:
    images: images to display. These will be overlaid using coloring, scaling and origin information.
    size: size of output image in pixels in row, col format
    lines: lines to draw on images, containing line endpoints in um
    sidebar_division: the size of divisions on the sidebar
    
    config: the following parameters are expected: 
                                LINE_WIDTH, LINE_COLOR
                                SIDEBAR_COLOR, SIDEBAR_SIZE

    Ouput: image_to_display
    '''
    out_image = 255*numpy.ones((size['row'], size['col'], 3), dtype = numpy.uint8)
    if not isinstance(images,  list):
        images = [images]
    if len(images) == 1:
        merged_image = images[0]
    else:
        #here the images are merged: 1. merge with coloring different layers, 2. merge without coloring
        pass
    image_area = utils.rc_add(size,  utils.cr((2*config.SIDEBAR_SIZE, 2*config.SIDEBAR_SIZE)), '-')
    #calculate scaling factor for rescaling image to required image size
    rescale = (numpy.cast['float64'](utils.nd(image_area)) / merged_image['image'].shape[:2]).min()
    rescaled_image = generic.rescale_numpy_array_image(merged_image['image'], rescale)
    #Draw lines
    if len(rescaled_image.shape) == 2:
        image_with_line = numpy.array([rescaled_image, rescaled_image, rescaled_image])
        image_with_line = numpy.rollaxis(image_with_line, 0, 3)
    else:
        image_with_line = rescaled_image
        image_with_line = numpy.rollaxis(image_with_line, 0, 2)
    #create sidebar
    image_with_sidebar = draw_scalebar(image_with_line, merged_image['origin'], utils.rc_multiply_with_constant(merged_image['scale'], 1.0/rescale), frame_size = config.SIDEBAR_SIZE, fill = sidebar_fill, gridlines = gridlines)
    for line in lines:
        #Line: x1,y1,x2, y2 - x - col, y = row
        #Considering MES/Image origin
        image_height = merged_image['image'].shape[0]*merged_image['scale']['row']
        line_in_pixel  = [(line[1] - merged_image['origin']['col'])/merged_image['scale']['col'] + config.SIDEBAR_SIZE,
                            (-line[0] + image_height + merged_image['origin']['row'])/merged_image['scale']['row'] + config.SIDEBAR_SIZE,
                            (line[3] - merged_image['origin']['col'])/merged_image['scale']['col'] + config.SIDEBAR_SIZE,
                            (-line[2] + image_height + merged_image['origin']['row'])/merged_image['scale']['row'] + config.SIDEBAR_SIZE]
        line_in_pixel = (numpy.cast['int32'](numpy.array(line_in_pixel)*rescale)).tolist()
        image_with_sidebar = generic.draw_line_numpy_array(image_with_sidebar, line_in_pixel)
    out_image[0:image_with_sidebar.shape[0], 0:image_with_sidebar.shape[1], :] = image_with_sidebar
    return out_image

def draw_scalebar(image, origin, scale, frame_size = None, fill = (0, 0, 0), gridlines = False):
    if frame_size == None:
        frame_size = 0.05 * min(image.shape)
    if not isinstance(scale,  numpy.ndarray) and not isinstance(scale,  numpy.void):
        scale = utils.rc((scale, scale))
    #Scale = unit (um) per pixel
    frame_color = 255
    fontsize = int(frame_size/3)
    if len(image.shape) == 3:
        image_with_frame_shape = (image.shape[0]+2*frame_size, image.shape[1]+2*frame_size, image.shape[2])
    else:
        image_with_frame_shape = (image.shape[0]+2*frame_size, image.shape[1]+2*frame_size)
    image_with_frame = frame_color*numpy.ones(image_with_frame_shape, dtype = numpy.uint8)
    if len(image.shape) == 3:
        image_with_frame[frame_size:frame_size+image.shape[0], frame_size:frame_size+image.shape[1], :] = generic_visexpA.normalize(image,numpy.uint8)
    else:
        image_with_frame[frame_size:frame_size+image.shape[0], frame_size:frame_size+image.shape[1]] = generic_visexpA.normalize(image,numpy.uint8)
    im = Image.fromarray(image_with_frame)
    im = im.convert('RGB')
    draw = ImageDraw.Draw(im)
    if os.name == 'nt':
        font = ImageFont.truetype("arial.ttf", fontsize)
    else:
        font = ImageFont.truetype("/usr/share/fonts/truetype/msttcorefonts/arial.ttf", fontsize)
    number_of_divisions = 6
    image_size = utils.cr((image.shape[0]*float(scale['row']), image.shape[1]*float(scale['col'])))
    division_col = int(numpy.round(float(image_size['row']) / number_of_divisions, -1))
    number_of_divisions_modified = int(float(image_size['row']) / division_col)
    col_labels = numpy.linspace(origin['col'], origin['col'] + number_of_divisions_modified * division_col, number_of_divisions_modified+1)
    col_labels = 10*numpy.floor(0.1 * col_labels)
    division_row = int(numpy.round(float(image_size['col']) / number_of_divisions, -1))
    number_of_divisions_modified = int(float(image_size['col']) / division_row)
    row_labels = numpy.linspace(origin['row'], origin['row'] + number_of_divisions_modified * division_row, number_of_divisions_modified+1)
    row_labels = 10*numpy.floor(0.1 * row_labels)
    #Overlay labels
    for label in col_labels:
        position = int((label-origin['col'])/scale['col']) + frame_size
        draw.text((position, 5),  str(int(label)), fill = fill, font = font)
        if gridlines and position > frame_size and position < image.shape[1]+frame_size:
            draw.line((position, frame_size, position, image.shape[0]+frame_size), fill = fill, width = 0)
        draw.line((position, int(0.75*frame_size), position, frame_size), fill = fill, width = 0)
        #Opposite side
        draw.text((position, image_with_frame.shape[0] - fontsize-5),  str(int(label)), fill = fill, font = font)
        if not gridlines:
            draw.line((position,  image_with_frame.shape[0] - int(0.75*frame_size), position,  image_with_frame.shape[0] - frame_size), fill = fill, width = 0)
        
    for label in row_labels:
        position = image.shape[0] +frame_size - int((label-origin['row'])/scale['row'])
        draw.text((5, position), str(int(label)), fill = fill, font = font)
        if gridlines and position > frame_size and position < image.shape[0]+frame_size:
            draw.line((frame_size, position, image.shape[1]+frame_size, position), fill = fill, width = 0)
        draw.line((int(0.75*frame_size), position, frame_size, position), fill = fill, width = 0)
        #Opposite side
        draw.text((image_with_frame.shape[1] - int(2.0*fontsize), position),  str(int(label)), fill = fill, font = font)
        if not gridlines:
            draw.line((image_with_frame.shape[1] - int(0.75*frame_size), position,  image_with_frame.shape[1] - frame_size, position), fill = fill, width = 0)
    im = numpy.asarray(im)
    return im
    
class GuiTest(QtCore.QThread):
    #Initializing, loader methods
    def __init__(self, parent):
        self.parent = parent
        QtCore.QThread.__init__(self)
        self.queue = Queue.Queue()
        self.parent.connect(self, QtCore.SIGNAL('printc'),  self.parent.printc)
        
    def run(self):
        self.printc('TEST: Starting')
        self.parent.main_tab.setCurrentIndex(2)
        #setting mouse strain to a random id
        id = 'test_{0}' .format(int(time.time()))
        self.parent.animal_parameters_widget.mouse_strain.setEditText(id)
        self.printc('TEST: Creating animal parameter file')
        self.parent.poller.signal_id_queue.put('save_animal_parameters')
        t = utils.Timeout(5.0)
        while id not in self.parent.poller.mouse_file:
            if t.is_timeout():
                self.printc('TEST FAIL: mouse file not created')
                break
        self.parent.main_tab.setCurrentIndex(0)
        self.printc('TEST: Acquiring xy image')
        current_xy_scan = copy.deepcopy(self.parent.poller.xy_scan)
        self.parent.poller.signal_id_queue.put('acquire_xy_scan')
        t = utils.Timeout(5.0)
        while True:
            time.sleep(0.5)
            if t.is_timeout():
                self.printc('TEST FAIL: XY scan did not succeed')
                break
        self.printc('TEST: Acquiring xz image')
        self.parent.poller.signal_id_queue.put('acquire_xz_scan')
        current_xz_scan = copy.deepcopy(self.parent.poller.xz_scan)
        t = utils.Timeout(5.0)
        while True:
            time.sleep(0.5)
            if t.is_timeout():
                self.printc('TEST FAIL: XZ scan did not succeed')
                break
        #Set region_name to 'master'
        self.parent.main_widget.scan_region_groupbox.scan_regions_combobox.setEditText('master')
        self.printc('TEST: Adding master position')
        self.parent.poller.signal_id_queue.put('add_scan_region')
        
        
    def start_test(self):
        self.start()
        
    def printc(self, text):
        self.emit(QtCore.SIGNAL('printc'), text)

def run_gui():
    app = Qt.QApplication(sys.argv)
    gui = VisionExperimentGui(sys.argv[1], sys.argv[2])
    app.exec_()

if __name__ == '__main__':
    run_gui()
