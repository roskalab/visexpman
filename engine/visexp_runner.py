#TODO: ENABLE_UDP shall be replaced with udp config dictionary (similar to mes interface)
import sys
import threading
import time
import unittest
import os.path
import Queue
import socket
import logging
import os
import traceback
import random
import zipfile
import numpy
import re
import visexpman
import visexpman.engine.vision_experiment
from visexpman.engine.vision_experiment import command_handler

def find_out_config():
    '''
    Finds out configuration from the calling arguments. The following options are supported:
    - No argument: SafestartConfig is loaded
    - Username and config class name is encoded into one argument in the following form:
        user<separator>configclass, where separator can be: . , / \ <space> 
    - username and config class are provided as separate arguments
    '''        
    #TODO: optparser shall be used
    separators = [' ',  '.',  ',',  '/',  '\\']
    config_class = ''
    user = ''
    if len(sys.argv) == 0:
        raise RuntimeError('No command line arguments')
    elif len(sys.argv) == 1:
        config_class = 'SafestartConfig'
        user = 'default'
    elif len(sys.argv) == 2:
        for separator in separators:
            if sys.argv[1].find(separator) != -1:
                parameters = sys.argv[1].split(separator)
                user = sys.argv[1].split(separator)[0]
                config_class = sys.argv[1].split(separator)[1]
                break
    elif len(sys.argv) == 3:
        config_class = sys.argv[2]
        user = sys.argv[1]
    else:
        raise RuntimeError('Unsupported command line arguments')
    if config_class =='' and user == '':
        raise RuntimeError('Invalid command line argument')
    return user, config_class

class TestFindoutConfig(unittest.TestCase):
    #== Test cases of find_out_config() function ==
    def test_01_find_out_config_no_arguments(self):
        sys.argv = ['module.py']
        user, config_class = find_out_config()
        self.assertEqual((config_class, user),  ('SafestartConfig', 'default'))

    def test_02_find_out_config_only_username(self):
        sys.argv = ['module.py', 'testuser']
        self.assertRaises(RuntimeError,  find_out_config)
        
    def test_03_find_out_config_arguments_with_separator(self):
        sys.argv = ['module.py', 'test_user.config']
        user, config_class = find_out_config()
        self.assertEqual((config_class, user),  ('config', 'test_user'))
        
    def test_04_find_out_config_arguments_with_separator(self):
        sys.argv = ['module.py', 'test_user/config']
        user, config_class = find_out_config()
        self.assertEqual((config_class, user),  ('config', 'test_user'))
        
    def test_05_find_out_config_arguments_with_invalid_separator(self):
        sys.argv = ['module.py', 'test_user@config']        
        self.assertRaises(RuntimeError,  find_out_config)

    def test_06_find_out_config_two_arguments(self):
        sys.argv = ['module.py', 'test_user', 'config'] 
        user, config_class = find_out_config()
        self.assertEqual((config_class, user),  ('config', 'test_user'))

    def test_07_find_out_config_three_arguments(self):
        sys.argv = ['module.py', 'test_user', 'config',  'dummy'] 
        self.assertRaises(RuntimeError,  find_out_config)

    def test_08_find_out_config_no_arguments(self):
        sys.argv = [] 
        self.assertRaises(RuntimeError,  find_out_config)

if __name__ == "__main__":
    commands = []
    for i in range(0):
        if i == 0:
            commands.append([0.0, 'SOCexecute_experimentEOCEOP'])
        else:
            commands.append([430.0, 'SOCexecute_experimentEOCEOP'])
    v = visexpman.engine.vision_experiment.VisionExperimentRunner(*find_out_config())
    cs = command_handler.CommandSender(v.config, v, commands)
    cs.start()
    v.run_loop()
    cs.close()
