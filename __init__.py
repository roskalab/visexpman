import sys
import os
import numpy
from visexpman.engine.generic import utils

version = '0.1'
#run modes:
# - application
# - full test
# - test without hardware
run_mode = 'application'
run_mode = 'full test'
#run_mode = 'test without hardware'
#== Test parameters ==
test = (run_mode != 'application')

#For running automated tests, network operations have to be disabled for visexp_runner
enable_network = (run_mode == 'application')

#Set this to False if any of the controleld hardware (parallel port, filterwheel, etc) is not available
hardware_test = (run_mode == 'full test')

#The maximal number of pixels that can differ from the reference frame at the testing the rendering of visual stimulation patterns
pixel_difference_threshold = 10.0

if os.name == 'nt':
    reference_frames_folder = 'm:\\Raicszol\\visexpman\\test_data\\reference_frames_win'
elif os.name == 'posix':
    reference_frames_folder = '/media/Common/visexpman_data/reference_frames'

