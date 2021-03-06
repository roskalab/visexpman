import logging
import datetime
import time
import os.path
import tempfile
import shutil
import unittest
import threading
from visexpman.users.zoltan.test import unit_test_runner
from visexpman.engine.generic import utils
from visexpman.engine.generic import file

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
        self.path = file.generate_filename(os.path.join(unit_test_runner.TEST_working_folder, 'log_unit_test.txt'))

    def test_01_automatic_saving_with_timestamps(self):
        while True:
            if int(time.time()*1000)%1000 < 500:
                break        
        reference_date = str(datetime.datetime.now()).split('.')[0]        
        log = Log(self.path, self.path)
        log.info('logged1')
        log.info('logged2')
        log.handler.flush()
        log_file_content = file.read_text_file(self.path)
        self.assertEqual((os.path.exists(self.path), 
                          log_file_content.find('logged1') != -1, 
                          log_file_content.find('logged2') != -1, 
                          log_file_content.find(reference_date) != -1), 
                          (True, True, True, True))
                          
    def test_02_user_controlled_saving_with_timestamps(self):
        while True:
            if int(time.time()*1000)%1000 < 500:
                break        
        reference_date = str(datetime.datetime.now()).split('.')[0]        
        log = Log(self.path, self.path, write_mode = 'user control')
        log.info('logged1')
        log.info('logged2')        
        log_file_content_pre_flush = file.read_text_file(self.path)
        log.flush()
        log_file_content = file.read_text_file(self.path)
        self.assertEqual((os.path.exists(self.path), 
                          log_file_content.find('logged1') != -1, 
                          log_file_content.find('logged2') != -1, 
                          log_file_content.find(reference_date) != -1, 
                          log_file_content_pre_flush), 
                          (True, True, True, True, ''))
                          
    def test_03_automatic_saving_with_elapsed_time(self):
        while True:
            if int(time.time()*1000)%1000 < 500:
                break        
        reference_date = str(datetime.datetime.now()).split('.')[0]
        log = Log(self.path, self.path, timestamp = 'elapsed_time')
        log.info('logged1')
        log.info('logged2')
        log.handler.flush()
        log_file_content = file.read_text_file(self.path)
        time_stamps = []
        for line in log_file_content.split('\n'):
            if len(line) > 0:
                time_stamps.append(float(line.split('\t')[0])< 1e-2)
        self.assertEqual((os.path.exists(self.path), 
                          log_file_content.find('logged1') != -1, 
                          log_file_content.find('logged2') != -1, 
                          log_file_content.find(reference_date) == -1, 
                          time_stamps[0], 
                          time_stamps[1]), 
                          (True, True, True, True, True, True))
                          
    def test_04_user_controlled_saving_with_elapsed_time(self):
        while True:
            if int(time.time()*1000)%1000 < 500:
                break        
        reference_date = str(datetime.datetime.now()).split('.')[0]
        log = Log(self.path, self.path, write_mode = 'user control', timestamp = 'elapsed_time')
        log.info('logged1')
        log.info('logged2')
        log_file_content_pre_flush = file.read_text_file(self.path)
        log.flush()
        log_file_content = file.read_text_file(self.path)
        time_stamps = []
        for line in log_file_content.split('\n'):
            if len(line) > 0:
                time_stamps.append(float(line.split('\t')[0])< 1e-2)
        self.assertEqual((os.path.exists(self.path), 
                          log_file_content.find('logged1') != -1, 
                          log_file_content.find('logged2') != -1, 
                          log_file_content.find(reference_date) == -1, 
                          time_stamps[0], 
                          time_stamps[1], 
                          log_file_content_pre_flush), 
                          (True, True, True, True, True, True, ''))
                          
    def tearDown(self):
        pass
        
if __name__ == "__main__":
    unittest.main()
        
