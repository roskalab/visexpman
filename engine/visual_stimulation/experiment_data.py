import visexpA.engine.datahandlers.hdf5io as hdf5io
from visexpman.engine.generic import utils
import copy

#== Saving/loading data to hdf5 ==
def save_config(hdf5, machine_config, experiment_config = None):
    hdf5.machine_config = copy.deepcopy(machine_config.get_all_parameters()) #The deepcopy is necessary to avoid conflict between daqmx and hdf5io
    hdf5.save('machine_config')
    hdf5.experiment_config = experiment_config.get_all_parameters()
    hdf5.save('experiment_config')
    
def save_position(hdf5, stagexyz, objective_z = None):
    '''
    z is the objective's position, since this is more frequently used than z_stage.
    '''
    hdf5.position = utils.pack_position(stagexyz, objective_z)
    hdf5.save('position')
    
def read_master_position(path):
        hdf5_handler = hdf5io.Hdf5io(path)
        master_position = {}
        if hdf5_handler.findvar('master_position') != None:
            master_position = hdf5_handler.master_position
        hdf5_handler.close()
        return master_position
