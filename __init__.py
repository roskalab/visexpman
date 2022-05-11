import sys
#Expose most commonly used modules
from visexpman.engine.generic import (fileop, utils, signal, gui, imageop,colors)
from visexpman.engine.hardware_interface import daq
try:
    from visexpman.engine.hardware_interface.scanner_control import pmt2undistorted_image
except:
    pass



version = 'v0.4.0'
if '--vu' in sys.argv:
    USER_MODULE= str(sys.argv[sys.argv.index('--vu')+1]+".users")
else:
    USER_MODULE='visexpman.users'
#try:
#    from visexpman.applications.video_splitter import video_splitter
#except:
#    pass
