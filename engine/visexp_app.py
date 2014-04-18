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
import visexpman.engine
from visexpman.engine.visexp_gui import VisionExperimentGui
from visexpman.engine.generic.command_parser import ServerLoop
from visexpman.engine.vision_experiment.screen import VisionExperimentScreen, check_keyboard
from visexpman.engine.generic import introspect
from visexpman.engine.generic import utils
from visexpman.engine.generic import fileop
from visexpA.engine.datahandlers import hdf5io

class StimulationLoop(ServerLoop, VisionExperimentScreen):
    def __init__(self, machine_config, socket_queues, command, log):
        ServerLoop.__init__(self, machine_config, socket_queues, command, log)
        self.load_stim_context()
        VisionExperimentScreen.__init__(self)
        self.exit=False
        if not introspect.is_test_running():
            #Call measure framerate by putting a message into queue. 
            self.socket_queues['fromsocket'].put({'function': 'measure_frame_rate', 'kwargs' :{'duration':1.0, 'background_color': self.stim_context['background_color']}})

    def load_stim_context(self):
        '''
        Loads stim application's context
        '''
        context_filename = fileop.get_context_filename(self.config)
        if os.path.exists(context_filename):
            self.stim_context = utils.array2object(hdf5io.read_item(context_filename, 'context', self.config))
        else:
            self.stim_context = {}
        if not self.stim_context.has_key('screen_center'):
            self.stim_context['screen_center'] = self.config.SCREEN_CENTER
        if not self.stim_context.has_key('background_color'):
            self.stim_context['background_color'] = self.config.BACKGROUND_COLOR
        if not self.stim_context.has_key('user_background_color'):            
            self.stim_context['user_background_color'] = 0.75

    def save_stim_context(self):
        hdf5io.save_item(fileop.get_context_filename(self.config), 'context', utils.object2array(self.stim_context), self.config,  overwrite = True)
        
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
        for key_pressed in check_keyboard():
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
            raise HardwareError('Measured frame rate is out of acceptable range. Check projector\'s frame rate or graphics card settings.')        
        return frame_rate
        
    def exit_application(self):
        self.exit=True
        
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
            self.send('{0} variable does not exists'.format(varname))
        else:
            self.stim_context[varname] = value
            
    def set_variable(self,varname, value):
        if not hasattr(self, varname):
            self.send('{0} variable does not exists'.format(varname))
        else:
            setattr(self, varname, value)
            
    def set_filterwheel(self, channel, filter):
        raise NotImplementedError('')
        
    def set_experiment_config(self,source_code, experiment_config_name):
        '''
        When user changes Experiment config name (stimulus), the selected experiment config
        is sent to stim. Pre experiment is displayed if available
        '''
        
    def start_experiment(self,parameters):
        #Create experiment config class from experiment source code
        introspect.import_code(parameters['experiment_config_source_code'],'experiment_module', add_to_sys_modules=1)
        experiment_module = __import__('experiment_module')
        self.experiment_config = getattr(experiment_module, parameters['experiment_name'])(self.config, self.queues, \
                                                                                                  self.connections, self.log, getattr(experiment_module,experiment_name), loadable_source_code)
        
        
        
        
        
        self.printl(parameters)
        
def run_main_ui(context):
    context['logger'].start()#This needs to be started separately from application_init ensuring that other logger source can be added 
    gui =  VisionExperimentGui(config=context['machine_config'], 
                                                        application_name =context['application_name'], 
                                                        log=context['logger'],
                                                        socket_queues = context['socket_queues'])

def run_stim(context, timeout = None):
    stim = StimulationLoop(context['machine_config'], context['socket_queues']['stim'], context['command'], context['logger'])
    context['logger'].start()
    stim.run(timeout=timeout)

def run_application():
    context = visexpman.engine.application_init()
    globals()['run_{0}'.format(context['application_name'])](context)
    visexpman.engine.stop_application(context)

class TestStim(unittest.TestCase):
    def setUp(self):
        if '_04_' in self._testMethodName:
            self.configname = 'ULCornerTestConfig'
        else:
            self.configname = 'GUITestConfig'
        #Erase work folder, including context files
        self.machine_config = utils.fetch_classes('visexpman.users.test', 'GUITestConfig', required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig,direct = False)[0][1]()
        self.machine_config.application_name='stim'
        self.machine_config.user = 'test'
        fileop.cleanup_files(self.machine_config)
        self.context = visexpman.engine.application_init(user = 'test', config = self.configname, application_name = 'stim')
        self.dont_kill_processes = introspect.get_python_processes()
        
    def _prepare_capture_folder(self):
        self.context['machine_config'].ENABLE_FRAME_CAPTURE = True
        self.context['machine_config'].CAPTURE_PATH = os.path.join(self.context['machine_config'].root_folder, 'capture')
        fileop.mkdir_notexists(self.context['machine_config'].CAPTURE_PATH, remove_if_exists=True)
        return self.context['machine_config'].CAPTURE_PATH
        
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
        capture_path = self._prepare_capture_folder()
        self.context['machine_config'].COLOR_MASK = numpy.array([0.5, 0.5, 1.0])
        client = self._send_commands_to_stim([{'function': 'set_context_variable', 'args': ['background_color', 0.5]},
            {'function': 'set_context_variable', 'args': ['screen_center', utils.rc((200,300))]},
            {'function': 'set_variable', 'args': ['show_text', False]},
            {'function': 'set_variable', 'args': ['bullseye_size', 100.0]},
            {'function': 'set_variable', 'args': ['show_bullseye', True]},
            {'function': 'read', 'args': ['stim_context']}])
        run_stim(self.context,timeout=10)
        t0=time.time()
        while True:
            context_sent = client.recv()['data']
            if context_sent is not None or time.time()-t0>30:
                break
        self.assertEqual(context_sent[0], 'stim_context')
        self.assertEqual(context_sent[1]['background_color'], 0.5)
        self.assertEqual(context_sent[1]['screen_center'], utils.rc((200,300)))
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
        expected_color = numpy.array([0.5, 0.5, 0.5+1/6.0])*255
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
        numpy.testing.assert_allclose(ref_frame, last_frame, 0, 1)
        
    def test_04_ulcorner_coordinate_system(self):
        '''
        Checks if bullseye is put to the right place in ulcorner coordinate system
        '''
        capture_path = self._prepare_capture_folder()
        self.context['machine_config'].COLOR_MASK = numpy.array([0.5, 0.5, 1.0])
        client = self._send_commands_to_stim([{'function': 'set_context_variable', 'args': ['background_color', 0.5]},
            {'function': 'set_context_variable', 'args': ['screen_center', utils.rc((200,300))]},
            {'function': 'set_variable', 'args': ['show_text', False]},
            {'function': 'set_variable', 'args': ['bullseye_size', 100.0]},
            {'function': 'set_variable', 'args': ['show_bullseye', True]},
            {'function': 'read', 'args': ['stim_context']}])
        run_stim(self.context,timeout=10)
        client.terminate()
        captured_files = map(os.path.join, len(os.listdir(capture_path))*[capture_path], os.listdir(capture_path))
        captured_files.sort()
        from PIL import Image
        last_frame = numpy.cast['float'](numpy.asarray(Image.open(captured_files[-1])))
        ref_frame = numpy.cast['float'](numpy.asarray(Image.open(os.path.join(self.context['machine_config'].PACKAGE_PATH, 'data', 'images', 'visexp_app_test_04.png'))))
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
        self.context = visexpman.engine.application_init(user = 'test', config =self.configname, application_name = 'stim')
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

if __name__=='__main__':
    if len(sys.argv)>1:
        run_application()
    else:
        unittest.main()
