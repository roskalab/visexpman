import multiprocessing
import logging
import datetime
import time
import os.path
import tempfile
import shutil
import unittest
import threading
import copy
try:
    from visexpman.users.test import unittest_aggregator
except:
    pass
from visexpman.engine.generic import utils,fileop,stringop

class LoggingError(Exception):
    '''
    Logger process related error
    '''
    
def log2str(msg):
    msg_out = copy.deepcopy(msg)
    #Experiment config source code is not logged
    if utils.safe_has_key(msg_out, 'args') and isinstance(msg_out['args'], list):
        if len(msg_out['args'])>0:
            if utils.safe_has_key(msg_out['args'][0], 'experiment_config_source_code'):
                msg_out['args'][0]['experiment_config_source_code'] = 'Not logged'
            if utils.safe_has_key(msg_out['args'][0], 'stimulus_source_code'):
                msg_out['args'][0]['stimulus_source_code'] = 'Not logged'
            #THIS MIGHT BE OBSOLETE
            for vn in ['xsignal', 'ysignal', 'frame_trigger_signal', 'valid_data_mask', 
                            'stimulus_flash_trigger_signal', 'one_period_valid_data_mask', 'one_period_x_scanner_signal']:
                if utils.safe_has_key(msg_out['args'][0], vn):
                    msg_out['args'][0][vn] = 'Not logged'
    return str(msg_out)
    
class LoggerHelper(object):
    '''
    Set of functions for adding log entries.
    '''
    def __init__(self, queue=None):
        if not hasattr(self, 'sources'):
            self.queue = queue
            
    def info(self, msg, source='default', queue = None):
        self.add_entry(msg, source, 'INFO', queue)
    
    def warning(self, msg, source='default', queue = None):
        self.add_entry(msg, source, 'WARNING', queue)
        
    def error(self, msg, source='default', queue = None):
        self.add_entry(msg, source, 'ERROR', queue)
        
    def debug(self, msg, source='default', queue = None):
        self.add_entry(msg, source, 'DEBUG', queue)
        
    def add_entry(self, msg, source, loglevel, queue):
        entry = [time.time(), loglevel, source, msg]
        if not hasattr(self, 'sources'):
            q = self.queue
        elif self.sources.has_key(source):
            q = self.sources[source]
        else:
            raise LoggingError('{0} logging source was not added to logger'.format(source))
        if queue is not None:#Message is put to provided queue, this is used for sending log info to remote application's console
            queue.put(entry[-1])
        q.put(entry)
        

class Logger(multiprocessing.Process,LoggerHelper):
    '''
    Logger process that receives log entries via queues and saves all to one file.
    File operations can be suspended to minimize timing jitters in visual stimulation or in other 'real time' activities.
    
    Machine config is not passed on purpose. 
    Passing such items including big dinctionaries increase the runtime of the start() method of the process
    
    The process/log channel architecture makes sure that parallel processes can send log messages to the same logfile.
    Generally logging would be sufficient for this purpose but with logger file write cannot be controlled while stimulation is presented
    '''
    def __init__(self, *args, **kwargs):
        multiprocessing.Process.__init__(self)
        self.filename = kwargs['filename']
        self.logpath = os.path.split(self.filename)[0]
        if kwargs.has_key('remote_logpath'):
            self.remote_logpath = kwargs['remote_logpath']
        self.command = multiprocessing.Queue()
        self.sources = {}
        self.add_source('default')
        self.saving2file_enable = True
        
    def get_queues(self):
        return self.sources

    def add_source(self, source_name):
        if self.sources.has_key(source_name):#If source already added silently do nothing
            return
        if self.pid is not None:
            raise LoggingError('Logger process alread started, {0} source cannot be added'.format(source_name))
        self.sources[source_name] = multiprocessing.Queue()
        return self.sources[source_name]
        
    def flush(self):
        '''
        Read source queues and save entries to file
        '''
        entries = []
        timestamps = []
        for source_name, source in self.sources.items():
            while not source.empty():
                entries.append(source.get())
                timestamps.append(entries[-1][0])
        if len(timestamps)==0:
            return
        #Sort by time
        timestamps.sort()
        str2file = ''
        for timestamp in timestamps:
            for entry in entries:
                if entry[0] == timestamp:
                    str2file += self._entry2text(entry)
                    entries.remove(entry)
                    break
        self.file.write(str2file)
        try:
            self.file.flush()#Happens for unknown reason
        except:
            import traceback
            print traceback.format_exc()
                
    def _entry2text(self, entry):
        return '{0}.{4} {1}/{2}\t{3}\n'.format(utils.timestamp2ymdhms(entry[0]), entry[1], entry[2], entry[3],int(entry[0]*10)%10)
        
    def upload_logfiles(self):
        '''
        Copies log files from LOG_PATH to REMOTE_LOG_PATH
        '''
        for fn in fileop.listdir_fullpath(self.logpath):
            if fileop.is_first_tag(fn, 'log_') and os.path.splitext(fn)[1] == '.txt':
                target_path = os.path.join(self.remote_logpath, os.path.split(fn)[1])
                if not os.path.exists(target_path):#Copy file if cannot be found in remote log folder
                    import shutil
                    shutil.copyfile(fn, target_path)
                    shutil.copystat(fn, target_path)

    ########### Commands ###########
    def terminate(self):
        self.command.put('terminate')
        while True:
            state = not self.command.empty()
            if state:
                break
            time.sleep(0.1)
        self.join()
        
    def suspend(self):
        '''
        suspends saving to file until resume is not called
        '''
        self.command.put('suspend')
        if 0:
            self.sources['default'].put([time.time(), 'DEBUG', 'default', 'suspend'])
        
    def resume(self):
        '''
        Resumes saving log entries to file
        '''
        self.command.put('resume')
        if 0:
            self.sources['default'].put([time.time(), 'DEBUG', 'default', 'resume'])

    def run(self):
        t0=time.time()
        while not os.path.exists(os.path.split(self.filename)[0]) and time.time()-t0<30.0:
            time.sleep(1)
        self.file = open(self.filename, 'wt')#Create file
        while True:
            time.sleep(0.1)
            if not self.command.empty():
                command = self.command.get()
                if command == 'terminate':
                    self.flush()
                    break
                elif command == 'suspend':
                    self.saving2file_enable = False
                elif command == 'resume':
                    self.saving2file_enable = True
            if self.saving2file_enable:
                self.flush()
        self.flush()#Make sure that all entries in queue are saved
        self.file.close()
        if hasattr(self, 'remote_logpath') and os.path.exists(self.remote_logpath):#Do nothing when  remote log path not provided 
            self.upload_logfiles()
        self.command.put('terminated')
        
def get_logfilename(config):
    '''
    filename format: log_<machine config name>_<username>_<user_interface_name>_yy-mm-dd-hhmm.txt
    '''
    expected_attributes = ['user', 'user_interface_name', 'LOG_PATH']
    if not all([hasattr(config, expected_attribute) for expected_attribute in expected_attributes]):
        from visexpman.engine import MachineConfigError
        raise MachineConfigError('LOG_PATH, user and user_interface_name shall be an attribute in machine config')
    while True:
        filename =  os.path.join(config.LOG_PATH, 'log_{0}_{1}_{2}_{3}.txt'.format(config.__class__.__name__, config.user, config.user_interface_name, utils.datetime_string()))
        if not os.path.exists(filename):
            break
        time.sleep(1.0)
    return filename

class TestLog(unittest.TestCase):
    def setUp(self):
        import visexpman.engine.vision_experiment.configuration
        self.machine_config = utils.fetch_classes('visexpman.users.test', 'GUITestConfig', required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig,direct = False)[0][1](clear_files=True)
        self.machine_config.user_interface_name='main_ui'
        self.machine_config.user = 'test'

    def test_01_create_logger(self):
        p= Logger(filename=get_logfilename(self.machine_config), remote_logpath = self.machine_config.REMOTE_LOG_PATH)
        p.add_source('mysource')
        p.start()
        p.info('test1', 'mysource')
        time.sleep(1.5)
        if not os.path.exists(p.filename):
            pass
        filesize1=os.path.getsize(p.filename)
        p.suspend()
        p.info('test2')
        time.sleep(1)
        filesize2=os.path.getsize(p.filename)
        self.assertEqual(filesize1, filesize2)#File size not changed, during suspend no new entry flushed to file
        p.resume()
        p.warning('test3')
        time.sleep(1)
#        p.run()
        p.terminate()
        logged_text = fileop.read_text_file(p.filename)
        filelist  = {}
        filelist['logfiles'] = fileop.listdir_fullpath(self.machine_config.LOG_PATH)
        filelist['remotelogfiles'] = fileop.listdir_fullpath(self.machine_config.REMOTE_LOG_PATH)
        for k, v in filelist.items():
            filelist[k] = [os.path.split(i)[1] for i in v]
        self.assertEqual(len(logged_text.split('INFO'))-1, 2)
        self.assertEqual(len(logged_text.split('WARNING'))-1, 1)
        self.assertEqual(len(logged_text.split('\n'))-1, 3)
        self.assertIn('test1', logged_text)
        self.assertIn('test2', logged_text)
        self.assertIn('test3', logged_text), 
        self.assertEqual(filelist['logfiles'], filelist['remotelogfiles'])
        
    def test_02_no_remote_logger(self):
        p= Logger(filename=get_logfilename(self.machine_config))
        p.add_source('mysource')
        p.start()
        p.info('test1', 'mysource')
        time.sleep(1)
        p.info('test2')
        time.sleep(1)
        p.warning('test3')
        p.info('test4')
        time.sleep(1)
        p.terminate()
        logged_text = fileop.read_text_file(p.filename)
        filelist  = {}
        filelist['logfiles'] = fileop.listdir_fullpath(self.machine_config.LOG_PATH)
        for k, v in filelist.items():
            filelist[k] = [os.path.split(i)[1] for i in v]
        self.assertEqual(len(logged_text.split('INFO'))-1, 3)
        self.assertEqual(len(logged_text.split('WARNING'))-1, 1)
        self.assertEqual(len(logged_text.split('\n'))-1, 4)
        self.assertIn('test1', logged_text)
        self.assertIn('test2', logged_text)
        self.assertIn('test3', logged_text)
        self.assertIn('test4', logged_text)

        
    def tearDown(self):
        pass
        
if __name__ == "__main__":
    unittest.main()
        
