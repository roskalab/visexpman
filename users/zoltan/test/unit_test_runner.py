import unittest
import sys
import os

#run modes:
# - application
# - full test
# - full test, filterhweel disabled
# - test without hardware

#command line parameters:
#1. test - mandatory
#2. mandatory
#   -h - skip hardware related tests
#    -f run all tests
#TODO# 3.optional: -d - delete all files generated during test


#== Test control ==
#Parse command line arguments
run_mode = 'application'
if len(sys.argv) > 2:
    if sys.argv[1] == 'test':
        if sys.argv[2] == '-f':
            run_mode = 'full test'
        elif sys.argv[2] == '-h':
            run_mode = 'test without hardware'

TEST_os = os.name
if hasattr(os,  'uname'):
    if os.uname()[0] != 'Linux':
        TEST_os = 'osx'

#== Test parameters ==
TEST_test = (run_mode != 'application')

#For running automated tests, network operations have to be disabled for visexp_runner
TEST_enable_network = (run_mode == 'application')

#Set this to False if any of the controleld hardware (parallel port, filterwheel, etc) is not available
TEST_hardware_test = (run_mode == 'full test')

#The maximal number of pixels that can differ from the reference frame at the testing the rendering of visual stimulation patterns
TEST_pixel_difference_threshold = 50.0

if TEST_os == 'nt':
    TEST_reference_frames_folder = 'm:\\Zoltan\\visexpman\\test_data\\reference_frames_win'
elif TEST_os == 'posix':
    TEST_reference_frames_folder = '/media/Common/visexpman_data/reference_frames'
elif TEST_os == 'osx':
    TEST_reference_frames_folder = '/Users/rz/visexpman/data/test_data/reference_frames_osx'

#== Hardware config during test ==
TEST_filterwheel_enable  = True #If set to False, many tests fail.

if TEST_os == 'nt':
    TEST_com_port = 'COM4'
    TEST_working_folder = 'c:\\_del\\test'
    TEST_valid_file = 'c:\\windows\\win.ini'
    TEST_invalid_file = 'c:\\windows'
elif TEST_os == 'posix':
    TEST_com_port = '/dev/ttyUSB0'
    TEST_working_folder = '/media/Common/visexpman_data/test'
    TEST_valid_file = '/home/zoltan/Downloads/qtgl.py'
    TEST_invalid_file = '/home'
elif TEST_os == 'osx':
    TEST_com_port = ''
    TEST_working_folder = '/Users/rz/visexpman/data/test'
    TEST_valid_file = '/Users/rz/test_stimulus.py'
    TEST_invalid_file = '/Users'
    
TEST_daq = (os.name == 'nt') and TEST_hardware_test
TEST_daq_device = 'Dev1'

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
               {'test_class_path' : 'visexpman.engine.generic.utils.TestUtils',
               'enable' : True},
               {'test_class_path' : 'visexpman.engine.generic.geometry.testGeometry',
               'enable' : not True}, #Not part of visexpman application
               {'test_class_path' : 'visexpman.engine.visual_stimulation.configuration.testApplicationConfiguration',
               'enable' : True},
               {'test_class_path' : 'visexpman.engine.hardware_interface.instrument.testInstruments',
               'enable' : TEST_hardware_test}, #Shutter tests are not complete
               {'test_class_path' : 'visexpman.engine.hardware_interface.daq_instrument.TestDaqInstruments',
               'enable' : TEST_daq},
               {'test_class_path' : 'visexpman.engine.hardware_interface.network_interface.testNetworkInterface',
               'enable' : True},
               {'test_class_path' : 'visexpman.engine.visual_stimulation.stimulation_control.testExternalHardware',
               'enable' : TEST_hardware_test},
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
