'''
Starter module of all Vision Experiment Manager applications

-u zoltan -c CaImagingTestConfig -a main_ui
-u zoltan -c CaImagingTestConfig -a main_ui --testmode 1
'''
import sys
import unittest
import visexpman.engine
import time
import os.path
from visexpman.engine.visexp_gui import VisionExperimentGui
from visexpman.engine.generic.command_parser import ServerLoop
from visexpman.engine.generic import introspect

class StimulationLoop(ServerLoop):
    def __init__(self, machine_config, queued_socket, command, log):
        ServerLoop.__init__(self, machine_config, queued_socket, command, log)
        
    def test(self):
        self.printl('test OK')
        
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
        client.terminate()
        self.assertNotEqual(os.path.getsize(self.context['logger'].filename), 0)
        from visexpman.engine.generic import fileop
        self.assertIn('stim\ttest OK', fileop.read_text_file(self.context['logger'].filename))

if __name__=='__main__':
    if len(sys.argv)>1:
        run_application()
    else:
        unittest.main()
