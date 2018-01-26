import os.path
import numpy
import unittest
import os
try:
    from visexpman.users.test import unittest_aggregator
except:
    pass

class InvalidParameterValue(Exception):
    pass
    
class OutOfRangeParameterValue(Exception):
    pass  
    
class Parameter(object):
    '''
    Parameter class determines the type of parameter automatically. Then performs range check or other checks when it is applicable.
    The aim of this class is to handle parameter like values and check their values when the type of the parameter requires it.
    The following data types are supported:
    list of numeric - range check
    list of string - no range check
    list of dictionary - no range check, usage: store complex hardware configurations
    enumerated - range check
    switch
    path- validity check
    file - validity check
    numeric - range check
    array - numpy array, no range check

    (---Parameter class shall determine the type of parameter automatically. Then the provided range shall be checked. At certain types instead of range, other checking algorithms shall be run.
    Supported types:
    
    list of numeric
    list of string
    list of dictionary
    array
    dictionary
    path
    file
    switch
    numeric
    enumerated--)
    
    Attributes:
    - value: its value is None if _status is False    
    - range_    
    
    Methods:
    - set
    '''
    
    def __init__(self,  value,  range_ = None,  is_path = False, is_file=False,check_range = True, name = ''):
        self.name = name
        self.v = None
        self.range_ = range_
        self._detect_type(value, range_ = range_,  is_path = is_path,  is_file=is_file)
        if check_range:
            self._check_parameter_range(range_)
        self.value = self.v #alias for value attribute

    def _detect_type(self,  value, range_ = None,  is_path = False,  is_file=False):
        '''
        Determine type of value based on the value itself, the range and the path switch.
        '''
        exceptionType = None
        if isinstance(value,  list):
            is_all_numeric = True
            is_all_string = True
            is_all_dict = True            
            for item in value:                
                if not isinstance(item,  str):
                    is_all_string = False
                if (not isinstance(item,  int)) and (not isinstance(item,  float)):
                    is_all_numeric = False
                if not isinstance(item,  dict):
                    is_all_dict = False            
            if is_all_numeric and ((not is_all_string) and (not is_all_dict)):
                self._type = 'numeric'
            elif ((not is_all_numeric) and (not is_all_dict)) and is_all_string:
                self._type = 'string'
            elif ((not is_all_numeric) and (not is_all_string)) and is_all_dict:
                self._type = 'dict'
            else:
                exceptionType = InvalidParameterValue
        elif isinstance(value,  numpy.ndarray):
            self._type = 'array'
        elif isinstance(value,  dict):
            self._type = 'dict'
        elif isinstance(value,  str):
            if is_path:
                self._type = 'path'
            elif is_file:
                self._type = 'file'
            else:
                self._type = 'string'
        elif isinstance(value,  bool):
            self._type = 'switch'
        elif isinstance(value,  int) or isinstance(value,  float):
            self._type = 'numeric'
        else:
            exceptionType = InvalidParameterValue
            
        if range_ != None:
            if len(range_) > 2 and not isinstance(value,  list):                
                self._type = 'enumerated'
        
        if exceptionType != None:
            raise exceptionType((value,self.name))
        else:
            self.v = value
            
    def _check_parameter_range(self,  range_):
        exceptionType = None
        if self._type == 'path':
            if not os.path.exists(self.v):
                raise IOError('Path '+self.v+' does not exist')
            elif range_ != None:
                raise RuntimeError('Invalid parameter range: {0}, value: {1}, name: {2}'.format(range_, self.v, self.name))
        elif self._type == 'file':
            if not os.path.isfile(self.v):
                raise IOError('Path to file '+self.v+' does not exist')
            elif range_ != None:
                raise RuntimeError('Invalid parameter range: {0}, value: {1}, name: {2}'.format(range_, self.v, self.name))
        elif self._type == 'dict':
            if range_ != None:
                raise RuntimeError('Invalid parameter range: {0}, value: {1}, name: {2}'.format(range_, self.v, self.name))
        elif self._type == 'string':
            if range_ != None:
                raise RuntimeError('Invalid parameter range: {0}, value: {1}, name: {2}'.format(range_, self.v, self.name))
        elif self._type == 'array':            
            if range_ != None:
                raise RuntimeError('Invalid parameter range: {0}, value: {1}, name: {2}'.format(range_, self.v, self.name))
        elif self._type == 'switch':
            if range_ != None:
                raise RuntimeError('Invalid parameter range: {0}, value: {1}, name: {2}'.format(range_, self.v, self.name))
        elif self._type == 'enumerated':
            in_range = False
            if not self.v in range_:
                print self.v
                raise OutOfRangeParameterValue
        elif self._type == 'numeric':            
            if range_ == None:
                raise RuntimeError('Invalid parameter range: {0}, value: {1}, name: {2}'.format(range_, self.v,self.name))
            elif len(range_) != 2:                
                raise RuntimeError('Invalid parameter range: {0}, value: {1}, name: {2}'.format(range_, self.v, self.name))
            elif not ((isinstance(range_[0],  int) or isinstance(range_[0],  float)) and (isinstance(range_[1],  int) or isinstance(range_[1],  float))) and (isinstance(self.v,  int) or isinstance(self.v,  float)):
                if not isinstance(self.v,  list):
                    raise RuntimeError('Invalid parameter range: {0}, value: {1}, name: {2}'.format(range_, self.v, self.name))
            elif isinstance(self.v,  list):                
                if len(range_[0]) != len(self.v) or len(range_[1]) != len(self.v):
                    raise RuntimeError('Invalid parameter range: {0}, value: {1}, name: {2}'.format(range_, self.v, self.name))
                for range_item in range_:
                    for range_item_item in range_item:
                        if (not isinstance(range_item_item,  int)) and (not isinstance(range_item_item,  float)):
                            raise RuntimeError('Invalid parameter range: {0}, value: {1}, name: {2}'.format(range_, self.v, self.name))
                for item in self.v:
                    if (not isinstance(range_item_item,  int)) and (not isinstance(range_item_item,  float)):
                        raise InvalidParameterValue
                #check if value is in the specified range. For every element in the data list there should be a pair of range values
                for i in range(len(range_[0])):
                    if not self.v[i] >= range_[0][i] and self.v[i] <= range_[1][i]:
                        raise OutOfRangeParameterValue
            else:
                if not(range_[0] <= self.v and range_[1] >= self.v):
                    raise OutOfRangeParameterValue('range {0}, value: {1}, name: {2}'.format(range_, self.v, self.name))
        else:
            raise RuntimeError('Invalid parameter range: {0}, value: {1}, name: {2}'.format(range_, self.v, self.name))
                

    def set(self,  new_value):
        self.v = new_value
        self._check_parameter_range(self.range_)
        self.value = self.v
            
class testParameter(unittest.TestCase):
    '''
    list of numeric - range check OK
    list of string - no range check OK
    list of dictionary - no range check, usage: store complex hardware configurations OK
    enumerated - range check OK
    switch OK
    path- validity check OK
    file - validity check OK
    numeric - range check OK
    array - numpy array, no range check OK
    '''    
        
    #Tests for constructor
    
    def test_01_valid_path_parameter(self):        
        if os.name == 'nt':
            value = 'c:\windows'
        elif os.name == 'posix':        
            value = '/home/'
        p = Parameter(value,  is_path = True)
        self.assertEqual((p._type,  p.v),  ('path', value))
        
    def test_02_invalid_path_parameter(self):
        value = '/home/unknown_user'
        self.assertRaises(IOError,  Parameter,  value,  is_path = True)
        
    def test_03_valid_file_parameter(self):
        if unittest_aggregator.TEST_valid_file==None:
            raise IOError('TEST_valid_file parameter incorrect')
        p = Parameter(unittest_aggregator.TEST_valid_file,  is_file = True)
        self.assertEqual((p._type,  p.v),  ('file', unittest_aggregator.TEST_valid_file))
        
    def test_04_invalid_file_parameter(self):
        self.assertRaises(IOError,  Parameter, unittest_aggregator.TEST_invalid_file,  is_file = True)
        
    def test_05_invalid_file_parameter(self):
        value = '/home/test.txt'
        self.assertRaises(IOError,  Parameter,  value,  is_file = True)
        
    def test_06_valid_string_parameter(self):
        value = 'some text'
        p = Parameter(value)
        self.assertEqual((p._type,  p.v),  ('string', value))
        
    def test_07_string_parameter_with_range(self):
        value = 'some text'
        range_ = [1, 20]
        self.assertRaises(RuntimeError,  Parameter,  value,  range_ = range_)
        
    def test_08_valid_switch_parameter(self):
        value = True
        p = Parameter(value)
        self.assertEqual((p._type,  p.v),  ('switch', value))
        
    def test_09_invalid_switch_parameter(self):
        value = True
        range_ = [1, 2]        
        self.assertRaises(RuntimeError,  Parameter,  value,  range_ = range_)        
        
    def test_10_valid_enumerated_parameter(self):
        value = 'a'
        range_ = ['a',  2,  3,  'b',  1.0]
        p = Parameter(value,  range_ = range_)
        self.assertEqual((p._type,  p.v),  ('enumerated', value))
        
    def test_11_enumerated_parameter_out_of_range(self):        
        value = 'x'
        range_ = ['a',  2,  3,  'b']        
        self.assertRaises(OutOfRangeParameterValue,  Parameter,  value,  range_ = range_)
        
    def test_12_enumerated_parameter_invalid_range(self):        
        value = 'x'
        range_ = 'a'        
        self.assertRaises(RuntimeError,  Parameter,  value,  range_ = range_)        
        
    def test_13_valid_numeric_parameter(self):
        value = 1
        range_ = [-1,  10.0]
        p = Parameter(value,  range_ = range_)
        self.assertEqual((p._type,  p.v),  ('numeric', value))
        
    def test_14_numeric_parameter_out_of_range(self):
        value = 100
        range_ = [-10.0,  10.0]        
        self.assertRaises(OutOfRangeParameterValue,  Parameter,  value,  range_ = range_)        

    def test_15_numeric_parameter_invalid_range_1(self):
        value = 10.0        
        self.assertRaises(RuntimeError,  Parameter,  value)
        
    def test_16_numeric_parameter_invalid_range_1(self):
        value = 10.0
        range_ = [10.0,  10.0]
        p = Parameter(value,  range_ = range_)
        self.assertEqual((p._type,  p.v),  ('numeric', value))
        
    def test_17_numeric_parameter_invalid_range_2(self):
        value = 1.0
        range_ = ['a',  10.0]
        self.assertRaises(RuntimeError,  Parameter,  value,  range_ = range_)
    
    def test_18_numeric_parameter_invalid_range_3(self):
        value = 1.0
        range_ = [0.0,  10.0,  20.0]
        self.assertRaises(OutOfRangeParameterValue,  Parameter,  value,  range_ = range_)
        
    def test_19_invalid_numeric_parameter_1(self):
        value = ['a',  1]
        range_ = [0.0,  10.0]
        self.assertRaises(InvalidParameterValue,  Parameter,  value,  range_ = range_)        
        
    def test_20_invalid_numeric_parameter_2(self):
        value = 'a'
        range_ = [0.0,  10.0]
        self.assertRaises(RuntimeError,  Parameter,  value,  range_ = range_)
        
    def test_21_numeric_list_parameter(self):
        value = [1, 2, 3]
        range_ = [[0, 0, 0],  [10, 10, 10]]
        p = Parameter(value, range_ = range_)
        self.assertEqual((p._type,  p.v),  ('numeric', value))

    def test_22_numeric_list_parameter_invalid_range1(self):
        value = [1, 2, 3]
        range_ = [[0, 0],  [10, 10, 10]]        
        self.assertRaises(RuntimeError,  Parameter,  value,  range_ = range_)
        
    def test_23_numeric_list_parameter_invalid_range2(self):
        value = [1, 2, 3]
        range_ = [[0, 0,  'a'],  [10, 10, 10]]
        self.assertRaises(RuntimeError,  Parameter,  value,  range_ = range_)
        
    def test_24_invalid_numeric_list_parameter_1(self):
        value = [1, 2]
        range_ = [[0, 0,  0],  [10, 10, 10]]
        self.assertRaises(RuntimeError,  Parameter,  value,  range_ = range_)
        
    def test_25_invalid_numeric_list_parameter_2(self):
        value = [1, 2,  'a']
        range_ = [[0, 0,  0],  [10, 10, 10]]
        self.assertRaises(InvalidParameterValue,  Parameter,  value,  range_ = range_)
        
    def test_26_numeric_list_out_of_range(self):
        value = [1, 2,  -2]
        range_ = [[0, 0,  0],  [10, 10, 10]]
        self.assertRaises(OutOfRangeParameterValue,  Parameter,  value,  range_ = range_)
        
    def test_27_string_list_parameter(self):
        value = ['value1', 'value2', 'value3']        
        p = Parameter(value)
        self.assertEqual((p._type,  p.v),  ('string', value))
        
    def test_28_string_list_parameter_with_range(self):
        value = ['value1', 'value2', 'value3']        
        range_ = [1, 2, 3]
        self.assertRaises(RuntimeError, Parameter,  value,  range_ = range_)
        
    def test_29_dict_parameter(self):
        value = {'a': 1,  'b':2}        
        p = Parameter(value)
        self.assertEqual((p._type,  p.v),  ('dict', value))
        
    def test_30_invalid_dict_parameter(self):
        value = {'a': 1,  'b':2}
        range_ = [1, 2]
        self.assertRaises(RuntimeError,  Parameter,  value,  range_ = range_)        
        
    def test_31_list_of_dict_parameter(self):
        value = [{'a': 1,  'b':2},  {'c': 1,  'b':3}]
        p = Parameter(value)
        self.assertEqual((p._type,  p.v),  ('dict', value))
    
    def test_32_array_parameter(self):
        value = numpy.array([1, 2, 3])
        p = Parameter(value)
        self.assertEqual((p._type,  p.v),  ('array', value))
        
    def test_33_array_parameter_with_range(self):
        value = numpy.array([1, 2, 3])
        range_ = [1, 2]        
        self.assertRaises(RuntimeError,  Parameter,  value,  range_ = range_)        

    #test set method    
    def test_34_set_valid_value(self):
        new_value = 0.5
        p = Parameter(1,  (-1,  2))
        p.set(new_value)
        self.assertEqual((p._type,  p.v),  ('numeric', new_value))
        
    def test_35_set_out_of_range_value(self):
        value = 1
        new_value = 5
        p = Parameter(value,  (-1,  2))        
        self.assertRaises(OutOfRangeParameterValue,  p.set,  new_value)        
        
    def test_36_set_invalid_type_value_1(self):
        value = 1
        new_value = [1, 2]
        p = Parameter(value,  (-1,  2))
        self.assertRaises(TypeError,  p.set,  new_value) 
        
    def test_37_set_invalid_type_value_2(self):        
        value = [1, 2]
        new_value = 1
        p = Parameter(value,  [[0, 0],  [5, 5]])
        self.assertRaises(RuntimeError,  p.set,  new_value) 
        
    def test_38_set_valid_value(self):
        if os.name == 'nt':
            value = 'c:\Program Files'
            new_value = 'c:/windows'
        elif os.name == 'posix':
            value = '/home'  
            new_value = '/var'
        
        p = Parameter(value, is_path = True)        
        p.set(new_value)         
        self.assertEqual((p._type,  p.v),  ('path', new_value))
        
    def test_39_set_valid_value(self):
        new_value = ['x',  'y',  'z']
        p = Parameter(['a', 'b',  'c'])
        p.set(new_value)         
        self.assertEqual((p._type,  p.v),  ('string', new_value))
        
    def test_40_set_valid_value(self):
        new_value = True
        p = Parameter(False)
        p.set(new_value)         
        self.assertEqual((p._type,  p.v),  ('switch', new_value))

if __name__ == "__main__":
    unittest.main()
