'''
Starter module of all Vision Experiment Manager applications

-u zoltan -c CaImagingTestConfig -a main_ui
-u zoltan -c CaImagingTestConfig -a main_ui --testmode 1
'''
import visexpman.engine
from visexpman.engine.visexp_gui import VisionExperimentGui

def run_application():
    context = visexpman.engine.application_init()
    if context['application_name'] == 'main_ui':
        context['logger'].start()#This needs to be started separately from application_init ensuring that other logger source can be added 
        gui =  VisionExperimentGui(config=context['machine_config'], 
                                                        application_name =context['application_name'], 
                                                        log=context['logger'],
                                                        sockets = context['sockets'])
    elif context['application_name'] == 'stim':
        pass
    visexpman.engine.stop_application(context)

if __name__=='__main__':
    run_application()
