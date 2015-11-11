#OBSOLETE MODULE
import sys
import time
import Queue
import os
import numpy
import traceback
import re
import cPickle as pickle

import PyQt4.QtCore as QtCore

from visexpman.engine.generic import introspect
from visexpman.engine.generic import command_parser
from visexpman.engine.generic import utils
from visexpman.engine.hardware_interface import network_interface
from visexpman.engine.hardware_interface import stage_control
from visexpman.engine.hardware_interface import instrument
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
        
