import sys
import pylab
import time
import os
import numpy
import shutil
import tempfile
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig
from visexpman.engine.generic import utils
from visexpman.engine.generic import file
from visexpman.engine import visexp_runner
from visexpman.engine.hardware_interface import lightmeter
from visexpA.engine.datahandlers import hdf5io

class ProjectorCalibrationSetup(VisionExperimentConfig):
    def _set_user_parameters(self):
        EXPERIMENT_CONFIG = 'ProjectorCalibrationParameters'
        COORDINATE_SYSTEM='ulcorner'
        SCREEN_UM_TO_PIXEL_SCALE= 1.0
        PLATFORM = 'standalone'
        #=== paths/data handling ===
        root_folder = tempfile.gettempdir()
        
        LOG_PATH = root_folder
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = root_folder
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        
        #=== screen ===
        FULLSCREEN = not True
        SCREEN_RESOLUTION = utils.cr([800, 600])
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        
        
        #=== Network ===
        ENABLE_UDP = False
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = 'localhost'
        self.COMMAND_RELAY_SERVER['CLIENTS_ENABLE'] = False
        self.COMMAND_RELAY_SERVER['ENABLE'] = False
        #=== hardware ===
        ENABLE_PARALLEL_PORT = False
        
#         self.GAMMA_CORRECTION = numpy.array([
#                                             [0, 12.5], 
#                                             [10, 27], 
#                                             [20, 55], 
#                                             [30, 83], 
#                                             [40, 109], 
#                                             [50, 256], 
#                                             [60, 351], 
#                                             [70, 490], 
#                                             [80, 646], 
#                                             [90, 826], 
#                                             [100, 950], 
#                                             [110, 1088], 
#                                             [120, 1245], 
#                                             [130, 1340], 
#                                             [140, 4590], 
#                                             [150, 6528], 
#                                             [160, 8390], 
#                                             [170, 11530], 
#                                             [180, 14170], 
#                                             [190, 16400], 
#                                             [200, 17680], 
#                                             [210, 18790], 
#                                             [220, 19160], 
#                                             [230, 19250], 
#                                             [240, 19250], 
#                                             [255, 19260], 
#                                             ])

        self._create_parameters_from_locals(locals())      
        
class ProjectorCalibrationParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.CALIBRATION_POINTS = 3
        self.SETTLING_TIME = 0.5
        self.REPEATS = 1
        self.INTENSITY_RANGE = [0.0, 0.6]
        self.SAMPLES_PER_STEP = 10
        self.runnable = 'ProjectorCalibration'        
        self._create_parameters_from_locals(locals())

class ProjectorCalibration(experiment.Experiment):
    def prepare(self):
        if self.machine_config.OS == 'win':
            self.lightmeter = lightmeter.LightMeter(self.machine_config)
            self.ref_intensities = []
            self.measured_intensities = []
        
    def run(self):
        self.projector_calibration(intensity_range = self.experiment_config.INTENSITY_RANGE, 
                                  npoints = self.experiment_config.CALIBRATION_POINTS, time_per_point = self.experiment_config.SETTLING_TIME, repeats = self.experiment_config.REPEATS)
        if hasattr(self, 'lightmeter'):
            self.calculate_gamma_curve()
            self.lightmeter.release_instrument()
            
    def measure_light_power(self, reference_intensity):
        if hasattr(self, 'lightmeter'):
            p = []
            for i in range(self.experiment_config.SAMPLES_PER_STEP):
                p.append(self.lightmeter.read_power())
            self.ref_intensities.append(reference_intensity)
            self.measured_intensities.append(numpy.array(p).mean())
            
    def calculate_gamma_curve(self):
        print numpy.array([self.ref_intensities, self.measured_intensities])
        h = hdf5io.Hdf5io('c:\\visexp\\data\\calib.hdf5', filelocking = False)
        h.ref_intensities = self.ref_intensities
        h.measured_intensities = self.measured_intensities
        h.save(['ref_intensities', 'measured_intensities'], overwrite = True)
        h.close()

if __name__=='__main__':    
    v = visexp_runner.VisionExperimentRunner('zoltan', 'ProjectorCalibrationSetup')
    v.run_experiment()
    hdf5io.lockman.__del__()
    
