import sys,time,numpy
import logging
import os
import visexpman
from visexpman.engine.generic.configuration import Config
from visexpman.engine.generic import utils, file
import stimulation_library
import inspect
import visexpA.engine.datahandlers.hdf5io as hdf5io
from visexpman.engine.generic import introspect
from visexpman.engine.vision_experiment import configuration

class ExperimentConfig(Config):
    def __init__(self, machine_config, queues, connections, application_log, experiment_class = None, source_code = None, parameters = {}):
        self.machine_config = machine_config
        self.queues = queues
        self.connections = connections
        self.application_log = application_log
        Config.__init__(self, machine_config)
        if machine_config != None:
            self.create_runnable(experiment_class, source_code, parameters) # needs to be called so that runnable is instantiated and other checks are done        

    def create_runnable(self, experiment_class, source_code, parameters):
        if self.runnable == None:
            raise ValueError('You must specify the class which will run the experiment')
        else:
            if experiment_class == None and source_code == None:
                expconfigs=[]
                for u in ['common',self.machine_config.user]:
                    expcs=utils.fetch_classes('visexpman.users.'+ u, classname = self.runnable,  
                                                    required_ancestors = visexpman.engine.vision_experiment.experiment.Experiment, direct=False)
                    if len(expcs)>0:
                        expconfigs.append(expcs)
                self.runnable = expconfigs[0][0][1]\
                    (self.machine_config, self, self.queues, self.connections, self.application_log, parameters = parameters) # instantiates the code that will run the actual stimulation
            else:
                self.runnable = experiment_class(self.machine_config, self, self.queues, self.connections, self.application_log, source_code, parameters = parameters)
            if hasattr(self, 'pre_runnable'):
                expconfigs=[]
                for u in ['common',self.machine_config.user]:
                    expconfigs.extend(utils.fetch_classes('visexpman.users.'+ u, required_ancestors = visexpman.engine.vision_experiment.experiment.PreExperiment, direct=False))
                for pre_experiment_class in expconfigs: 
                    if pre_experiment_class[1].__name__ == self.pre_runnable:
                        self.pre_runnable = pre_experiment_class[1](self.machine_config, self, self.queues, self.connections, self.application_log, parameters = parameters) # instantiates the code that will run the pre experiment code
                        break

    def run(self, fragment_id = 0):
        if self.runnable == None:
            raise ValueError('Specified stimulus class is not instantiated.')
        else:
            function_args = inspect.getargspec(self.runnable.run)
            if 'fragment_id' in function_args.args:
                self.runnable.run(fragment_id = fragment_id)
            else:
                self.runnable.run()
        self.runnable.cleanup()
        
    def post_experiment(self):
        self.runnable.post_experiment()
        
    def pre_first_fragment(self):
        self.runnable.pre_first_fragment()
        
    def set_experiment_control_context(self):
        self.runnable.set_experiment_control_context()

class Experiment(stimulation_library.StimulationSequences):
    '''
    The usage of experiment fragments assumes the existence of number_of_fragments variable
    The floowing variable is saved to the output file: self.experiment_specific_data
    '''
    def __init__(self, machine_config, experiment_config, queues, connections, application_log, source_code = None , parameters = {}):
        self.parameters = parameters
        self.experiment_config = experiment_config
        self.machine_config = machine_config
        self.queues = queues
        self.connections = connections
        if source_code != None:
            self.source_code = source_code
        self.experiment_name = self.__class__.__name__.split('_')[0]
        self.experiment_config_name = self.experiment_config.__class__.__name__
        self.name_tag = self.experiment_config_name.replace('Config', '').replace('config', '')
        self.user_data = {}
        self.prepare()
        stimulation_library.Stimulations.__init__(self, self.machine_config, application_log)

    def prepare(self):
        '''
        Compulsory outputs for fragmented mes experiments:
            self.number_of_fragments
            self.fragment_durations - list of fragment stim times in sec
            
        '''
        pass
        
    def pre_first_fragment(self):
        '''
        Called before run if experiment is fragmented
        '''

    def run(self, fragment_id = 0):
        '''
        fragment_id: experiment can be split up to measurement fragments.
        '''    
        pass

    def cleanup(self):
        '''
        Operations to execute right after running the experiment. Saving user specific files, closing instruments  that are not handled within Device class, user specific file operations
        '''
        pass
        
    def post_experiment(self):
        '''
        Instructions can be put here that are intended to execute after the whole experiment procedure, when all the logfiles are flushed
        '''
        pass
        
    ################# helpers ############################
#     def printl(self, message):
#         '''
#         Helper function that can be called during experiment. The message is sent to:
#         -standard output
#         -gui
#         -experiment log
#         '''
#         print message
#         self.to_gui.put(str(message))
#         if hasattr(self, 'log'):
#             self.log.info(str(message))
        
    def save_variables(self,variable_names):
        '''
        self.<<variable names>> will ba saved to self.user_data (experiment_specific_data)
        '''
        for v in variable_names:
            self.user_data[v] = getattr(self,v)

class PreExperiment(Experiment):
    '''
    The run method of this experiment will be called prior the experiment to provide some initial stimulus while the experimental setup is being set up.
    '''
    pass
    #TODO: Overlay menu on pre experiment visual stimulus so that the text is blended to the graphical pattern
    #Preexperiment can be a static image, that is always drawn when the non-experiment screen is redrawn.
    #Alternatively while preexperiment runs, keyboard handler&command handler shall be called.


######################### Restore experiment config from measurement data #########################

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
        

class MetaStimulus(object):
    '''
    Multiple stimuli can be called in a user defined order
    '''
    def __init__(self, poller,  config):
        self.config=config
        self.poller=poller
        self.n_issued_commands=0
        self.id=str(int(time.time()))
        self.poller.printc('Starting {0}/{1} metastim'.format(self.__class__.__name__, self.id))

    def read_depth(self):
        depthstr=str(self.poller.parent.main_widget.experiment_control_groupbox.objective_positions_combobox.currentText())
        depthparams=map(int,depthstr.split(','))
        depths=range(depthparams[0],depthparams[1],-depthparams[2])
        depths.append(depthparams[1])
        return depths

    def read_laser(self,depths):
        laserstr=str(self.poller.parent.main_widget.experiment_control_groupbox.laser_intensities_combobox.currentText())
        laserpars=map(int, laserstr.split(','))
        return numpy.linspace(laserpars[0], laserpars[1], len(depths))
        
    def sleep(self, duration):
        self.poller.queues['stim']['out'].put('SOCsleepEOC{0}EOP'.format(duration))
        self.n_issued_commands+=1
        self.poller.printc('sleep for {0} s'.format(duration))
       
    def start_experiment(self,  stimulus_name,  depth,  laser):
        import time, copy
        self.experiment_parameters = {}
        self.experiment_parameters['metastim']=self.__class__.__name__
        self.experiment_parameters['metastim_id']=self.id
        self.experiment_parameters['user']=self.poller.animal_parameters['user']
        self.experiment_parameters['intrinsic'] = False
        self.experiment_parameters['stage_position']=self.poller.stage_position
        self.experiment_parameters['mouse_file'] = os.path.split(self.poller.mouse_file)[1]
        region_name = self.poller.parent.get_current_region_name()
        if len(region_name)>0:
            self.experiment_parameters['region_name'] = region_name
        self.experiment_parameters['experiment_config'] = stimulus_name
        self.experiment_parameters['scan_mode'] = 'xy'
        self.experiment_parameters['id'] = str(int(time.time()))
        self.poller.issued_ids.append(self.experiment_parameters['id'])
        self.experiment_parameters['objective_position'] = depth
        self.experiment_parameters['laser_intensity']=laser
        #generate parameter file
        parameter_file = os.path.join(self.config.EXPERIMENT_DATA_PATH, self.experiment_parameters['id']+'.hdf5')
        if os.path.exists(parameter_file):
            time.sleep(1.1)
            self.experiment_parameters['id'] = str(int(time.time()))
            self.poller.issued_ids[-1]=self.experiment_parameters['id']
            parameter_file = os.path.join(self.config.EXPERIMENT_DATA_PATH, self.experiment_parameters['id']+'.hdf5')
        h = hdf5io.Hdf5io(parameter_file,filelocking=False)
        h.parameters = copy.deepcopy(self.experiment_parameters)
        h.scan_regions = copy.deepcopy(self.poller.scan_regions)
        h.scan_regions = {self.experiment_parameters['region_name'] : h.scan_regions[self.experiment_parameters['region_name']]}#Keep only current scan region
        h.animal_parameters = copy.deepcopy(self.poller.animal_parameters)
        h.anesthesia_history = copy.deepcopy(self.poller.anesthesia_history)
        if self.poller.parent.main_widget.override_imaging_channels_checkbox.checkState()==2:
            h.animal_parameters['overridden']={'both_channels': h.animal_parameters['both_channels'], 'red_labeling': self.poller.animal_parameters['red_labeling']}
            h.animal_parameters['both_channels']=self.poller.parent.main_widget.record_red_channel_checkbox.checkState()==2
            h.animal_parameters['red_labeling']='yes' if self.poller.parent.main_widget.enable_prepost_scan_checkbox.checkState()==2 else 'no'
        fields_to_save = ['parameters']
        fields_to_save.extend(['scan_regions', 'animal_parameters', 'anesthesia_history'])
        h.save(fields_to_save)
        h.close()
        file.wait4file_ready(parameter_file)
        self.poller.printc('{0}{1} parameter file generated'.format(self.experiment_parameters['id'],'/{0} um'.format(self.experiment_parameters['objective_position']) if self.experiment_parameters.has_key('objective_position') else ''))
        command = 'SOCexecute_experimentEOCid={0},experiment_config={1}EOP' .format(self.experiment_parameters['id'], self.experiment_parameters['experiment_config'])
        time.sleep(0.5)
        self.poller.queues['stim']['out'].put('SOCpingEOCEOP')
        self.poller.queues['stim']['out'].put(command)
        
    def stop(self):
        self.poller.graceful_stop_experiment()
        self.poller.stop_experiment()
        for i in range(self.n_issued_commands):#Abort sleeps
            command = 'SOCabort_experimentEOCguiEOP'
            self.poller.queues['stim']['out'].put(command)
            
    def show_pre(self, classname):
        command='SOCselect_experimentEOC{0}EOP'.format(classname)
        self.poller.printc('{0} pre exp selected'.format(classname))
        self.poller.queues['stim']['out'].put(command)
        
    def run(self):
        '''
        Here comes the user sequence
        '''
