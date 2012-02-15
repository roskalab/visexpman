import visexpA.engine.datahandlers.importers as importers
import visexpA.engine.datahandlers.hdf5io as hdf5io
import visexpA.engine.datahandlers.matlabfile as matlabfile
from visexpman.engine.hardware_interface import mes_interface
from visexpman.engine.generic import utils
from visexpman.engine.generic import file
import os
import os.path
import numpy
import Image
from visexpman.engine.generic import introspect
from visexpman.users.daniel import moving_dot, configurations
import pp
import random
import re
start_point = utils.cr((0, 10))
end_point = utils.cr((0, -10))
spatial_resolution = 1

res = utils.calculate_trajectory(start_point,  end_point,  spatial_resolution)
pass
