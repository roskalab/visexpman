import sys
import os.path
import os 

import Parameter

class Config(object):
    def __init__(self,  base_path = None):
        print 'Loaded configuration class: ' + self.__class__.__name__        
        self.base_path = base_path
        self._create_generic_parameters()        
        self._create_parameter_aliases()        
        self._create_application_parameters()        
        self._create_parameter_aliases()        
        self._set_user_specific_parameters()        
        self._calculate_parameters()        
        #check for new parameters created by calculate_parameters method, get their names and load them:        
        self._create_parameter_aliases()
        
    def _create_generic_parameters(self):
        if self.base_path != None:
            self.BASE_PATH_p = Parameter.Parameter(self.base_path, is_path = True)
        elif os.name == 'nt' and os.path.exists(os.path.dirname(sys.argv[0])):
            self.BASE_PATH_p = Parameter.Parameter(os.path.dirname(sys.argv[0]), is_path = True)
        else:
            self.BASE_PATH_p = Parameter.Parameter(os.getcwd(), is_path = True)

    def _create_parameters_from_locals(self,  locals): 
        for k,  v in locals.items():
            if k.isupper() and k.find('_RANGE') == -1:                
                if isinstance(v,  list):
                    if len(v) == 1: #when no range is provied (list of strings or dictionaries)
                        setattr(self,  k + '_p',  Parameter.Parameter(v[0]))
                    else:
                        setattr(self,  k + '_p',  Parameter.Parameter(v[0],  range_ = v[1]))
                elif k.find('_PATH') != -1: #"PATH" is encoded into variable name
                    setattr(self,  k + '_p',  Parameter.Parameter(v,  is_path = True))
                else:
                    setattr(self,  k + '_p',  Parameter.Parameter(v))

    def _set_parameters_from_locals(self,  locals):
        for k,  v in locals.items():
            if k.isupper() and k.find('_RANGE') == -1:
                self.set(k,  v)
                
    def _create_application_parameters(self):
        '''
        By overdefining this function, the application/user etc specific parameters can be definced here:
            self.PAR_p =              
        '''
        pass
        
    def _set_user_specific_parameters(self):
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
        getattr(getattr(self,  parameter_name + '_p'),  'set')(new_value)
        setattr(self,  parameter_name,  new_value)

    def _create_parameter_aliases(self):
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
                
    def _update_parameter_aliases(self):
        pass            

    def print_parameters(self):
        class_variables = dir(self)
        parameter_names = [class_variable for class_variable in class_variables if class_variable.isupper()] 
        for parameter_name in parameter_names:
            print parameter_name + ' = ' + str(getattr(self,  parameter_name))
    
#class ConfigurationTestClass(Config):
#    def _create_user_parameters(self):
#        pass
#        
#    def _set_user_specific_parameters(self):
#        pass
#    
#    def _calculate_parameters(self):
#        pass
#    
#class testConfiguration(unittest.TestCase):
#    def test_01_valid_path_parameter(self):
#        pass
    
if __name__ == "__main__":
#    unittest.main()
    c = Config()
#    c.print_parameters()
#    c.set('BASE_PATH',  '/home')
#    c.print_parameters() 
    
