'''
Starter module of all Vision Experiment Manager applications

-u zoltan -c CaImagingTestConfig -a main_ui
-u zoltan -c CaImagingTestConfig -a main_ui --testmode 1
'''
import visexpman.engine
from visexpman.engine.visexp_gui import VisionExperimentGui

def start_network_communication():
    pass

def run_application():
    config, log = visexpman.engine.application_init()
    start_network_communication()
    if config.application_name == 'main_ui':
        log.start()#This needs to be started separately from application_init ensuring that other logger source can be added 
        gui =  VisionExperimentGui(config=config, application_name = config.application_name, log=log)
        
    
    
    #Terminate logger process
    log.terminate()
    log.join()
    pass

if __name__=='__main__':
    run_application()
