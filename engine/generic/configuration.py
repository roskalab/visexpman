import os, platform, copy, utils, parameter, unittest

PRINT_PAR_NAMES = False

class Config(object):
    def __init__(self, machine_config=None, generic_parameters = True, ignore_range = False):
        '''
        Machine config: main, setup/user etc specific config that may be used by experiment configs
        
        Usage:
        
        Application level configuration:
        Creating parameters, overdefine this function:
        
        def _create_application_parameters(self):
            PAR1 = 
            PAR2 = 
            ...
            self._create_parameters_from_locals(locals())
        
        Here calculations can be defined using the parameters created in _create_application_parameters function
        
        def _calculate_parameters(self):
            ...
        
        User/Setgup level configuration:
        
        Existing parameters can be changed
        def _set_user_parameters(self):
            PAR1 =
            PAR2 = 
            ...
            self._set_parameters_from_locals(locals())
        
        Additional parameters can be created if needed
        def _create_parameters(self):
            PAR1 = 
            PAR = 
            self._create_parameters_from_locals(locals())
        '''
        self.machine_config = machine_config#OBSOLETE?
        self.ignore_range = ignore_range
        if generic_parameters:
            self._create_generic_parameters()
        #The _create_application_parameters and the _calculate_parameters methods will be overdefined in the application child class.
        self._create_application_parameters()
        self._create_parameters()
        #Override default values of parameters created by _create_application_parameters()
        self._set_user_parameters()
        #create/update parameters from existing parameter values
        self._calculate_parameters()
        #check for modified or new parameters created by calculate_parameters method, get their names and load them:
        self._create_parameter_aliases()

    def _create_generic_parameters(self):
        self.PACKAGE_PATH_p = parameter.Parameter(os.path.split(os.path.split(os.path.dirname(parameter.__file__))[0])[0], is_path=True)
        OS = platform.system()
        IS64BIT = '64' in platform.machine()
        self.OS_p = parameter.Parameter(OS)
        self.IS64BIT_p = parameter.Parameter(IS64BIT)
        self._create_parameter_aliases()
        return

    def _create_parameters_from_locals(self, locals, check_path = True):
        for k, v in locals.items():
            if hasattr(self, k):  # parameter was already initialized, just update with new value
                self.set(k, v)
            elif k.isupper() and '_RANGE' not in k:
                if PRINT_PAR_NAMES:
                    print k, v
                if self.ignore_range:
                    setattr(self, k + '_p',  parameter.Parameter(v,  check_range = False,name=k))
                elif isinstance(v,  list):
                    if len(v)==2 and ((isinstance(v[1], (list, tuple)) and v[1][0] !='not_range') or v[1]==None):
                        setattr(self,  k + '_p',  parameter.Parameter(v[0],  range_ = v[1],name=k))
                    elif len(v) == 1: #when no range is provided (list of strings or dictionaries) # why we do this???
                        setattr(self,  k + '_p',  parameter.Parameter(v))
                    elif len(v)==2 and isinstance(v[1], (list, tuple)) and v[1][0] =='not_range':
                        # in theory such data would not be used as data
                        # for the rare case when parameter is a two element list, seond element is a 4 element list with first element 'not_range', meaning that second element is also data and should be treated as data
                        v[1] = v[1][1:] # remove helper string
                        setattr(self,  k + '_p',  parameter.Parameter(v,name=k))
                    else:
                        setattr(self,  k + '_p',  parameter.Parameter(v,name=k))                        
                elif '_PATH' in k: #"PATH" is encoded into variable name
                    setattr(self,  k + '_p',  parameter.Parameter(v, is_path = check_path,name=k))
                elif '_FILE' in k: #variable name ends with _FILE
                    setattr(self,  k + '_p',  parameter.Parameter(v, is_file = check_path,name=k))
                else:
                    setattr(self,  k + '_p', parameter.Parameter(v,name=k))
        self._create_parameter_aliases()

    def _set_parameters_from_locals(self,  locals):
        for k,  v in locals.items():
            if k.isupper() and '_RANGE' not in k:
                self.set(k,  v)
                
    def _create_application_parameters(self):
        '''
        By overdefining this function, the application/user etc specific parameters can be defined here:
            self.PAR_p =              
        '''
        pass
        
    def _create_parameters(self):
        '''
        By overdefining this function, additional parameters can be created
            self.PAR_p =              
        '''
        pass
        
    def _set_user_parameters(self):
        '''
        Function for overriding the application's 'default parameter values
        '''
        pass

    def _calculate_parameters(self):
        '''
        Function for modifying parameters with calculations and creating new parameters calculated from existing values
        '''
        pass

    def set(self,  parameter_name,  new_value):
        '''
        Change value of a parameter in config. Perhaps this function shall be disabled so that parameters could not be modified in runtime or outside the class definition.
        '''        
        getattr(getattr(self,  parameter_name + '_p'),  'set')(new_value) 
        setattr(self,  parameter_name,  new_value)
        

    def _create_parameter_aliases(self):
        '''
        The value of self.PARNAME_p parameters are copied to a self.PARNAME variable
        '''
        class_variables = dir(self)
        parameters = [class_variable for class_variable in class_variables if class_variable.find('_p') != -1 and class_variable.replace('_p',  '').isupper()] 
        parameter_values = []
        parameter_names = []
        for parameter in parameters:
            parameter_reference = getattr(self,  parameter)
            parameter_value = getattr(parameter_reference,  'v')
            parameter_name = parameter.replace('_p',  '')            
            if not hasattr(self,  parameter_name):
                setattr(self,  parameter_name, parameter_value)

    def print_parameters(self):
        class_variables = dir(self)
        parameter_names = [class_variable for class_variable in class_variables if class_variable.isupper()] 
        for parameter_name in parameter_names:
            print parameter_name + ' = ' + str(getattr(self,  parameter_name))
            
    def get_all_parameters(self):
    #TODO: test case for this function
        class_variables = dir(self)
        parameter_names = [class_variable for class_variable in class_variables if class_variable.isupper() or 'user' == class_variable]        
        all_parameters = {}
        for parameter_name in parameter_names:
            all_parameters[parameter_name] = getattr(self, parameter_name)
            if hasattr(all_parameters[parameter_name], 'keys'):
                if all_parameters[parameter_name] == {}:
                    all_parameters[parameter_name] = 0
            elif all_parameters[parameter_name] == None:
                all_parameters[parameter_name] = 0
            #If a list contains dictionary items, convert them to a dict of dict. hdf5io module cannot handle this type of data
            elif isinstance(getattr(self,  parameter_name), list):
                if isinstance(getattr(self,  parameter_name)[0], dict):
                    d = {}
                    for i in range(len(getattr(self, parameter_name))):
                        parameter_value = getattr(self, parameter_name)[i]
                        d['index_'+str(i)] = parameter_value
                    all_parameters[parameter_name] = d
        return all_parameters
        
    def todict(self):
        packed2dict = {}
        for parameter_name in [class_variable for class_variable in dir(self) if class_variable.isupper() or 'user' == class_variable]:
            packed2dict[parameter_name] = getattr(self,parameter_name)
        return packed2dict
        
    def serialize(self):
        config_modified = copy.copy(self)
        removable_attributes = ['machine_config', 'runnable', 'pre_runnable', 'queues', 'GAMMA_CORRECTION']
        for a in removable_attributes:
            setattr(config_modified, a, 0)
        return utils.object2array(config_modified)
        
### Classes for test purposes ###
        
class ApplicationTestClass(Config):
    def _create_application_parameters(self):
        PAR1 = [1, [-2, 2]]
        PAR2 = [2, [-1, 2]] 
        self._create_parameters_from_locals(locals())
        
    def _calculate_parameters(self):        
        self.PAR3_p = parameter.Parameter(self.PAR1+self.PAR2, range_ = [-2,  2])        
        
class UserTestClass(ApplicationTestClass):
    def _create_parameters(self):
        PAR4 = [1, [-2, 2]]
        self._create_parameters_from_locals(locals())        

    def _set_user_parameters(self):
        PAR1 = -2
        self._set_parameters_from_locals(locals())
        
class WrongUserTestClass(UserTestClass):
    def _set_user_parameters(self):
        PAR1 = -2
        PAR5 = 200
        self._set_parameters_from_locals(locals())
#TODO: test cases for complex parameters: list of dict, dict of dict....
class testConfiguration(unittest.TestCase):    
    def test_01_package_path_parameter(self):
        '''
        Test whether the default parameter has a correct value and the constructor of the class runs without error
        '''
        package_path = os.path.split(os.path.split(os.path.dirname(parameter.__file__))[0])[0]
        config = Config()
        self.assertEqual((config.PACKAGE_PATH_p.v, config.PACKAGE_PATH),  (package_path, package_path))
        
    def test_02_subclass_structure(self):
        '''
        Test if the overdefined functions in the test classes create and modify the parameters correctly
        '''
        a = UserTestClass()
        self.assertEqual((a.PAR1, a.PAR2, a.PAR3, a.PAR4),  (-2, 2, 0, 1))
        
    def test_03_set_parameter_in_config(self):
        a = UserTestClass()
        a.set('PAR1', 0)
        self.assertEqual((a.PAR1, a.PAR2, a.PAR3, a.PAR4),  (0, 2, 0, 1))
        
    def test_04_set_parameter_in_config_out_of_range(self):
        a = UserTestClass()        
        self.assertRaises(parameter.OutOfRangeParameterValue, a.set, 'PAR1', 10)
        
    def test_05_wrong_user_class_definition(self):        
        self.assertRaises(AttributeError, WrongUserTestClass)    
    
if __name__ == "__main__":
    unittest.main()
