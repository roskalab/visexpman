import shutil
import time
import numpy
import re
import Queue
import traceback
import os
import os.path
import webbrowser
import copy

import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

from visexpman.engine.vision_experiment import experiment_data
from visexpman.engine.hardware_interface import mes_interface
from visexpman.engine.hardware_interface import network_interface
from visexpman.engine import generic
from visexpman.engine.generic import utils
from visexpman.engine.generic import file
from visexpA.engine.datadisplay import imaged
from visexpA.engine.datahandlers import matlabfile
from visexpA.engine.datahandlers import hdf5io

BUTTON_HIGHLIGHT = 'color: red'

class ExperimentControlGroupBox(QtGui.QGroupBox):
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Experiment control', parent)
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        #TODO: add xz scan config parameter widgets
        #Stimulation/experiment control related
        self.experiment_name = QtGui.QComboBox(self)
        self.experiment_name.setEditable(True)
        self.experiment_name.addItems(QtCore.QStringList([]))
        self.start_experiment_button = QtGui.QPushButton('Start experiment',  self)
        self.start_experiment_button.setStyleSheet(QtCore.QString(BUTTON_HIGHLIGHT))
        self.stop_experiment_button = QtGui.QPushButton('Stop experiment',  self)
        self.stop_experiment_button.setStyleSheet(QtCore.QString(BUTTON_HIGHLIGHT))
        self.next_depth_button = QtGui.QPushButton('Next',  self)
        self.redo_depth_button = QtGui.QPushButton('Redo',  self)
        self.previous_depth_button = QtGui.QPushButton('Prev',  self)
        self.graceful_stop_experiment_button = QtGui.QPushButton('Graceful stop experiment',  self)
#        self.identify_flourescence_intensity_distribution_button = QtGui.QPushButton('Fluorescence distribution',  self)
        self.objective_positions_label = QtGui.QLabel('Objective range [um]\n start,end,step',  self)
        self.objective_positions_combobox = QtGui.QComboBox(self)
        self.objective_positions_combobox.setEditable(True)
        self.laser_intensities_label = QtGui.QLabel('Laser intensity (min, max) [%]',  self)
        self.laser_intensities_combobox = QtGui.QComboBox(self)
        self.laser_intensities_combobox.setEditable(True)
        self.scan_mode = QtGui.QComboBox(self)
        self.scan_mode.addItems(QtCore.QStringList(['xy', 'xz']))

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.experiment_name, 0, 0, 1, 2)
        self.layout.addWidget(self.start_experiment_button, 0, 2, 1, 2)
        self.layout.addWidget(self.stop_experiment_button, 0, 4)
        self.layout.addWidget(self.graceful_stop_experiment_button, 0, 5)
        self.layout.addWidget(self.previous_depth_button, 1, 0, 1, 2)
        self.layout.addWidget(self.next_depth_button, 1, 4, 1, 1)
        self.layout.addWidget(self.redo_depth_button, 1, 2, 1, 2)
        self.layout.addWidget(self.scan_mode, 2, 0)
        self.layout.addWidget(self.objective_positions_label, 2, 4)
        self.layout.addWidget(self.objective_positions_combobox, 2, 5, 1, 2)
        self.layout.addWidget(self.laser_intensities_label, 3, 3, 1, 2)
        self.layout.addWidget(self.laser_intensities_combobox, 3, 5, 1, 1)
        self.setLayout(self.layout)        

class AnimalParametersWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.create_widgets()
        self.create_layout()
        self.config = config
        self.resize(self.config.TAB_SIZE['col'], self.config.TAB_SIZE['row'])

    def create_widgets(self):
        default_date = QtCore.QDate(2012, 1, 1)
        date_format = QtCore.QString('dd-MM-yyyy')
        ear_punch_items = QtCore.QStringList(['0',  '1',  '2'])                
        self.mouse_birth_date_label = QtGui.QLabel('Mouse birth date',  self)        
        self.mouse_birth_date = QtGui.QDateEdit(self)
        self.mouse_birth_date.setDisplayFormat(date_format)
        self.mouse_birth_date.setDate(default_date)
        self.gcamp_injection_date_label = QtGui.QLabel('GCAMP injection date',  self)
        self.gcamp_injection_date = QtGui.QDateEdit(self)
        self.gcamp_injection_date.setDisplayFormat(date_format)
        self.gcamp_injection_date.setDate(default_date)
        self.ear_punch_l_label = QtGui.QLabel('Ear punch L',  self)
        self.ear_punch_l = QtGui.QComboBox(self)
        self.ear_punch_l.addItems(ear_punch_items)
        self.ear_punch_r_label = QtGui.QLabel('Ear punch R',  self)
        self.ear_punch_r = QtGui.QComboBox(self)                
        self.ear_punch_r.addItems(ear_punch_items)
        self.gender_label = QtGui.QLabel('Gender',  self)
        self.gender = QtGui.QComboBox(self)        
        self.gender.addItems(QtCore.QStringList(['male', 'female']))
        self.anesthesia_protocol_label = QtGui.QLabel('Anesthesia protocol',  self)
        self.anesthesia_protocol = QtGui.QComboBox(self)        
        self.anesthesia_protocol.addItems(QtCore.QStringList(['isoflCP 0.5', 'isoflCP 1.0', 'isoflCP 1.5']))
        self.anesthesia_protocol.setEditable(True)
        self.mouse_strain_label = QtGui.QLabel('Mouse strain',  self)
        self.mouse_strain = QtGui.QComboBox(self)
        self.mouse_strain.addItems(QtCore.QStringList(['chat', 'chatdtr', 'bl6', 'grik4']))
        self.mouse_strain.setEditable(True)
        self.comments = QtGui.QComboBox(self)
        self.comments.setEditable(True)
        self.comments.setToolTip('Add comment')
        self.new_mouse_file_button = QtGui.QPushButton('Create new mouse file',  self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.mouse_birth_date_label, 0, 0)
        self.layout.addWidget(self.mouse_birth_date, 1, 0)
        self.layout.addWidget(self.gcamp_injection_date_label, 2, 0)
        self.layout.addWidget(self.gcamp_injection_date, 3, 0)
        self.layout.addWidget(self.ear_punch_l_label, 0, 1)
        self.layout.addWidget(self.ear_punch_l, 1, 1)
        self.layout.addWidget(self.ear_punch_r_label, 2, 1)
        self.layout.addWidget(self.ear_punch_r, 3, 1)
        self.layout.addWidget(self.gender_label, 0, 2)
        self.layout.addWidget(self.gender, 1, 2)
        self.layout.addWidget(self.mouse_strain_label, 2, 2)
        self.layout.addWidget(self.mouse_strain, 3, 2)
        self.layout.addWidget(self.anesthesia_protocol_label, 4, 0)
        self.layout.addWidget(self.anesthesia_protocol, 4, 1)
        self.layout.addWidget(self.comments, 5, 0, 1, 3)
        self.layout.addWidget(self.new_mouse_file_button, 6, 0, 1, 2)
        self.layout.setRowStretch(10, 5)
        self.layout.setColumnStretch(5,10)
        self.setLayout(self.layout)

################### Image display #######################
class ImagesWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.config = config
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.TAB_SIZE['col'], self.config.TAB_SIZE['row'])
        
    def create_widgets(self):
        self.image_display = []
        for i in range(4):
            self.image_display.append(QtGui.QLabel())
        self.blank_image = 128*numpy.ones((self.config.IMAGE_SIZE['col'], self.config.IMAGE_SIZE['row']), dtype = numpy.uint8)
        for image in self.image_display:
            image.setPixmap(imaged.array_to_qpixmap(self.blank_image))
            
    def clear_image_display(self, index):
        self.image_display[index].setPixmap(imaged.array_to_qpixmap(self.blank_image))
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        for i in range(len(self.image_display)):
            self.layout.addWidget(self.image_display[i], i/2, (i%2)*2, 1, 1)
        
        self.layout.setRowStretch(3, 3)
        self.layout.setColumnStretch(3, 3)
        self.setLayout(self.layout)
        
class OverviewWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.config = config
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.TAB_SIZE['col'], self.config.TAB_SIZE['row'])
        
    def create_widgets(self):
        self.image_display = QtGui.QLabel()
        blank_image = 128*numpy.ones((self.config.OVERVIEW_IMAGE_SIZE['col'], self.config.OVERVIEW_IMAGE_SIZE['row']), dtype = numpy.uint8)
        self.image_display.setPixmap(imaged.array_to_qpixmap(blank_image))
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.image_display, 0, 0, 1, 1)
        self.layout.setRowStretch(3, 3)
        self.layout.setColumnStretch(3, 3)
        self.setLayout(self.layout)
        
class ScanRegionGroupBox(QtGui.QGroupBox):
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Scan regions', parent)
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.select_mouse_file_label = QtGui.QLabel('Select mouse file', self)
        self.select_mouse_file = QtGui.QComboBox(self)
        self.animal_parameters_label = QtGui.QLabel('', self)
        self.get_xy_scan_button = QtGui.QPushButton('XY scan',  self)
        self.get_xy_scan_button.setStyleSheet(QtCore.QString(BUTTON_HIGHLIGHT))
        self.use_saved_scan_settings_label = QtGui.QLabel('Use saved scan settings', self)
        self.use_saved_scan_settings_settings_checkbox = QtGui.QCheckBox(self)
        self.add_button = QtGui.QPushButton('Add',  self)
        self.scan_regions_combobox = QtGui.QComboBox(self)
        self.scan_regions_combobox.setEditable(True)
        self.remove_button = QtGui.QPushButton('Remove',  self)
        self.move_to_button = QtGui.QPushButton('Move to',  self)
        self.move_to_button.setStyleSheet(QtCore.QString(BUTTON_HIGHLIGHT))
        self.region_info = QtGui.QLabel('',  self)
        self.move_to_region_options = {}
        self.move_to_region_options['header_labels'] = [ QtGui.QLabel('Move', self), QtGui.QLabel('Realign', self), QtGui.QLabel('Adjust origin', self)]
        self.move_to_region_options['row_labels'] = [ QtGui.QLabel('Stage', self), QtGui.QLabel('Objective', self)]
        self.move_to_region_options['checkboxes'] = {}
        self.move_to_region_options['checkboxes']['stage_move'] = QtGui.QCheckBox(self)
        self.move_to_region_options['checkboxes']['stage_realign'] = QtGui.QCheckBox(self)
        self.move_to_region_options['checkboxes']['stage_origin_adjust'] = QtGui.QCheckBox(self)
        self.move_to_region_options['checkboxes']['objective_move'] = QtGui.QCheckBox(self)
        self.move_to_region_options['checkboxes']['objective_move'].setEnabled(False)
        self.move_to_region_options['checkboxes']['objective_realign'] = QtGui.QCheckBox(self)
        self.move_to_region_options['checkboxes']['objective_origin_adjust'] = QtGui.QCheckBox(self)
        for k, v in self.move_to_region_options['checkboxes'].items():
#            if 'origin_adjust' not in k and 'objective_move' not in k:
            if 'stage_move' in k:
                v.setCheckState(2)
        self.xz_scan_button = QtGui.QPushButton('XZ scan',  self)
        self.xz_scan_button.setStyleSheet(QtCore.QString(BUTTON_HIGHLIGHT))
        self.process_status_label = QtGui.QLabel('', self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.select_mouse_file_label, 0, 0, 1, 1)
        self.layout.addWidget(self.select_mouse_file, 0, 1, 1, 3)
        self.layout.addWidget(self.animal_parameters_label, 1, 0, 1, 4)
        self.layout.addWidget(self.use_saved_scan_settings_label, 2, 1, 1, 1)
        self.layout.addWidget(self.use_saved_scan_settings_settings_checkbox, 2, 2, 1, 1)
        self.layout.addWidget(self.get_xy_scan_button, 3, 3, 1, 1)
        self.layout.addWidget(self.xz_scan_button, 3, 2, 1, 1)
        self.layout.addWidget(self.add_button, 3, 0, 1, 1)
        self.layout.addWidget(self.scan_regions_combobox, 4, 0, 1, 2)
        self.layout.addWidget(self.region_info, 4, 3, 1, 1)
        self.layout.addWidget(self.remove_button, 5, 0, 1, 1)
        self.layout.addWidget(self.move_to_button, 4, 2, 1, 1)
        self.layout.addWidget(self.move_to_region_options['header_labels'][0], 5, 1, 1, 1)
        self.layout.addWidget(self.move_to_region_options['header_labels'][1], 5, 2, 1, 1)
        self.layout.addWidget(self.move_to_region_options['header_labels'][2], 5, 3, 1, 1)
        self.layout.addWidget(self.move_to_region_options['row_labels'][0], 6, 0, 1, 1)
        self.layout.addWidget(self.move_to_region_options['row_labels'][1], 7, 0, 1, 1)
        self.layout.addWidget(self.move_to_region_options['checkboxes']['stage_move'], 6, 1, 1, 1)
        self.layout.addWidget(self.move_to_region_options['checkboxes']['stage_realign'], 6, 2, 1, 1)
        self.layout.addWidget(self.move_to_region_options['checkboxes']['stage_origin_adjust'], 6, 3, 1, 1)
        self.layout.addWidget(self.move_to_region_options['checkboxes']['objective_move'], 7, 1, 1, 1)
        self.layout.addWidget(self.move_to_region_options['checkboxes']['objective_realign'], 7, 2, 1, 1)
        self.layout.addWidget(self.move_to_region_options['checkboxes']['objective_origin_adjust'], 7, 3, 1, 1)
        self.layout.addWidget(self.process_status_label, 8, 0, 2, 4)
        self.layout.setRowStretch(10, 10)
        self.layout.setColumnStretch(10, 10)
        self.setLayout(self.layout)
        
class RoiWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.config = config
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.TAB_SIZE['col'], self.config.TAB_SIZE['row'])
        
    def create_widgets(self):
        self.roi_info_image_display = QtGui.QLabel()
        blank_image = 128*numpy.ones((self.config.ROI_INFO_IMAGE_SIZE['row'], self.config.ROI_INFO_IMAGE_SIZE['col']), dtype = numpy.uint8)
        self.roi_info_image_display.setPixmap(imaged.array_to_qpixmap(blank_image))
        self.select_cell_label = QtGui.QLabel('Select cell',  self)
        self.select_cell_combobox = QtGui.QComboBox(self)
        self.select_cell_combobox.setEditable(False)
        self.cell_id_display_label = QtGui.QLabel('',  self)
        self.next_button = QtGui.QPushButton('>>',  self)
        self.previous_button = QtGui.QPushButton('<<',  self)
        self.accept_cell_button = QtGui.QPushButton('Accept cell',  self)
        self.ignore_cell_button = QtGui.QPushButton('Ignore cell',  self)
        self.cell_group_label = QtGui.QLabel('Cell group',  self)
        self.cell_group_edit_combobox = QtGui.QComboBox(self)
        self.cell_group_edit_combobox.setEditable(True)
        self.cell_filter_name_combobox = QtGui.QComboBox(self)
        self.cell_filter_name_combobox.addItems(QtCore.QStringList(['No filter', 'depth', 'id', 'date', 'stimulus']))
        self.cell_filter_combobox = QtGui.QComboBox(self)
        self.show_soma_roi_label = QtGui.QLabel('Show soma roi',  self)
        self.show_soma_roi_checkbox = QtGui.QCheckBox(self)
        self.xz_line_length_label = QtGui.QLabel('XZ line length',  self)
        self.xz_line_length_combobox = QtGui.QComboBox(self)
        self.xz_line_length_combobox.setEditable(True)
        self.cell_merge_distance_label =  QtGui.QLabel('Cell merge distance [um]',  self)
        self.cell_merge_distance_combobox = QtGui.QComboBox(self)
        self.cell_merge_distance_combobox.setEditable(True)
        self.cell_group_combobox = QtGui.QComboBox(self)
        self.create_xz_lines_button = QtGui.QPushButton('XZ lines',  self)
        self.xy_scan_button = QtGui.QPushButton('XY scan',  self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.roi_info_image_display, 0, 0, 1, 13)
        self.layout.addWidget(self.select_cell_label, 1, 0)
        self.layout.addWidget(self.select_cell_combobox, 1, 1, 1, 2)
        self.layout.addWidget(self.cell_id_display_label, 1, 3, 1, 2)
        self.layout.addWidget(self.previous_button, 1, 5)
        self.layout.addWidget(self.accept_cell_button, 1, 6)
        self.layout.addWidget(self.ignore_cell_button, 1, 7)
        self.layout.addWidget(self.next_button, 1, 8)
        self.layout.addWidget(self.cell_group_label, 1, 9)
        self.layout.addWidget(self.cell_group_edit_combobox, 1, 10, 1, 2)
        self.layout.addWidget(self.cell_filter_name_combobox, 2, 0, 1, 2)
        self.layout.addWidget(self.cell_filter_combobox, 2, 2, 1, 2)
        self.layout.addWidget(self.show_soma_roi_label, 2, 4, 1, 2)
        self.layout.addWidget(self.show_soma_roi_checkbox, 2, 5, 1, 1)
        self.layout.addWidget(self.xy_scan_button, 2, 6, 1, 1)
        
        self.layout.addWidget(self.create_xz_lines_button, 3, 0, 1, 1)
        self.layout.addWidget(self.cell_group_combobox, 3, 1, 1, 1)
        self.layout.addWidget(self.xz_line_length_label, 3, 2)
        self.layout.addWidget(self.xz_line_length_combobox, 3, 3, 1, 1)
        self.layout.addWidget(self.cell_merge_distance_label, 3, 4, 1, 1)
        self.layout.addWidget(self.cell_merge_distance_combobox, 3, 5, 1, 1)
        
        self.layout.setRowStretch(3, 3)
        self.layout.setColumnStretch(15, 15)
        self.setLayout(self.layout)

class MainWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.config = config
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.TAB_SIZE['col'], self.config.TAB_SIZE['row'])
        
    def create_widgets(self):
        #MES related
        self.z_stack_button = QtGui.QPushButton('Create Z stack', self)
        #Stage related
        self.set_stage_origin_button = QtGui.QPushButton('Set stage origin', self)
        self.set_stage_origin_button.setStyleSheet(QtCore.QString(BUTTON_HIGHLIGHT))
        self.read_stage_button = QtGui.QPushButton('Read stage', self)
        self.move_stage_button = QtGui.QPushButton('Move stage', self)
        self.stop_stage_button = QtGui.QPushButton('Stop stage', self)
        self.current_position_label = QtGui.QLabel('', self)
        #Development
        self.experiment_control_groupbox = ExperimentControlGroupBox(self)
        self.scan_region_groupbox = ScanRegionGroupBox(self)
        self.set_objective_button = QtGui.QPushButton('Set objective', self)
        self.run_fragment_process_button = QtGui.QPushButton('Run fragment process',  self)
        self.show_fragment_process_status_button = QtGui.QPushButton('Show fragment process status',  self)
        #Network related
        self.connected_clients_label = QtGui.QLabel('', self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.experiment_control_groupbox, 0, 0, 2, 4)
#        self.layout.addWidget(self.set_objective_value_button, 2, 8, 1, 1)        
        self.layout.addWidget(self.scan_region_groupbox, 4, 0, 2, 4)
        
        self.layout.addWidget(self.connected_clients_label, 8, 0, 1, 4)
        
        self.layout.addWidget(self.z_stack_button, 9, 0, 1, 1)
        self.layout.addWidget(self.run_fragment_process_button, 11, 0, 1, 1)
        self.layout.addWidget(self.show_fragment_process_status_button, 11, 1, 1, 1)

        self.layout.addWidget(self.set_stage_origin_button, 10, 0, 1, 1)
        self.layout.addWidget(self.read_stage_button, 10, 1, 1, 1)
        self.layout.addWidget(self.move_stage_button, 10, 2, 1, 1)
        self.layout.addWidget(self.stop_stage_button, 10, 3, 1, 1)
        self.layout.addWidget(self.set_objective_button, 10, 4, 1, 1)
        self.layout.addWidget(self.current_position_label, 10, 5, 1, 2)
        
        self.layout.setRowStretch(10, 10)
        self.layout.setColumnStretch(10, 10)
        self.setLayout(self.layout)

################### Debug/helper widgets #######################
class HelpersWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.config = config
        #generate connection name list
        self.connection_names = ['']
        for k, v in self.config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'].items():
            if 'GUI' in k:
                self.connection_names.append(k.replace('GUI', '').replace('_', '').lower())
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.TAB_SIZE['col'], self.config.TAB_SIZE['row'])
        
    def create_widgets(self):
        #Helpers
        self.save_xy_scan_button = QtGui.QPushButton('Save xy image',  self)
        self.help_button = QtGui.QPushButton('Help',  self)
        self.override_enforcing_set_stage_origin_checkbox = QtGui.QCheckBox(self)
        self.override_enforcing_set_stage_origin_checkbox.setToolTip('Do not check for set stage origin')
        self.add_simulated_measurement_file_button = QtGui.QPushButton('Add simulated measurement file',  self)
        self.rebuild_cell_database_button = QtGui.QPushButton('Rebuild cell database button',  self)
        #Network related
        self.show_connected_clients_button = QtGui.QPushButton('Show connected clients',  self)
        self.show_network_messages_button = QtGui.QPushButton('Show network messages',  self)
        self.select_connection_list = QtGui.QComboBox(self)
        self.select_connection_list.addItems(QtCore.QStringList(self.connection_names))
        self.send_command_button = QtGui.QPushButton('Send command',  self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.show_connected_clients_button, 0, 0, 1, 1)
        self.layout.addWidget(self.show_network_messages_button, 0, 1, 1, 1)
        self.layout.addWidget(self.select_connection_list, 0, 2, 1, 1)
        self.layout.addWidget(self.send_command_button, 0, 3, 1, 1)
        
        self.layout.addWidget(self.save_xy_scan_button, 1, 0, 1, 1)
        self.layout.addWidget(self.help_button, 1, 1, 1, 1)
        self.layout.addWidget(self.override_enforcing_set_stage_origin_checkbox, 1, 2, 1, 1)
        self.layout.addWidget(self.add_simulated_measurement_file_button, 1, 3, 1, 1)
        self.layout.addWidget(self.rebuild_cell_database_button, 1, 4, 1, 1)
        
        self.layout.setRowStretch(10, 10)
        self.layout.setColumnStretch(10, 10)
        self.setLayout(self.layout)

class StandardIOWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.config = config
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.TAB_SIZE['col'], 0.5*self.config.TAB_SIZE['row'])
        
    def create_widgets(self):
        self.text_out = QtGui.QTextEdit(self)
        self.text_out.setPlainText('')
        self.text_out.setReadOnly(True)
        self.text_out.ensureCursorVisible()
        self.text_out.setCursorWidth(5)
        self.text_in = QtGui.QTextEdit(self)
        self.text_in.setToolTip('self.printc()')
        
        self.execute_python_button = QtGui.QPushButton('Execute python code',  self)
        self.clear_console_button = QtGui.QPushButton('Clear console',  self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.text_out, 0, 0, 4, 3)
        self.layout.addWidget(self.text_in, 1, 3, 1, 2)
        self.layout.addWidget(self.execute_python_button, 0, 3, 1, 1)#, alignment = QtCore.Qt.AlignTop)
        self.layout.addWidget(self.clear_console_button, 0, 4, 1, 1)#, alignment = QtCore.Qt.AlignTop)
        self.layout.setRowStretch(300, 300)
        self.layout.setColumnStretch(0, 100)
        self.setLayout(self.layout)
        
parameter_extract = re.compile('EOC(.+)EOP')
command_extract = re.compile('SOC(.+)EOC')

################### Poller #######################
class Poller(QtCore.QThread):
    def __init__(self, parent):
        self.signal_id_queue = Queue.Queue() #signal parameter is passed to handler
        self.gui_thread_queue = Queue.Queue()
        self.parent = parent
        self.config = self.parent.config
        QtCore.QThread.__init__(self)
        self.abort = False
        self.xz_scan_acquired = False
        self.stage_origin_set = False
        self.cell_status_changed_in_cache = False
        self.connect_signals()
        self.init_network()
        self.mes_interface = mes_interface.MesInterface(self.config, self.queues, self.connections)
        self.init_variables()
        self.load_context()
        
    def connect_signals(self):
        self.parent.connect(self, QtCore.SIGNAL('printc'),  self.parent.printc)
        self.parent.connect(self, QtCore.SIGNAL('periodic_gui_update'),  self.parent.periodic_gui_update)
        self.parent.connect(self, QtCore.SIGNAL('update_scan_regions'),  self.parent.update_scan_regions)
        self.parent.connect(self, QtCore.SIGNAL('show_image'),  self.parent.show_image)
        self.parent.connect(self, QtCore.SIGNAL('show_overwrite_region_messagebox'),  self.parent.show_overwrite_region_messagebox)
        self.parent.connect(self, QtCore.SIGNAL('show_verify_add_region_messagebox'),  self.parent.show_verify_add_region_messagebox)
        
    def connect_signals_to_widgets(self):
        self.parent.connect(self, QtCore.SIGNAL('clear_image_display'), self.parent.images_widget.clear_image_display)
        
    def init_network(self):
        self.command_relay_server = network_interface.CommandRelayServer(self.config)
        self.connections = {}
        self.queues = {}
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
    
    def abort_poller(self):
        self.abort = True
    
    def printc(self, text):
        self.emit(QtCore.SIGNAL('printc'), text)
        
    def show_image(self, image, channel, scale, line = [], origin = None):
        self.emit(QtCore.SIGNAL('show_image'), image, channel, scale, line, origin)
        
    def update_scan_regions(self):
        self.emit(QtCore.SIGNAL('update_scan_regions'))

    def run(self):
        self.printc('poller starts')
        last_time = time.time()
        startup_time = last_time
        init_job_run = False
        while not self.abort:
            now = time.time()
            elapsed_time = now - last_time
            if elapsed_time > self.config.GUI_REFRESH_PERIOD:
                last_time = now
                self.periodic()
            self.update_network_connection_status()
            self.handle_events()
            self.handle_commands()
            time.sleep(1e-2)
        self.close()
        self.printc('poller stopped')
        
    def close(self):
        self.save_cells()
        hdf5io.save_item(self.config.CONTEXT_FILE, 'last_region_name',  self.parent.get_current_region_name(), overwrite = True)
        self.printc('Wait till server is closed')
        self.queues['mes']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.queues['stim']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.queues['analysis']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.command_relay_server.shutdown_servers()
        time.sleep(3.0)

    def periodic(self):
        self.emit(QtCore.SIGNAL('periodic_gui_update'))

    def init_job(self):
        '''
        Functions that need to be called only once at application start
        The order of the function calls is very important.
        '''
        self.connect_signals_to_widgets()
        if utils.safe_has_key(self.xy_scan, self.config.DEFAULT_PMT_CHANNEL):
            self.show_image(self.xy_scan[self.config.DEFAULT_PMT_CHANNEL], 0, self.xy_scan['scale'], origin = self.xy_scan['origin'])
        if utils.safe_has_key(self.xz_scan, 'scaled_image'):
            self.show_image(self.xz_scan['scaled_image'], 2, self.xz_scan['scaled_scale'], origin = self.xz_scan['origin'])
        self.parent.update_mouse_files_combobox()
        self.parent.update_current_mouse_path()
        if os.path.isfile(self.mouse_file):
            h = hdf5io.Hdf5io(self.mouse_file)
            images  = h.findvar('images')
            if images is not None:
                self.images = images
            self.scan_regions = h.findvar('scan_regions')
            self.parent.update_region_names_combobox()
            if hasattr(self.scan_regions, 'keys') and self.last_region_name in self.scan_regions.keys():
                scan_region_names = self.scan_regions.keys()
                scan_region_names.sort()#combo box items are in an alphabetic order  but  order of keys in a dict is random
                self.parent.main_widget.scan_region_groupbox.scan_regions_combobox.setCurrentIndex(scan_region_names.index(self.last_region_name))
            self.parent.update_jobhandler_process_status()
            cells  = h.findvar('cells')
            if cells is not None:
                self.cells = cells
                self.parent.update_cell_group_combobox()
            h.close()

    def handle_events(self):
        for k, queue in self.queues.items():
            if not queue['in'].empty():
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
                        hdf5io.save_item(self.mouse_file.replace('.hdf5', '_z_stack.hdf5'), 'z_stack', self.z_stack)
                        self.printc('Z stack is saved to {0}' .format(z_stack_file_path))
                        os.remove(self.z_stack_path)
                    elif command == 'jobhandler_started':
                        self.set_mouse_file()
                    elif command == 'measurement_ready':
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
                        self.set_process_status_flag(parameter, flags)
                    elif command == 'find_cells_ready':
                        self.add_cells_to_database(parameter)
                    elif command == 'mouse_file_copy':
                        if parameter == '':
                            tag = 'jobhandler'
                        else:
                            tag = parameter
                        self.backup_mouse_file(tag = tag)
                        self.queues['analysis']['out'].put('SOCmouse_file_copiedEOCEOP')
                    else:
                        self.printc(k.upper() + ' '  + message)

    def handle_commands(self):
        if not self.signal_id_queue.empty():
            function_call = self.signal_id_queue.get()
            if hasattr(self, function_call):
                try:
                    getattr(self, function_call)()
                except:
                    self.printc(traceback.format_exc())
            else:
                self.printc('{0} method does not exists'.format(function_call))

    def pass_signal(self, signal_id):
        self.signal_id_queue.put(str(signal_id))
        
    ############## Measurement file handling ########################
    def add_cells_to_database(self, id, update_gui = True):
        self.save_cells()
        scan_regions, region_name, h, measurement_file_path, depth = self.read_scan_regions(id)
        if scan_regions is None:
            return
        #read cell info from measurement file
        h_measurement = hdf5io.Hdf5io(measurement_file_path)
        scan_regions[region_name]['process_status'][id]['find_cells_ready'] = True
        h.load('images')
        if not hasattr(h,  'images'):
            h.images = {}
        h.images[id] = {}
        h.images[id]['meanimage'] = h_measurement.findvar('meanimage')
        h.images[id]['accepted_somaimage'] = h_measurement.findvar('accepted_somaimage')
        h.images[id]['scale'] = h_measurement.findvar('image_scale')
        h.images[id]['origin'] = h_measurement.findvar('image_origin')
        self.images = copy.deepcopy(h.images)
        h.load('cells')
        if not hasattr(h,  'cells'):
            h.cells = {}
        if not h.cells.has_key(region_name):
            h.cells[region_name] = {}
        h.load('roi_curves')
        if not hasattr(h,  'roi_curves'):
            h.roi_curves = {}
        if not h.roi_curves.has_key(region_name):
            h.roi_curves[region_name] = {}
        soma_rois = h_measurement.findvar('soma_rois')
        roi_centers = h_measurement.findvar('roi_centers')
        roi_curves= h_measurement.findvar('roi_curve_images')
        if hasattr(roi_curves, 'shape'):
            roi_curves = [roi_curves]
        depth = int(h_measurement.findvar('position')['z'][0])
        stimulus = h_measurement.findvar('stimulus_class')
        if soma_rois is None or len(soma_rois) == 0:
            number_of_new_cells = 0
        else:
            number_of_new_cells = len(soma_rois)
        for i in range(number_of_new_cells):
            cell_id = ('{0}_{1:2}_{2}_{3}'.format(depth, i, stimulus, id)).replace(' ', '0')
            h.cells[region_name][cell_id] = {}
            h.cells[region_name][cell_id]['depth'] = depth
            h.cells[region_name][cell_id]['id'] = id
            h.cells[region_name][cell_id]['soma_roi'] = soma_rois[i]
            h.cells[region_name][cell_id]['roi_center'] = roi_centers[i]
            h.cells[region_name][cell_id]['accepted'] = False
            h.cells[region_name][cell_id]['group'] = ''
            h.cells[region_name][cell_id]['add_date'] = utils.datetime_string().replace('_', ' ')
            h.cells[region_name][cell_id]['stimulus'] = stimulus
            h.roi_curves[region_name][cell_id] = roi_curves[i]
            
        h_measurement.close()
        #Save changes
        h.scan_regions = scan_regions
        h.save(['scan_regions', 'images', 'cells', 'roi_curves'], overwrite=True)
        self.printc('{1} cells added from {0}'.format(id, number_of_new_cells))
        h.close()
        #Create copy of mouse file that can be read by other applications
        self.backup_mouse_file(h.filename)
        if update_gui:
            self.parent.update_cell_list(copy.deepcopy(h.cells))
            self.parent.update_cell_filter_list()
            self.parent.update_jobhandler_process_status(scan_regions)
#            self.update_cell_group_combobox()
        
    def set_process_status_flag(self, id, flag_names):
        scan_regions, region_name, h, measurement_file_path, depth = self.read_scan_regions(id)
        if scan_regions is None:
            return
        for flag_name in flag_names:
            scan_regions[region_name]['process_status'][id][flag_name] = True
        h.scan_regions = scan_regions
        h.save('scan_regions', overwrite=True)
        h.close()
        self.backup_mouse_file(h.filename)
        self.printc('Process status flag set: {1}/{0}'.format(flag_names,  id))
        self.parent.update_jobhandler_process_status(scan_regions)
    
    def add_measurement_id(self, id):
        scan_regions, region_name, h, measurement_file_path, depth = self.read_scan_regions(id)
        if scan_regions is None:
            return
        if not scan_regions[region_name].has_key('process_status'):
            scan_regions[region_name]['process_status'] = {}
        if scan_regions[region_name]['process_status'].has_key(id):
            self.printc('ID alread exists')
        scan_regions[region_name]['process_status'][id] = {}
        scan_regions[region_name]['process_status'][id]['fragment_check_ready'] = False
        scan_regions[region_name]['process_status'][id]['mesextractor_ready'] = False
        scan_regions[region_name]['process_status'][id]['find_cells_ready'] = False
        scan_regions[region_name]['process_status'][id]['info'] = {}
        scan_regions[region_name]['process_status'][id]['info']['depth'] = depth
        h.scan_regions = scan_regions
        h.save('scan_regions', overwrite=True)
        h.close()
        self.backup_mouse_file(h.filename)
        self.printc('Measurement ID added: {0}'.format(id))
        self.parent.update_jobhandler_process_status(scan_regions)
        
    def read_scan_regions(self, id):
        #read call parameters
        measurement_file_path = file.get_measurement_file_path_from_id(id, self.config)
        if measurement_file_path is None or not os.path.exists(measurement_file_path):
            self.printc('Measurement file not found: {0}, {1}' .format(measurement_file_path,  id))
            return 4*[None]
        fromfile = hdf5io.read_item(measurement_file_path, ['call_parameters', 'position'])
        call_parameters = fromfile[0]
        depth = fromfile[1]['z'][0]
        #Read the database from the mouse file pointed by the measurement file
        mouse_file = os.path.join(self.config.EXPERIMENT_DATA_PATH, call_parameters['mouse_file'])
        if not os.path.exists(mouse_file):
            self.printc('Mouse file ({0}) assigned to measurement ({1}) is missing' .format(mouse_file,  id))
            return 4*[None]
        h = hdf5io.Hdf5io(mouse_file)
        scan_regions = h.findvar('scan_regions')
        if scan_regions[call_parameters['region_name']].has_key(id):
            self.printc('ID already exists: {0}'.format(id))
            h.close()
            return 4*[None]
        return scan_regions, call_parameters['region_name'], h, measurement_file_path, depth
 
    def rebuild_cell_database(self):
        self.clear_process_status()
        measurement_file_paths = file.filtered_file_list(self.config.EXPERIMENT_DATA_PATH, ['fragment','hdf5'], fullpath = True,filter_condition='and')
        for measurement_path in measurement_file_paths:
            id = file.parse_fragment_filename(measurement_path)['id']
            flags = ['fragment_check_ready', 'mesextractor_ready']
            self.add_measurement_id(id)
            self.set_process_status_flag(id, flags)
            self.add_cells_to_database(id, update_gui = (measurement_file_paths[-1] == measurement_path))
        
    def clear_process_status(self):
        h = hdf5io.Hdf5io(self.mouse_file)
        self.backup_mouse_file(self.mouse_file)
        h.load('roi_curves')
        h.roi_curves = {}
        h.load('cells')
        h.cells = {}
        h.load('scan_regions')
        for region_name in h.scan_regions.keys():
            h.scan_regions[region_name]['process_status'] = {}
        h.save(['scan_regions', 'roi_curves', 'cells'], overwrite=True)
        h.close()
        self.cells = {}

    def next_cell(self):
        current_index = self.parent.roi_widget.select_cell_combobox.currentIndex()
        current_index += 1
        if current_index >= len(self.cell_ids):
            current_index = 0
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
        self.cells[self.parent.get_current_region_name()][self.parent.get_current_cell_id()]['group'] = str(self.parent.roi_widget.cell_group_edit_combobox.currentText())
        self.next_cell()
        self.cell_status_changed_in_cache = True
        
    def save_cells(self):
        if hasattr(self, 'cells') and self.cell_status_changed_in_cache:
            h = hdf5io.Hdf5io(self.mouse_file)
            h.load('cells')
            if hasattr(h, 'cells') and hasattr(h.cells, 'items'):
                for region_name, cells_in_region in self.cells.items():
                    for cell_id, cell in cells_in_region.items():
                        h.cells[region_name][cell_id] = cell
                h.save('cells', overwrite=True)
                self.cells = copy.deepcopy(h.cells)
            h.close()
            self.backup_mouse_file()
            self.printc('Cell settings saved')
            self.parent.update_cell_group_combobox()
            self.cell_status_changed_in_cache = False
            
    ############## Analysis ########################
    def set_mouse_file(self):
        self.printc('Mouse file sent to jobhandler')
        self.queues['analysis']['out'].put('SOCset_mouse_fileEOCfilename={0}EOP'.format(os.path.split(self.mouse_file)[1].replace('.hdf5', '_jobhandler.hdf5')))
                                           
    ########## Manage context ###############
    def init_variables(self):
        self.files_to_delete = []
        
    def load_context(self):
        context_hdf5 = hdf5io.Hdf5io(self.config.CONTEXT_FILE)
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
        self.last_region_name = context_hdf5.findvar('last_region_name')
        context_hdf5.close()
        self.stage_position_valid = False
        self.scan_regions = {}
        
    def save_context(self):        
        context_hdf5 = hdf5io.Hdf5io(self.config.CONTEXT_FILE)
        context_hdf5.stage_origin = self.stage_origin
        context_hdf5.stage_position = self.stage_position        
        context_hdf5.save('stage_origin',overwrite = True)
        context_hdf5.save('stage_position', overwrite = True)
        if hasattr(self,  'xy_scan'):
            context_hdf5.xy_scan = self.xy_scan
            context_hdf5.save('xy_scan', overwrite = True)
        if hasattr(self, 'xz_scan'):
            context_hdf5.xz_scan = self.xz_scan
            context_hdf5.save('xz_scan', overwrite = True)
        context_hdf5.close()

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
        
    def move_stage(self):
        movement = self.parent.scanc().split(',')
        if len(movement) == 2:
            #Only two values are accepted
            movement.append('0')
        else:
            self.printc('invalid coordinates')
            return
        self.parent.main_widget.scan_region_groupbox.scan_regions_combobox.setEditText('')
        self.move_stage_relative(movement)

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
                self.xy_scan,  result = self.mes_interface.acquire_xy_scan(self.config.MES_TIMEOUT, parameter_file = parameter_file_path)
            else:
                self.xy_scan = {}
                result = False
        elif self.parent.main_widget.scan_region_groupbox.use_saved_scan_settings_settings_checkbox.checkState() == 0:
            self.xy_scan,  result = self.mes_interface.acquire_xy_scan(self.config.MES_TIMEOUT)
        if hasattr(self.xy_scan, 'has_key'):
            if self.xy_scan.has_key('path'):#For unknown reason this key is not found sometimes
                self.files_to_delete.append(self.xy_scan['path'])
        if result:
            self.show_image(self.xy_scan[self.config.DEFAULT_PMT_CHANNEL], 0, self.xy_scan['scale'], origin = self.xy_scan['origin'])
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
        self.show_image(self.xz_scan['scaled_image'], 2, self.xz_scan['scaled_scale'], line = objective_position_marker, origin = self.xz_scan['origin'])
        self.save_context()
        self.xz_scan_acquired = True
        return result
        
    def create_xz_lines(self):
        self.printc('Creating xz lines,  please wait...')
        selected_mouse_file = str(self.parent.main_widget.scan_region_groupbox.select_mouse_file.currentText())
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
            roi_locations, rois = experiment_data.read_merge_rois(self.cells, 
                                cell_group = self.parent.get_current_cell_group(),
                                region_name =  region_name, 
                                objective_position = self.objective_position, 
                                objective_origin = self.objective_origin, 
                                z_range = self.config.XZ_SCAN_CONFIG['Z_RANGE'], 
                                merge_distance = merge_distance)
            if roi_locations is not None:
                line_length = str(self.parent.roi_widget.xz_line_length_combobox.currentText())
                xz_config = copy.deepcopy(self.config.XZ_SCAN_CONFIG)
                if line_length != '':
                    xz_config['LINE_LENGTH'] = float(line_length)
                if not self.mes_interface.create_XZline_from_points(roi_locations, xz_config, True):
                        selfprintc('Creating xz lines did not succeed')
                else:
                    self.printc('{0} xz lines created'.format(roi_locations.shape[0]))
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
        mouse_birth_date = self.parent.animal_parameters_widget.mouse_birth_date.date()
        mouse_birth_date = '{0}-{1}-{2}'.format(mouse_birth_date.day(),  mouse_birth_date.month(),  mouse_birth_date.year())
        gcamp_injection_date = self.parent.animal_parameters_widget.gcamp_injection_date.date()
        gcamp_injection_date = '{0}-{1}-{2}'.format(gcamp_injection_date.day(),  gcamp_injection_date.month(),  gcamp_injection_date.year())                

        self.animal_parameters = {
            'mouse_birth_date' : mouse_birth_date,
            'gcamp_injection_date' : gcamp_injection_date,
            'anesthesia_protocol' : str(self.parent.animal_parameters_widget.anesthesia_protocol.currentText()),
            'gender' : str(self.parent.animal_parameters_widget.gender.currentText()),
            'ear_punch_l' : str(self.parent.animal_parameters_widget.ear_punch_l.currentText()), 
            'ear_punch_r' : str(self.parent.animal_parameters_widget.ear_punch_r.currentText()),
            'strain' : str(self.parent.animal_parameters_widget.mouse_strain.currentText()),
            'comments' : str(self.parent.animal_parameters_widget.comments.currentText()),
        }        
        name = '{0}_{1}_{2}_{3}_{4}' .format(self.animal_parameters['strain'], self.animal_parameters['mouse_birth_date'] , self.animal_parameters['gcamp_injection_date'], \
                                         self.animal_parameters['ear_punch_l'], self.animal_parameters['ear_punch_r'])

        self.mouse_file = os.path.join(self.config.EXPERIMENT_DATA_PATH, self.generate_animal_filename('mouse', self.animal_parameters))
        
        if os.path.exists(self.mouse_file):
            self.printc('Animal parameter file already exists')
        else:
            variable_name = 'animal_parameters_{0}'.format(int(time.time()))
            hdf5io.save_item(self.mouse_file, variable_name, self.animal_parameters)
            time.sleep(0.1)#Wait till file is created
            #set selected mouse file to this one
            self.parent.update_mouse_files_combobox(set_to_value = os.path.split(self.mouse_file)[-1])
            #Clear image displays showing regions
            self.emit(QtCore.SIGNAL('clear_image_display'), 1)
            self.emit(QtCore.SIGNAL('clear_image_display'), 3)
            self.printc('Animal parameter file saved')
            self.backup_mouse_file()
            
    
    ################### Regions #######################
    def add_scan_region(self, widget = None):
        '''
        The following data are saved:
        -two photon image of the brain surface
        -mes parameter file of two photon acquisition so that later the very same image could be taken to help realignment
        -objective positon where the data acquisition shall take place. This is below the brain surface
        -stage position. If master position is saved, the current position is set to origin. The origin of stimulation software is also 
        '''
        self.parent.update_current_mouse_path()
        if not self.xz_scan_acquired and hasattr(self, 'xz_scan'):
            del self.xz_scan
        if not hasattr(self, 'xy_scan'):
            self.printc('No brain surface image is acquired')
            return
        if self.xy_scan['averaging'] < self.config.MIN_SCAN_REGION_AVERAGING:
            self.printc('Brain surface image averaging is only {0}, set it to {1}' .format(self.xy_scan['averaging'], self.config.MIN_SCAN_REGION_AVERAGING))
            return
        if hasattr(self, 'xz_scan') and self.xz_scan['averaging'] < self.config.MIN_SCAN_REGION_AVERAGING:
            self.printc('Number of frames is only {0}, set it to {1}' .format(self.xz_scan['averaging'], self.config.MIN_SCAN_REGION_AVERAGING))
            return
        if not (os.path.exists(self.mouse_file) and '.hdf5' in self.mouse_file):
            self.printc('mouse file not found')
            return
        result, self.objective_position = self.mes_interface.read_objective_position(timeout = self.config.MES_TIMEOUT)
        if not result:
            self.printc('MES does not respond')
            return
        if not self.read_stage(display_coords = False):
            self.printc('Stage cannot be accessed')
            return
        #Read scan regions
        hdf5_handler = hdf5io.Hdf5io(self.mouse_file)
        self.scan_regions = hdf5_handler.findvar('scan_regions')
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
                hdf5_handler.close()
                return
        else:
            relative_position = numpy.round(self.stage_position-self.stage_origin, 0)
            region_name_tag = '_{0}_{1}'.format(int(relative_position[0]),int(relative_position[1]))
            region_name = region_name + region_name_tag
            region_name = region_name.replace(' ', '_')
            #Check if generated region name exists
            if self.scan_regions.has_key(region_name):
                #Ask for confirmation to overwrite if region name already exists
                self.emit(QtCore.SIGNAL('show_overwrite_region_messagebox'))
                while self.gui_thread_queue.empty():
                    time.sleep(0.1) 
                if not self.gui_thread_queue.get():
                    self.printc('Region not saved')
                    hdf5_handler.close()
                    return
        if not('master' in region_name or '0_0' in region_name or self.has_master_position(self.scan_regions)):
            self.printc('Master position has to be defined')
            hdf5_handler.close()
            return
        if 'master' in region_name:
           if not self.set_stage_origin():
                self.printc('Setting origin did not succeed')
                hdf5_handler.close()
                return
        scan_region = {}
        scan_region['add_date'] = utils.datetime_string().replace('_', ' ')
        scan_region['position'] = utils.pack_position(self.stage_position-self.stage_origin, self.objective_position)
        scan_region['xy'] = {}
        scan_region['xy']['image'] = self.xy_scan[self.config.DEFAULT_PMT_CHANNEL]
        scan_region['xy']['scale'] = self.xy_scan['scale']
        scan_region['xy']['origin'] = self.xy_scan['origin']
        scan_region['xy']['mes_parameters']  = utils.file_to_binary_array(self.xy_scan['path'].tostring())
        #Save xy line scan parameters
        if hasattr(self, 'xz_scan') and False:
            #Ask for verification wheather line scan is set back to xy
            self.emit(QtCore.SIGNAL('show_verify_add_region_messagebox'))
            while self.gui_thread_queue.empty():
                time.sleep(0.1) 
            if not self.gui_thread_queue.get():
                self.printc('Region not saved')
                hdf5_handler.close()
                return
        result, line_scan_path, line_scan_path_on_mes = self.mes_interface.get_line_scan_parameters()
        if result and os.path.exists(line_scan_path):
            scan_region['xy_scan_parameters'] = utils.file_to_binary_array(line_scan_path)
            os.remove(line_scan_path)
        #Vertical section
        if hasattr(self, 'xz_scan'):
            if self.xz_scan !=  None:
                scan_region['xz'] = self.xz_scan
                scan_region['xz']['mes_parameters'] = utils.file_to_binary_array(self.xz_scan['path'].tostring())
            else:
                self.printc('Vertical scan is not available')
        else:
            self.printc('Vertical scan is not available')
        #Save new scan region to hdf5 file
        self.scan_regions[region_name] = scan_region
        hdf5_handler.scan_regions = self.scan_regions
        hdf5_handler.save('scan_regions', overwrite = True)
        hdf5_handler.close()
        self.backup_mouse_file()
        self.parent.update_region_names_combobox(region_name)
        self.update_scan_regions()
        self.printc('{0} scan region saved'.format(region_name))

    def remove_scan_region(self):
        selected_region = self.parent.get_current_region_name()
        if selected_region != 'master' and 'r_0_0' not in selected_region:
            if self.scan_regions.has_key(selected_region):
                del self.scan_regions[selected_region]
            hdf5io.save_item(self.mouse_file, 'scan_regions', self.scan_regions, overwrite=True)
            self.backup_mouse_file()
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
            self.printc('Origin not set')
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
            if not self.register_images(self.xy_scan[self.config.DEFAULT_PMT_CHANNEL], self.scan_regions[selected_region]['xy']['image'], self.xy_scan['scale']):
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
            if not self.register_images(self.xy_scan[self.config.DEFAULT_PMT_CHANNEL], self.scan_regions[selected_region]['xy']['image'], self.xy_scan['scale']):
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
        hdf5io.save_item(mouse_file_path,  'intensity_calibration_data', xz_scans, overwrite = False)
        self.printc('Done')
        
    def stop_experiment(self):
        command = 'SOCabort_experimentEOCguiEOP'
        self.queues['stim']['out'].put(command)
        self.printc('Stopping experiment requested, please wait')

    def graceful_stop_experiment(self):
        command = 'SOCgraceful_stop_experimentEOCguiEOP'
        self.queues['stim']['out'].put(command)
        self.printc('Graceful stop requested, please wait')

    def start_experiment(self):
        self.printc('Experiment started, please wait')
        self.experiment_parameters = {}
        self.experiment_parameters['mouse_file'] = os.path.split(self.mouse_file)[1]
        region_name = self.parent.get_current_region_name()
        if len(region_name)>0:
            self.experiment_parameters['region_name'] = region_name
        objective_range_string = str(self.parent.main_widget.experiment_control_groupbox.objective_positions_combobox.currentText())
        if len(objective_range_string)>0:
            objective_positions = map(float, objective_range_string.split(','))
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
            self.experiment_parameters['laser_intensities'] = numpy.linspace(self.experiment_parameters['laser_intensities'][0],
                                                                                            self.experiment_parameters['laser_intensities'][1], 
                                                                                            self.experiment_parameters['number_of_depths'])
            #generic.expspace(self.experiment_parameters['laser_intensities'][0], self.experiment_parameters['laser_intensities'][1],  self.experiment_parameters['objective_positions'].shape[0])
        #Set back next/prev/redo button texts
        self.parent.main_widget.experiment_control_groupbox.next_depth_button.setText('Next')
        self.parent.main_widget.experiment_control_groupbox.previous_depth_button.setText('Prev')
        self.parent.main_widget.experiment_control_groupbox.redo_depth_button.setText('Redo')
        #Start experiment batch
        self.generate_experiment_start_command(self.experiment_parameters)

    def generate_experiment_start_command(self, experiment_parameters):
        #Ensure that user can switch between different stimulations during the experiment batch
        self.experiment_parameters['experiment_config'] = str(self.parent.main_widget.experiment_control_groupbox.experiment_name.currentText())
        self.experiment_parameters['scan_mode'] = str(self.parent.main_widget.experiment_control_groupbox.scan_mode.currentText())
        if self.experiment_parameters['scan_mode'] == 'xz':
            line_length = str(self.parent.roi_widget.xz_line_length_combobox.currentText())
            if line_length != '':
                self.experiment_parameters['xz_line_length'] = line_length
            merge_distance = str(self.parent.roi_widget.cell_merge_distance_combobox.currentText())
            if merge_distance != '':
                self.experiment_parameters['merge_distance'] = merge_distance
        parameters = 'experiment_config={0},scan_mode={1}' \
                        .format(experiment_parameters['experiment_config'], experiment_parameters['scan_mode'])
        if experiment_parameters.has_key('mouse_file') and experiment_parameters.has_key('mouse_file') != '':
            parameters += ',mouse_file={0}'.format(experiment_parameters['mouse_file'])
        if experiment_parameters.has_key('current_objective_position_index') and experiment_parameters.has_key('objective_positions'):
            objective_position = experiment_parameters['objective_positions'][experiment_parameters['current_objective_position_index']]
            parameters += ',objective_positions={0}'.format(objective_position)
            self.parent.main_widget.experiment_control_groupbox.redo_depth_button.setText('Redo {0} um'.format(objective_position))
            #Update redo and next buttons
            time.sleep(0.2)
            if experiment_parameters['current_objective_position_index']+1 < experiment_parameters['objective_positions'].shape[0]:
                objective_position = experiment_parameters['objective_positions'][experiment_parameters['current_objective_position_index']+1]
                self.parent.main_widget.experiment_control_groupbox.next_depth_button.setText('Next {0} um'.format(objective_position))
            if experiment_parameters['current_objective_position_index'] > 0:
                objective_position = experiment_parameters['objective_positions'][experiment_parameters['current_objective_position_index']-1]
                self.parent.main_widget.experiment_control_groupbox.previous_depth_button.setText('Prev {0} um'.format(objective_position))
        if experiment_parameters.has_key('current_objective_position_index') and experiment_parameters.has_key('laser_intensities'):
            laser_intensities = experiment_parameters['laser_intensities'][experiment_parameters['current_objective_position_index']]
            parameters += ',laser_intensities={0}'.format(laser_intensities)
        if experiment_parameters.has_key('region_name') and experiment_parameters['region_name'] != '':
            parameters += ',region_name='+experiment_parameters['region_name']
        if experiment_parameters['scan_mode'] == 'xz':
            if experiment_parameters.has_key('xz_line_length'):
                parameters += ',xz_line_length='+experiment_parameters['xz_line_length']
            if experiment_parameters.has_key('z_resolution'):
                parameters += ',z_resolution='+experiment_parameters['z_resolution']
            if experiment_parameters.has_key('merge_distance'):
                parameters += ',merge_distance='+experiment_parameters['merge_distance']
            parameters += ',cell_group='+self.parent.get_current_cell_group()
        command = 'SOCexecute_experimentEOC{0}EOP' .format(parameters)
        self.backup_mouse_file(tag = 'stim')
        self.queues['stim']['out'].put(command)
        self.printc(parameters)
        
    def previous_experiment(self):
        if self.experiment_parameters.has_key('current_objective_position_index') and \
            self.experiment_parameters['current_objective_position_index'] > 0:
            self.experiment_parameters['current_objective_position_index'] -= 1
            self.generate_experiment_start_command(self.experiment_parameters)
        
    def redo_experiment(self):
        self.generate_experiment_start_command(self.experiment_parameters)
        
    def next_experiment(self):
        if self.experiment_parameters.has_key('current_objective_position_index'):
            self.experiment_parameters['current_objective_position_index'] += 1
            if self.experiment_parameters['current_objective_position_index'] < self.experiment_parameters['objective_positions'].shape[0]:
                self.generate_experiment_start_command(self.experiment_parameters)
       
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
            
    ############ Data processing control ##################
    def run_fragment_process(self):
        command = 'SOCrun_fragment_status_checkEOCEOP'
        self.queues['analysis']['out'].put(command)
        self.printc('Run fragment process')
        
    def show_fragment_process_status(self):
        command = 'SOCrun_fragment_status_checkEOCstatus_only=TrueEOP'
        self.queues['analysis']['out'].put(command)
        self.printc('Read fragment process status')
            
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
        if hasattr(self.parent, 'main_widget') and hasattr(self.command_relay_server, 'servers'):
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
            if connection_status['STIM_ANALYSIS/ANALYSIS'] and connection_status['STIM_ANALYSIS/STIM']:
                connected += 'STIM-ANALYSIS'
                n_connected += 1
            n_connections = len(self.config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'].keys())
            connected = 'Alive connections ({0}/{1}): '.format(n_connected, n_connections) + connected
            self.parent.main_widget.connected_clients_label.setText(connected)
            
    ################ Helper functions ###################
    def show_help(self):
        if webbrowser.open_new_tab(self.config.MANUAL_URL):
            self.printc('Shown in default webbrowser')
            
    def add_simulated_measurement_file(self):
        self.clear_process_status()
        commands = []
        for path in file.listdir_fullpath(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'simulated_data')):
            if '.hdf5' in path:
                h = hdf5io.Hdf5io(path)
                h.load('call_parameters')
                h.call_parameters['mouse_file'] = os.path.split(self.mouse_file)[1]
                h.save('call_parameters', overwrite = True)
                h.close()
            target_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, os.path.split(path)[1])
            if os.path.exists(target_path):
                os.remove(target_path)
            shutil.copyfile(path, target_path)
            if '.hdf5' in path:
                commands.append('SOCmeasurement_readyEOC{0}EOP'.format(file.parse_fragment_filename(path)['id']))
                self.printc('Simulated file copied: {0}'.format(path))
        time.sleep(1.0)
        for command in commands:
            self.queues['stim']['in'].put(command)
        self.queues['analysis']['out'].put('SOCclear_joblistEOCEOP')
        self.printc('Done')
            
    def save_xy_scan(self):
        hdf5_handler = hdf5io.Hdf5io(file.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'xy_scan.hdf5')))
        hdf5_handler.xy_scan = self.xy_scan
        hdf5_handler.stage_position = self.stage_position
        hdf5_handler.save(['xy_scan', 'stage_position'])
        hdf5_handler.close()
            
    ############# Helpers #############
    def backup_mouse_file(self, mouse_file = None, tag = None):
        if mouse_file is None:
            mouse_file = self.mouse_file
        if tag is None:
            tag = 'copy'
        copy_path = mouse_file.replace('.hdf5', '_' +tag+'.hdf5')
        shutil.copyfile(mouse_file, copy_path)
        time.sleep(0.2)#Wait to make sure that file is completely copied
        
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
        image_hdf5_handler = hdf5io.Hdf5io(os.path.join(self.config.CONTEXT_PATH, 'image.hdf5'))
        image_hdf5_handler.f1 = f1
        image_hdf5_handler.f2 = f2
        image_hdf5_handler.save(['f1', 'f2'], overwrite = True)
        image_hdf5_handler.close()
        
    def register_images(self, f1, f2, scale,  print_result = True):
        import Image
#        from visexpA.engine.dataprocessors import generic
#        Image.fromarray(generic.normalize(f1,  numpy.uint8)).save(file.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'f1.png')))
#        Image.fromarray(generic.normalize(f2,  numpy.uint8)).save(file.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'f2.png')))
        self.create_image_registration_data_file(f1, f2)
        utils.empty_queue(self.queues['analysis']['in'])
        arguments = ''
        self.queues['analysis']['out'].put('SOCregisterEOC' + arguments + 'EOP')
        if not utils.wait_data_appear_in_queue(self.queues['analysis']['in'], 10.0):
            self.printc('Analysis not connected')
            return False
        if 'SOCregisterEOCstartedEOP' not in self.queues['analysis']['in'].get():
            self.printc('Image registration did not start')
            return False
        if utils.wait_data_appear_in_queue(self.queues['analysis']['in'], timeout = self.config.MAX_REGISTRATION_TIME):#TODO: the content of the queue also need to be checked
            while not self.queues['analysis']['in'].empty():
                    response = self.queues['analysis']['in'].get()
                    if 'error' in response:
                        self.printc('Image registration resulted error')
                        return False
                    elif 'register' in response:
                        self.registration_result = self.parse_list_response(response) #rotation in angle, center or rotation, translation
                        self.suggested_translation = utils.cr(utils.nd(scale) * self.registration_result[-2:]*numpy.array([-1, 1]))
                        if print_result:
                            self.printc(self.registration_result[-2:])
                            self.printc('Suggested translation: {0}'.format(self.suggested_translation))
                        return True
        else:
            self.printc('Analysis does not respond')
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
        name = '{5}_{0}_{1}_{2}_{3}_{4}.{6}' .format(animal_parameters['strain'], animal_parameters['mouse_birth_date'] , animal_parameters['gcamp_injection_date'], \
                                         animal_parameters['ear_punch_l'], animal_parameters['ear_punch_r'], tag, extension)
        return name
        
    def fetch_backup_mouse_file_path(self):
        mouse_file_copy = self.mouse_file.replace('.hdf5', '_copy.hdf5')
        if os.path.exists(mouse_file_copy):
            return mouse_file_copy
        else:
            return self.mouse_file
        
    

# Test cases:
# 1. move stage - set stage origin - including read stage
# 2. set / read objective
# 3. acquire z stack
# 4. add region with vertical scan test
# 5. move to region, register and realign
# 6. vertical realign


if __name__ == '__main__':
    pass
    
