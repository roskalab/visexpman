import unittest
import sys
import visexpman

class unitTestRunner():
    '''
    This class is responsible for maintaining a list of implemented and ready to run unit tests. Test methods are aggregated and executed with unittest's TextTestRunner class.
    '''
    def __init__(self):        
        self.test_configs = [
               {'test_class_path' : 'visexpman.engine.visexp_runner.testVisexpRunner',
               'enable' : True},
               {'test_class_path' : 'visexpman.engine.visexp_runner.testFindoutConfig',
               'enable' : True}, 
               {'test_class_path' : 'visexpman.engine.generic.configuration.testConfiguration',
               'enable' : True},
               {'test_class_path' : 'visexpman.engine.generic.parameter.testParameter',
               'enable' : True},
               {'test_class_path' : 'visexpman.engine.generic.geometry.testGeometry',
               'enable' : not True}, #Not part of visexpman application
               {'test_class_path' : 'visexpman.engine.visual_stimulation.configuration.testApplicationConfiguration',
               'enable' : True},
               {'test_class_path' : 'visexpman.engine.hardware_interface.instrument.testInstruments',
               'enable' : visexpman.hardware_test}, #Shutter tests are not complete
               {'test_class_path' : 'visexpman.engine.hardware_interface.network_interface.testNetworkInterface',
               'enable' : True},
               {'test_class_path' : 'visexpman.engine.visual_stimulation.stimulation_control.testExternalHardware',
               'enable' : visexpman.hardware_test},
               {'test_class_path' : 'visexpman.engine.visual_stimulation.stimulation_control.testDataHandler',
               'enable' : True},
               ]

    def fetch_test_methods(self, test_class):
        '''
            Fetch test method names from a test class
        '''
        test_methods = []
        for method in dir(test_class):
            if method.find('test') != -1:
                test_methods.append(method)
        return test_methods

    def reference_to_test_class(self, test_class_path):
        '''
        Returns a reference to the test class given in string format
        '''
        test_class_name = test_class_path.split('.')[-1]
        module_path = test_class_path.replace('.' + test_class_name, '')        
        __import__(module_path)
        return getattr(sys.modules[module_path], test_class_name)
    
    def run(self):
        '''
        Aggregates and runs tests.
        '''        
        test_suite = unittest.TestSuite()
        #Collect test classes, get test methods from them and add methods to test suite.
        for test_config in self.test_configs:
            if test_config['enable']:
                test_class = self.reference_to_test_class(test_config['test_class_path'])
                test_methods = self.fetch_test_methods(test_class)
                for test_method in test_methods:
                    test_suite.addTest(test_class(test_method))
        #Run tests
        unittest.TextTestRunner(verbosity=2).run(test_suite)        

if __name__ == "__main__":
    utr = unitTestRunner()
    utr.run()
