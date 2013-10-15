import sys
import time
import Queue
import os
import numpy
import traceback
import re
import cPickle as pickle

import PyQt4.QtCore as QtCore

from visexpman.engine.generic import introspect
from visexpman.engine.generic import command_parser
from visexpman.engine.vision_experiment import screen
from visexpman.engine.generic import utils
from visexpman.engine.hardware_interface import network_interface
from visexpman.engine.hardware_interface import stage_control
from visexpA.engine.datahandlers import hdf5io

find_experiment_class_name = re.compile('class (.+)\(experiment.Experiment\)')
find_experiment_config_class_name = re.compile('class (.+)\(experiment.ExperimentConfig\)')

class CommandHandler(command_parser.CommandParser, screen.ScreenAndKeyboardHandler):
    '''
    Handles all the commands related to vision experiment manager (aka stimulation software, visexp_runner). Commands are received from keyboard and network
    interface. The network interface is connected to a gui application of the framework (visexp_gui).
    
    There are two groups of commands:
    -adjustments: like show bullseye, change background color, set filterwheel, stage read/write. These are executed in up to a couple of seconds
    -experiment control: start_experiment, execution time can be several minutes depending on the experiment/stimulus configuration
    '''
    def __init__(self):
        self.keyboard_command_queue = Queue.Queue()
        #Here the set of queues are defined from commands are parsed
        queue_in = [self.queues['mes']['in'], self.queues['gui']['in'], self.keyboard_command_queue, self.queues['udp']['in']]
        #Set of queues where command parser output is relayed NOT YET IMPLEMENTED IN command_parser
        queue_out = self.queues['gui']['out']
        command_parser.CommandParser.__init__(self, queue_in, queue_out, log = self.log, failsafe = False)
        screen.ScreenAndKeyboardHandler.__init__(self)
        self.stage_origin = numpy.zeros(3)
        if hasattr(self.config, 'CONTEXT_FILE'):
            try:
                self.stage_origin = hdf5io.read_item(self.config.CONTEXT_FILE, 'stage_origin')
            except:
                self.log.info('Context file cannot be opened')
            if self.stage_origin == None:
                self.stage_origin = numpy.zeros(3)
        
###### Commands ######    
    def quit(self):
        if hasattr(self, 'loop_state'):
            self.loop_state = 'end loop'
        return 'quit'
        
    def bullseye(self,  size = 0):
        self.show_bullseye = not self.show_bullseye
        return 'bullseye'

    def color(self, color):
        self.user_background_color = int(color)
        return 'color'
        
    def hide_menu(self):
        self.hide_menu = not self.hide_menu
        if self.hide_menu:
            return ''
        else:
            return 'menu is unhidden'

    def echo(self, par=''):
        import random
        self.queues['mes']['out'].put('SOCechoEOCvisexpman_{0}EOP'.format(int(random.random()*10e5)))
        result = network_interface.wait_for_response(self.queues['mes']['in'], ['SOCechoEOCvisexpmanEOP'], timeout = self.config.MES_TIMEOUT)
        return 'echo ' + str(result)
        
    def filterwheel(self, filterwheel_id = 1, filter_position = 1):
        if hasattr(self.config, 'FILTERWHEEL_SERIAL_PORT'):            
            filterwheel = instrument.Filterwheel(self.config, id = filterwheel_id)
            filterwheel.set(filter_position)
            if os.name == 'nt':
                filterwheel.release_instrument()
        return 'filterwheel ' + str(filterwheel_id) + ',  ' +str(filter_position)
        
    def stage(self,par, new_x = 0, new_y = 0, new_z = 0):
        '''
        read stage:
            command: SOCstageEOCreadEOP
            response: SOCstageEOCx,y,zEOP
        set stage:
            command: SOCstageEOCset,y,zEOP
            response: SOCstageEOC<status>,x,y,zEOP, <status> = OK, error
        '''
        try:
            st = time.time()
            if 'read' in par or 'set' in par or 'origin' in par:
                stage = stage_control.AllegraStage(self.config, log = self.log, queue = self.queues['gui']['in'])
                position = stage.read_position()
                if 'set' not in par:
                    self.queues['gui']['out'].put('SOCstageEOC{0},{1},{2}EOP'.format(position[0], position[1], position[2]))
                if 'origin' in par:
                    self.stage_origin = position
                if 'set' in par:
                    new_position = numpy.array([float(new_x), float(new_y), float(new_z)])
                    reached = stage.move(new_position)
                    position = stage.position
                    self.queues['gui']['out'].put('SOCstageEOC{0},{1},{2}EOP'.format(position[0], position[1], position[2]))
                stage.release_instrument()
            return str(par) + ' ' + str(position) + '\n' + str(time.time() - st) + ' ' + str(stage.command_counter )
        except:
            return str(traceback.format_exc())

###### Experiment related commands ###############
    def select_experiment(self, experiment_index):
        '''
        Selects experiment config based on keyboard command and instantiates the experiment config class
        '''
        self.selected_experiment_config_index = int(experiment_index)
        self.experiment_config = self.experiment_config_list[int(self.selected_experiment_config_index)][1](self.config, self.queues, self.connections, self.log)
        return 'selected experiment: ' + str(experiment_index) + ' '

    def execute_experiment(self, **kwargs):
        '''
        There are two ways of executing and experiment:
        1. source code of experiment and experiment config classes are received from a remote machine. These classes are instantiated and the experiment
        starting method is called
        2. Only parameters of the experiment are sent and its run method is called. Such parameters can be provided: experiment config name, scan region name, scan mode, xz scan parameters ...
        '''
        if kwargs.has_key('source_code'):
            source_code = kwargs['source_code']
        else:
           source_code = ''
        if kwargs.has_key('experiment_config'):
            for experiment_config in self.experiment_config_list:
                if experiment_config[1].__name__ == kwargs['experiment_config']:
                    self.experiment_config = experiment_config[1](self.config, self.queues, self.connections, self.log, parameters = kwargs)
                    break
        elif source_code != '':
            loadable_source_code = source_code.replace('<newline>', '\n')
            loadable_source_code = loadable_source_code.replace('<comma>', ',')
            loadable_source_code = loadable_source_code.replace('<equal>', '=')
            experiment_class_name = find_experiment_class_name.findall(loadable_source_code)[0]
            experiment_config_class_name = find_experiment_config_class_name.findall(loadable_source_code)[0]
            #rename classes
            tag = '_' + str(int(time.time()))
            loadable_source_code = loadable_source_code.replace(experiment_class_name, experiment_class_name+tag)
            loadable_source_code = loadable_source_code.replace(experiment_config_class_name, experiment_config_class_name+tag)
            
            introspect.import_code(loadable_source_code,'experiment_module',add_to_sys_modules=1)
            experiment_module = __import__('experiment_module')
            self.experiment_config = getattr(experiment_module, experiment_config_class_name+tag)(self.config, self.queues, \
                                                                                                  self.connections, self.log, getattr(experiment_module,experiment_class_name+tag), loadable_source_code)
        else:
            #reload(sys.modules[self.experiment_config_list[int(self.selected_experiment_config_index)][1].__module__])#This results the failure of pickling config:
            self.experiment_config = self.experiment_config_list[int(self.selected_experiment_config_index)][1](self.config, self.queues, self.connections, self.log, parameters = kwargs)
        #Change screen to pre expriment visual pattern
        if hasattr(self.experiment_config, 'pre_runnable') and self.experiment_config.pre_runnable is not None:
            self.clear_screen_to_background()
            self.experiment_config.pre_runnable.run()
            self.flip()
        #Remove abort commands from queue
        utils.is_keyword_in_queue(self.queues['gui']['in'], 'abort', keep_in_queue = False)
        context = {}
        context['stage_origin'] = self.stage_origin
        result = self.experiment_config.runnable.run_experiment(context)
        return result

class CommandSender(QtCore.QThread):
    '''
    A thread that can be configured to send commands via keyboard command queue with a predefined timing
    '''
    def __init__(self, config, caller, commands):
        self.config = config
        self.caller = caller
        self.commands = commands
        QtCore.QThread.__init__(self)
        
    def send_command(self, command):
        self.caller.keyboard_command_queue.put(command)
        
    def run(self):
        for command in self.commands:
            time.sleep(command[0])
            self.send_command(command[1])            

    def close(self):
        self.terminate()
        self.wait()
