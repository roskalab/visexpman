import unittest
import sys
import os
import datetime
import os.path
import zipfile
import tempfile
import time
import shutil
import argparse
import platform
import getpass
import psutil

TEST_test = 'unittest_aggregator' in sys.argv[0] or 'code_tester' in sys.argv[0]

if TEST_test:
    global argparser
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--no_user_action', help='Tests that require user action are not executed.', action='store_true')
    argparser.add_argument('--daq', help='Tests using DAQmx are enabled, assumes that daq device is connected and the operating system is windows', action='store_true')
    argparser.add_argument('--stage', help='Stage tests enabled, stage controller has to be connected via serial port', action='store_true')
    argparser.add_argument('--goniometer', help='Goniometer tests enabled, Motorized goniometer has to be connected via serial port', action='store_true')
    argparser.add_argument('--remote_focus', help='Remote focus tests enabled, Remote focus controller has to be connected via serial port', action='store_true')
    argparser.add_argument('--mes', help='Tests using MES are enabled. MES computer shall be available.', action='store_true')
    argparser.add_argument('--uled', help='Tests expecting microled array are enabled.', action='store_true')
    argparser.add_argument('--pp', help='Tests using parallel port are enabled. Parallel port driver has to be loaded and user shall have root access if tests are run on linux', action='store_true')
    argparser.add_argument('--fw', help='Filterwheel tests enabled.', action='store_true')
    argparser.add_argument('--stim', help='Enable running stimulation pattern tests. Reference frames shall be available', action='store_true')
    argparser.add_argument('--short', help='Run shorter tests.', action='store_true')
    argparser.add_argument('--frame_rate', help='Consider frame rate at visexp_runner tests.', action='store_true')
    argparser.add_argument('--delete_files', help='Delete files generated during test.', action='store_true')
    argparser.add_argument('--repeat', help='Repeat the unit tests.', default=1)

    TEST_no_user_action = getattr(argparser.parse_args(), 'no_user_action')
    TEST_daq = getattr(argparser.parse_args(), 'daq')
    TEST_stage = getattr(argparser.parse_args(), 'stage')
    TEST_goniometer = getattr(argparser.parse_args(), 'goniometer')
    TEST_remote_focus = getattr(argparser.parse_args(), 'remote_focus')
    TEST_mes = getattr(argparser.parse_args(), 'mes')
    TEST_uled = getattr(argparser.parse_args(), 'uled')
    TEST_parallel_port = getattr(argparser.parse_args(), 'pp')
    TEST_filterwheel = getattr(argparser.parse_args(), 'fw')
    TEST_stim = getattr(argparser.parse_args(), 'stim')
    TEST_consider_frame_rate = getattr(argparser.parse_args(), 'frame_rate')
    TEST_short = getattr(argparser.parse_args(), 'short')
    TEST_delete_files = getattr(argparser.parse_args(), 'delete_files')
    TEST_repeat = int(getattr(argparser.parse_args(), 'repeat'))
else:
    TEST_no_user_action = False
    TEST_daq = False
    TEST_stage = False
    TEST_goniometer = False
    TEST_remote_focus = False
    TEST_mes = False
    TEST_uled = False
    TEST_parallel_port = False
    TEST_filterwheel = False
    TEST_stim = False
    TEST_consider_frame_rate = False
    TEST_short = False
    TEST_delete_files = False
    TEST_repeat = 1

TEST_os = platform.system()
TEST_machine_info = platform.uname()
TEST_machine_name = TEST_machine_info[1]
TEST_osuser = getpass.getuser()
if TEST_os == 'Darwin':
    TEST_os = 'OSX'
################# Test parameters ####################
#The maximal number of pixels that can differ from the reference frame at the testing the rendering of visual stimulation patterns
#TEST_pixel_difference_threshold = 50.0

TEST_working_folder = ['/tmp/wf', '/mnt/rzws/work-rzws', 'r:\\work-rznb-win7', 'c:\\temp']
TEST_results_folder = ['/mnt/rzws/test_results', 'r:\\test_results', '/tmp', 'c:\\temp']
TEST_test_data_folder = ['/mnt/rzws/test_data', 'r:\\test_data', '/home/rz/codes/data/test_data']

#if TEST_os == 'nt':
#    TEST_test_data_folder = 'u:\\software_test\\ref_data'
#    TEST_working_folder =  'u:\\software_test\\working'
#    
#    TEST_reference_frames_folder = 'v:\\data\\test\\frames_win'
#    TEST_reference_mat_file = 'v:\\data\\test\\mes\\line_scan_parameters.mat'
#    TEST_reference_z_stack_file = 'v:\\data\\test\\mes\\z_stack_ref.mat'
#    TEST_reference_data_folder = 'v:\\data\\test'
#    TEST_com_port = 'COM4'
#    
#    TEST_stage_com_port = 'COM1'
#    TEST_goniometer_com_port = 'COM9'
#elif TEST_os == 'posix':
    
#    root = '/mnt/rznb/'#Support running unittests on notebook
#    if not os.path.exists(root):
#        root = '/mnt/databig/'
#    TEST_test_data_folder = os.path.join(root, 'software_test/ref_data')
#    TEST_working_folder = os.path.join(root, 'software_test/working')
#    
#    TEST_reference_frames_folder = '/home/zoltan/visexp/data/test/frames'
#    TEST_reference_mat_file = '/home/zoltan/visexp/data/test/mes/line_scan_parameters.mat'
#    TEST_reference_z_stack_file = '/home/zoltan/visexp/data/test/mes/z_stack_ref.mat'
#    TEST_reference_data_folder = '/mnt/rzws/data/test'
#    TEST_com_port = '/dev/ttyUSB0'
#    
#    
#    TEST_stage_com_port = ''
#    TEST_goniometer_com_port = ''
#elif TEST_os == 'osx':
#    TEST_reference_frames_folder = '/Users/rz/visexpman/data/test_data/reference_frames_osx'
#    TEST_com_port = ''
#    TEST_working_folder = '/Users/rz/visexpman/data/test'
#    TEST_stage_com_port = ''
#    TEST_goniometer_com_port = ''


#== Hardware config during test ==
TEST_daq_device = 'Dev1'

################# Enable unit tests  ####################

TEST_unittests = [
    'visexpman.engine.visexp_gui.testVisionExperimentGui',
    'visexpman.engine.vision_experiment.experiment_control.TestCaImaging', 
    'visexpman.engine.visexp_app.TestStim',    
    'visexpman.engine.vision_experiment.experiment.testExperimentHelpers', 
    'visexpman.engine.vision_experiment.experiment_data.TestExperimentData', 
    'visexpman.engine.vision_experiment.screen.TestCaImagingScreen',     
    'visexpman.engine.vision_experiment.stimulation_library.TestStimulationPatterns', 
    'visexpman.engine.TestApplicationInit',
    'visexpman.engine.generic.parameter.testParameter',
    'visexpman.engine.generic.fileop.TestFileops',
    'visexpman.engine.generic.utils.TestUtils',
    'visexpman.engine.generic.log.TestLog',
    'visexpman.engine.generic.signal.TestSignal',
    'visexpman.engine.generic.colors.TestColorUtils',
    'visexpman.engine.generic.videofile.TestVideoFile',
    'visexpman.engine.generic.geometry.TestGeometry',
    'visexpman.engine.hardware_interface.queued_socket.TestQueuedSocket',
    'visexpman.engine.hardware_interface.instrument.TestInstrument',
    'visexpman.engine.hardware_interface.daq_instrument.TestAnalogIOProcess',
    'visexpman.engine.hardware_interface.scanner_control.TestScannerControl',
                ]
                
TEST_priority_unittests = [
                    'testVisionExperimentGui.test_01_select_stimfile', 
                       ]

TEST_single_unittest = ''#TestStim.test_07_execute_experiment'#TestCaImagingScreen.test_01_image_display'

def get_python_processes():
    pids = []
    for pid in psutil.get_pid_list():
        try:
            p = psutil.Process(pid)
            if 'python' in p.name:
                pids.append(pid)
        except:
            pass
    return pids

def kill_python_processes(dont_kill_pids):
    pids = get_python_processes()
    for pid in pids:
        if pid not in dont_kill_pids:
            p = psutil.Process(pid)
            name = p.name
            p.kill()
            print '{0}/{1} process killed'.format(name, pid)
            
def generate_filename(path):
    '''
    Inserts index into filename resulting unique name.
    '''    
    index = 0
    number_of_digits = 5
    while True:
        testable_path = path.replace('.',  '_{0:0=5}.'.format(index))
        if not os.path.isfile(testable_path):
            break
        index = index + 1
        if index >= 10 ** number_of_digits:
            raise RuntimeError('Filename cannot be generated')
    return testable_path
    
def select_path_exists(paths, dirs = True):
    for path in paths:
        if os.path.exists(path) and ((os.path.isdir(path) and dirs) or (not os.path.isdir(path) and not dirs)):
            return path
            
TEST_valid_file = select_path_exists(['/mnt/rzws/codes/visexpman/__init__.py', '/etc/fstab', 'c:\\temp\\dummy.txt', 'r:\\codes\\visexpman\\__init__.py', 'x:\\src\\visexpman\\__init__.py', 'v:\\code\\visexpman\\__init__.py', 'c:\\Users\\rz\\codes\\__init__.py', 'c:\\WINDOWS\\TASKMAN.exe'],dirs=False)
if TEST_valid_file is None:
    raise IOError('TEST_valid_file parameter incorrect')
TEST_invalid_file = '/home'
    
def prepare_test_data(modulename, working_folder=None, clean_working_dir = True, copy_only_first_file = False):
    ref_folder = os.path.join(select_path_exists(TEST_test_data_folder), modulename)
    if working_folder is None:
        working_folder = select_path_exists(TEST_working_folder)
    elif not os.path.exists(working_folder):
        os.mkdir(working_folder)
    print 'preparing test data for {0}'.format(modulename)
    if clean_working_dir and os.path.exists(working_folder):
        shutil.rmtree(working_folder)
        os.mkdir(working_folder)
    for filename in os.listdir(ref_folder):
        output_folder = os.path.join(os.path.dirname(filename), 'output',  os.path.split(filename)[1])
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)
        fn = os.path.join(ref_folder, filename)
        shutil.copy(fn, working_folder)
        if os.path.exists(fn.replace('.hdf5', '.mat')):
            shutil.copy(fn.replace('.hdf5', '.mat'), working_folder)
        if copy_only_first_file:
            break
    time.sleep(1.0)
    return working_folder
    
def run_test(path):
    '''
    Runs single test. Path shall contain full module path, test suite class name and test method name separated with dot
    '''
    module_name = '.'.join(path.split('.')[:-2])
    __import__(module_name)
    test_suite = unittest.TestSuite()
    test_suite.addTest(getattr(sys.modules[module_name],path.split('.')[-2])(path.split('.')[-1]))
    unittest.TextTestRunner(verbosity=2).run(test_suite)
    
import threading
class ShowTestProgress(threading.Thread):
    def __init__(self,filename,ntests):
        threading.Thread.__init__(self)
        self.filename = filename
        self.ntests=ntests
            
    def run(self):
        tests_finished = False
        start_line = -1
        prev_lines = -1
        while True:
            f = open(self.filename, 'rt')
            txt = f.read()
            f.close()
            lines = txt.split('\n')
            for line_index in range(len(lines)):
                if 'Test results' in lines[line_index]:
                    start_line = line_index
                elif 'Ran' in lines[line_index] and 'tests' in lines[line_index]:
                    tests_finished = True
            if prev_lines != len(lines):
                prev_lines = len(lines)
                if len(lines) - (start_line+1)> self.ntests:
                    break
                if len(lines) == 0:
                    test_name = ''
                else:
                    test_name = lines[-1]
                    test_name = test_name.split(' ')[0]
                sys.stdout.write('\r=========== {0}/{1} ===========\t{2}            '.format(len(lines) - (start_line+1),self.ntests,test_name))
                sys.stdout.flush()
            if tests_finished:
                break
            time.sleep(2.0)

class UnitTestRunner(object):
    '''
    This class is responsible for maintaining a list of implemented and ready to run unit tests. Test methods are aggregated and executed with unittest's TextTestRunner class.
    '''
    def __init__(self):        
        self.dont_kill_processes = get_python_processes()

    def _fetch_test_methods(self, test_class):
        '''
            Fetch test method names from a test class
        '''
        test_methods = []
        for method in dir(test_class):
            if 'test' in method:
                test_methods.append(method)
        return test_methods

    def _reference_to_test_class(self, test_class_path):
        '''
        Returns a reference to the test class given in string format
        '''
        test_class_name = test_class_path.split('.')[-1]
        module_path = test_class_path.replace('.' + test_class_name, '')
        __import__(module_path)
        return getattr(sys.modules[module_path], test_class_name)
        
    def _save_computer_parameters(self,f):
        f.write('\n################# Computer parameters ####################\n')
        for vn in ['uname', 'architecture', 'python_build', 'python_version']:
            f.write('{0}: {1}\r\n'.format(vn, getattr(platform,vn)()))
        
    def _save_test_parameters(self, f):
        f.write('\n################# Test parameters ####################\n')
        for pn in dir(sys.modules[__name__]):
            if 'TEST_' in pn[:5]:
                f.write('{0} = {1}\n'.format(pn, getattr(sys.modules[__name__], pn)))
        pass

    def run(self):
        '''
        Aggregates and runs tests.
        '''
        unit_test_start_time = time.time()
        if False and TEST_os == 'posix' and TEST_parallel_port:
            #load parallel port driver        
            os.system('rmmod lp')
            os.system('modprobe ppdev')#TODO: replace to popen
        self.test_log = tempfile.mkstemp()[1]        
        f = open(self.test_log,  'w')
        f.write(str(sys.argv) + '\n')
        self._save_computer_parameters(f)
        self._save_test_parameters(f)
        f.write('\n################# Test results ####################\n')
        test_suite = unittest.TestSuite()
        #Collect test classes, get test methods from them and add methods to test suite.
        aggregated_test_methods = []
        for test_class_name in TEST_unittests:
            test_class = self._reference_to_test_class(test_class_name)
            test_methods = self._fetch_test_methods(test_class)
            append = True
            if TEST_single_unittest != '' and TEST_single_unittest.split('.')[0] == test_class.__name__ and TEST_single_unittest.split('.')[1] in test_methods:
                test_method = TEST_single_unittest.split('.')[1]
                aggregated_test_methods.append([test_class.__name__ + '.' + test_method, test_method, test_class])
            elif TEST_single_unittest == '':
                aggregated_test_methods.extend([[test_class.__name__ + '.' + test_method, test_method, test_class] for test_method in test_methods])
        #Split list to two: 1. put items in TEST_priority_unittests to the beginning of the list. 2. shuffle the rest
        priority_unittests = []
        other_unittests = []
        for method in aggregated_test_methods:
            if method[0] in TEST_priority_unittests:
                priority_unittests.append(method)
            else:
                other_unittests.append(method)
        reordered_unittests = []
        reordered_unittests.extend(priority_unittests)
        import random
        random.seed(0)
        other_unittests = TEST_repeat*other_unittests
        random.shuffle(other_unittests)
        reordered_unittests.extend(other_unittests)
        for test_method in reordered_unittests:
            test_suite.addTest(test_method[2](test_method[1]))
        #Run tests
        stp = ShowTestProgress(self.test_log, len(reordered_unittests))
        stp.start()
        unittest.TextTestRunner(f, verbosity=2).run(test_suite)
        f.write('\n' + str(datetime.datetime.now())+'\n')
        f.close()
        f = open(self.test_log)
        print f.read()
        f.close()
        #Save tested source files
        if TEST_single_unittest == '':#Do not save source code and test log if single test is run. One test is only run for debug purposes
            self.save_source_and_results()
        if TEST_delete_files:
            print TEST_working_folder

        if TEST_delete_files:
            time.sleep(2.0)
            wfolder = select_folder_exists(TEST_working_folder)
            shutil.rmtree(wfolder)
            os.mkdir(wfolder)
        #Kill stuck processes
        kill_python_processes(self.dont_kill_processes)

    def save_source_and_results(self):
        test_EXPERIMENT_DATA_PATH = generate_filename(os.path.join(select_path_exists(TEST_results_folder), 'test_archive.zip'))
        package_path = os.path.split(os.path.split(sys.modules['visexpman'].__file__)[0])[0]
        #generate list of archivable files and write them to zipfile        
        source_zip = zipfile.ZipFile(test_EXPERIMENT_DATA_PATH, "w")
        for (path, dirs, files) in os.walk(package_path):
            for file in files:                
                if file[-3:] == '.py':
                    file_path = os.path.join(path,  file)
                    source_zip.write(file_path,  file_path.replace(package_path,  ''))
        source_zip.write(self.test_log,  'test_results.txt')
        source_zip.close()
        #Copy testt log to visexpman/data
        shutil.copy(self.test_log, os.path.join(package_path,'visexpman','data','unit_test_results_{0}.txt'.format(TEST_machine_name)))

if __name__ == "__main__":
    utr = UnitTestRunner()
    utr.run()

