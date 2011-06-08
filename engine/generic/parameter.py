import os.path
import numpy
import unittest

class InvalidParameterValue(Exception):
    pass
    
class OutOfRangeParameterValue(Exception):
    pass
    
class InvalidParameterRange(Exception):
    pass


class Parameter(object):
    '''
    Parameter class shall determine the type of parameter automatically. Then the provided range shall be checked. At certain types instead of range, other checking algorithms shall be run.
    Supported types:
    - path
    - string
    - enumerated
    - numeric
    - switch (boolean)
        
    Attributes:
    - value: its value is None if _status is False    
    - range_    
    
    Methods:
    - set    
    ''' 
    
    def __init__(self,  value,  range_ = None,  is_path = False):
        self.v = None
        self.range_ = range_
        self._detect_type(value, range_ = range_,  is_path = is_path)
        self._check_parameter_range(range_)

    def _detect_type(self,  value, range_ = None,  is_path = False):
        '''
        Determine type of value based on the value itself, the range and the path switch.
        The following exceptions are thrown:
        InvalidParameterRange: invalid parameter range is provided
        OutOfRangeParameterValue: value is not within the range
        InvalidParameterValue : value is not valid        
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
            raise exceptionType(value)
        else:
            self.v = value
            
    def _check_parameter_range(self,  range_):
        exceptionType = None        
        if self._type == 'path':
            if not os.path.exists(self.v):
                exceptionType = IOError
            elif range_ != None:
                exceptionType = InvalidParameterRange
        elif self._type == 'dict':
            if range_ != None:
                exceptionType = InvalidParameterRange
        elif self._type == 'string':
            if range_ != None:
                exceptionType = InvalidParameterRange
        elif self._type == 'array':
            #TODO: untested
            if range_ != None:
                exceptionType = InvalidParameterRange
        elif self._type == 'switch':
            if range_ != None:
                exceptionType = InvalidParameterRange
        elif self._type == 'enumerated':
            in_range = False
            for range_item in range_:
                if self.v == range_item:
                    in_range = True
                    break
            if not in_range:
                exceptionType = OutOfRangeParameterValue
        elif self._type == 'numeric':            
            if range_ == None:                
                exceptionType = InvalidParameterRange
            elif len(range_) != 2:                
                exceptionType = InvalidParameterRange
            elif not ((isinstance(range_[0],  int) or isinstance(range_[0],  float)) and (isinstance(range_[1],  int) or isinstance(range_[1],  float))) and (isinstance(self.v,  int) or isinstance(self.v,  float)):
                if not isinstance(self.v,  list):
                    exceptionType = InvalidParameterRange
            elif isinstance(self.v,  list):                
                if len(range_[0]) != len(self.v) or len(range_[1]) != len(self.v):
                    exceptionType = InvalidParameterRange
                for range_item in range_:
                    for range_item_item in range_item:
                        if (not isinstance(range_item_item,  int)) and (not isinstance(range_item_item,  float)):
                            exceptionType = InvalidParameterRange                            
                for item in self.v:
                    if (not isinstance(range_item_item,  int)) and (not isinstance(range_item_item,  float)):
                        exceptionType = InvalidParameterValue
                        
                if exceptionType == None:
                    for i in range(len(range_[0])):
                        if not self.v[i] >= range_[0][i] and self.v[i] <= range_[1][i]:
                            exceptionType = OutOfRangeParameterValue
                            break
                
            else:
                if not(range_[0] <= self.v and range_[1] >= self.v):
                    exceptionType = OutOfRangeParameterValue
        else:
            exceptionType = InvalidParameterRange
                
        if exceptionType != None:            
            raise exceptionType(self.v)

    def set(self,  new_value):
        self.v = new_value
        self._check_parameter_range(self.range_)        
            
class testParameter(unittest.TestCase):
    
    #Tests for constructor
    
    def test_01_valid_path_parameter(self):
        value = '/home/'
        p = Parameter(value,  is_path = True)
        self.assertEqual((p._type,  p.v),  ('path', value))
        
    def test_02_invalid_path_parameter(self):
        value = '/home/unknown_user'
        self.assertRaises(InvalidParameterValue,  Parameter,  value,  is_path = True)
        
    def test_03_valid_string_parameter(self):
        value = 'some text'
        p = Parameter(value)
        self.assertEqual((p._type,  p.v),  ('string', value))
        
    def test_04_string_parameter_with_range(self):
        value = 'some text'
        range_ = [1, 20]
        self.assertRaises(InvalidParameterRange,  Parameter,  value,  range_ = range_)
        
    def test_05_valid_switch_parameter(self):
        value = True
        p = Parameter(value)
        self.assertEqual((p._type,  p.v),  ('switch', value))
        
    def test_06_invalid_switch_parameter(self):
        value = True
        range_ = [1, 2]        
        self.assertRaises(InvalidParameterRange,  Parameter,  value,  range_ = range_)        
        
    def test_07_valid_enumerated_parameter(self):
        value = 'a'
        range_ = ['a',  2,  3,  'b',  1.0]
        p = Parameter(value,  range_ = range_)
        self.assertEqual((p._type,  p.v),  ('enumerated', value))
        
    def test_08_enumerated_parameter_out_of_range(self):        
        value = 'x'
        range_ = ['a',  2,  3,  'b']        
        self.assertRaises(OutOfRangeParameterValue,  Parameter,  value,  range_ = range_)
        
    def test_09_enumerated_parameter_invalid_range(self):        
        value = 'x'
        range_ = 'a'        
        self.assertRaises(InvalidParameterRange,  Parameter,  value,  range_ = range_)        
        
    def test_10_valid_numeric_parameter(self):
        value = 1
        range_ = [-1,  10.0]
        p = Parameter(value,  range_ = range_)
        self.assertEqual((p._type,  p.v),  ('numeric', value))
        
    def test_11_numeric_parameter_out_of_range(self):
        value = 100
        range_ = [-10.0,  10.0]        
        self.assertRaises(OutOfRangeParameterValue,  Parameter,  value,  range_ = range_)        

    def test_12_numeric_parameter_invalid_range_1(self):
        value = 10.0        
        self.assertRaises(InvalidParameterRange,  Parameter,  value)
        
    def test_13_numeric_parameter_invalid_range_1(self):
        value = 10.0
        range_ = [10.0,  10.0]
        p = Parameter(value,  range_ = range_)
        self.assertEqual((p._type,  p.v),  ('numeric', value))
        
    def test_14_numeric_parameter_invalid_range_2(self):
        value = 1.0
        range_ = ['a',  10.0]
        self.assertRaises(InvalidParameterRange,  Parameter,  value,  range_ = range_)
    
    def test_15_numeric_parameter_invalid_range_3(self):
        value = 1.0
        range_ = [0.0,  10.0,  20.0]
        self.assertRaises(OutOfRangeParameterValue,  Parameter,  value,  range_ = range_)
        
    def test_16_invalid_numeric_parameter_1(self):
        value = ['a',  1]
        range_ = [0.0,  10.0]
        self.assertRaises(InvalidParameterValue,  Parameter,  value,  range_ = range_)        
        
    def test_17_invalid_numeric_parameter_2(self):
        value = 'a'
        range_ = [0.0,  10.0]
        self.assertRaises(InvalidParameterRange,  Parameter,  value,  range_ = range_)
        
    def test_18_numeric_list_parameter(self):
        value = [1, 2, 3]
        range_ = [[0, 0, 0],  [10, 10, 10]]
        p = Parameter(value, range_ = range_)
        self.assertEqual((p._type,  p.v),  ('numeric', value))

    def test_19_numeric_list_parameter_invalid_range1(self):
        value = [1, 2, 3]
        range_ = [[0, 0],  [10, 10, 10]]        
        self.assertRaises(InvalidParameterRange,  Parameter,  value,  range_ = range_)
        
    def test_20_numeric_list_parameter_invalid_range2(self):
        value = [1, 2, 3]
        range_ = [[0, 0,  'a'],  [10, 10, 10]]
        self.assertRaises(InvalidParameterRange,  Parameter,  value,  range_ = range_)
        
    def test_21_invalid_numeric_list_parameter_1(self):
        value = [1, 2]
        range_ = [[0, 0,  0],  [10, 10, 10]]
        self.assertRaises(InvalidParameterRange,  Parameter,  value,  range_ = range_)
        
    def test_22_invalid_numeric_list_parameter_2(self):
        value = [1, 2,  'a']
        range_ = [[0, 0,  0],  [10, 10, 10]]
        self.assertRaises(InvalidParameterValue,  Parameter,  value,  range_ = range_)
        
    def test_23_numeric_list_out_of_range(self):
        value = [1, 2,  -2]
        range_ = [[0, 0,  0],  [10, 10, 10]]
        self.assertRaises(OutOfRangeParameterValue,  Parameter,  value,  range_ = range_)
        
    def test_24_string_list_parameter(self):
        value = ['value1', 'value2', 'value3']        
        p = Parameter(value)
        self.assertEqual((p._type,  p.v),  ('string', value))
        
    def test_25_string_list_parameter(self):
        value = ['value1', 'value2', 'value3']        
        range_ = [1, 2, 3]
        self.assertRaises(InvalidParameterRange,  Parameter,  value,  range_ = range_)
        
    def test_26_dict_parameter(self):
        value = {'a': 1,  'b':2}        
        p = Parameter(value)
        self.assertEqual((p._type,  p.v),  ('dict', value))
        
    def test_27_ivnalid_dict_parameter(self):
        value = {'a': 1,  'b':2}
        range_ = [1, 2]
        self.assertRaises(InvalidParameterRange,  Parameter,  value,  range_ = range_)        
        
    def test_28_list_of_dict_parameter(self):
        value = [{'a': 1,  'b':2},  {'c': 1,  'b':3}]
        p = Parameter(value)
        self.assertEqual((p._type,  p.v),  ('dict', value))

    #test set method    
    def test_29_set_valid_value(self):
        new_value = 0.5
        p = Parameter(1,  (-1,  2))
        p.set(new_value)
        self.assertEqual((p._type,  p.v),  ('numeric', new_value))
        
    def test_30_set_out_of_range_value(self):
        value = 1
        new_value = 5
        p = Parameter(value,  (-1,  2))        
        self.assertRaises(OutOfRangeParameterValue,  p.set,  new_value)        
        
    def test_31_set_invalid_type_value_1(self):
        value = 1
        new_value = [1, 2]
        p = Parameter(value,  (-1,  2))
        self.assertRaises(TypeError,  p.set,  new_value) 
        
    def test_32_set_invalid_type_value_2(self):        
        value = [1, 2]
        new_value = 1
        p = Parameter(value,  [[0, 0],  [5, 5]])
        self.assertRaises(InvalidParameterRange,  p.set,  new_value) 
        
    def test_33_set_valid_value(self):
        new_value = '/var'
        p = Parameter('/home', is_path = True)        
        p.set(new_value)         
        self.assertEqual((p._type,  p.v),  ('path', new_value))
        
    def test_34_set_valid_value(self):
        new_value = ['x',  'y',  'z']
        p = Parameter(['a', 'b',  'c'])
        p.set(new_value)         
        self.assertEqual((p._type,  p.v),  ('string', new_value))
        
    def test_35_set_valid_value(self):
        new_value = True
        p = Parameter(False)
        p.set(new_value)         
        self.assertEqual((p._type,  p.v),  ('switch', new_value))


if __name__ == "__main__":
    unittest.main()

    
