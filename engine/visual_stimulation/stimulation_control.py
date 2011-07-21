import sys
import zipfile as zip
import os
import os.path
import time
import numpy

from OpenGL.GL import *
from OpenGL.GLU import *
import logging
from visexpman.engine.generic import utils    

#import modules for stimulus files:
#from random import *
#from numpy import *

import experiment
import visexpman.engine.hardware_interface.instrument

import threading

#if self.config.ENABLE_PARALLEL_PORT:
#    import parallel
    
import stimulation_library

import visexpman.users as users

class StimulationControl():
    '''
    StimulationControl handles stimulation sequences, generating TTL triggers and log stimulation events with timestamps
    '''
    def __init__(self, visual_stimulation_runner, config, user_interface):
        
        self.visual_stimulation_runner = visual_stimulation_runner
        self.config = config
        self.stimulation_file = ''            
        self.user_interface = user_interface
        #self.udp_interface = udp_interface
        if self.config.ENABLE_PARALLEL_PORT:
            import parallel
            try:
                self.parallel = parallel.Parallel()
            except WindowsError:
                self.parallel = None
                self.config.set('ENABLE_PARALLEL_PORT',  False)
        else:
            self.parallel = None
        self.st = stimulation_library.Stimulations(config,  user_interface,  self,  self.parallel)
        self.state = 'idle'
        
        self.screen = user_interface.screen
        
        self.stimulation_script = ''
        self.measurement_id = 'not defined'
        
        #calculate wait time for frame rate control
        if self.config.SCREEN_EXPECTED_FRAME_RATE == self.config.SCREEN_MAX_FRAME_RATE:
            self.wait_time = 0.0
        else:
            self.wait_time = 1.0/self.config.SCREEN_EXPECTED_FRAME_RATE * self.config.FRAME_WAIT_FACTOR
            
        #initialize event logging
        self.logfile_path = self.config.LOG_PATH + os.sep + 'log' + str(time.time()).replace('.', '') + '.txt'       
        
        #self.logfile = psychopy.log.LogFile(self.logfile_path,  level = psychopy.log.DATA,  filemode = 'w')        
            
        self.log_file_index = 0        
        #psychopy.log.console.setLevel(psychopy.log.WARNING)
            
        #self._disable_frame_interval_watch()
        
        #intitialize filterwheels
        if self.config.FILTERWHEEL_ENABLE:
            self.filterwheels = []
            for i in range(len(self.config.FILTERWHEEL_SERIAL_PORT)):
                self.filterwheels.append(generic.Instrument.Filterwheel(self.config,  id = i))
            
    def is_next_pressed(self):
        return self.user_interface.is_next_pressed()
        
    def _enable_frame_interval_watch(self):        
        self.screen.setRecordFrameIntervals(True)        

    def _disable_frame_interval_watch(self):        
        self.screen.setRecordFrameIntervals(False)             

    def zip_py_files(self, zip_path,  base_path, log):
        '''
        Saves Presentinator source files, stimulation file(s) and log file into a zip file
        '''
        files =  os.listdir(base_path)        
        file = zip.ZipFile(zip_path, "w")
        for filename in files:
            full_path = base_path + os.sep + filename
            if full_path.find('.py') != -1 and full_path.find('.pyc') == -1:
                file.write(full_path, filename, zip.ZIP_DEFLATED)
            elif os.path.isdir(full_path):
                subfolder_files =  os.listdir(full_path)
                for subfolder_file in subfolder_files:
                    subfolder_full_path = full_path + os.sep + subfolder_file
                    filepath_in_zip = full_path[full_path.rfind(os.sep):] + os.sep + subfolder_file
                    if subfolder_full_path.find('.py') != -1 and subfolder_full_path.find('.pyc') == -1:
                        file.write(subfolder_full_path, filepath_in_zip, zip.ZIP_DEFLATED)
        
        #save log file to temporary file
        log_filename = 'log.txt'
        f = open(log_filename ,  'wt')
        f.write(log)
        f.close()
        file.write(log_filename , 'log/' + log_filename, zip.ZIP_DEFLATED)
        file.close()
        os.remove(log_filename)
        
    def last_stimulus_log(self):
        return utils.read_text_file(self.logfile_path)[self.log_file_index:]
    
    def log_data(self, log_message):
        f = open(self.logfile_path,  'at')
        string_to_file = "%2.3f"% (time.time() - self.start_time)
        string_to_file += '\t' + log_message + '\n'
        f.write(string_to_file)
        f.close()
    
    def runStimulation(self):
        '''
        Runs stimulation and takes care of triggering and frame interval watching
        '''
        if hasattr(self.visual_stimulation_runner, 'selected_experiment_config') and hasattr(self.visual_stimulation_runner.selected_experiment_config, 'run'):
            #save log file index which is the current size of log file
            #self.log_file_index = len(utils.read_text_file(self.logfile_path))
            self.visual_stimulation_runner.state = 'stimulation'
            
            #psychopy.log.data('Measurement ID: ' + self.measurement_id)

            #self._enable_frame_interval_watch()
            if self.config.ENABLE_PARALLEL_PORT:
                self.parallel.setData(self.config.ACQUISITION_TRIGGER_ON)
            self.stimulation_start_time = time.time()
            if hasattr(self.visual_stimulation_runner.selected_experiment_config, 'pre_runnable') and self.visual_stimulation_runner.selected_experiment_config.pre_runnable is not None:
                self.visual_stimulation_runner.selected_experiment_config.pre_runnable.run()
            self.visual_stimulation_runner.selected_experiment_config.run(self.st)
            #psychopy.log.data(log_string)            
                
            if self.config.ENABLE_PARALLEL_PORT:
                self.parallel.setData(self.config.ACQUISITION_TRIGGER_OFF)
                       
            #self._disable_frame_interval_watch()
            self.st.set_background(self.config.BACKGROUND_COLOR)            
            
            #psychopy.log.flush()
            if self.config.ENABLE_FRAME_CAPTURE:
                self.user_interface.screen.saveMovieFrames(self.config.CAPTURE_PATH + '/captured' + str(time.time()).replace('.', '') + '.bmp')            
#                e.cleanup()
            #save stimulus, source and log files into zip            
            #log = self.last_stimulus_log()
            
            if len(self.config.ARCHIVE_PATH)  == 0:
                zip_path = self.config.ARCHIVE_PATH + str(time.time()).replace('.', '') + '.zip'
            else:
                zip_path = self.config.ARCHIVE_PATH + os.sep + str(time.time()).replace('.', '') + '.zip'
                
            #if user log file path defined save log data using that path
            for local in locals():
                if local == 'user_log_file_path':
                    if os.path.exists(os.path.dirname(user_log_file_path)):                
                        f = open(user_log_file_path ,  'wt')
                        f.write(log)
                        f.close()

#             self.zip_py_files(zip_path,  self.config.BASE_PATH, log)
            self.visual_stimulation_runner.state = 'idle'
        else:
            raise AttributeError('Stimulus config class does not have a run method?')

if __name__ == "__main__":
    pass
