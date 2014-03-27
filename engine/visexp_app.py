'''
Starter module of all Vision Experiment Manager applications

-u zoltan -c CaImagingTestConfig -a main_ui
-u zoltan -c CaImagingTestConfig -a stim
-u zoltan -c CaImagingTestConfig -a main_ui --testmode 1
'''
import sys
import unittest
import visexpman.engine
import time
import os.path
from visexpman.engine.visexp_gui import VisionExperimentGui
from visexpman.engine.generic.command_parser import ServerLoop
from visexpman.engine.vision_experiment.screen import VisionExperimentScreen, check_keyboard
from visexpman.engine.generic import introspect

class StimulationLoop(ServerLoop, VisionExperimentScreen):
    def __init__(self, machine_config, queued_socket, command, log):
        ServerLoop.__init__(self, machine_config, queued_socket, command, log)
        VisionExperimentScreen.__init__(self)
        
    def application_callback(self):
        '''
        Watching keyboard commands and refreshing screen come here
        
        '''
        #Check keyboard
        for key_pressed in check_keyboard():
            if key_pressed == 'escape':
                return 'terminate'
            else:
                self.printl('Key pressed: {0}'.format(key_pressed))
        #Update screen
        self.refresh_non_experiment_screen()
        
    def at_prcess_end(self):
        self.close_screen()
        
    def test(self):
        self.printl('test OK 1')
        time.sleep(0.1)
        self.printl('test OK 2')
        
    def printl(self, message, loglevel='info', stdio = True):
        ServerLoop.printl(self, message, loglevel, stdio)
        #Show text on graphics screen.
        self.screen_text = self.screen_text + '\n' + message
        #Limit number of lines. New lines are diplayed under the last line, When screen is full, uppermost line is discarded
        lines = self.screen_text.split('\n')
        if len(lines)> self.max_print_lines:
            lines = lines[-self.max_print_lines:]
        self.screen_text = '\n'.join(lines)
        
def run_main_ui(context):
    context['logger'].start()#This needs to be started separately from application_init ensuring that other logger source can be added 
    gui =  VisionExperimentGui(config=context['machine_config'], 
                                                        application_name =context['application_name'], 
                                                        log=context['logger'],
                                                        sockets = context['sockets'])
        
def run_stim(context, timeout = None):
    stim = StimulationLoop(context['machine_config'], context['sockets']['stim'], context['command'], context['logger'])
    context['logger'].start()
    stim.run(timeout=timeout)

def run_application():
    context = visexpman.engine.application_init()
    globals()['run_{0}'.format(context['application_name'])](context)
    visexpman.engine.stop_application(context)

class TestStim(unittest.TestCase):
    def setUp(self):
        self.context = visexpman.engine.application_init(user = 'test', config ='GUITestConfig', application_name = 'stim')
        self.dont_kill_processes = introspect.get_python_processes()
        
    def tearDown(self):
        visexpman.engine.stop_application(self.context)
        introspect.kill_python_processes(self.dont_kill_processes)
        
    def test_01_start_stim_loop(self):
        self.context['command'].put('terminate')
        run_stim(self.context)
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
            
    def test_03_pressbutton(self):
        from visexpman.engine.hardware_interface import queued_socket
        import multiprocessing
        
#        client = queued_socket.QueuedSocket('{0}-{1} socket'.format('main_ui', 'stim'), 
#                                                                                    False, 
#                                                                                    10000,
#                                                                                    multiprocessing.Queue(), 
#                                                                                    multiprocessing.Queue(), 
#                                                                                    ip= '127.0.0.1',
#                                                                                    log=None)
#        client.start()
        run_stim(self.context)
        pass
#        client.terminate()

if __name__=='__main__':
    if len(sys.argv)>1:
        run_application()
    else:
        unittest.main()
