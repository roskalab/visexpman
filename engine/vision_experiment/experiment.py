import sys
import logging
import os
import visexpman

from visexpman.engine.generic.configuration import Config
from visexpman.engine.generic import utils
from visexpman.engine.generic import fileop
from visexpman.engine.generic import introspect
from visexpman.engine import ExperimentConfigError
import stimulation_library

import inspect
import hdf5io
from visexpman.engine.generic import introspect
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
    def __init__(self, machine_config, queues = None, experiment_module = None, parameters = None, log=None):
        Config.__init__(self, ignore_range = True)
        self.editable=True#If false, experiment config parameters cannot be edited from GUI
        if machine_config != None:
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
        stimulation_library.Stimulations.__init__(self, machine_config, queues, log)
        self.prepare()

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


######################### Restore experiment config from measurement data #########################

#OBSOLETE
class MachineConfig(configuration.VisionExperimentConfig):
    def __init__(self, machine_config_dict, default_user = None):
        self.machine_config_dict = machine_config_dict
        self.default_user = default_user
        configuration.VisionExperimentConfig.__init__(self)
        
    def _set_user_parameters(self):
        copy_parameters = ['COORDINATE_SYSTEM']
        for k, v in self.machine_config_dict.items():
            if k in copy_parameters:
                setattr(self, k, v)
        if not hasattr(self, 'user'):
            self.user = self.default_user
        self._create_parameters_from_locals(locals())
        pass
    
#OBSOLETE
def restore_experiment_config(experiment_config_name, fragment_hdf5_handler = None,  experiment_source = None,  machine_config_dict = None, user = None):
    if fragment_hdf5_handler != None and experiment_source == None and machine_config_dict == None:
        experiment_source = fragment_hdf5_handler.findvar('experiment_source').tostring()
        machine_config_dict = fragment_hdf5_handler.findvar('machine_config')
    machine_config = MachineConfig(machine_config_dict, default_user = user)
    introspect.import_code(experiment_source,'experiment_module',add_to_sys_modules=1)
    experiment_module = __import__('experiment_module')
    experiment_config = getattr(experiment_module, experiment_config_name)(machine_config = machine_config, caller = None)
    return experiment_config
    a = experiment_module.MovingDot(machine_config, None, experiment_config)
    
def get_experiment_duration(experiment_config_class, config, source=None):
    if source is None:
        experiment_class = utils.fetch_classes('visexpman.users.'+ config.user, classname = experiment_config_class, required_ancestors = visexpman.engine.vision_experiment.experiment.ExperimentConfig,direct = False)[0][1]
        experiment_class_object = experiment_class(config).runnable
    else:
        introspect.import_code(source,'experiment_config_module', add_to_sys_modules=1)
        experiment_config_module = __import__('experiment_config_module')
        experiment_config_class_object = getattr(experiment_config_module, experiment_config_class)(None)
        experiment_class_object = getattr(experiment_config_module,experiment_config_class_object.runnable)(config,experiment_config_class_object)
    if hasattr(experiment_class_object, 'stimulus_duration'):
        return experiment_class_object.stimulus_duration
    else:
        from visexpman.engine import ExperimentConfigError
        raise ExperimentConfigError('Stimulus duration is unknown')

def parse_stimulation_file(filename):
    '''
    From a stimulation file get the names of experiment classes and the parameter values for each
    Only the values defined in the class itself are fetched, parameters from ancestors are ignored
    '''
    if fileop.file_extension(filename) != 'py':
        raise RuntimeError('Files only with py extension can be selected: {0}'.format(filename))
    source_code = fileop.read_text_file(filename)
    introspect.import_code(source_code,'experiment_module', add_to_sys_modules=1)
    experiment_module = __import__('experiment_module')
    experiment_config_classes = {}
    for c in inspect.getmembers(experiment_module,inspect.isclass):
        if 'ExperimentConfig' in introspect.class_ancestors(c[1]):
            try:
                expconfig_lines = source_code.split('class '+c[0])[1].split('def _create_parameters')[1].split('def')[0].split('\n')
                experiment_config_classes[c[0]] = \
                    [expconfig_line.replace(' ','') for expconfig_line in expconfig_lines \
                        if '=' in expconfig_line and (expconfig_line.split('=')[0].replace('self.','').isupper() or 'self.editable' in expconfig_line.split('=')[0])]
            except:
                continue
    return experiment_config_classes

class testExperimentHelpers(unittest.TestCase):
    def test_01_parse_stim_file(self):
        experiment_config_classes = parse_stimulation_file(os.path.join(fileop.visexpman_package_path(), 'users','test','test_stimulus.py'))
        self.assertEqual((
                          experiment_config_classes.has_key('GUITestExperimentConfig'), 
                          experiment_config_classes.has_key('DebugExperimentConfig'), 
                          ), 
                          (True, True))
    
    def test_02_read_experiment_duration(self):
        from visexpman.users.test.test_configurations import GUITestConfig
        conf = GUITestConfig()
        conf.user='test'
        duration = get_experiment_duration('DebugExperimentConfig', conf, source=None)
        self.assertEqual(duration, 10.0)
        self.assertEqual(isinstance(get_experiment_duration('TestCommonExperimentConfig', conf, source=None), float), True)#Testing something from the common folder
        
    def test_03_read_experiment_duration_from_source(self):
        from visexpman.users.test.test_configurations import GUITestConfig
        conf = GUITestConfig()
        conf.user='test'
        source = fileop.read_text_file(os.path.join(fileop.get_user_module_folder(conf), 'test_stimulus.py'))
        conf.user='zoltan'
        duration = get_experiment_duration('DebugExperimentConfig', conf, source=source)
        self.assertEqual(duration, 10.0)
        
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
        
    
if __name__ == "__main__":
    unittest.main()
