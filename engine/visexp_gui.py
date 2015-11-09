#OBSOLETE
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
from PIL import Image, ImageDraw, ImageFont

import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

import visexpman
from visexpman.engine.vision_experiment import configuration
from visexpman.engine.vision_experiment import gui
from visexpman.engine.generic import gui as gui_generic
from visexpman.engine.vision_experiment import gui_pollers
from visexpman.engine.hardware_interface import network_interface
from visexpman.engine.generic import utils, fileop, stringop, log, introspect
from visexpman.engine import generic, MachineConfigError
from visexpman.users.test import unittest_aggregator
import hdf5io


MAX_NUMBER_OF_DISPLAYED_MEASUREMENTS = 30
MAX_ANESTHESIA_ENTRIES = 20
parameter_extract = re.compile('EOC(.+)EOP')

ENABLE_MOUSE_FILE_HANDLER = False

################### Main widget #######################
class CorticalVisionExperimentGui(QtGui.QWidget):
    '''
    Main Qt GUI class of vision experiment manager gui.
    '''
    def __init__(self, user, config_class):
        self.config = utils.fetch_classes('visexpman.users.'+user, classname = config_class, required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig,direct = False)[0][1]()
        self.config.user = user
        self.console_text = ''
        self.log = log.Log('gui log', fileop.generate_filename(os.path.join(self.config.LOG_PATH, 'gui_log.txt')), local_saving = True)
        self.poller = gui_pollers.CorticalGUIPoller(self)
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
        self.main_widget = gui.MainWidget(self)
        self.animal_parameters_groupbox = gui.AnimalParametersWidget(self)
        self.images_widget = gui.ImagesWidget(self)
        self.overview_widget = gui.OverviewWidget(self)
        self.roi_widget = gui.RoiWidget(self)
        self.common_widget = gui.CommonWidget(self)
        self.helpers_widget = gui.HelpersWidget(self)
        self.zstack_widget = gui.ZstackWidget(self)
        self.main_tab = QtGui.QTabWidget(self)
        self.main_tab.addTab(self.main_widget, 'Main')
        self.main_tab.addTab(self.roi_widget, 'ROI')
        self.main_tab.addTab(self.animal_parameters_groupbox, 'Animal parameters')
        self.main_tab.addTab(self.zstack_widget, 'Z stack')
        self.main_tab.addTab(self.helpers_widget, 'Helpers')
        self.main_tab.setCurrentIndex(0)
        #Image tab
        self.image_tab = QtGui.QTabWidget(self)
        self.image_tab.addTab(self.images_widget, 'Regions')
        self.image_tab.addTab(self.overview_widget, 'Overview')
        self.standard_io_widget = gui.StandardIOWidget(self)
        gui_generic.load_experiment_config_names(self.config, self.main_widget.experiment_control_groupbox.experiment_name)
        
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
        if hasattr(self.poller,'widget_context_values'):
            for ref_string, value in self.poller.widget_context_values.items():
                ref = introspect.string2objectreference(self,ref_string.replace('parent.',''))
                if hasattr(ref,'setEditText'):
                    ref.setEditText(value)
        if hasattr(self.poller,  'last_mouse_file_name'):
            self.update_mouse_files_combobox(set_to_value = self.poller.last_mouse_file_name)
        else:
            self.update_mouse_files_combobox()
        if hasattr(self.poller,  'last_region_name'):
            self.update_widgets_when_mouse_file_changed(selected_region = self.poller.last_region_name)
        else:
            self.update_widgets_when_mouse_file_changed()
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
                  self.main_widget.scan_region_groupbox.scan_regions_combobox, self.animal_parameters_groupbox.new_mouse_file_button, 
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
        self.connect(self.common_widget.show_xzlines_checkbox, QtCore.SIGNAL('stateChanged(int)'),  self.xzline_checkbox_changed)
        self.connect(self.common_widget.registration_subimage_combobox, QtCore.SIGNAL('editTextChanged(const QString &)'),  self.subimage_parameters_changed)
        
        self.connect_and_map_signal(self.main_widget.scan_region_groupbox.select_mouse_file, 'mouse_file_changed', 'currentIndexChanged')
        self.connect(self.main_widget.scan_region_groupbox.scan_regions_combobox, QtCore.SIGNAL('currentIndexChanged(int)'),  self.region_name_changed)
        self.connect(self.animal_parameters_groupbox.anesthesia_history_groupbox.show_experiments_checkbox, QtCore.SIGNAL('stateChanged(int)'),  self.update_anesthesia_history)

        self.connect_and_map_signal(self.animal_parameters_groupbox.new_mouse_file_button, 'save_animal_parameters')
        self.connect_and_map_signal(self.animal_parameters_groupbox.anesthesia_history_groupbox.add_button, 'add_to_anesthesia_history')
        self.connect_and_map_signal(self.animal_parameters_groupbox.anesthesia_history_groupbox.remove_button, 'remove_last_from_anesthesia_history')
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
        self.connect(self.roi_widget.show_selection_on_left_checkbox, QtCore.SIGNAL('stateChanged(int)'),  self.show_selection_on_left_checkbox_changed)
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
        self.connect_and_map_signal(self.helpers_widget.camera_button, 'camera_test')
        self.connect(self.standard_io_widget.console_message_filter_combobox, QtCore.SIGNAL('currentIndexChanged(int)'),  self.console_message_filter_changed)

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
        self.connect_and_map_signal(self.zstack_widget.z_stack_button, 'acquire_z_stack')
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
        if hasattr(self.poller, 'mouse_file'):
            self.update_mouse_files_combobox(set_to_value = os.path.split(self.poller.mouse_file)[1])
        else:
            self.update_mouse_files_combobox()
            
    def tab_changed(self, currentIndex):
#        if currentIndex != 1:#If user switched from ROI tab, save cell selections
#            self.poller.signal_id_queue.put('save_cells')
        #Load meanimages or scan region images
        image_widget = self.images_widget.image_display[0]
        if currentIndex == 0:
            self.update_scan_regions()
            self.show_image(image_widget.raw_image, 0, image_widget.scale, line = image_widget.line, origin = image_widget.origin)
        elif currentIndex == 1:
            self.update_meanimage()
            self.show_image(image_widget.raw_image, 0, image_widget.scale, line = image_widget.line, origin = image_widget.origin)
            self.update_cell_info()
            self.update_cell_group_combobox()
            
    def gridline_checkbox_changed(self):
        self.update_gridlined_images()
        
    def xzline_checkbox_changed(self):
        self.update_gridlined_images()

    def subimage_parameters_changed(self):
        self.update_xy_images()
        
    def show_soma_roi_checkbox_changed(self):
        self.update_meanimage()
        
    def show_selection_on_left_checkbox_changed(self):
        self.update_rois_on_live_image()
        
    def cell_group_changed(self):
        self.update_meanimage()
        self.update_suggested_depth_label()
        self.update_cell_info()
            
    def region_name_changed(self):
        self.update_scan_regions()
        self.update_analysis_status()
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
        
    def console_message_filter_changed(self):
        self.update_console()
        
    def update_console(self):
        current_filter = self.standard_io_widget.console_message_filter_combobox.currentText()
#        self.printc(current_filter)
        if current_filter == '':
            self.filtered_console_text = self.console_text
        else:
            self.filtered_console_text = [line for line in self.console_text.split('\n') if len(line.split(' ')) >1 and line.split(' ')[1].lower() == current_filter]
        if isinstance(self.filtered_console_text, list):
            self.filtered_console_text = '\n'.join(self.filtered_console_text)
        self.standard_io_widget.text_out.setPlainText(self.filtered_console_text)
        self.standard_io_widget.text_out.moveCursor(QtGui.QTextCursor.End)

    ################### GUI updaters #################
    def update_anesthesia_history(self):
        text = 'Time\t\tsubstance\tamount\tcomment\n'
        if hasattr(self.poller, 'anesthesia_history'):
            entries = copy.deepcopy(self.poller.anesthesia_history)#[-MAX_ANESTHESIA_ENTRIES:]
            if self.animal_parameters_groupbox.anesthesia_history_groupbox.show_experiments_checkbox.checkState() != 0:
                for region_name, analysis_status_per_region in self.poller.analysis_status.items():
                    for id in analysis_status_per_region.keys():
                        stimulus_entry = self.poller.analysis_status[region_name][id]['info']
                        entry = {}
                        entry['timestamp'] = float(id)
                        entry['amount'] = '{0}, {1}' .format(stimulus_entry['scan_mode'], stimulus_entry['depth'])
                        entry['substance'] = stimulus_entry['stimulus'].replace('Config', '')
                        entry['comment'] = region_name
                        entries.append(entry)
                ids = [e['timestamp'] for e in entries]
                ids.sort()
                #Sort whole list by timestamp
                entries = [[e for e in entries if e['timestamp'] == id][0] for id in ids]
            
            number_of_rows = len(entries)
            self.animal_parameters_groupbox.anesthesia_history_groupbox.history.setRowCount(number_of_rows)
            self.animal_parameters_groupbox.anesthesia_history_groupbox.history.setVerticalHeaderLabels(QtCore.QStringList(number_of_rows * ['']))
            for row in range(number_of_rows):
                entry = entries[row]
                self.animal_parameters_groupbox.anesthesia_history_groupbox.history.setItem(row, 0, QtGui.QTableWidgetItem(utils.timestamp2ymdhm(entry['timestamp'])))
                self.animal_parameters_groupbox.anesthesia_history_groupbox.history.setItem(row, 1, QtGui.QTableWidgetItem(entry['substance']))
                self.animal_parameters_groupbox.anesthesia_history_groupbox.history.setItem(row, 2, QtGui.QTableWidgetItem(entry['amount']))
                self.animal_parameters_groupbox.anesthesia_history_groupbox.history.setItem(row, 3, QtGui.QTableWidgetItem(entry['comment']))
            self.animal_parameters_groupbox.anesthesia_history_groupbox.history.scrollToBottom()
        
    def update_anesthesia_history_date_widget(self):
        now = time.localtime()
        self.animal_parameters_groupbox.anesthesia_history_groupbox.date.setDateTime(QtCore.QDateTime(QtCore.QDate(now.tm_year, now.tm_mon, now.tm_mday), QtCore.QTime(now.tm_hour, now.tm_min)))
        
    def update_widgets_when_mouse_file_changed(self, selected_region=None):
        self.update_animal_parameter_display()
        self.update_region_names_combobox(selected_region = selected_region)
        self.update_scan_regions()
        self.update_analysis_status()
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
            if self.config.SHOW_OVERVIEW:
                self.show_image(image, 'overview', scale, origin = utils.rc((0, 0)))
            #Update region info
            region_add_date = scan_regions[selected_region].get('add_date','unknown')
            self.main_widget.scan_region_groupbox.region_info.setText('{3}\n{0:.2f}, {1:.2f}, {2:.2f}' 
                                                                      .format(scan_regions[selected_region]['position']['x'][0], scan_regions[selected_region]['position']['y'][0], 
                                                                              scan_regions[selected_region]['position']['z'][0], region_add_date))
        else:
                self.show_image(self.images_widget.blank_image, 1, no_scale, origin = utils.rc((0, 0)))
                self.show_image(self.images_widget.blank_image, 3, no_scale, origin = utils.rc((0, 0)))
                self.show_image(self.images_widget.blank_image, 'overview', no_scale, origin = utils.rc((0, 0)))
                self.main_widget.scan_region_groupbox.region_info.setText('')
                
    def update_file_id_combobox(self):
        if not hasattr(self.poller, 'analysis_status'):
            return
        region_name = self.get_current_region_name()
        analysis_status = self.poller.analysis_status
        if utils.safe_has_key(analysis_status, region_name):
            ids = analysis_status[region_name].keys()
            ids.sort()
            ids.reverse()
            self.update_combo_box_list(self.main_widget.measurement_datafile_status_groupbox.ids_combobox,ids)
        else:
            self.update_combo_box_list(self.main_widget.measurement_datafile_status_groupbox.ids_combobox,[])
            
    def clear_analysis_status_table(self):
            self.main_widget.measurement_datafile_status_groupbox.analysis_status_table.setRowCount(0)
            self.main_widget.measurement_datafile_status_groupbox.analysis_status_table.clear()
            self.main_widget.measurement_datafile_status_groupbox.set_headers()
                
    def update_analysis_status(self):
        if not hasattr(self.poller, 'analysis_status'):
            self.clear_analysis_status_table()
            return
        analysis_status = self.poller.analysis_status
        region_name = self.get_current_region_name()
        if not utils.safe_has_key(analysis_status, region_name):
            self.clear_analysis_status_table()
            return
        status_text = ''
        ids = analysis_status[region_name].keys()
        ids.sort()
        number_of_rows = len(ids)
        self.main_widget.measurement_datafile_status_groupbox.analysis_status_table.setRowCount(number_of_rows)
        self.main_widget.measurement_datafile_status_groupbox.analysis_status_table.setVerticalHeaderLabels(QtCore.QStringList(number_of_rows * ['']))
        if number_of_rows == 0:
            self.clear_analysis_status_table()
            return 
        for row in range(number_of_rows):
            id = ids[row]
            status = analysis_status[region_name][id]
            if status['info'].has_key('depth'):
                depth = str(int(numpy.round(status['info']['depth'], 0)))
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
                    laser_intensity = '{0:1.1f}'.format(float(status['info']['laser_intensity']))
                except:
                    laser_intensity = 'NA'
            else:
                laser_intensity = 0.0
            if status['find_cells_ready']:
                if status['info'].has_key('number_of_cells'):
                    status = '{0}' .format(status['info']['number_of_cells'])
                else:
                    status = 'ready'
            elif status['mesextractor_ready']:
                status = '**'
            elif status['fragment_check_ready']:
                status = '*'
            else:
                status = '*'
            self.main_widget.measurement_datafile_status_groupbox.analysis_status_table.setItem(row, 0, QtGui.QTableWidgetItem(scan_mode))
            self.main_widget.measurement_datafile_status_groupbox.analysis_status_table.setItem(row, 1, QtGui.QTableWidgetItem(depth))
            self.main_widget.measurement_datafile_status_groupbox.analysis_status_table.setItem(row, 2, QtGui.QTableWidgetItem(id[-4:]))
            self.main_widget.measurement_datafile_status_groupbox.analysis_status_table.setItem(row, 3, QtGui.QTableWidgetItem(laser_intensity))
            self.main_widget.measurement_datafile_status_groupbox.analysis_status_table.setItem(row, 4, QtGui.QTableWidgetItem(status))
            self.main_widget.measurement_datafile_status_groupbox.analysis_status_table.setItem(row, 5, QtGui.QTableWidgetItem(stimulus))
            self.main_widget.measurement_datafile_status_groupbox.analysis_status_table.scrollToBottom()

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
            #Generate list of cells in current cell group
            current_cellgroup = self.get_current_cell_group()
            if current_cellgroup != '':
                number_of_columns = 3
                cell_id_counter = 0
                text += '\n'
                for cell_id, cell in self.poller.cells[region_name].items():
                    if cell['group'] == current_cellgroup:
                        text += cell_id + ', '
                        cell_id_counter += 1
                        if cell_id_counter != 0 and cell_id_counter % number_of_columns == 0:
                            text += '\n'
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
        '''
        Updates meanimage on ROI tab
        '''
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
            self.update_rois_on_live_image()
            
    def update_rois_on_live_image(self):
        '''
        Updates soma rois on live image if ROI tab is active
        '''
        region_name = self.get_current_region_name()
        cell_group = self.get_current_cell_group()
        if hasattr(self.poller, 'xy_scan') and utils.safe_has_key(self.poller.cells, region_name) and self.main_tab.currentIndex() == 1:
            image = copy.deepcopy(self.poller.xy_scan[self.config.DEFAULT_PMT_CHANNEL])
            image = generic.pack_to_rgb(image)
            image = generic_visexpA.normalize(image, outtype=numpy.uint8, std_range = 10)
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
            mi = numpy.take(image, [0, 0, 0], axis=2).copy()
            try:
                meanimage = imaged.draw_on_meanimage(mi, self.poller.xy_scan['origin'], self.poller.xy_scan['scale'], soma_rois = soma_rois_to_display, used_rois = cells_to_display)
            except:
                meanimage = mi
                self.printc(traceback.format_exc())
            if self.roi_widget.show_selection_on_left_checkbox.checkState() == 0:
                meanimage = image
            self.show_image(scipy.ndimage.rotate(meanimage, -90), 0, scale=self.poller.xy_scan['scale'], origin = self.poller.xy_scan['origin'])

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
            if self.common_widget.show_xzlines_checkbox.checkState() == 0:
                line = []
            gridlines = (self.common_widget.show_gridlines_checkbox.checkState() != 0)
            if gridlines:
                sidebar_fill = (100, 50, 0)
                if (channel == 0 or channel ==1) and len(box) == 4 and self.main_tab.currentIndex() != 1:
                    line.extend(generic.box_to_lines(box))
            else:
                sidebar_fill = (0, 0, 0)
            if channel == 2 or channel == 3:#Scale xz images such that height is approximately equals with with
                image_in['image'] = generic.rescale_numpy_array_image(image_in['image'], utils.cr((float(image_in['image'].shape[0])/(0.3*image_in['image'].shape[1]), 1.0)))
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
                if i == 1:
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
        try:
            self.update_console()
        except RuntimeError:
            pass#gui not yet initialized
#        print text
        try:
            self.log.info(text)
        except:
            print 'gui: logging error'

    def scanc(self):
        return str(self.standard_io_widget.text_in.toPlainText())

    def closeEvent(self, e):
        self.printc('Please wait till gui closes')
        e.accept()
        self.log.copy()
        self.poller.abort = True
        self.poller.wait()
        sys.exit(0)
        #TMP111self.mouse_file_handler.abort = True
#        time.sleep(15.0) #Enough time to close network connections
        
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
    image_with_sidebar = draw_scalebar(image_with_line, merged_image['origin'], utils.rc_x_const(merged_image['scale'], 1.0/rescale), frame_size = config.SIDEBAR_SIZE, fill = sidebar_fill, gridlines = gridlines)
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
    number_of_divisions = 7
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
        self.parent.animal_parameters_groupbox.mouse_strain.setEditText(id)
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

        
class CentralWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.parent=parent
        self.config = config
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        self.main_widget = gui.MainWidget(self)
        self.animal_parameters_groupbox = gui.AnimalParametersGroupbox(self, self.config)
        self.experiment_log_groupbox = gui.ExperimentLogGroupbox(self)
        self.calibration_groupbox = gui.CalibrationGroupbox(self)
        self.parameters_groupbox = gui.MachineParametersGroupbox(self)
        self.ca_displays = gui.CaImagingVisualisationControlWidget(self)
        self.main_tab = QtGui.QTabWidget(self)
        self.main_tab.addTab(self.main_widget, 'Main')
        self.main_tab.addTab(self.experiment_log_groupbox, 'Experiment log')
        self.main_tab.addTab(self.animal_parameters_groupbox, 'Animal parameters')
        self.main_tab.addTab(self.parameters_groupbox, 'Parameters')
        self.main_tab.addTab(self.calibration_groupbox, 'Calibration')
        self.main_tab.addTab(self.ca_displays, 'Display setup')
        self.main_tab.setCurrentIndex(0)
        self.main_tab.setFixedHeight(self.config.GUI['GUI_SIZE']['row']*0.7)
        self.main_tab.setMaximumWidth(self.config.GUI['GUI_SIZE']['col']*0.6)
        self.network_status = QtGui.QLabel('', self)
        self.text_out = QtGui.QTextEdit(self)
        self.text_out.setPlainText('')
        self.text_out.setReadOnly(True)
        self.text_out.ensureCursorVisible()
        self.text_out.setCursorWidth(5)
        self.text_out.setMaximumWidth(700)
        self.plot = gui.Plot(self)
        self.browse_data_file_button = QtGui.QPushButton('Display datafile',  self)
        
        self.live_scan_start = QtGui.QPushButton('Live scan start', self)
        self.live_scan_stop = QtGui.QPushButton('Live scan stop', self)
        self.snap = QtGui.QPushButton('Snap', self)
        self.save2file = gui_generic.LabeledCheckBox(self, 'Save to file')
        self.averaging = gui_generic.LabeledInput(self, 'Averaging')
        self.analysis = gui.Analysis(self)
        self.image = gui.ImageMainUI(self,roi_diameter=4)
        
        
        self.main_tab.addTab(self.analysis, 'Analysis')
        self.main_tab.setCurrentIndex(6)
        self.console = gui.PythonConsole(self)
        self.main_tab.addTab(self.console, 'Debug')

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.main_tab, 0, 0, 3, 3)
        self.layout.addWidget(self.network_status, 3,  0, 1, 2)
        self.layout.addWidget(self.text_out, 4,  0, 1, 2)
        self.layout.addWidget(self.browse_data_file_button, 0, 3, 1, 1)
        
        self.layout.addWidget(self.live_scan_start, 1, 3)
        self.layout.addWidget(self.live_scan_stop, 1, 4)
        self.layout.addWidget(self.save2file, 1, 5)
        self.layout.addWidget(self.snap, 1, 6)
        self.layout.addWidget(self.averaging, 1, 7)
        self.layout.addWidget(self.image, 2, 3, 1,4)
        
        self.layout.addWidget(self.plot, 3, 2, 2, 3)
        self.setLayout(self.layout)

class VisionExperimentGui(Qt.QMainWindow):
    def __init__(self, config=None, user_interface_name=None, log = None, socket_queues = None, warning = []):
        if QtCore.QCoreApplication.instance() is None:
            qt_app = Qt.QApplication([])
#            qt_app.setStyleSheet(fileop.read_text_file('/home/rz/Downloads/QTDark.stylesheet'))
#            qt_app.setStyle('windows')
        self.source_name = '{0}' .format(user_interface_name)
        self.config = config
        self.log = log
        self.socket_queues = socket_queues
        self.console_text = ''
        Qt.QMainWindow.__init__(self)
        self._set_window_title()
        self.create_widgets()
        self.resize(self.config.GUI['GUI_SIZE']['col'], self.config.GUI['GUI_SIZE']['row'])
        self.poller = gui_pollers.VisexpGuiPoller(self)
        self.central_widget.console.set_poller(self.poller)
        self.block_widgets(True)
        self.init_variables()
        self.connect_signals()
        self.poller.start()
        self.showMaximized()
        self.init_widget_content()
        self.block_widgets(False)
        self.display_warnings(warning)
        
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
        
    def create_widgets(self):
        self.central_widget = CentralWidget(self, self.config)
        self.setCentralWidget(self.central_widget)
        
    def display_warnings(self, warnings):
        for warning in warnings:
            if 'tiff' in str(warning.message) or 'non-integer' in str(warning.message):
                continue
            if not introspect.is_test_running():
                self.notify_user('WARNING', str(warning.message))
            self.log.warning(warning.message, self.source_name)
        
    def init_variables(self):
        self.console_text = ''
        
    def init_widget_content(self):
        '''
        Load widget values if previous context is saved. Otherwise ...
        '''
        #Set widget values from context
        for widget_path in self.poller.context['widgets']:
            if self.poller.context['widgets'][widget_path] is None:#None if widget path not found in context file. Then corresponding widget is not updated
                continue
            ref = introspect.string2objectreference(self,'.'.join(widget_path.replace('.parent', '').split('.')[:-1]))
            if hasattr(ref, 'setCheckState'):
                getattr(ref, 'setCheckState')(self.poller.context['widgets'][widget_path])
            elif hasattr(ref, 'setText'):
                getattr(ref, 'setText')(self.poller.context['widgets'][widget_path])
            elif isinstance(self.poller.context['widgets'][widget_path], int) and hasattr(ref, 'setCurrentIndex'):
                getattr(ref, 'setCurrentIndex')(self.poller.context['widgets'][widget_path])
            elif isinstance(self.poller.context['widgets'][widget_path], str) and hasattr(ref, 'setEditText'):
                getattr(ref, 'setEditText')(self.poller.context['widgets'][widget_path])
            elif isinstance(self.poller.context['widgets'][widget_path], list):
                [getattr(ref,'item')(index).setSelected(True) for index in self.poller.context['widgets'][widget_path]]
        self.update_experiment_parameter_table()
        self.update_animal_file_list()
        self.update_animal_parameters_table()
        self.update_experiment_log_suggested_date()
        self.update_experiment_log()
        self.update_machine_parameters()
        self.update_recording_status()
        if self.poller.testmode == 13 or self.poller.testmode == 14:
            self.central_widget.main_widget.experiment_options_groupbox.recording_channel.list.item(1).setSelected(True)
#        gui_generic.load_experiment_config_names(self.config, self.central_widget.main_widget.experiment_control_groupbox.experiment_name)
        
    def connect_signals(self):
        
        self.connect(self.central_widget.main_widget.experiment_control_groupbox.experiment_name, QtCore.SIGNAL('currentIndexChanged(const QString &)'),  self.experiment_name_changed)
        self.connect(self.central_widget.animal_parameters_groupbox.animal_filename.input, QtCore.SIGNAL('currentIndexChanged(const QString &)'),  self.animal_filename_changed)
        self.connect(self.central_widget.animal_parameters_groupbox.animal_filename.input, QtCore.SIGNAL('editTextChanged(const QString &)'),  self.animal_filename_changed)
        self.connect(self.central_widget.parameters_groupbox.table['scanner'], QtCore.SIGNAL('cellChanged(int,int)'),  self.machine_parameter_table_content_changed)
        self.connect(self.central_widget.main_widget.recording_status.table, QtCore.SIGNAL('cellActivated(int,int)'),  self.recording_selected_for_display)
#        self.connect(self.central_widget.animal_parameters_groupbox.animal_filename, QtCore.SIGNAL('editTextChanged(const QString &)'),  self.animal_filename_changed)
        #Signals mapped to poller functions
        self.signal_mapper = QtCore.QSignalMapper(self)
        widget2poller_function = [[self.central_widget.main_widget.experiment_control_groupbox.start_experiment_button, 'experiment_control.add_experiment'],
                                  [self.central_widget.main_widget.experiment_control_groupbox.stop_experiment_button, 'experiment_control.stop_experiment'],
                                  [self.central_widget.main_widget.experiment_control_groupbox.browse_experiment_file_button, 'experiment_control.browse'],
                                  [self.central_widget.main_widget.experiment_parameters.reload, 'experiment_control.reload_experiment_parameters'],
                                  [self.central_widget.main_widget.experiment_parameters.save, 'experiment_control.save_experiment_parameters'],
                                  [self.central_widget.animal_parameters_groupbox.new_animal_file_button, 'animal_file.save_animal_parameters'],
                                  [self.central_widget.animal_parameters_groupbox.update_animal_file_button, 'animal_file.update'],
                                  [self.central_widget.animal_parameters_groupbox.reload_animal_parameters_button, 'animal_file.reload_animal_parameters'],
                                  [self.central_widget.animal_parameters_groupbox.animal_files_from_data_storage, 'animal_file.search_data_storage'],
                                  [self.central_widget.animal_parameters_groupbox.copy_animal_files_from_data_storage, 'animal_file.copy'],
                                  [self.central_widget.experiment_log_groupbox.new_entry.add_button, 'experiment_log.add'],
                                  [self.central_widget.experiment_log_groupbox.remove_button, 'experiment_log.remove'],
                                  [self.central_widget.main_widget.recording_status.remove, 'experiment_control.remove_experiment'],
                                  [self.central_widget.main_widget.recording_status.set_state, 'experiment_control.set_experiment_state'],
                                  [self.central_widget.parameters_groupbox.check_scan_parameters_button, 'experiment_control.check_scan_parameters'],
                                  [self.central_widget.snap, 'experiment_control.snap_ca_image'],
                                  [self.central_widget.live_scan_start, 'experiment_control.live_scan_start'],
                                  [self.central_widget.live_scan_stop, 'experiment_control.live_scan_stop'],
                                  [self.central_widget.main_widget.toolbox.bullseye_toggle, 'toolbox.toggle_bullseye'],
                                  [self.central_widget.main_widget.toolbox.filterwheel0, 'toolbox.set_filterwheel0', 'currentIndexChanged'],
                                  [self.central_widget.main_widget.toolbox.filterwheel1, 'toolbox.set_filterwheel1', 'currentIndexChanged'],
                                  [self.central_widget.main_widget.toolbox.grey_level, 'toolbox.set_color', 'currentIndexChanged'],
                                  [self.central_widget.main_widget.toolbox.projector_enable.input, 'toolbox.set_projector', 'stateChanged'],
                                  [self.central_widget.browse_data_file_button, 'display_datafile'],
                                  ]
        
        for item in widget2poller_function:
            gui_generic.connect_and_map_signal(self, *item)
        
        #display config changed    
        function_link = 'visualisation_control.generate_display_configuration'
        display_config_changed_signals = []
        for i in range(self.config.MAX_CA_IMAGE_DISPLAYS):
            parent_widget = self.central_widget.ca_displays.display_configs[i]
            display_config_changed_signals.append([parent_widget.enable, function_link, 'stateChanged'])
            display_config_changed_signals.append([parent_widget.name.input, function_link, 'textEdited'])
            display_config_changed_signals.append([parent_widget.channel_select.input, function_link, 'currentIndexChanged'])
            display_config_changed_signals.append([parent_widget.exploring_mode_options.input, function_link, 'currentIndexChanged'])
            display_config_changed_signals.append([parent_widget.recording_mode_options.input, function_link, 'currentIndexChanged'])
            display_config_changed_signals.append([parent_widget.gridline_select.input, function_link, 'currentIndexChanged'])
        for item in display_config_changed_signals:
            gui_generic.connect_and_map_signal(self, item[0],item[1], item[2])
            
        self.signal_mapper.mapped[str].connect(self.poller.pass_signal)
        
    def block_widgets(self,  block):
        if not hasattr(self, 'blocked_widgets'):
            self.blocked_widgets =  [self.central_widget.main_widget.experiment_control_groupbox.experiment_name, 
                                     self.central_widget.animal_parameters_groupbox.animal_filename.input, 
                                     ]
        [w.blockSignals(block) for w in self.blocked_widgets]
        
    def printc(self, text, logonly = False):
        if not isinstance(text, str):
            text = str(text)
        if not logonly:
            self.console_text  += utils.timestamp2hms(time.time()) + ' '  + text + '\n'
            self.update_console()
        if 'warning' in text.lower():
            self.log.warning(text.replace('WARNING: ',''), self.source_name)
        elif 'error' in text.lower():
            self.log.error(text.replace('ERROR: ',''), self.source_name)
        else:
            self.log.info(text, self.source_name)
        
    def update_console(self):
        self.central_widget.text_out.setPlainText(self.console_text)
        self.central_widget.text_out.moveCursor(QtGui.QTextCursor.End)
        
    def closeEvent(self, e):
        e.accept()
        self.close_app()
        
    def close_app(self):
        self.printc('Please wait till gui closes')
        self.poller.abort = True
        self.poller.wait()
        self.close()
        
    ################# GUI events ####################
    def experiment_name_changed(self):
        self.update_experiment_parameter_table()
        
    def animal_filename_changed(self):
        self.poller.animal_file.filename = str(self.central_widget.animal_parameters_groupbox.animal_filename.input.currentText())
        #poller/animal parameters class needs to load animal parameters from selected file
        self.poller.animal_file.load()
        
    def machine_parameter_table_content_changed(self):
        self.central_widget.parameters_groupbox.machine_parameters['scanner'] = self.central_widget.parameters_groupbox.table['scanner'].get_values()
        formatted = {}
        for k,v in self.central_widget.parameters_groupbox.machine_parameters['scanner'].items():
            if isinstance(v,list):
                formatted[k] = '#'.join(v)
            else:
                formatted[k] = v
        self.central_widget.parameters_groupbox.machine_parameters['scanner'] = formatted
        
    def recording_selected_for_display(self,row,col):
        entry = self.poller.animal_file.recordings[len(self.poller.animal_file.recordings) -1- row]
        if entry['status'] == 'done':
            filename = fileop.find_recording_filename(entry['id'], self.config)
            if filename is not None:
                self.poller.display_datafile(filename)

    ################# Update widgets #################### 
    def update_recording_status(self):
        if not hasattr(self.poller.animal_file, 'recordings'):
            return
        #Convert list of experiment commands to parameter table format
        entry_order = []
        status_data = {}
        for recording in self.poller.animal_file.recordings:
            name = fileop.get_recording_name(self.config, recording, ' ')
            entry_order.append(name)
            comment = 'Issue time: {0}, id: {6}, scanning range: {1}, resolution: {2} {3}, duration: {4} s, recording channel(s): {5}'\
                    .format(utils.timestamp2hms(int(recording['id'])/100.0), recording['scanning_range'], 
                                                          recording['pixel_size'], recording['resolution_unit'], 
                                                          recording['duration'], recording['recording_channels'], recording['id'])
            status_data[name] = recording['status']+'#'+comment
        entry_order.reverse()
        self.central_widget.main_widget.recording_status.table.set_values(status_data, entry_order)
        
    def update_machine_parameters(self):
        self.central_widget.parameters_groupbox.table['scanner'].blockSignals(True)
        formatted = {}
        self.central_widget.parameters_groupbox.table['scanner'].set_values(self.central_widget.parameters_groupbox.machine_parameters['scanner'], 
                                                                            self.central_widget.parameters_groupbox.machine_parameter_order['scanner'])
        self.central_widget.parameters_groupbox.table['scanner'].blockSignals(False)
        
    def update_experiment_log(self):
        if not hasattr(self.poller.animal_file, 'log'):
            return
        log = copy.deepcopy(self.poller.animal_file.log)
        log = utils.sort_dict(log, 'date')
        log.reverse()
        widget = self.central_widget.experiment_log_groupbox.log
        nrows = len(log)
        widget.setRowCount(nrows)
        widget.setVerticalHeaderLabels(QtCore.QStringList(nrows*['']))
        flags = QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsEnabled
        for row in range(nrows):
            item = QtGui.QTableWidgetItem(utils.timestamp2ymdhm(log[row]['date']))
            item.setFlags(flags)
            widget.setItem(row, 0, item)
            if log[row]['substance'] == '' and log[row]['amount'] == '':
                log_text = log[row]['comment']
            else:
                log_text = '{1} {0}'.format(log[row]['substance'], log[row]['amount'], log[row]['comment'])
                if log[row]['comment'] != '':
                    log_text += ', ' + log[row]['comment']
            item = QtGui.QTableWidgetItem(log_text)
            item.timestamp = log[row]['timestamp']
            item.setFlags(flags)
            widget.setItem(row, 1, item)
        widget.scrollToTop()
    
    def update_experiment_log_suggested_date(self):
        now = time.localtime()
        self.central_widget.experiment_log_groupbox.new_entry.date.setDateTime(QtCore.QDateTime(QtCore.QDate(now.tm_year, now.tm_mon, now.tm_mday), QtCore.QTime(now.tm_hour, now.tm_min, now.tm_sec)))

    def update_experiment_parameter_table(self):
        experiment_config_name = os.path.split(str(self.central_widget.main_widget.experiment_control_groupbox.experiment_name.currentText()))[-1]
        if not self.poller.experiment_control.experiment_config_classes.has_key(experiment_config_name):
            return
        pars = {}
        for par in self.poller.experiment_control.experiment_config_classes[experiment_config_name]:
            parname = (par.split('='))[0]
            pars[parname]= (par.split('='))[1]
        self.central_widget.main_widget.experiment_parameters.values.set_values(pars)
        
    def update_animal_parameters_table(self):
        if not hasattr(self.poller.animal_file, 'filename'):
            return
        self._set_window_title(animal_file = self.poller.animal_file.filename)
        #Convert animal parameter names to title format
        animal_params = {}
        for k, v in self.poller.animal_file.animal_parameters.items():
            animal_params[stringop.to_title(k)]=v
        parnames = [stringop.to_title(pn) for pn in self.central_widget.animal_parameters_groupbox.parameter_names]
        self.central_widget.animal_parameters_groupbox.table.set_values(\
                                                                                                                    animal_params, parname_order = parnames)

    def update_animal_file_list(self):
        text_before_list_update = str(self.central_widget.animal_parameters_groupbox.animal_filename.input.currentText())
        animal_filenames = self.poller.animal_file.animal_files.keys()
        animal_filenames.sort()
        widget = self.central_widget.animal_parameters_groupbox.animal_filename.input
        if hasattr(self.poller.animal_file, 'filename'):
            selected_item = self.poller.animal_file.filename
        else:
            selected_item = None
        gui_generic.update_combo_box_list(self, widget, animal_filenames, selected_item)
        if text_before_list_update == '' and animal_filenames != []:#If selected animal filename was an empty string, set item pointed by current index and load its content
            self.poller.animal_file.filename = animal_filenames[widget.currentIndex()]
            self.poller.animal_file.load_animal_parameters()

    ################# Pop up dialoges ####################
    def ask4confirmation(self, action2confirm):
        utils.empty_queue(self.poller.gui_thread_queue)
        reply = QtGui.QMessageBox.question(self, 'Confirm following action', action2confirm, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.No:
            self.poller.gui_thread_queue.put(False)
        else:
            self.poller.gui_thread_queue.put(True)
            
    def ask4filename(self,title, directory, filter):
        utils.empty_queue(self.poller.gui_thread_queue)
        filename = QtGui.QFileDialog.getOpenFileName(self, title, directory, filter)
        self.poller.gui_thread_queue.put(str(filename))
        
    def notify_user(self, title, message):
        utils.empty_queue(self.poller.gui_thread_queue)
        QtGui.QMessageBox.question(self, title, message, QtGui.QMessageBox.Ok)
        self.poller.gui_thread_queue.put(True)
        self.printc(title + '\t' + message, logonly = True)
        
    def update_curve(self,curves):
        self.central_widget.plot.update(curves)
        
    def update_image(self, image,scale=1):
        self.central_widget.image.set_image(image)
        self.central_widget.image.set_scale(scale)
        
    def set_experiment_progressbar(self, value, attribute='setValue'):
        self.central_widget.main_widget.experiment_control_groupbox.experiment_progress.setValue(value)
        
    def set_experiment_progressbar_range(self, max_value):
        self.central_widget.main_widget.experiment_control_groupbox.experiment_progress.setRange(0, max_value)
        
    def set_experiment_names(self, experiment_names):
        current_experiment_config_name = str(self.central_widget.main_widget.experiment_control_groupbox.experiment_name.currentText())
        self.central_widget.main_widget.experiment_control_groupbox.experiment_name.blockSignals(True)
        self.central_widget.main_widget.experiment_control_groupbox.experiment_name.clear()
        self.central_widget.main_widget.experiment_control_groupbox.experiment_name.blockSignals(False)
        experiment_names.sort()
        self.central_widget.main_widget.experiment_control_groupbox.experiment_name.addItems(QtCore.QStringList(experiment_names))
        if current_experiment_config_name in experiment_names:#Retain experiment name in combobox if possible
            self.central_widget.main_widget.experiment_control_groupbox.experiment_name.setCurrentIndex(experiment_names.index(current_experiment_config_name))
        if len(experiment_names) == 0:#If no experiment configs found in selected file, erase items from parameter table
            self.central_widget.main_widget.experiment_parameters.values.set_values({})

    ################# Helper functions ####################
    def _set_window_title(self, animal_file=''):
        if not self.config.USER_INTERFACE_NAMES.has_key(self.config.user_interface_name):
            raise MachineConfigError('Unknown application name: {0}' .format(self.config.user_interface_name))
        self.setWindowTitle('{0} - {1}' .format(utils.get_window_title(self.config), animal_file) )
        
    def select_recording_item(self, row, state):
        self.central_widget.main_widget.recording_status.table.item(row,1).setSelected(state)
        
    def select_experiment_log_entry(self, row):
        self.central_widget.experiment_log_groupbox.log.item(row,1).setSelected(True)
        
    def __str__(self):
        return introspect.object2str(self)
        
def run_cortical_gui():
    app = Qt.QApplication(sys.argv)
    gui = CorticalVisionExperimentGui(sys.argv[1], sys.argv[2])
    app.exec_()   
    
import unittest
import platform
class testVisionExperimentGui(unittest.TestCase):
    
    def setUp(self):
        from visexpman.users.test.test_configurations import GUITestConfig
        self.machine_config = GUITestConfig()
        self.machine_config.user_interface_name='main_ui'
        self.machine_config.user = 'test'
        fileop.cleanup_files(self.machine_config)
        self.test_13_14_expected_values = (1, 'done', 'C2', 1.0, 'um/pixel', utils.rc((200.0, 200.0)), 'DebugExperimentConfig', 10.0, ['SIDE'], utils.rc((10.0, 0.0)))     
        
    def tearDown(self):
        time.sleep(10)
        
    def _call_gui(self, testmode):
        import subprocess
        code = 'python {0} -u test -c GUITestConfig -a main_ui --testmode {1}'.format(os.path.join(fileop.visexpman_package_path(), 'engine', 'visexp_app.py'), testmode)
        subprocess.call(code, shell=True)
        
    def _read_context(self):
        fn = fileop.get_context_filename(self.machine_config)
        if platform.system() == 'Windows':
            h = hdf5io.Hdf5io(fn,filelocking=False)
            h.close()#Making sure that file is closed
        if os.path.exists(fn):
            time.sleep(1.0)
            context = utils.array2object(hdf5io.read_item(fn, 'context', filelocking=False))
            return context
            
    def _check_logfile(self,context):
        logfile_content = fileop.read_text_file(context['variables']['self.parent.log.filename'])
        self.assertNotIn(logfile_content.lower(),'error')#any error reported
        self.assertGreater(int(logfile_content.split('phase counter: ')[1].split('\n')[0]),0)#check if phase counter is greater than 0
        
    
    def _create_animal_parameter_file(self, id):
        '''
        Creates animal parameter file in tmp folder with the given id
        '''
        self.machine_config.printc = ''
        ap = gui.AnimalFile(self.machine_config, self.machine_config, None)
        animal_parameters = {'imaging_channels': 'green', 'red_labeling': '', 'green_labeling': 'label '+id , 'injection_target': '', 'ear_punch_left': '2', 'comment': '', 'strain': 'strain', 'ear_punch_right': '1', 'gender': 'male', 'birth_date': '1-1-2013', 'injection_date': '1-5-2013', 'id': id}
        animal_file = ap._get_animal_filename(animal_parameters)
        hdf5io.save_item(animal_file, 'animal_parameters', utils.object2array(animal_parameters), config=self.machine_config, overwrite = True)
        fileop.remove_if_exists(os.path.join(tempfile.gettempdir(), os.path.split(animal_file)[1]))
        shutil.move(animal_file, tempfile.gettempdir())
        
#    @unittest.skip('')

    @unittest.skipIf(unittest_aggregator.TEST_no_user_action,  'Requires user action')        
    def test_01_select_stimfile(self):
        '''
        Tests if py module can be opened as a stimfile and experiment configuration parameters can be parsed and displayed.total
        '''
        time.sleep(1.0)
        sourcefile_path = os.path.join(os.path.split(sys.modules['visexpman'].__file__)[0], 'users', 'test', 'test_stimulus.py')
        source_before = fileop.read_text_file(sourcefile_path)
#        gui =  VisionExperimentGui('test', 'GUITestConfig', 'main_ui', testmode=1)
        self._call_gui(1)
        context = self._read_context()
        self._check_logfile(context)
        self.assertIn('GUITestExperimentConfig', context['variables']['self.experiment_control.experiment_config_classes.keys'])
        self.assertEqual(context['variables']['self.parent.central_widget.main_widget.experiment_parameters.values.rowCount'], 3)
        self.assertIn('test_stimulus.py', context['variables']['self.experiment_control.user_selected_stimulation_module'])
        self.assertEqual(source_before, fileop.read_text_file(sourcefile_path))
                          
#    @unittest.skip('')
    def test_02_create_animal_file(self):
        '''
        Creating animal file is tested
        '''
        self._call_gui(2)
        context = self._read_context()
        self._check_logfile(context)
        self.assertTrue(os.path.exists(context['variables']['self.animal_file.filename']))
        self.assertEqual(os.path.split(context['variables']['self.animal_file.filename'])[1], 'animal_test_strain_1-1-2013_1-5-2013_L2R1.hdf5')
        self.assertEqual(utils.array2object(hdf5io.read_item(context['variables']['self.animal_file.filename'], 'animal_parameters', self.machine_config)),
                                                                                  {'imaging_channels': 'green', 'red_labeling': '', 'green_labeling': 'label',
                                                                                    'injection_target': '', 'ear_punch_left': '2', 
                                                                                    'comment': '', 'strain': 'strain', 'ear_punch_right': '1',
                                                                                    'gender': 'male', 'birth_date': '1-1-2013', 'injection_date': '1-5-2013', 'id': 'test'})

#    @unittest.skip('')
    def test_03_animal_file_parameter_not_provided(self):
        self._call_gui(3)
        context = self._read_context()
        self._check_logfile(context)
        self.assertEqual((os.path.exists(context['variables']['self.animal_file.filename']), 
                                                              ), 
                                                              (False, 
                                                              ))
    
#    @unittest.skip('')
    def test_04_load_animal_files_from_data_storage_and_switch(self):
        '''
        Load animal parameter files from data storage and select the second one. Then modify date of birth, reload original values, finally modify labeling and save changes to file, which sould not happen because it is on data storage
        '''
        #Create animal file in tmp
        self._create_animal_parameter_file('data_storage1')
        self._create_animal_parameter_file('data_storage2')
#        gui =  VisionExperimentGui('test', 'GUITestConfig', 'main_ui', testmode=4)
        #Run gui
        self._call_gui(4)
        context = self._read_context()
        self._check_logfile(context)
        self.assertEqual((
            stringop.string_in_list(context['variables']['self.animal_file.animal_files.keys'], 'data_storage1'), 
            stringop.string_in_list(context['variables']['self.animal_file.animal_files.keys'], 'data_storage2'), 
            utils.array2object(hdf5io.read_item(context['variables']['self.animal_file.filename'], 'animal_parameters', self.machine_config)), 
            ), (True, True, 
            {'imaging_channels': 'green', 'red_labeling': '', 'green_labeling': 'label data_storage2', 'injection_target': '', 'ear_punch_left': '2', 'comment': '', 'strain': 'strain', 'ear_punch_right': '1', 'gender': 'male', 'birth_date': '1-1-2013', 'injection_date': '1-5-2013', 'id': 'data_storage2'}
                                                                          ))
    
#    @unittest.skip('') 
    def test_05_load_animal_files_from_data_storage_and_modify(self):
        '''
        Load animal parameter files from data storage, copy second to experiment data, then modify it.
        Finally create a new animal file
        '''
        from visexpman.engine.vision_experiment import experiment_data
        #Create animal file in tmp
        self._create_animal_parameter_file('data_storage1')
        self._create_animal_parameter_file('data_storage2')
        #Run gui
        self._call_gui(5)
        
        context = self._read_context()
        self._check_logfile(context)
        for fn in context['variables']['self.animal_file.animal_files.keys']:
            if 'data_storage2' in fn and  experiment_data.get_user_experiment_data_folder(self.machine_config) in fn:
                copied_animal_file = fn
                break
        self.assertEqual((
            stringop.string_in_list(context['variables']['self.animal_file.animal_files.keys'], 'data_storage1'), 
            stringop.string_in_list(context['variables']['self.animal_file.animal_files.keys'], 'data_storage2'), 
            stringop.string_in_list(context['variables']['self.animal_file.animal_files.keys'], experiment_data.get_user_experiment_data_folder(self.machine_config)), 
            len(context['variables']['self.animal_file.animal_files.keys']), 
            utils.array2object(hdf5io.read_item(context['variables']['self.animal_file.filename'], 'animal_parameters', self.machine_config)), 
            utils.array2object(hdf5io.read_item(copied_animal_file, 'animal_parameters', self.machine_config)),
            ), (True, True, True, 4, 
            {'imaging_channels': 'green', 'red_labeling': 'yes', 'green_labeling': 'modified_label', 'injection_target': '', 'ear_punch_left': '2', 'comment': '', 'strain': 'secondstrain', 'ear_punch_right': '1', 'gender': 'male', 'birth_date': '1-1-2012', 'injection_date': '1-1-2012', 'id': 'second_one'}, 
            {'imaging_channels': 'green', 'red_labeling': 'yes', 'green_labeling': 'modified_label', 'injection_target': '', 'ear_punch_left': '2', 'comment': '', 'strain': 'strain', 'ear_punch_right': '1', 'gender': 'male', 'birth_date': '1-1-2013', 'injection_date': '1-5-2013', 'id': 'data_storage2'}
                                                                          ))
        
#    @unittest.skip('') 
    def test_06_modify_animal_parameter_name(self):
        '''
        Modify animal strain to trigger animal file renaming
        '''
        self._call_gui(6)
        
        context = self._read_context()
        self._check_logfile(context)
        self.assertEqual((os.path.exists(context['variables']['self.animal_file.filename']), 
                                                              os.path.exists(context['variables']['self.animal_file.filename'].replace('test1', 'test')), 
                                                              utils.array2object(hdf5io.read_item(context['variables']['self.animal_file.filename'], 'animal_parameters', self.machine_config))), (
                                                              True, False, 
                                                              {'imaging_channels': 'green', 'red_labeling': '', 'green_labeling': 'label1', 'injection_target': '', 'ear_punch_left': '1', 'comment': '', 'strain': 'strain', 'ear_punch_right': '1', 'gender': 'male', 'birth_date': '1-1-2010', 'injection_date': '1-1-2010', 'id': 'test1'}
                                                              ))

#    @unittest.skip('') 
    def test_07_add_experiment_log_entry(self):
        '''
        Adding an experiment log netry when neither context nor animal file is available. No error should occur
        '''
        self._call_gui(7)
        context = self._read_context()
        self._check_logfile(context)
        self.assertEqual((context['widgets']['self.parent.central_widget.main_widget.experiment_control_groupbox.experiment_name.currentText'], 
                          context['variables'].has_key('self.animal_file.filename')
                          ), (
                          'DebugExperimentConfig', False
                          ))
                          
#    @unittest.skip('') 
    def test_08_context_file_no_animal_file_add_log_entry(self):
        '''
        Adding an experiment log entry when context file is available but animal file not. No error should occur. Also checking if experiment name is loaded from context file
        '''
        self._call_gui(0)
        self._call_gui(8)
        context = self._read_context()
        self.assertEqual((context['widgets']['self.parent.central_widget.main_widget.experiment_control_groupbox.experiment_name.currentText'], 
                          context['variables'].has_key('self.animal_file.filename')
                          ), (
                          'GUITestExperimentConfig', False
                          ))
        
#    @unittest.skip('') 
    def test_09_no_context_file_but_animal_file_add_log_entry(self):
        '''
        Starting up the gui with animal file but without context file and trying to add a log entry
        '''
        
        self._call_gui(9)
        context = self._read_context()
        self._check_logfile(context)
        explog = utils.array2object(hdf5io.read_item(context['variables']['self.animal_file.filename'], 'log', self.machine_config))
        self.assertEqual((context['widgets']['self.parent.central_widget.main_widget.experiment_control_groupbox.experiment_name.currentText'], 
                          context['variables'].has_key('self.animal_file.filename'), 
                          os.path.split(context['variables']['self.animal_file.filename'])[1], 
                          len(explog)
                          ), (
                          'DebugExperimentConfig', True, 'animal_addlog1_1_1-1-2009_1-1-2009_L0R0.hdf5', 3
                          ))

#    @unittest.skip('') 
    def test_10_remove_experiment_log_entry(self):
        '''
        Context file is available, two animal files are created, experiment log added to one. Experiment log entry remove also tested
        '''
        self._call_gui(0)
        self._call_gui(10)
        context = self._read_context()
        explog = utils.array2object(hdf5io.read_item(context['variables']['self.animal_file.filename'], 'log', self.machine_config))
        other_animal_filename = [fn for fn in context['variables']['self.animal_file.animal_files.keys'] if fn != context['variables']['self.animal_file.filename']][0]
        explog2 = utils.array2object(hdf5io.read_item(other_animal_filename, 'log', self.machine_config))
        self.assertEqual((context['widgets']['self.parent.central_widget.main_widget.experiment_control_groupbox.experiment_name.currentText'], 
                          context['variables'].has_key('self.animal_file.filename'), 
                          os.path.split(context['variables']['self.animal_file.filename'])[1], 
                          len(explog), 
                          len(context['variables']['self.animal_file.animal_files.keys']), 
                          len(explog2)
                          ), (
                          'GUITestExperimentConfig', True, 'animal_addlog1_1_1-1-2009_1-1-2009_L0R0.hdf5', 3, 2, 2
                          ))

#    @unittest.skip('') 
    def test_11_copy_animal_file_after_gui_start(self):
        '''
        Animal files are copied to user's experiment data folder and these should be detected
        If fails APP_CLOSE_TIMEOUT shall be increased
        '''
        self._create_animal_parameter_file('copied1')
        self._create_animal_parameter_file('copied2')
        self._call_gui(11)
        context = self._read_context()
        self._check_logfile(context)
        self.assertEqual(len(context['variables']['self.animal_file.animal_files.keys']), 2)

#    @unittest.skip('')
    def test_12_context_loading(self):
        '''
        Animal files are created and and one is selected. Widget content is modified. 
        App is started again and animal file name shall remain the selected one.
        Context file after the second and first run shall have the same content. 
        '''
        self._call_gui(12)
        
#        from visexpman.engine.visexp_app import run_main_ui
#        context = visexpman.engine.application_init(user='test', config ='GUITestConfig', user_interface_name='main_ui')
#        context['machine_config'].testmode=12
#        run_main_ui(context)
#        visexpman.engine.stop_application(context)
        contexts = []
        context = self._read_context()
        contexts.append(context)
        self._call_gui(0)
        context = self._read_context()
        contexts.append(context)
        expected_values = ('animal_id1_12_12-12-2012_12-12-2012_L0R0.hdf5',
        'cell',
        '100, 100')
        for context in contexts:
            self._check_logfile(context)
            self.assertEqual((
                os.path.split(context['variables']['self.animal_file.filename'])[1],
                context['widgets']['self.parent.central_widget.main_widget.experiment_options_groupbox.cell_name.input.text'],
                context['widgets']['self.parent.central_widget.main_widget.experiment_options_groupbox.scanning_range.input.text'],
                ),expected_values)
                
#    @unittest.skip('')
    def test_13_add_remove_experiment_no_animal_file(self):
        '''
        Add many experiment entries and modify their status, finally remove one
        '''
        self._call_gui(13)
        context = self._read_context()
        self._check_logfile(context)
        self.assertEqual((len(context['variables']['self.animal_file.recordings']), 
                    context['variables']['self.animal_file.recordings'][0]['status'], 
                    context['variables']['self.animal_file.recordings'][0]['cell_name'], 
                    context['variables']['self.animal_file.recordings'][0]['pixel_size'], 
                    context['variables']['self.animal_file.recordings'][0]['resolution_unit'], 
                    context['variables']['self.animal_file.recordings'][0]['scanning_range'], 
                    context['variables']['self.animal_file.recordings'][0]['experiment_name'], 
                    context['variables']['self.animal_file.recordings'][0]['duration'], 
                    context['variables']['self.animal_file.recordings'][0]['recording_channels'], 
                    context['variables']['self.animal_file.recordings'][0]['scan_center'], 
                    ), self.test_13_14_expected_values)
        #Test state transition data
        self.assertTrue(isinstance(context['variables']['self.animal_file.recordings'][0]['state_transition_times'][0][0],str))
        self.assertGreater(context['variables']['self.animal_file.recordings'][0]['state_transition_times'][0][1],1418811772)
        self.assertEqual(len(context['variables']['self.animal_file.recordings'][0]['state_transition_times']),2)
    
#    @unittest.skip('')
    def test_14_add_remove_experiment_animal_file(self):
        self._call_gui(14)
        context = self._read_context()
        self._check_logfile(context)
        recordings = utils.array2object(hdf5io.read_item(context['variables']['self.animal_file.filename'], 'recordings', self.machine_config))
        self.assertEqual((len(recordings), 
                    recordings[0]['status'], 
                    recordings[0]['cell_name'], 
                    recordings[0]['pixel_size'], 
                    recordings[0]['resolution_unit'], 
                    recordings[0]['scanning_range'], 
                    recordings[0]['experiment_name'], 
                    recordings[0]['duration'], 
                    recordings[0]['recording_channels'], 
                    recordings[0]['scan_center'], 
                    ), self.test_13_14_expected_values)
        self.assertTrue(isinstance(context['variables']['self.animal_file.recordings'][0]['state_transition_times'][0][0],str))
        self.assertGreater(context['variables']['self.animal_file.recordings'][0]['state_transition_times'][0][1],1418811772)
        self.assertEqual(len(context['variables']['self.animal_file.recordings'][0]['state_transition_times']),2)

        
#    def test_15(self):
#        for i in range(8):
#            self._call_gui(15)
                    
if __name__ == '__main__':
    unittest.main()
