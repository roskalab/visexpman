import multiprocessing
import logging
import datetime
import time
import os.path
import tempfile
import shutil
import unittest
import threading
from visexpman.users.test import unittest_aggregator
from visexpman.engine.generic import utils
from visexpman.engine.generic import fileop

class LoggingError(Exception):
    '''
    Logger process related error
    '''

class Logger(multiprocessing.Process):
    '''
    Logger process that receives log entries via queues and saves all to one file.
    File operations can be suspended to minimize timing jitters in visual stimulation or in other 'real time' activities.
    
    Machine config is not passed on purpose. 
    Passing such items including big dinctionaries increase the runtime of the start() method of the process
    '''
    def __init__(self, *args, **kwargs):
        multiprocessing.Process.__init__(self)
        self.filename = kwargs['filename']
        self.logpath = kwargs['logpath']
        self.remote_logpath = kwargs['remote_logpath']
        self.command = multiprocessing.Queue()
        self.sources = {}
        self.add_source('default')
        self.saving2file_enable = True

    def add_source(self, source_name):
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
        #Sort by time
        timestamps.sort()
        str2file = ''
        for timestamp in timestamps:
            for entry in entries:
                if entry[0] == timestamp:
                    str2file += self._entry2text(entry)
                    break
        self.file.write(str2file)
        self.file.flush()
                
    def _entry2text(self, entry):
        return '{0} {1}/{2}\t{3}\n'.format(utils.timestamp2ymdhms(entry[0]), entry[1], entry[2], entry[3])
        
    def info(self, msg, source='default'):
        self.add_entry(msg, source, 'INFO')
    
    def warning(self, msg, source='default'):
        self.add_entry(msg, source, 'WARNING')
        
    def error(self, msg, source='default'):
        self.add_entry(msg, source, 'ERROR')
        
    def add_entry(self, msg, source, loglevel):
        if self.sources.has_key(source):
            self.sources[source].put([time.time(), loglevel, source, msg])#Timestamp is not captured when the data saving takes place
        else:
            from visexpman.engine import LoggingError
            raise LoggingError('{0} logging source was not added to logger'.format(source))
        
    def upload_logfiles(self):
        '''
        Copies log files from LOG_PATH to REMOTE_LOG_PATH
        '''
        for fn in fileop.listdir_fullpath(self.logpath):
            if fileop.is_first_tag(fn, 'log_') and fileop.file_extension(fn) == 'txt':
                target_path = os.path.join(self.remote_logpath, os.path.split(fn)[1])
                if not os.path.exists(target_path):#Copy file if cannot be found in remote log folder
                    import shutil
                    shutil.copyfile(fn, target_path)
                    shutil.copystat(fn, target_path)

    ########### Commands ###########
    def terminate(self):
        self.command.put('terminate')
        self.join()
        
    def suspend(self):
        '''
        suspends saving to file until resume is not called
        '''
        self.command.put('suspend')
        
    def resume(self):
        '''
        Resumes saving log entries to file
        '''
        self.command.put('resume')

    def run(self):
        self.file = open(self.filename, 'wt')#Create file
        while True:
            time.sleep(0.1)
            if not self.command.empty():
                command = self.command.get()
                if command == 'terminate':
                    self.flush()
                    self.file.close()
                    break
                elif command == 'suspend':
                    self.saving2file_enable = False
                elif command == 'resume':
                    self.saving2file_enable = True
            self.flush()
        self.file.close()
        if os.path.exists(self.remote_logpath):#Do nothing when  remote log path not provided 
            self.upload_logfiles()

class TestLog(unittest.TestCase):
    def setUp(self):
        import visexpman.engine.vision_experiment.configuration
        self.machine_config = utils.fetch_classes('visexpman.users.test', 'GUITestConfig', required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig,direct = False)[0][1](clear_files=True)
        self.machine_config.application_name='main_ui'
        self.machine_config.user = 'test'

    def test_01_create_logger(self):
        p= Logger(filename=fileop.get_logfilename(self.machine_config), logpath = self.machine_config.LOG_PATH, remote_logpath = self.machine_config.REMOTE_LOG_PATH)
        p.add_source('mysource')
        p.start()
        p.info('test1', 'mysource')
        time.sleep(1)
        p.suspend()
        p.info('test2')
        time.sleep(1)
        p.resume()
        p.warning('test3')
        time.sleep(1)
#        p.run()
        p.terminate()
        p.join()
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
        pass
        
    def tearDown(self):
        pass
        
if __name__ == "__main__":
    unittest.main()
        
