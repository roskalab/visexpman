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

class Logger(multiprocessing.Process):
    '''
    Logger process that receives log entries via queues and saves all to one file.
    File operations can be suspended to minimize timing jitters in visual stimulation or in other 'real time' activities.
    '''
    def __init__(self, *args, **kwargs):
        multiprocessing.Process.__init__(self)
        self.config = args[0]
        if kwargs.has_key('filename'):
            self.filename = kwargs['filename']
        else:
            self.filename = fileop.get_logfilename(self.config)
        self.command = multiprocessing.Queue()
        self.sources = {}
        self.add_source('default')
        self.saving2file_enable = True

    def add_source(self, source_name):
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
            self.sources[source].put([time.time(), loglevel, source, msg])
        else:
            from visexpman.engine import LoggingError
            raise LoggingError('{0} logging source was not added to logger'.format(source))
        
    def upload_logfiles(self):
        '''
        Copies log files from LOG_PATH to REMOTE_LOG_PATH
        '''
        if not hasattr(self.config, 'REMOTE_LOG_PATH') or not os.path.exists(self.config.REMOTE_LOG_PATH):
            return
        for fn in fileop.listdir_fullpath(self.config.LOG_PATH):
            if fileop.is_first_tag(fn, 'log_') and fileop.file_extension(fn) == 'txt':
                target_path = os.path.join(self.config.REMOTE_LOG_PATH, os.path.split(fn)[1])
                if not os.path.exists(target_path):#Copy file if cannot be found in remote log folder
                    import shutil
                    shutil.copyfile(fn, target_path)
                    shutil.copystat(fn, target_path)

    ########### Commands ###########
    def terminate(self):
        self.command.put('terminate')
        
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
        self.upload_logfiles()

class Log(object):
    def __init__(self, name,  path, write_mode = 'automatic', timestamp = 'date_time', local_saving = False, format_string = '%(message)s'):
        '''
        write_mode: 'automatic', 'user controlled' - way of saving data to disk
        '''
        self.path = path
        self.local_saving = local_saving
        if self.local_saving:
            self.log_path = os.path.join(tempfile.gettempdir(), os.path.split(path)[1])
        else:
            self.log_path = path
            
        self.log = logging.getLogger(name)
        self.handler = logging.FileHandler(self.log_path)
        formatter = logging.Formatter(format_string)
        self.handler.setFormatter(formatter)
        self.log.addHandler(self.handler)
        self.log.setLevel(logging.INFO)
        self.write_mode = write_mode
        self.timestamp = timestamp
        self.log_messages = []
        self.log_dict = {}#Not tested
        self.start_time = time.time()
        self.entry_count = 0
        
    def info(self, message, log_timestamp = True):
        message = str(message)
        message_to_log = message
        if self.timestamp == 'date_time' and log_timestamp:
            message_to_log = str(datetime.datetime.now()) + '\t' + message
            key = utils.datetime_string()
        elif self.timestamp == 'elapsed_time' and log_timestamp:
            elapsed_time = round(time.time() - self.start_time, 3)
            message_to_log = str(elapsed_time) + '\t' + message
            key = elapsed_time
        else:
            message_to_log = message
            key = 'entry_' + str(self.entry_count)
        if self.write_mode == 'automatic':
            self.log.info(message_to_log)
            self.entry_count += 1
        elif self.write_mode == 'user control':
            self.log_messages.append(message_to_log)
            self.log_dict['time_'+str(key).replace('.', 'p')] = message
            self.entry_count += 1
            
    def error(self, message):
        self.log.error(message)
        
    def warning(self, message):
        self.log.warning(message)
        
    def debug(self, message):
        self.log.debug(message)

    def flush(self):
        full_log = ''
        for item in self.log_messages:
            full_log += item + '\n'
        self.log.info(full_log)
        self.log_messages = []
        time.sleep(0.1)
        try:#Sometimes random errors occur at this point
            self.handler.flush()
        except:
            time.sleep(2.0)
            try:
                self.handler.flush()
            except:
                print 'Flushing log file was not successful'
        
    def queue(self, queue, name = None):
        '''
        Assuming that each item in the queue is a list or tuple, where the first item is a timestamp
        '''
        if name != None:
            self.info(name, log_timestamp = False)
        for entry in utils.empty_queue(queue):
            self.info([utils.timestamp2hms(entry[0]), entry[1]], log_timestamp = False)
            
    def copy(self):
        if self.local_saving:
            shutil.copyfile(self.log_path, self.path)
            
class LoggerThread(threading.Thread, Log):
    def __init__(self, command_queue, log_queue, name,  path, write_mode = 'automatic', timestamp = 'date_time', local_saving = False, format_string = '%(message)s'):
        Log.__init__(self, name,  path, write_mode, timestamp, local_saving, format_string)
        threading.Thread.__init__(self)
        self.command_queue = command_queue
        self.log_queue = log_queue
        
    def run(self):
        while True:
            time.sleep(0.1)
            if not self.command_queue.empty():
                command = self.command_queue.get()
                if command == 'TERMINATE':
                    break
            else:
                for entry in utils.empty_queue(self.log_queue):
                    self.info('{0}: {1}' .format(utils.timestamp2hms(entry[0]), entry[1]), log_timestamp = False)
        self.copy()
                 
                 
class TestLog(unittest.TestCase):
    def setUp(self):
        import visexpman.engine.vision_experiment.configuration
        self.machine_config = utils.fetch_classes('visexpman.users.test', 'GUITestConfig', required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig,direct = False)[0][1]()
        self.machine_config.application_name='main_ui'
        self.machine_config.user = 'test'

#    def test_01_automatic_saving_with_timestamps(self):
#        while True:
#            if int(time.time()*1000)%1000 < 500:
#                break        
#        reference_date = str(datetime.datetime.now()).split('.')[0]        
#        log = Log(self.path, self.path)
#        log.info('logged1')
#        log.info('logged2')
#        log.handler.flush()
#        log_file_content = fileop.read_text_file(self.path)
#        self.assertEqual((os.path.exists(self.path), 
#                          log_file_content.find('logged1') != -1, 
#                          log_file_content.find('logged2') != -1, 
#                          log_file_content.find(reference_date) != -1), 
#                          (True, True, True, True))
#                          
#    def test_02_user_controlled_saving_with_timestamps(self):
#        while True:
#            if int(time.time()*1000)%1000 < 500:
#                break        
#        reference_date = str(datetime.datetime.now()).split('.')[0]        
#        log = Log(self.path, self.path, write_mode = 'user control')
#        log.info('logged1')
#        log.info('logged2')        
#        log_file_content_pre_flush = fileop.read_text_file(self.path)
#        log.flush()
#        log_file_content = fileop.read_text_file(self.path)
#        self.assertEqual((os.path.exists(self.path), 
#                          log_file_content.find('logged1') != -1, 
#                          log_file_content.find('logged2') != -1, 
#                          log_file_content.find(reference_date) != -1, 
#                          log_file_content_pre_flush), 
#                          (True, True, True, True, ''))
#                          
#    def test_03_automatic_saving_with_elapsed_time(self):
#        while True:
#            if int(time.time()*1000)%1000 < 500:
#                break        
#        reference_date = str(datetime.datetime.now()).split('.')[0]
#        log = Log(self.path, self.path, timestamp = 'elapsed_time')
#        log.info('logged1')
#        log.info('logged2')
#        log.handler.flush()
#        log_file_content = fileop.read_text_file(self.path)
#        time_stamps = []
#        for line in log_file_content.split('\n'):
#            if len(line) > 0:
#                time_stamps.append(float(line.split('\t')[0])< 1e-2)
#        self.assertEqual((os.path.exists(self.path), 
#                          log_file_content.find('logged1') != -1, 
#                          log_file_content.find('logged2') != -1, 
#                          log_file_content.find(reference_date) == -1, 
#                          time_stamps[0], 
#                          time_stamps[1]), 
#                          (True, True, True, True, True, True))
#                          
#    def test_04_user_controlled_saving_with_elapsed_time(self):
#        while True:
#            if int(time.time()*1000)%1000 < 500:
#                break        
#        reference_date = str(datetime.datetime.now()).split('.')[0]
#        log = Log(self.path, self.path, write_mode = 'user control', timestamp = 'elapsed_time')
#        log.info('logged1')
#        log.info('logged2')
#        log_file_content_pre_flush = fileop.read_text_file(self.path)
#        log.flush()
#        log_file_content = fileop.read_text_file(self.path)
#        time_stamps = []
#        for line in log_file_content.split('\n'):
#            if len(line) > 0:
#                time_stamps.append(float(line.split('\t')[0])< 1e-2)
#        self.assertEqual((os.path.exists(self.path), 
#                          log_file_content.find('logged1') != -1, 
#                          log_file_content.find('logged2') != -1, 
#                          log_file_content.find(reference_date) == -1, 
#                          time_stamps[0], 
#                          time_stamps[1], 
#                          log_file_content_pre_flush), 
#                          (True, True, True, True, True, True, ''))
#                          

    def test_01_create_logger(self):
        p= Logger(self.machine_config)
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
        self.assertEqual((len(logged_text.split('INFO'))-1, len(logged_text.split('WARNING'))-1, len(logged_text.split('\n'))-1, 
                            'test1' in logged_text, 'test2' in logged_text, 'test3' in logged_text, filelist['logfiles']), 
                         (2, 1, 3, True, True, True, filelist['remotelogfiles'])
                         )
        pass

    
    def tearDown(self):
        pass
        
if __name__ == "__main__":
    unittest.main()
        
