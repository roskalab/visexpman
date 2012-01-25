import visexpA.engine.datahandlers.importers as importers
import visexpA.engine.datahandlers.hdf5io as hdf5io
import visexpA.engine.datahandlers.matlabfile as matlabfile
from visexpman.engine.hardware_interface import mes_interface
from visexpman.engine.generic import utils
import os
import os.path
import numpy
import Image
from visexpman.engine.generic import introspect
from visexpman.engine.visual_stimulation import configuration
from visexpman.engine.visual_stimulation import experiment


path = '/home/zoltan/visexp/debug/test.hdf5'
h = hdf5io.Hdf5io(path)
experiment_source = h.findvar('experiment_source').tostring()
machine_config_dict = h.findvar('machine_config')
conf = experiment.restore_experiment_config('MovingDotConfig', fragment_hdf5_handler = h, user = 'daniel')
h.close()
pass
