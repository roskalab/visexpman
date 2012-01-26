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
from visexpman.engine.visual_stimulation import experiment_data
from visexpman.users.daniel import moving_dot, configurations
path = '/home/zoltan/visexp/debug/test1.hdf5'
h = hdf5io.Hdf5io(path)
machine_config = configurations.WinDev(None)
experiment_config = moving_dot.MovingDotConfig(machine_config,  None)
experiment_data.save_config(h, machine_config, experiment_config)
h.close()
pass
#path = '/home/zoltan/visexp/data/20120106/fragment_0.0_0.0_-154.0_MovingDot_1325865160_0.hdf5'
#h = hdf5io.Hdf5io(path)
#experiment_source = h.findvar('experiment_source').tostring()
#machine_config_dict = h.findvar('machine_config')
#conf = experiment.restore_experiment_config('MovingDotConfig', fragment_hdf5_handler = h, user = 'daniel')
#h.close()
#pass


