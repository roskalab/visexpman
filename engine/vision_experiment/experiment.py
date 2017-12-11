import sys, threading, time
import logging
import os
import visexpman

from visexpman.engine.generic.configuration import Config
from visexpman.engine.generic import utils,fileop,introspect
from visexpman.engine import ExperimentConfigError
import stimulation_library

import inspect
from visexpman.engine.vision_experiment import configuration

import unittest

class ExperimentConfig(Config):
    '''
    Init parameters:
    machine config
    parameters: saved to experiment config.
    socket queues
    log
    '''
    def __init__(self, machine_config, queues = None, experiment_module = None, parameters = None, log=None, screen=None, create_runnable=True):
        Config.__init__(self, machine_config=machine_config,ignore_range = True)
        check_experiment_config(self)
        self.editable=True#If false, experiment config parameters cannot be edited from GUI
        self.name=self.__class__.__name__
        if machine_config != None and create_runnable:
            self.create_runnable(machine_config, queues, experiment_module, parameters, log) # needs to be called so that runnable is instantiated and other checks are done

    def create_runnable(self, machine_config, queues, experiment_module, parameters, log):
        '''
        Find experiment class and instantiate it
        '''
        #Find experiment class
        if self.runnable is None:
            raise ValueError('You must specify the class which will run the experiment')
        elif self.runnable in dir(experiment_module):#experiment class is implemented in source code
            experiment_class = getattr(experiment_module, self.runnable)
        else: #experiment class is in common or user module
            for u in ['common', machine_config.user]:
                experiment_class = utils.fetch_classes('visexpman.users.'+ u, classname = self.runnable,  
                                                    required_ancestors = visexpman.engine.vision_experiment.experiment.Experiment, direct=False)
                if len(experiment_class) == 1:
                    experiment_class = experiment_class[0][1]
                    break
        if isinstance(experiment_class,list) and len(experiment_class) == 0:
            raise ExperimentConfigError('runnable points to a non existing experiment class')
        #check if class inherits from experiment
        if len([True for base in experiment_class.__bases__ if base.__name__ =='Experiment'])==0:
            raise ExperimentConfigError('runnable points to a class that does not inherit from Experiment')
        #Instantiate experiment class
        self.runnable = experiment_class(machine_config, self, queues, parameters, log)

    def run(self, fragment_id = 0):#OBSOLETE
        if self.runnable == None:
            raise ValueError('Specified stimulus class is not instantiated.')
        else:
            function_args = inspect.getargspec(self.runnable.run)
            if 'fragment_id' in function_args.args:
                self.runnable.run(fragment_id = fragment_id)
            else:
                self.runnable.run()
        self.runnable.cleanup()
        
def check_experiment_config(config):
    timing_keywords=['duration', 'time', 'delay', 'pause']
    second_millisecond_warning_threshold=200
    for vn in dir(config):
        if vn.isupper():
            #Variable names with timing_keywords and woutout _MS tag considered as timing parameters in seconds
            if any([kw.upper() in vn and '_MS' not in vn for kw in timing_keywords]):
                v=getattr(config, vn)
                if v >second_millisecond_warning_threshold:
                    import warnings
                    warnings.warn('{0} ({1}) parameter might be in milliseconds'.format(vn,v))

class Experiment(stimulation_library.AdvancedStimulation):
    '''
    The usage of experiment fragments assumes the existence of number_of_fragments variable
    The following variable is saved to the output file: self.experiment_specific_data
    '''
    def __init__(self, machine_config, experiment_config=None, queues=None, parameters=None, log=None):
        self.parameters = parameters#Parameters coming from main_ui
        self.experiment_config = experiment_config
        self.experiment_name = self.__class__.__name__.split('_')[0]
        self.experiment_config_name = self.experiment_config.__class__.__name__.split('_')[0]
        self.name='{0}/{1}'.format(self.experiment_name,self.experiment_config_name)
        stimulation_library.Stimulations.__init__(self, machine_config, parameters, queues, log)
        

    def prepare(self):
        '''
        self.experiment_duration must be calculated here
        Longer calculations for stimulation shall be implemented here
        '''
    
    def run(self, fragment_id = 0):
        '''
        fragment_id: experiment can be split up to measurement fragments.
        '''    
        pass

    def post_experiment(self):
        '''
        Operations to execute right after the experiment. Saving user specific files, closing instruments  that are not handled within Device class, user specific file operations
        '''        
        
    ################# helpers ############################
    def set_default_experiment_parameter_values(self, parameter_default_values):
        '''
        parameter values in parameter_default_values are copied to self.parametername variable if these values are defined in experiment config. 
        Otherwise the default values provided in parameter_default_values are copied.
        '''
        for k, v in parameter_default_values.items():
            if hasattr(self.experiment_config, k):
                setattr(self, k.lower(), getattr(self.experiment_config, k))
            else:
                setattr(self, k.lower(), v)
                
#    def printl(self, message):
#         '''
#         Helper function that can be called during experiment. The message is sent to:
#         -standard output
#         -gui
#         -experiment log
#         '''
#         print message
##         self.to_gui.put(str(message))
##         if hasattr(self, 'log'):
##             self.log.info(str(message))
        
    def save_variables(self,variable_names):
        '''
        self.<<variable names>> will ba saved to self.user_data (experiment_specific_data)
        '''
        for v in variable_names:
            self.user_data[v] = getattr(self,v)

class PreExperiment(Experiment):
    '''
    The prerun method of this experiment will be called prior the experiment to provide some initial stimulus while the experimental setup is being set up.
    
    The prerun method can draw only one frame at a time withoud flipping it.
    For moving pre runnable pattern the user shall use a state variable for control
    '''
    pass
    #TODO: Overlay menu on pre experiment visual stimulus so that the text is blended to the graphical pattern
    #Preexperiment can be a static image, that is always drawn when the non-experiment screen is redrawn.
    #Alternatively while preexperiment runs, keyboard handler&command handler shall be called.


class Stimulus(stimulation_library.AdvancedStimulation):
    '''
    Superclass for all user defined stimuli. Stimulus logic and parameters are also included in this class.
    '''
    def __init__(self, machine_config, queues = None, parameters = None, log=None, init_hardware=True,**kwargs):
        self.kwargs=kwargs
        if init_hardware:
            stimulation_library.Stimulations.__init__(self, machine_config, parameters, queues, log)
        self.default_configuration()
        self.configuration()
        check_experiment_config(self)
        self.calculate_stimulus_duration()
        self.name=self.__class__.__name__
        
    def default_configuration(self):
        '''
        Shall be used by Stimulus superclasses
        '''
        
    def configuration(self):
        '''
        This method needs to be overdefined by subclasses. The experiment configuration parameters are defined here
        '''
        
    def calculate_stimulus_duration(self):
        '''
        Method for calculating the stimulus duration from the stimulus configuration parameters.
        
        Compulsory for stimuli intentended for Ca imaging
        '''
        
    def run(self):
        '''
        Placeholder for main stimulus logic
        '''
        
    def prepare(self):
        '''
        Place for computation intensive code that should run before run() method is called
        '''
        
        
    def prestim(self):
        '''
        Stimulus pattern generation on idle screen
        '''
        
    def config2dict(self):
        d={}
        for vn in dir(self):
            if vn.isupper():
                d[vn]=getattr(self,vn)
        return d
        
class BehavioralProtocol(threading.Thread):
#class BehavioralProtocol(multiprocessing.Process):
    '''
    Compulsory parameters:
        TRIGGER_TIME: when actions triggered
        DURATION_MIN, DURATION_MAX: overall duration will be randomized between these values
    '''
    ENABLE_IMAGING_SOURCE_CAMERA=False
    def __init__(self,engine):
        threading.Thread.__init__(self)
        #multiprocessing.Process.__init__(self)
        self.engine=engine
        self.init()
        
    def generate_duration(self):
        if self.TRIGGER_TIME>self.DURATION_MIN:
            raise RuntimeError('duration range ({0}, {1}) shall be longer than trigger time ({2})'.format(self.DURATION_MIN, self.DURATION_MAX,self.TRIGGER_TIME))
        self.duration=numpy.round(numpy.random.random()*(self.DURATION_MAX-self.DURATION_MIN)+self.DURATION_MIN,0)
        logging.info('Protocol duration is {0}'.format(self.duration))
        
    def prepare(self):
        '''
        precalculation, initialization
        '''
        
    def init(self):
        if not hasattr(self, 'duration') and hasattr(self, 'TRIGGER_TIME'):
            self.generate_duration()
        self.prepare()
        self.starttime=time.time()
        
    def run(self):
        self.init()
        self.trigger_fired=False
        while True:
            now=time.time()
            if now-self.starttime>self.TRIGGER_TIME and not self.trigger_fired:
                logging.info('Protocol event trigger')
                self.triggered()
                self.trigger_fired=True
            if self.isfinished():
                logging.info('Protocol finishes')
                break
            time.sleep(0.1)
        
    def triggered(self):
        '''
        When protocol main event triggered, actions taken implemented here
        '''
        
    def stat(self):
        '''
        calculate statistics
        '''
        
    def isfinished(self):
        return time.time()-self.starttime>=self.duration
    
def get_experiment_duration(experiment_config_class, config, source=None):
    if '_'in experiment_config_class:
        raise ExperimentConfigError('Stimulus name cannot contain _ character')
    if source is None:
        stimulus_class = utils.fetch_classes('visexpman.users.'+ config.user, classname = experiment_config_class, required_ancestors = visexpman.engine.vision_experiment.experiment.Stimulus,direct = False)
        if len(stimulus_class)==1:
            experiment_class_object=stimulus_class[0][1]
        else:
            try:
                experiment_class = utils.fetch_classes('visexpman.users.'+ config.user, classname = experiment_config_class, required_ancestors = visexpman.engine.vision_experiment.experiment.ExperimentConfig,direct = False)[0][1]
            except IndexError:
                experiment_class = utils.fetch_classes('visexpman.users.common', classname = experiment_config_class, required_ancestors = visexpman.engine.vision_experiment.experiment.ExperimentConfig,direct = False)[0][1]
            experiment_class_object = experiment_class(config).runnable
    else:
        introspect.import_code(source,'experiment_config_module', add_to_sys_modules=1)
        experiment_config_module = __import__('experiment_config_module')
        ecclass=getattr(experiment_config_module, experiment_config_class)
        if hasattr(ecclass, 'calculate_stimulus_duration'):
            experiment_class_object=ecclass
        else:
            experiment_config_class_object = ecclass(config, create_runnable=False)
            if hasattr(experiment_config_module,experiment_config_class_object.runnable):
                experiment_class_object = getattr(experiment_config_module,experiment_config_class_object.runnable)(config,experiment_config_class_object)
            else:
                experiment_class = utils.fetch_classes('visexpman.users.common', classname = experiment_config_class_object.runnable, required_ancestors = visexpman.engine.vision_experiment.experiment.Experiment,direct = False)[0][1]
                experiment_class_object = experiment_class(config, experiment_config_class_object)
    if hasattr(experiment_class_object,'calculate_stimulus_duration'):
        ec=experiment_class_object(config)
        ec.configuration()
        ec.calculate_stimulus_duration()
    else:
        ec=None
        experiment_class_object.prepare()
    if hasattr(experiment_class_object, 'duration'):
        return experiment_class_object.duration
    elif hasattr(ec, 'duration'):
        return ec.duration
    else:
        from visexpman.engine import ExperimentConfigError
        raise ExperimentConfigError('Stimulus duration is unknown')
        
def read_stimulus_parameters(stimname, filename,config):
    source_code=fileop.read_text_file(filename)
    introspect.import_code(source_code,'experiment_module', add_to_sys_modules=1)
    em=__import__('experiment_module')
    ec=getattr(em,stimname)(config,create_runnable=False)
    return introspect.cap_attributes2dict(ec)

def parse_stimulation_file(filename):
    '''
    From a stimulation file get the names of experiment classes and the parameter values for each
    Only the values defined in the class itself are fetched, parameters from ancestors are ignored
    '''
    if os.path.splitext(filename)[1] != '.py':
        raise RuntimeError('Files only with py extension can be selected: {0}'.format(filename))
    source_code = fileop.read_text_file(filename)
    if 'import *' in source_code:
        raise RuntimeError('Parsing {0} might freeze'.format(filename))
    try:
        introspect.import_code(source_code,'experiment_module', add_to_sys_modules=1)
    except Exception as e:
        raise type(e)(e.message + '\r\nFile {0}, line {1}'.format(filename, sys.exc_info()[2].tb_lineno))
    experiment_module = __import__('experiment_module')
    experiment_config_classes = {}
    for c in inspect.getmembers(experiment_module,inspect.isclass):
        if c[1]==object:#call to =introspect.class_ancestors hangs
            continue
        ancestorts=introspect.class_ancestors(c[1])
        if 'ExperimentConfig' in ancestorts:
            try:
                expconfig_lines = source_code.split('class '+c[0])[1].split('def _create_parameters')[1].split('def')[0].split('\n')
                experiment_config_classes[c[0]] = \
                    [expconfig_line.replace(' ','') for expconfig_line in expconfig_lines \
                        if '=' in expconfig_line and (expconfig_line.split('=')[0].replace('self.','').isupper() or 'self.editable' in expconfig_line.split('=')[0])]
            except:
                continue
        elif 'Stimulus' in ancestorts:
            experiment_config_classes[c[0]] = []
    return experiment_config_classes

class testExperimentHelpers(unittest.TestCase):
    def test_01_parse_stim_file(self):
        experiment_config_classes = parse_stimulation_file(os.path.join(fileop.visexpman_package_path(), 'users','test','test_stimulus.py'))
        self.assertEqual((
                          experiment_config_classes.has_key('GUITestExperimentConfig'), 
                          experiment_config_classes.has_key('DebugExperimentConfig'), 
                          experiment_config_classes.has_key('TestStim'), 
                          ), 
                          (True, True, True))
        parse_stimulation_file(os.path.join(fileop.visexpman_package_path(), 'users','volker','plot_mcd.py'))
        parse_stimulation_file('v:\\codes\\zdev2\\visexpman\\users\\common\\behavioral_protocols.py')
    
    def test_02_read_experiment_duration(self):
        from visexpman.users.test.test_configurations import GUITestConfig
        conf = GUITestConfig()
        conf.user='test'
        duration = get_experiment_duration('DebugExperimentConfig', conf, source=None)#Legacy experiment config
        self.assertEqual(duration, 15.0)
        duration = get_experiment_duration('TestStim', conf, source=None)
        self.assertEqual(duration, 0.2)
        duration = get_experiment_duration('TestStim', conf, source=fileop.read_text_file(os.path.join(fileop.visexpman_package_path(),'users','test','test_stimulus.py')))
        self.assertEqual(duration, 0.2)
        
    def test_03_read_experiment_duration_from_source(self):
        from visexpman.users.test.test_configurations import GUITestConfig
        conf = GUITestConfig()
        conf.user='test'
        source = fileop.read_text_file(os.path.join(fileop.get_user_module_folder(conf), 'test_stimulus.py'))
        conf.user='zoltan'
        duration = get_experiment_duration('DebugExperimentConfig', conf, source=source)
        self.assertEqual(duration, 15.0)
        self.assertEqual(isinstance(get_experiment_duration('TestCommonExperimentConfig', conf, source=source), float), True)#Testing something from the common folder
        conf.user='zoltan'
        source = fileop.read_text_file(os.path.join(fileop.get_user_module_folder(conf), 'experiment_tests.py'))
        
    def test_04_not_existing_experiment_class(self):
        from visexpman.users.test.test_configurations import GUITestConfig
        conf = GUITestConfig()
        conf.user='test'
        self.assertRaises(ExperimentConfigError, get_experiment_duration,'Pointing2NotExistingConfig', conf, None)
        
    def test_05_exp_config_points2non_expclass(self):
        from visexpman.users.test.test_configurations import GUITestConfig
        conf = GUITestConfig()
        conf.user='test'
        self.assertRaises(ExperimentConfigError, get_experiment_duration,'Pointing2NonExpConfig', conf, None)
        
    def test_06_stimulusclass(self):
        from visexpman.engine.visexp_app import stimulation_tester
        context = stimulation_tester('test', 'GUITestConfig', 'TestStim', ENABLE_FRAME_CAPTURE = False)
        context = stimulation_tester('test', 'GUITestConfig', 'TestStim1', ENABLE_FRAME_CAPTURE = False)
        src=fileop.read_text_file(os.path.join(fileop.visexpman_package_path(), 'users', 'test','test_stimulus.py'))
        context = stimulation_tester('test', 'GUITestConfig', 'TestStim1', ENABLE_FRAME_CAPTURE = False, stimulus_source_code = src)
        
    def test_07(self):
        from visexpman.users.test.test_configurations import GUITestConfig
        conf = GUITestConfig()
        get_experiment_duration('ReceptiveFieldExploreNewAngleAdrian', conf, source=fileop.read_text_file(os.path.join(fileop.visexpman_package_path(),'users','adrian','receptive_field.py')))
        
    def test_08_read_experiment_parameters(self):
        from visexpman.users.test.test_configurations import GUITestConfig
        conf = GUITestConfig()
        read_stimulus_parameters('MovingBarTemplate', os.path.join(os.path.dirname(visexpman.__file__),'users','common','stimuli.py'),conf)
        
        
    
    
if __name__ == "__main__":
    unittest.main()
