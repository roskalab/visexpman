'''
Starter module of all Vision Experiment Manager applications

-u zoltan -c CaImagingTestConfig -a main_ui
-u zoltan -c CaImagingTestConfig -a stim
-u zoltan -c CaImagingTestConfig -a main_ui --testmode 1
'''
import sys
import unittest
import time
import os.path
import numpy
import warnings
import visexpman.engine
from visexpman.engine.generic.command_parser import ServerLoop
from visexpman.engine.vision_experiment.screen import StimulationScreen
from visexpman.engine.vision_experiment import experiment_data
from visexpman.engine.generic import utils,fileop,introspect
try:
    import hdf5io#TODO: thismoves with StimulationLoop
    context_file_type='hdf5'
except ImportError:
    import scipy.io
    context_file_type='mat'

class StimulationLoop(ServerLoop, StimulationScreen):#TODO: this class should be moved to stim.py
    def __init__(self, machine_config, socket_queues, command, log,context={}):
        ServerLoop.__init__(self, machine_config, socket_queues, command, log)
        self.experiment_configs = [ecn[1].__name__ for ecn in utils.fetch_classes('visexpman.users.'+self.machine_config.user, required_ancestors = visexpman.engine.vision_experiment.experiment.ExperimentConfig,direct = False)]
        self.experiment_configs.extend([ecn[1].__name__ for ecn in utils.fetch_classes('visexpman.users.'+self.machine_config.user, required_ancestors = visexpman.engine.vision_experiment.experiment.Stimulus,direct = False)])
        self.experiment_configs.sort()
        if len(self.experiment_configs)>10:
            self.experiment_configs = self.experiment_configs[:10]#TODO: give some warning
        self.load_stim_context()
        StimulationScreen.__init__(self)
        if self.machine_config.PLATFORM=='ao_cortical':
            self.mes_interface=dict([(k, context[k]) for k in ['mes_command','mes_response']])
        if not introspect.is_test_running() and machine_config.MEASURE_FRAME_RATE:
            #Call measure framerate by putting a message into queue.
            self.socket_queues['fromsocket'].put({'function': 'measure_frame_rate', 'kwargs' :{'duration':1.0, 'background_color': self.stim_context['background_color']}})

    def load_stim_context(self):
        '''
        Loads stim application's context
        '''
        context_filename = fileop.get_context_filename(self.config,'npy')
        if os.path.exists(context_filename):
            context_stream = numpy.load(context_filename)
            self.stim_context = utils.array2object(context_stream)
        else:
            self.stim_context = {}
        if not self.stim_context.has_key('screen_center'):
            self.stim_context['screen_center'] = self.config.SCREEN_CENTER
        if not self.stim_context.has_key('background_color'):
            self.stim_context['background_color'] = self.config.BACKGROUND_COLOR
        if not self.stim_context.has_key('user_background_color'):            
            self.stim_context['user_background_color'] = 0.75
        if not self.stim_context.has_key('bullseye_size'):            
            self.stim_context['bullseye_size'] = 100.0

    def save_stim_context(self):
        fn=fileop.get_context_filename(self.config,'npy')
        context_stream = utils.object2array(self.stim_context)
        numpy.save(fn,context_stream)
        
    def _set_background_color(self,color):
        self.stim_context['background_color'] = color
        self.send({'update': ['stim background color', color]})#Feedback to main_ui, this value show up in the box where user can adjust color,
    
    def application_callback(self):
        '''
        Watching keyboard commands and refreshing screen come here
        '''
        if self.exit:
            return 'terminate'
        #Check keyboard
        from visexpman.engine.generic.graphics import check_keyboard
        keys = check_keyboard()
        if not hasattr(self, 'command_issued') and 0:
            keys.extend(['0', 'e','escape'])#TODO: remove, this is for testing
            self.command_issued=True
        for key_pressed in keys:
            if key_pressed == self.config.KEYS['exit']:#Exit application
                return 'terminate'
            elif key_pressed == self.config.KEYS['measure framerate']:#measure frame rate
                self.measure_frame_rate()
            elif key_pressed == self.config.KEYS['hide text']:#show/hide text on screen
                self.show_text = not self.show_text
            elif key_pressed == self.config.KEYS['show bullseye']:#show/hide bullseye
                self.show_bullseye = not self.show_bullseye
            elif key_pressed == self.config.KEYS['set black']:
                self._set_background_color(0.0)
            elif key_pressed == self.config.KEYS['set grey']:
                self._set_background_color(0.5)
            elif key_pressed == self.config.KEYS['set white']:
                self._set_background_color(1.0)
            elif key_pressed == self.config.KEYS['set user color']:
                self._set_background_color(self.stim_context['user_background_color'])
            elif key_pressed == 'up':
                if self.config.VERTICAL_AXIS_POSITIVE_DIRECTION == 'down':
                    self.stim_context['screen_center']['row'] -= self.config.SCREEN_CENTER_ADJUST_STEP_SIZE
                elif self.config.VERTICAL_AXIS_POSITIVE_DIRECTION == 'up':
                    self.stim_context['screen_center']['row'] += self.config.SCREEN_CENTER_ADJUST_STEP_SIZE
            elif key_pressed == 'down':
                if self.config.VERTICAL_AXIS_POSITIVE_DIRECTION == 'down':
                    self.stim_context['screen_center']['row'] += self.config.SCREEN_CENTER_ADJUST_STEP_SIZE
                elif self.config.VERTICAL_AXIS_POSITIVE_DIRECTION == 'up':
                    self.stim_context['screen_center']['row'] -= self.config.SCREEN_CENTER_ADJUST_STEP_SIZE
            elif key_pressed == 'left':
                if self.config.HORIZONTAL_AXIS_POSITIVE_DIRECTION == 'right':
                    self.stim_context['screen_center']['col'] -= self.config.SCREEN_CENTER_ADJUST_STEP_SIZE
                elif self.config.HORIZONTAL_AXIS_POSITIVE_DIRECTION == 'left':
                    self.stim_context['screen_center']['col'] += self.config.SCREEN_CENTER_ADJUST_STEP_SIZE
            elif key_pressed == 'right':
                if self.config.HORIZONTAL_AXIS_POSITIVE_DIRECTION == 'right':
                    self.stim_context['screen_center']['col'] += self.config.SCREEN_CENTER_ADJUST_STEP_SIZE
                elif self.config.HORIZONTAL_AXIS_POSITIVE_DIRECTION == 'left':
                    self.stim_context['screen_center']['col'] -= self.config.SCREEN_CENTER_ADJUST_STEP_SIZE
            elif (self.config.PLATFORM in ['behav', 'hi_mea', 'standalone', 'intrinsic']) and key_pressed in self.experiment_select_commands:
                self.selected_experiment = self.experiment_configs[int(key_pressed)]
                self.printl('Experiment selected: {0}'.format(self.selected_experiment))
            elif (self.config.PLATFORM in ['behav', 'hi_mea', 'standalone', 'intrinsic']) and key_pressed == self.config.KEYS['start stimulus']:
                if not hasattr(self, 'selected_experiment'):
                    self.printl('Select stimulus first')
                    return
                parameters = {'experiment_name': self.selected_experiment, 'stimulus_only':False,
                    'id':experiment_data.get_id()}
                self.start_stimulus(parameters)
            else:
                self.printl('Key pressed: {0}'.format(key_pressed))
        #Update screen
        self.refresh_non_experiment_screen()
        
    def at_process_end(self):
        self.save_stim_context()
        self.close_screen()
        
    def printl(self, message, loglevel='info', stdio = True):
        ServerLoop.printl(self, message, loglevel, stdio)
        #Show text on graphics screen.
        self.screen_text = self.screen_text + '\n' + str(message)
        #Limit number of lines. New lines are diplayed under the last line, When screen is full, uppermost line is discarded
        lines = self.screen_text.split('\n')
        if len(lines)> self.max_print_lines:
            lines = lines[-self.max_print_lines:]
        self.screen_text = '\n'.join(lines)
        
    ########### Remotely callable functions ###########
    def test(self):
        self.printl('test OK 1')
        time.sleep(0.1)
        self.printl('test OK 2')

    def measure_frame_rate(self,duration=10.0, background_color=None ):
        from visexpman.engine.generic import colors
        cols = numpy.cos(numpy.arange(0, 2*numpy.pi, 2*numpy.pi/(self.config.SCREEN_EXPECTED_FRAME_RATE*duration)))+0.5
        cols = numpy.array(3*[cols]).T
        if background_color is not None:
            cols = numpy.ones_like(cols)*numpy.array(background_color)
        t0 = time.time()
        for color in cols:
            self.clear_screen(color = colors.convert_color(color, self.config))
            self.flip()
        runtime = time.time()-t0
        frame_rate = (self.config.SCREEN_EXPECTED_FRAME_RATE*duration)/runtime
        self.printl('Runtime: {0:.2f} s, measured frame rate: {1:.2f} Hz, expected frame rate: {2} Hz'.format(runtime, frame_rate, self.config.SCREEN_EXPECTED_FRAME_RATE))
        if abs(frame_rate-self.config.SCREEN_EXPECTED_FRAME_RATE)>self.config.FRAME_RATE_TOLERANCE:
            from visexpman.engine import HardwareError
            raise HardwareError('Measured frame rate ({0:1.2f}) is out of acceptable range. Check projector\'s frame rate or graphics card settings.'.format(frame_rate))
        return frame_rate
        
    def read(self,varname):
        if hasattr(self, varname):
            self.send({'data': [varname,getattr(self,varname)]})
        else:
            self.send('{0} variable does not exists'.format(varname))
            
    def set_context_variable(self, varname, value):
        '''
        Screen center, background color can be set with this function
        '''
        if not self.stim_context.has_key(varname):
            self.send('{0} context variable does not exists'.format(varname))
        else:
            self.stim_context[varname] = value
            
    def set_variable(self, varname, value):
        '''
        Screen center, background color can be set with this function
        '''
        if not hasattr(self,varname):
            self.send('{0} variable does not exists'.format(varname))
        else:
            setattr(self,varname,value)
            
    def set_filterwheel(self, channel, filter):
        raise NotImplementedError('')
        
    def toggle_bullseye(self,state):
        self.show_bullseye = state
        
    def check_mes_connection(self):
        if self.machine_config.PLATFORM!='ao_cortical':
            raise NotImplementedError()
        from visexpman.engine.hardware_interface import mes_interface
        res=mes_interface.check_mes_connection(self.mes_interface['mes_command'], self.mes_interface['mes_response'])
        self.send({'mes_connection_status': res})
        
    def set_experiment_config(self,source_code, experiment_config_name):
        '''
        When user changes Experiment config name (stimulus), the selected experiment config
        is sent to stim. Pre experiment is displayed if available
        '''
        
    def start_stimulus(self,parameters):
        #Create experiment config class from experiment source code
        if parameters.has_key('experiment_config_source_code'):
            introspect.import_code(parameters['experiment_config_source_code'],'experiment_module', add_to_sys_modules=1)
            experiment_module = __import__('experiment_module')
            self.experiment_config = getattr(experiment_module, parameters['stimclass'])(self.config, self.socket_queues, \
                                                                                                  experiment_module, parameters, self.log)
        elif parameters.has_key('stimulus_source_code'):
            introspect.import_code(parameters['stimulus_source_code'],'experiment_module', add_to_sys_modules=1)
            experiment_module = __import__('experiment_module')
            self.experiment_config = getattr(experiment_module, parameters['stimclass'])(self.config, self.socket_queues, \
                                                                                                  parameters, self.log,
                                                                                                  screen=self.screen if self.machine_config.SCREEN_MODE=='psychopy' else None)
        else:
            #Source code not provided, existing experiment config module is instantiated
            experiment_module = None
            experiment_config_class=[]
            for ancestor in [visexpman.engine.vision_experiment.experiment.ExperimentConfig,visexpman.engine.vision_experiment.experiment.Stimulus]:
                for u in [self.machine_config.user, 'common']:
                    experiment_config_class.extend(utils.fetch_classes('visexpman.users.'+ u, classname = parameters['experiment_name'],  
                                                        required_ancestors = ancestor, direct=False))
            if len(experiment_config_class)==0:
                from visexpman.engine import ExperimentConfigError
                raise ExperimentConfigError('{0} user\'s {1} experiment config cannot be fetched or does not exists'
                                            .format(self.machine_config.user, parameters['experiment_name']))
            if issubclass(experiment_config_class[0][1],visexpman.engine.vision_experiment.experiment.Stimulus):
                self.experiment_config = experiment_config_class[0][1](self.config, self.socket_queues, \
                                                                                                  parameters, self.log)
            else:
                self.experiment_config = experiment_config_class[0][1](self.config, self.socket_queues, \
                                                                                                  experiment_module, parameters, self.log)
        #Prepare experiment, run stimulation and save data
        self.isstimclass=issubclass(self.experiment_config.__class__,visexpman.engine.vision_experiment.experiment.Stimulus)
        runnable=self.experiment_config if self.isstimclass else self.experiment_config.runnable
        if parameters.get('stimulus_only', False):
            runnable.prepare()
        if hasattr(self, 'mes_interface'):
            runnable.mes_interface=self.mes_interface
        getattr(runnable, 'run' if parameters.get('stimulus_only', False) else 'execute')()
        self.stim_context['last_experiment_parameters'] = parameters
        self.stim_context['last_experiment_stimulus_frame_info'] = runnable.stimulus_frame_info

def run_main_ui(context):
    context['logger'].add_source('engine')
    context['logger'].start()#This needs to be started separately from application_init ensuring that other logger source can be added 
    from visexpman.engine.vision_experiment import main_ui
    main_ui.MainUI(context=context)

def run_stim(context, timeout = None):
    stim = StimulationLoop(context['machine_config'], context['socket_queues']['stim'], context['command'], context['logger'], context=context)
    context['logger'].start()
    stim.run(timeout=timeout)
    
def run_ca_imaging(context, timeout = None):
    context['logger'].add_source('engine')
    context['logger'].start()
    from visexpman.engine.vision_experiment import ca_imaging
    ca_imaging.CaImaging(context=context)
    

def stimulation_tester(user, machine_config, experiment_config, **kwargs):
    '''
    Runs the provided experiment config and terminates
    '''
    context = visexpman.engine.application_init(user = user, config = machine_config, user_interface_name = 'stim',enable_sockets=False)
    for k,v in kwargs.items():
        setattr(context['machine_config'], k, v)
    if context['machine_config'].ENABLE_FRAME_CAPTURE:
        context['capture_path'] = prepare_capture_folder(context['machine_config'])
    stim = StimulationLoop(context['machine_config'], context['socket_queues']['stim'], context['command'], context['logger'])
    parameters = {
            'experiment_name': experiment_config,
            'cell_name': '', 
            'stimulation_device' : '', 
            'stimulus_only':True,
            'id':str(int(numpy.round(time.time(), 2)*100))}
    if kwargs.has_key('stimulus_source_code'):
        parameters['stimulus_source_code']=kwargs['stimulus_source_code']
    commands = [{'function': 'start_stimulus', 'args': [parameters]}]
    commands.append({'function': 'exit_application'})
    map(context['socket_queues']['stim']['fromsocket'].put, commands)
    context['logger'].start()
    stim.run()
    visexpman.engine.stop_application(context)
    return context
    
def prepare_capture_folder(machine_config):
    machine_config.ENABLE_FRAME_CAPTURE = True
    machine_config.CAPTURE_PATH = os.path.join(machine_config.root_folder, 'capture')
    fileop.mkdir_notexists(machine_config.CAPTURE_PATH, remove_if_exists=True)
    return machine_config.CAPTURE_PATH


def run_application():
    warnings.simplefilter("always")
    with warnings.catch_warnings(record=True) as w:
        context = visexpman.engine.application_init()
        context['warning'] = w
        globals()['run_{0}'.format(context['user_interface_name'])](context)
        visexpman.engine.stop_application(context)

class TestStim(unittest.TestCase):
    def setUp(self):
        if '_04_' in self._testMethodName:
            self.configname = 'ULCornerTestConfig'
        else:
            self.configname = 'GUITestConfig'
        #Erase work folder, including context files
        self.machine_config = utils.fetch_classes('visexpman.users.test', 'GUITestConfig', required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig,direct = False)[0][1]()
        self.machine_config.user_interface_name='stim'
        self.machine_config.user = 'test'
        fileop.cleanup_files(self.machine_config)
        if '_08_' not in self._testMethodName:
            self.context = visexpman.engine.application_init(user = 'test', config = self.configname, user_interface_name = 'stim')
        self.dont_kill_processes = introspect.get_python_processes()
        
    def _send_commands_to_stim(self, commands):
        from visexpman.engine.hardware_interface import queued_socket
        import multiprocessing
        client = queued_socket.QueuedSocket('{0}-{1} socket'.format('main_ui', 'stim'), 
                                                                                    False, 
                                                                                    10000,
                                                                                    multiprocessing.Queue(), 
                                                                                    multiprocessing.Queue(), 
                                                                                    ip= '127.0.0.1',
                                                                                    log=None)
        client.start()
        for command in commands:
            client.send(command)
        return client
        
    def tearDown(self):
        if hasattr(self, 'context'):
            visexpman.engine.stop_application(self.context)
        introspect.kill_python_processes(self.dont_kill_processes)
        
    def test_01_start_stim_loop(self):
        self.context['command'].put('terminate')
        run_stim(self.context)
        time.sleep(5.0)
        t0 = time.time()
        while True:#Wait for file
            if os.path.exists(self.context['logger'].filename) or time.time()-t0>30.0:
                break
            time.sleep(1.0)
        self.assertNotEqual(os.path.getsize(self.context['logger'].filename), 0)
        
    def test_02_execute_command(self):
        from visexpman.engine.hardware_interface import queued_socket
        import multiprocessing
        client = queued_socket.QueuedSocket('{0}-{1} socket'.format('main_ui', 'stim'), 
                                                                                    False, 
                                                                                    10000,
                                                                                    multiprocessing.Queue(), 
                                                                                    multiprocessing.Queue(), 
                                                                                    ip= '127.0.0.1',
                                                                                    log=None)
        client.start()
        client.send({'function':'test'})
        run_stim(self.context, timeout = 10)
        self.assertEqual(client.recv(), 'test OK 1')
        self.assertEqual(client.recv(), 'test OK 2')
        client.terminate()
        self.assertNotEqual(os.path.getsize(self.context['logger'].filename), 0)
        from visexpman.engine.generic import fileop
        for tag in ['stim\t', 'sent: ']:
            self.assertIn(tag+'test OK 1', fileop.read_text_file(self.context['logger'].filename))
            self.assertIn(tag+'test OK 2', fileop.read_text_file(self.context['logger'].filename))
            
    def test_03_presscommands(self):
        capture_path = prepare_capture_folder(self.context['machine_config'])
        self.context['machine_config'].COLOR_MASK = numpy.array([0.5, 0.5, 1.0])
        client = self._send_commands_to_stim([{'function': 'set_context_variable', 'args': ['background_color', 0.5]},
            {'function': 'set_context_variable', 'args': ['screen_center', utils.rc((200,300))]},
            {'function': 'set_variable', 'args': ['show_text', False]},
            {'function': 'set_variable', 'args': ['bullseye_size', 100.0]},
            {'function': 'set_variable', 'args': ['bullseye_type', 'bullseye']},
            {'function': 'set_variable', 'args': ['show_bullseye', True]},
            {'function': 'read', 'args': ['stim_context']}])
        run_stim(self.context,timeout=10)
        t0=time.time()
        while True:
            context_sent = client.recv()
            if context_sent is not None or time.time()-t0>30:
                break
        self.assertEqual(context_sent['data'][0], 'stim_context')
        self.assertEqual(context_sent['data'][1]['background_color'], 0.5)
        self.assertEqual(context_sent['data'][1]['screen_center'], utils.rc((200,300)))
        client.terminate()
        saved_context = utils.array2object(hdf5io.read_item(fileop.get_context_filename(self.context['machine_config']), 'context', self.context['machine_config']))
        self.assertEqual(saved_context['background_color'], 0.5)
        self.assertEqual(saved_context['user_background_color'], 0.75)
        self.assertEqual(saved_context['screen_center'], utils.rc((200,300)))
        expected_in_log = ['set_context_variable', 'received', 'set_variable', 'read', 'show_text', 'bullseye_size', 'show_bullseye']
        map(self.assertIn, expected_in_log, [fileop.read_text_file(self.context['logger'].filename)]*len(expected_in_log))
        captured_files = map(os.path.join, len(os.listdir(capture_path))*[capture_path], os.listdir(capture_path))
        captured_files.sort()
        from PIL import Image
        first_frame = numpy.asarray(Image.open(captured_files[0]))
        #Frame size is equal with screen resolution parameter
        self.assertEqual(first_frame.shape, (int(self.context['machine_config'].SCREEN_RESOLUTION['row']),
                                                            int(self.context['machine_config'].SCREEN_RESOLUTION['col']), 3))
        self.assertEqual(numpy.asarray(Image.open(captured_files[1])).shape, numpy.asarray(Image.open(captured_files[2])).shape)#All frames have the same size
        self.assertEqual(numpy.asarray(Image.open(captured_files[0])).shape, numpy.asarray(Image.open(captured_files[-1])).shape)
        #Check screen color
        expected_color = numpy.ceil(numpy.array([0.5, 0.5, 0.5+1/6.0])*255)
        for captured_file in captured_files[-5:]:
            numpy.testing.assert_allclose(numpy.asarray(Image.open(captured_file))[0,0], expected_color,0,1)
            numpy.testing.assert_allclose(numpy.asarray(Image.open(captured_file))[1,0], expected_color,0,1)
            numpy.testing.assert_allclose(numpy.asarray(Image.open(captured_file))[0,1], expected_color,0,1)
            numpy.testing.assert_allclose(numpy.asarray(Image.open(captured_file))[0,-1], expected_color,0,1)
            numpy.testing.assert_allclose(numpy.asarray(Image.open(captured_file))[-1,-1], expected_color,0,1)
            numpy.testing.assert_allclose(numpy.asarray(Image.open(captured_file))[-1,-10], expected_color,0,1)
        #Check bullseye position
        last_frame = numpy.cast['float'](numpy.asarray(Image.open(captured_files[-1])))
        ref_frame = numpy.cast['float'](numpy.asarray(Image.open(os.path.join(self.context['machine_config'].PACKAGE_PATH, 'data', 'images', 'visexp_app_test_03.png'))))
        x1,y1,z=numpy.nonzero(last_frame-expected_color)
        x2,y2,z=numpy.nonzero(last_frame-expected_color)
        for m in ['min', 'max']:#Check if position of bullseye are OK
            self.assertEqual(getattr(x1, m)(),getattr(x2, m)())
            self.assertEqual(getattr(y1, m)(),getattr(y2, m)())
        ref_frame[x1.min():x1.max(), y1.min():y1.max(),:]=0#Clear bullseye pixels
        last_frame[x1.min():x1.max(), y1.min():y1.max(),:]=0
        
        numpy.testing.assert_allclose(ref_frame, last_frame, 0, 1)
        
    def test_04_ulcorner_coordinate_system(self):
        '''
        Checks if bullseye is put to the right place in ulcorner coordinate system
        '''
        capture_path = prepare_capture_folder(self.context['machine_config'])
        self.context['machine_config'].COLOR_MASK = numpy.array([0.5, 0.5, 1.0])
        client = self._send_commands_to_stim([{'function': 'set_context_variable', 'args': ['background_color', 0.5]},
            {'function': 'set_context_variable', 'args': ['screen_center', utils.rc((200,300))]},
            {'function': 'set_variable', 'args': ['show_text', False]},
            {'function': 'set_variable', 'args': ['bullseye_size', 100.0]},
            {'function': 'set_variable', 'args': ['bullseye_type', 'bullseye']},
            {'function': 'set_variable', 'args': ['show_bullseye', True]},])
            
        run_stim(self.context,timeout=10)
        client.terminate()
        captured_files = map(os.path.join, len(os.listdir(capture_path))*[capture_path], os.listdir(capture_path))
        captured_files.sort()
        from PIL import Image
        last_frame = numpy.cast['float'](numpy.asarray(Image.open(captured_files[-1])))
        ref_frame = numpy.cast['float'](numpy.asarray(Image.open(os.path.join(self.context['machine_config'].PACKAGE_PATH, 'data', 'images', 'visexp_app_test_04.png'))))
        expected_color = numpy.ceil(numpy.array([0.5, 0.5, 0.5+1/6.0])*255)
        x1,y1,z=numpy.nonzero(last_frame-expected_color)
        x2,y2,z=numpy.nonzero(last_frame-expected_color)
        for m in ['min', 'max']:#Check if position of bullseye are OK
            self.assertEqual(getattr(x1, m)(),getattr(x2, m)())
            self.assertEqual(getattr(y1, m)(),getattr(y2, m)())
        ref_frame[x1.min():x1.max(), y1.min():y1.max(),:]=0#Clear bullseye pixels
        last_frame[x1.min():x1.max(), y1.min():y1.max(),:]=0
        numpy.testing.assert_allclose(ref_frame, last_frame, 0, 1)
    
    def test_05_context_persistence(self):
        '''
        Checks if context values are preserved between two sessions
        '''
        client = self._send_commands_to_stim([{'function': 'set_context_variable', 'args': ['background_color', 0.5]},
            {'function': 'set_context_variable', 'args': ['screen_center', utils.rc((200,300))]},
            {'function': 'set_variable', 'args': ['show_text', False]},
            {'function': 'set_variable', 'args': ['bullseye_size', 100.0]},
            {'function': 'set_variable', 'args': ['show_bullseye', True]},
            {'function': 'read', 'args': ['stim_context']}])
        run_stim(self.context,timeout=15)
        client.terminate()
        saved_context1 = utils.array2object(hdf5io.read_item(fileop.get_context_filename(self.context['machine_config']), 'context', self.context['machine_config']))
        self.assertEqual(saved_context1['background_color'], 0.5)
        self.assertEqual(saved_context1['user_background_color'], 0.75)
        self.assertEqual(saved_context1['screen_center'], utils.rc((200,300)))
        visexpman.engine.stop_application(self.context)
        time.sleep(15.0)
        #Start stim again
        self.context = visexpman.engine.application_init(user = 'test', config =self.configname, user_interface_name = 'stim')
        run_stim(self.context,timeout=5)
        saved_context2 = utils.array2object(hdf5io.read_item(fileop.get_context_filename(self.context['machine_config']), 'context', self.context['machine_config']))
        self.assertEqual(saved_context2['background_color'], 0.5)
        self.assertEqual(saved_context2['user_background_color'], 0.75)
        self.assertEqual(saved_context2['screen_center'], utils.rc((200,300)))
        
    def test_06_measure_frame_rate(self):
        client = self._send_commands_to_stim([{'function': 'measure_frame_rate'}])
        run_stim(self.context,timeout=10)
        t0=time.time()
        while True:
            msg = client.recv()
            if msg is not None or time.time() - t0>30.0:
                break
            time.sleep(1.0)
        measured_framerate = float(msg.split('Hz')[0].split('measured frame rate: ')[1])
        numpy.testing.assert_allclose(measured_framerate, self.context['machine_config'].SCREEN_EXPECTED_FRAME_RATE, 0, self.context['machine_config'].FRAME_RATE_TOLERANCE)
        client.terminate()
        
    def test_07_execute_experiment(self):
        source = fileop.read_text_file(os.path.join(fileop.visexpman_package_path(), 'users', 'test', 'test_stimulus.py'))
        experiment_names = ['GUITestExperimentConfig', 'TestCommonExperimentConfig']
#        experiment_names = ['TestCommonExperimentConfig']
        parameters = {
            'experiment_name': '',
            'experiment_config_source_code' : source,
            'cell_name': 'cell0', 
            'stimulation_device' : '', 
            'recording_channels' : '', 
            'enable_scanner_synchronization' : False, 
            'scanning_range' : [100.0, 100.0], 
            'pixel_size' : 1.0, 
            'resolution_unit' : 'um/pixel', 
            'scan_center' : [0.0,0.0],
            'trigger_width' : 0.0,
            'trigger_delay' : 0.0,
            'status' : 'preparing', 
            'id':str(int(numpy.round(time.time(), 2)*100))}
        commands = []
        for experiment_name in experiment_names:
            import copy
            pars = copy.deepcopy(parameters)
            pars['experiment_name'] = experiment_name
            commands.append({'function': 'start_stimulus', 'args': [pars]})
        commands.append({'function': 'exit_application'})
        print len(commands)
        client = self._send_commands_to_stim(commands)
        run_stim(self.context,timeout=None)
        client.terminate()
        logfile_content = fileop.read_text_file(self.context['logger'].filename)
        self.assertNotIn('error', logfile_content.lower())
        expected_logs = ['Starting stimulation: MovingShapeExperiment/TestCommonExperimentConfig', 
                            'Starting stimulation: Debug/GUITestExperimentConfig', 
                            'Stimulation ended, saving data to file']
        map(self.assertIn,expected_logs,len(expected_logs)*[logfile_content])
        
    def test_08_stimulation_tester(self):
        context = stimulation_tester('test', 'GUITestConfig', 'TestCommonExperimentConfig')
        self.assertNotIn('error', fileop.read_text_file(context['logger'].filename).lower())
        
    #TODO: test for different bullseyes
    
if __name__=='__main__':
    if len(sys.argv)>1:
        if '--kill' in sys.argv:
            introspect.kill_other_python_processes()
        run_application()
        import psutil
        psutil.Process(os.getpid()).kill()#Sometimes the application does not terminate however all processes are terminated. psutil.Process(os.getpid()).open_files() fails
        
    else:
        unittest.main()
    
