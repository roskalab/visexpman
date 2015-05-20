##
import sys
import unittest
import time
import os.path
import numpy
import warnings
import visexpman.engine
from visexpman.engine.visexp_gui import VisionExperimentGui
from visexpman.engine.generic.command_parser import ServerLoop
from visexpman.engine.vision_experiment.screen import StimulationScreen
from visexpman.engine.vision_experiment import experiment_control
from visexpman.engine.generic.graphics import check_keyboard
from visexpman.engine.generic import utils,fileop,introspect
import hdf5io

import visexpman.engine.visexp_app as app
##
context = visexpman.engine.application_init(user='roland',
                                  config='MEAConfig',
                                  user_interface_name='stim')

##
context = visexpman.engine.application_init(user='antonia',
                                  config='MEASetup',
                                  user_interface_name='stim')


##
app.run_stim(context)
visexpman.engine.stop_application(context)


## 
#import serial
#s = [serial.Serial(context['machine_config'].DIGITAL_IO_PORT)]


##
#import serial
#s = serial.Serial('/dev/ttyS0')


## This works:
import parallel
p = parallel.Parallel()
##
for N in range(1,32):
    print N
    p.setData(N)
    time.sleep(0.5)

## Look at the log file:
c = context['machine_config']
folder = c.LOG_PATH

import scipy.io
M = scipy.io.loadmat(folder + 'log_MEAConfig_roland_stim_2015-05-18_09-16-45_NHPMarchingSquares_143193341669.mat')

##
for k,v in self.datafile.items() :
     #v
     for j in v:
        i         
        if j is None:
            print 'n'
        else:
            print 'i'
