import unittest
import sys
import os
import datetime
import os.path
import zipfile
import tempfile

#Quickstart: test without hardware : python unit_test_runner.py test -h

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
#TODO: individual command line switches for testing hardware related modules: -daq, -stage, -filterwheel, -parallel, ....

#== Test control ==
#Parse command line arguments
run_mode = 'application'
if len(sys.argv) > 2:
    if sys.argv[1] == 'test':
        if sys.argv[2] == '-f':
            run_mode = 'full test'
        elif sys.argv[2] == '-h':
            run_mode = 'test without hardware'

TEST_daq = False
TEST_stage = False
for arg in sys.argv:
    if arg == '-daqmx':
        TEST_daq = True
    elif arg == '-stage':
        TEST_stage = True
                    
            
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
    TEST_reference_mat_file = 'm:\\Zoltan\\visexpman\\test_data\\line_scan_parameters.mat'
elif TEST_os == 'posix':
    TEST_reference_frames_folder = '/media/Common/visexpman_data/reference_frames'
    TEST_reference_mat_file = '/home/zoltan/mdrive/Zoltan/visexpman/test_data/line_scan_parameters.mat'
elif TEST_os == 'osx':
    TEST_reference_frames_folder = '/Users/rz/visexpman/data/test_data/reference_frames_osx'

#== Hardware config during test ==
TEST_filterwheel_enable  = True #If set to False, many tests fail.

if TEST_os == 'nt':
    TEST_com_port = 'COM4'
    TEST_working_folder = 'c:\\temp\\test'
    TEST_valid_file = 'c:\\windows\\win.ini'
    TEST_invalid_file = 'c:\\windows'
    TEST_stage_com_port = 'COM1'
elif TEST_os == 'posix':
    TEST_com_port = '/dev/ttyUSB0'
    TEST_working_folder = '/media/Common/visexpman_data/test'
    TEST_valid_file = '/home/zoltan/Downloads/qtgl.py'
    TEST_invalid_file = '/home'
    TEST_stage_com_port = ''
elif TEST_os == 'osx':
    TEST_com_port = ''
    TEST_working_folder = '/Users/rz/visexpman/data/test'
    TEST_valid_file = '/Users/rz/test_stimulus.py'
    TEST_invalid_file = '/Users'
    TEST_stage_com_port = ''
    
TEST_daq_device = 'Dev1'

def generate_filename(path):
    '''
    Inserts index into filename resulting unique name.
    '''    
    index = 0
    number_of_digits = 5
    while True:
        testable_path = path.replace('.',  '_%5i.'%index).replace(' ', '0')
        if not os.path.isfile(testable_path):
            break
        index = index + 1
        if index >= 10 ** number_of_digits:
            raise RuntimeError('Filename cannot be generated')
    return testable_path

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
               {'test_class_path' : 'visexpman.engine.hardware_interface.instrument.TestInstruments',
               'enable' : TEST_hardware_test}, #Shutter tests are not complete
               {'test_class_path' : 'visexpman.engine.hardware_interface.daq_instrument.TestDaqInstruments',
               'enable' : TEST_daq},
               {'test_class_path' : 'visexpman.engine.hardware_interface.network_interface.TestNetworkInterface',
               'enable' : True},
               {'test_class_path' : 'visexpman.engine.visual_stimulation.stimulation_control.testExternalHardware',
               'enable' : TEST_hardware_test},
               {'test_class_path' : 'visexpman.engine.visual_stimulation.stimulation_control.testDataHandler',
               'enable' : True},
               {'test_class_path' : 'visexpman.engine.hardware_interface.motor_control.TestAllegraStage',
               'enable' : TEST_stage},
               {'test_class_path' : 'visexpman.engine.generic.log.TestLog',
               'enable' : True},
               {'test_class_path' : 'visexpman.engine.hardware_interface.mes_interface.TestMesInterface',
               'enable' : True},
               {'test_class_path' : 'visexpA.engine.datahandlers.matlabfile.TestMatData',
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
        self.test_log = tempfile.mktemp()        
        f = open(self.test_log,  'w')
        test_suite = unittest.TestSuite()
        #Collect test classes, get test methods from them and add methods to test suite.
        for test_config in self.test_configs:
            if test_config['enable']:
                test_class = self.reference_to_test_class(test_config['test_class_path'])
                test_methods = self.fetch_test_methods(test_class)
                for test_method in test_methods:
                    test_suite.addTest(test_class(test_method))
        #Run tests
        unittest.TextTestRunner(f, verbosity=2).run(test_suite)
        #Save tested source files        
        f.close()
        f = open(self.test_log)
        print f.read()
        f.close()
        
        self.save_source_and_results()
        print str(datetime.datetime.now())
        
    def save_source_and_results(self):
        test_EXPERIMENT_DATA_PATH = generate_filename(os.path.join(TEST_working_folder, 'test_archive.zip'))
        package_path = os.path.split(os.path.split(os.path.split(os.getcwd())[0])[0])[0]        
        #generate list of archivable files and write them to zipfile
        #TODO: include visexpa, 
        source_zip = zipfile.ZipFile(test_EXPERIMENT_DATA_PATH, "w")
        for (path, dirs, files) in os.walk(package_path):
            for file in files:                
                if file[-3:] == '.py':
                    file_path = os.path.join(path,  file)
                    source_zip.write(file_path,  file_path.replace(package_path,  ''))
        source_zip.write(self.test_log,  'test_log.txt')        
        source_zip.close()
        
if __name__ == "__main__":
    utr = unitTestRunner()
    utr.run()
    
