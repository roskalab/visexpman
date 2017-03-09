import sys
import time
import Queue
import os
import numpy
import traceback
import re
import cPickle as pickle
import zmq

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
                self.stage_origin = hdf5io.read_item(self.config.CONTEXT_FILE, 'stage_origin',filelocking=False)
            except:
                self.log.info('Context file cannot be opened')
            if self.stage_origin == None:
                self.stage_origin = numpy.zeros(3)
        self.initzmq()
        self.last_send_time=time.time()
        self.job_resend_period=40#second
                
    def initzmq(self):
        context=zmq.Context()
        self.pusher = context.socket(zmq.PAIR)
        port=self.config.JOBHANDLER_PUSHER_PORT
        ip=self.config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX']['GUI_ANALYSIS']['ANALYSIS']['LOCAL_IP']
        lip=self.config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX']['GUI_STIM']['STIM']['LOCAL_IP']
        #self.pusher.bind('tcp://{0}:{1}'.format(lip,port))
        self.pusher.connect('tcp://{0}:{1}'.format(ip,port))
        
###### Commands ######    

    def printl(self,message):
        print message
        self.queues['gui']['out'].put(message)
        self.log.info(message)
        
    def is_jobhandler_connected(self):
        while True:
            try:
                resp= self.pusher.recv(flags=zmq.NOBLOCK)
                time.sleep(0.1)
            except zmq.ZMQError:
                break
        try:
            self.pusher.send('ping',flags=zmq.NOBLOCK)
        except zmq.ZMQError:
            return False
        t0=time.time()
        res=False
        while True:
            try:
                res=self.pusher.recv(flags=zmq.NOBLOCK)=='pong'
                break
            except zmq.ZMQError:
                if time.time()-t0>2:
                    break
            time.sleep(0.1)
        return res
        
    def wait4jobhandler_resp(self,socket):
        t0=time.time()
        while True:
            try:
                resp=socket.recv(flags=zmq.NOBLOCK)
                break
            except zmq.ZMQError:
                if time.time()-t0>2:
                    resp='timeout'
                    break
            time.sleep(0.5)
        return resp
        
    def resendjobs(self):
#        if time.time()-self.last_send_time<self.job_resend_period:
#            self.last_send_time=time.time()
#            return 'not'
        print 'send'
        fn=os.path.join(self.config.CONTEXT_PATH,'stim.hdf5')
        h=hdf5io.Hdf5io(fn,filelocking=False)
        h.load('jobs')
        if not hasattr(h,'jobs'):
            h.close()
        else:
            sent=[]
            if len(h.jobs)>0:
                if not self.is_jobhandler_connected():
                    self.printl('Jobhandler not connected')
                    h.close()
                    self.log.info('exit resend function')
                    return 'not sent'
                self.printl('Sending jobs')
                for i in range(len(h.jobs)):
                    self.pusher.send(pickle.dumps(h.jobs[i],2),flags=zmq.NOBLOCK)
                    resp=self.wait4jobhandler_resp(self.pusher)
                    self.last_send_time=time.time()
                    if resp==h.jobs[i]['id']:
                        sent.append(h.jobs[i]['id'])
                        self.printl(h.jobs[i]['id'])
                    else:
                        self.printl('Sending failed, {0}'.format(resp))
                        break#Do not continue if does not work
                h.jobs=[j for j in h.jobs if j['id'] not in sent]
                if len(sent)>0:
                    self.printl('Done')
                    h.save('jobs')
            h.close()
        self.log.info('exit resend function')
        return 'sent'

    def quit(self):
        self.pusher.close()
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

    def ping(self):
        self.queues['gui']['out'].put('pong')
        return 'pong'

    def filterwheel(self, filterwheel_id = 1, filter_position = 1):
        if hasattr(self.config, 'FILTERWHEEL_SERIAL_PORT'):            
            filterwheel = instrument.Filterwheel(self.config, id = filterwheel_id)
            filterwheel.set(filter_position)
            if os.name == 'nt':
                filterwheel.release_instrument()
        return 'filterwheel ' + str(filterwheel_id) + ',  ' +str(filter_position)
        
    def stage(self,par, new_x = 0, new_y = 0, new_z = 0, togui=True):
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
                self.log.info('DEBUG: Stage position abs {0}' .format(position))
                if position == []:
                    self.queues['gui']['out'].put('SOCstageEOCerrorEOP')
                if 'set' not in par:
                    if togui:
                        self.queues['gui']['out'].put('SOCstageEOC{0},{1},{2}EOP'.format(position[0], position[1], position[2]))
                if 'origin' in par:
                    self.stage_origin = position
                    self.log.info('DEBUG: Stage origin is {0}' .format(self.stage_origin))
                if 'set' in par:
                    new_position = numpy.array([float(new_x), float(new_y), float(new_z)])
                    reached = stage.move(new_position)
                    position = stage.position
                    self.queues['gui']['out'].put('SOCstageEOC{0},{1},{2}EOP'.format(position[0], position[1], position[2]))
                stage.release_instrument()
                self.log.info('DEBUG: Stage position abs {0} (2)' .format(position))
            return str(par) + ' ' + str(position) + '\n' + str(time.time() - st) + ' ' + str(stage.command_counter )
        except:
            return str(traceback.format_exc())

###### Experiment related commands ###############
    def select_experiment(self, experiment_index):
        '''
        Selects experiment config based on keyboard command and instantiates the experiment config class
        '''
        if isinstance(experiment_index, int):
            self.selected_experiment_config_index = int(experiment_index)
        else:
            self.selected_experiment_config_index = [i for i in range(len(self.experiment_config_list)) if self.experiment_config_list[i][1].__name__==experiment_index][0]
        try:
            self.experiment_config = self.experiment_config_list[int(self.selected_experiment_config_index)][1](self.config, self.queues, self.connections, self.log)
        except:
            print 'preexp error'
        if hasattr(self.experiment_config, 'pre_runnable') and self.experiment_config.pre_runnable is not None:
            self.clear_screen_to_background()
            self.experiment_config.pre_runnable.run()
            self.flip()

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
        context['pusher'] = self.pusher
        result = self.experiment_config.runnable.run_experiment(context)
        self.resendjobs()
        self.log.info('after resend')
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
