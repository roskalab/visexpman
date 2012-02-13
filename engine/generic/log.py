import logging
import datetime
import time
import unittest
import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner
from visexpman.engine.generic import utils
from visexpman.engine.generic import file
import os.path

class Log(object):
    def __init__(self, name,  path, write_mode = 'automatic', timestamp = 'date_time'):
        '''
        write_mode: 'automatic', 'user controlled' - way of saving data to disk
        '''
        self.log = logging.getLogger(name)
        self.handler = logging.FileHandler(path)
        formatter = logging.Formatter('%(message)s')
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

    def flush(self):
        full_log = ''
        for item in self.log_messages:
            full_log += item + '\n'
        self.log.info(full_log)
        self.log_messages = []
        self.handler.flush()
        
    def queue(self, queue, name = None):
        '''
        Assuming that each item in the queue is a list or tuple, where the first item is a timestamp
        '''
        if name != None:
            self.info(name, log_timestamp = False)
        for entry in utils.empty_queue(queue):
            self.info([utils.time_stamp_to_hms(entry[0]), entry[1]], log_timestamp = False)
        
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
        
