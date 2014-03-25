'''
Starter module of all Vision Experiment Manager applications

-u zoltan -c CaImagingTestConfig -a main_ui
-u zoltan -c CaImagingTestConfig -a main_ui --testmode 1
'''
import sys
import unittest
import visexpman.engine
from visexpman.engine.visexp_gui import VisionExperimentGui
from visexpman.engine.generic.command_parser import ServerLoop

class StimulationLoop(ServerLoop):
    def __init__(self,  queued_socket, command, log):
        ServerLoop.__init__(self, queued_socket, command, log)
        
    def test(self):
        self.printl('test works')

def run_application():
    context = visexpman.engine.application_init()
    if context['application_name'] == 'main_ui':
        context['logger'].start()#This needs to be started separately from application_init ensuring that other logger source can be added 
        gui =  VisionExperimentGui(config=context['machine_config'], 
                                                        application_name =context['application_name'], 
                                                        log=context['logger'],
                                                        sockets = context['sockets'])
    elif context['application_name'] == 'stim':
        context['logger'].start()
        stim = StimulationLoop(context['sockets']['stim'], context['command'], context['logger'])
        stim.run()
    visexpman.engine.stop_application(context)

class TestStim(unittest.TestCase):
    def setUp(self):
        self.context = visexpman.engine.application_init(user = 'test', config ='GUITestConfig', application_name = 'stim')
        
    def test_01_start_stim_loop(self):
        from visexpman.engine.hardware_interface import queued_socket
        import multiprocessing
        import time
        self.context['logger'].start()
        client = queued_socket.QueuedSocket('{0}-{1} socket'.format('main_ui', 'stim'), 
                                                                                    False, 
                                                                                    10000,
                                                                                    multiprocessing.Queue(), 
                                                                                    multiprocessing.Queue(), 
                                                                                    ip= '127.0.0.1',
                                                                                    log=None)
        client.start()
        stim = StimulationLoop(self.context['sockets']['stim'], self.context['command'], self.context['logger'])
        client.send({'function':'test'})
        time.sleep(0)
        stim.run(5)
        self.context['command'].put('terminate')
        visexpman.engine.stop_application(self.context)
        client.terminate()
        
        
        
        

if __name__=='__main__':
    if len(sys.argv)>1:
        run_application()
    else:
        unittest.main()
