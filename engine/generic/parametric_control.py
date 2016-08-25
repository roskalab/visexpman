from math import *

class ParametricControl():
    """
    Each instance of this class can handle the parametric calculation of one variable. The new value of 
    the variable after each call of update function is calculated by using the provided formula.
    
    The formula can call functions from math module. The formula may contain parameters like 'prev'
    which is the previous value of the parametrically controlled variable. Additionally a parameters can be
    referenced that are placed in the 'parameters' list.
    
    Beside updating the variable, the update method can set the parameters and the formula. If these are
    not updated, the previously set values are used.
    
    Example:
    TBD
    """
    def __init__(self,  value = None,  time_tick = 0.0):
        if value != None:
            self.value = value
        self.formula = ''
        self.time_tick = time_tick            
        
    def update(self, value = None,  parameters = None,  formula = '' ,  time_tick = 0.0):
        """
        formula: valid variables: p[x] - parameters, prev - previous value, functions from math module, t - time elapsed since start of stimulation
        """        
        if value != None:
            try:
                self.value = float(value)
            except ValueError:
                self.value = 0.0
        if  parameters != None:
            self.parameters = parameters
            
        if len(formula) > 0:
            self.formula = formula        
        
        if self.value != None and len(self.formula) > 0:                        
            prev = self.value            
            p = self.parameters
            t = time_tick - self.time_tick
            try:
                new_value = eval(self.formula)
                self.value = new_value
            except (NameError,  ValueError,  IndexError,  TypeError):
                new_value = self.value
        else:            
            new_value = self.value        

        return new_value
    
def test():
    """
    Test cases:
    1. Adjust parameters, value and formula at first call
    2. Change parameters, value and formula at each call
    3. Use invalid symbol in formula
    4. Overindex parameter list
    5. Feed invalid data format into parameter list
    6. Feed invalid data format into value
    """
    test_configurations = [
                           {
                           'name':  'At first call adjust parameters, value and formula', 
                           'iterations' : 4, 
                           'update': [True,  False,  False,  False], 
                           'values' : [0.0], 
                           'parameters' : [[1.0,  -1.0]], 
                           'formulas' : ['prev + 1 + p[0] - abs(p[1])'] , 
                           'expected results':  [1.0,  2.0,  3.0,  4.0]
                           }, 
                             {
                           'name':  'Change parameters, value and formula at each call', 
                           'iterations' : 3, 
                           'update': [True,  True,  True], 
                           'values' : [1,  2,  3], 
                           'parameters' : [[1.0],  [8.0,  2.0],  [-1.0]], 
                           'formulas' : ['prev + 1 + p[0]',  'prev + 1 + sqrt(p[0] * p[1])',  'prev - p[0] * 2'] , 
                           'expected results':  [3.0,  7.0,  5.0]
                           }, 
                        {
                           'name':  'Invalid symbol in formula', 
                           'iterations' : 1, 
                           'update': [True], 
                           'values' : [1], 
                           'parameters' : [[1.0]], 
                           'formulas' : ['prev + invalid'], 
                           'expected results':  [1.0]
                           }, 
                        {
                           'name':  'Overindex parameter list', 
                           'iterations' : 1, 
                           'update': [True], 
                           'values' : [1], 
                           'parameters' : [[1.0]], 
                           'formulas' : ['prev + p[1]'], 
                           'expected results':  [1.0]
                           }, 
                        {
                           'name':  'Feed invalid data format into parameter list', 
                           'iterations' : 1, 
                           'update': [True], 
                           'values' : [1], 
                           'parameters' : [['o']], 
                           'formulas' : ['prev + p[0]'], 
                           'expected results':  [1.0]
                           }, 
                        {
                           'name':  'Feed invalid data format into value', 
                           'iterations' : 1, 
                           'update': [True], 
                           'values' : ['df'], 
                           'parameters' : [[1.0]], 
                           'formulas' : ['prev + p[0]'], 
                           'expected results':  [1.0]
                           },                           
                           
                           
                           
                           
                                        ]
                                        
    for test_configuration in test_configurations:
        test_case(test_configuration)
    
    
def test_case(configuration):        
    pc = ParametricControl()    
    result = True
    for i in range(configuration['iterations']): 
        if configuration['update'] [i]== True:
            res = pc.update(value = configuration['values'][i],  parameters = configuration['parameters'][i],  formula = configuration['formulas'][i])
        else:
            res = pc.update()        
        
        if res != configuration['expected results'][i]:
            result = False
    print 'test case: ' + configuration['name'] + ': ' + str(result)
    return result
    
if __name__ == "__main__":
    test()

#    t = time()
#    pc = ParametricControl()
#    pars = [1.0, 2.0]
#    formula = 'prev+2.0 + p[1]'
#    
#    print pc.update(value = 1.0,  parameters = pars,  formula = formula)
#    
#    
