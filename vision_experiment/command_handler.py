#OBSOLETE MODULE
import sys
import time
try:
    import Queue
except ImportError:
    import queue as Queue
import os
import numpy
import traceback
import re
try:
    import cPickle as pickle
except ImportError:
    import pickle
try:
    import PyQt4.QtCore as QtCore
except ImportError:
    import PyQt5.QtCore as QtCore

from visexpman.generic import introspect
from visexpman.generic import command_parser
from visexpman.generic import utils
from visexpman.hardware_interface import network_interface
from visexpman.hardware_interface import stage_control
from visexpman.hardware_interface import instrument
import hdf5io

find_experiment_class_name = re.compile('class (.+)\(experiment.Experiment\)')
find_experiment_config_class_name = re.compile('class (.+)\(experiment.ExperimentConfig\)')

class CommandSender(QtCore.QThread):
    '''
    A thread that can be configured to send commands via keyboard command queue with a predefined timing
    '''
    def __init__(self, config, caller, commands):
        self.config = config
        self.caller = caller
        self.commands = commands
        QtCore.QThread.__init__(self)
        
    def send_command(self, command):
        self.caller.keyboard_command_queue.put(command)
        
    def run(self):
        for command in self.commands:
            time.sleep(command[0])
            self.send_command(command[1])            

    def close(self):
        self.terminate()
        self.wait()
        
