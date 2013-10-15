import sys
import pylab
import time
import os
import os.path
import numpy
import shutil
import tempfile
import copy
import argparse
argparser = argparse.ArgumentParser()
argparser.add_argument('--calibrate', help='Run calibration process', action='store_true')
argparser.add_argument('--check_calibration', help='Rerun calibration process with loading gamma.hdf5 and it is not overwritten', action='store_true')
argparser.add_argument('--find_linear_range', help='Runs calibration with different intensity ranges', action='store_true')
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
        CALIBRATION_OUTPUT_PATH = 'c:\\visexp\\data'
        
        #=== screen ===
        FULLSCREEN = True
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
        
        self.LIGHT_METER = {}
        self.LIGHT_METER['ENABLE'] = True
        self.LIGHT_METER['AVERAGING'] = 200
        
        gamma_correction_path = os.path.join(CALIBRATION_OUTPUT_PATH, 'gamma.hdf5')
        if os.path.exists(gamma_correction_path) and getattr(argparser.parse_args(), 'check_calibration'):
            self.GAMMA_CORRECTION = copy.deepcopy(hdf5io.read_item(gamma_correction_path, 'gamma_correction', filelocking = False))
        self._create_parameters_from_locals(locals())      
        
class ProjectorCalibrationParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.CALIBRATION_POINTS = 100
        self.SETTLING_TIME = 1.0
        self.REPEATS = 2
        self.INTENSITY_RANGE = [0.0, 1.0]
        self.SAMPLES_PER_STEP = 10
        self.runnable = 'ProjectorCalibration'        
        self._create_parameters_from_locals(locals())
        
class FindLinearRangeParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.CALIBRATION_POINTS = 30
        self.SETTLING_TIME = 1.0
        self.REPEATS = 2
        self.INTENSITY_RANGE = [0.0, 1.0]
        self.MAX_INTENSITIES = [0.6, 0.8, 1.0]
        self.SAMPLES_PER_STEP = 10
        self.runnable = 'ProjectorCalibration'        
        self._create_parameters_from_locals(locals())


class ProjectorCalibration(experiment.Experiment):
    def prepare(self):
        if self.machine_config.OS == 'win' and hasattr(self.machine_config, 'LIGHT_METER') and self.machine_config.LIGHT_METER['ENABLE']:
            self.lightmeter = lightmeter.LightMeter(self.machine_config)
            for i in range(30):#dummy reads, might help
                self.lightmeter.read_power()
            self.ref_intensities = []
            self.measured_intensities = []
            self.raw_measured_intensities = []
            self.raw_ref_intensities = []
        
    def run(self):
        if hasattr(self.experiment_config, 'MAX_INTENSITIES'):
            for max_intensity in self.experiment_config.MAX_INTENSITIES:
                self.projector_calibration(intensity_range = [0.0, max_intensity], 
                                  npoints = self.experiment_config.CALIBRATION_POINTS, time_per_point = self.experiment_config.SETTLING_TIME, repeats = self.experiment_config.REPEATS)
        else:
            self.projector_calibration(intensity_range = self.experiment_config.INTENSITY_RANGE, 
                                  npoints = self.experiment_config.CALIBRATION_POINTS, time_per_point = self.experiment_config.SETTLING_TIME, repeats = self.experiment_config.REPEATS)
        time.sleep(0.5)
        if hasattr(self, 'lightmeter'):
            self.lightmeter.release_instrument()
            
    def measure_light_power(self, reference_intensity):
        if hasattr(self, 'lightmeter'):
            p = []
            for i in range(self.experiment_config.SAMPLES_PER_STEP):
                p.append(self.lightmeter.read_power())
            self.ref_intensities.append(reference_intensity)
            self.measured_intensities.append(numpy.array(p).mean())
            self.raw_measured_intensities.extend(p)
            self.raw_ref_intensities.extend(len(p)*[reference_intensity])
            
    def calculate_gamma_correction(self):
        if self.abort:
            return
        gamma_correction = self.join_gamma_correction(numpy.array([self.ref_intensities, self.measured_intensities]).T)
        output_file = os.path.join(self.machine_config.CALIBRATION_OUTPUT_PATH,os.path.split(self.fragment_files[0].filename)[1])
        shutil.move(self.fragment_files[0].filename, output_file)
        h = hdf5io.Hdf5io(output_file, filelocking = False)
        h.raw_ref_intensities = self.raw_ref_intensities
        h.raw_gamma_correction = numpy.array([self.raw_ref_intensities, self.raw_measured_intensities]).T
        h.gamma_correction = gamma_correction
        h.save(['gamma_correction', 'raw_gamma_correction'], overwrite = True)
        #Save gamma curve to mat file too
        import scipy.io
        data = {}
        data['raw_gamma_correction']=h.raw_gamma_correction
        data['gamma_correction']=h.gamma_correction
        scipy.io.savemat(os.path.join(os.path.split(output_file)[0], 'gamma.mat'), data, oned_as = 'column')
        data2txt = data['gamma_correction']
        normalized_intensity = data2txt[:,1]/data2txt[:,1].max()
        data2txt = data2txt.T.tolist()
        data2txt.append(normalized_intensity.tolist())
        if not getattr(argparser.parse_args(), 'check_calibration'):
            numpy.savetxt(os.path.join(os.path.split(output_file)[0], 'gamma.txt'), numpy.array(data2txt).T, fmt = '%2.9f')
        h.close()
        
        if not getattr(argparser.parse_args(), 'check_calibration'):
            shutil.copy(output_file, os.path.join(os.path.split(output_file)[0], 'gamma.hdf5'))
        pylab.figure(1)
        pylab.plot(self.raw_ref_intensities, self.raw_measured_intensities)
        pylab.figure(2)
        pylab.plot(self.raw_measured_intensities)
        pylab.figure(3)
        pylab.plot(gamma_correction[:,0], gamma_correction[:, 1])
        pylab.show()
        
    def join_gamma_correction(self, gamma_correction):
        ncurves = 2*self.experiment_config.REPEATS
        curve_length = gamma_correction.shape[0]/ncurves
        joined = numpy.zeros((curve_length,2))
        joined[:,0] = gamma_correction[:curve_length,0]
        pylab.figure(0)
        for rep in range(self.experiment_config.REPEATS):
            #rising part
            joined[:,1] += gamma_correction[rep*2*curve_length: (2*rep+1)*curve_length,1]/ncurves
            pylab.plot(gamma_correction[rep*2*curve_length: (2*rep+1)*curve_length,1]/ncurves)
            #falling part
            fp = gamma_correction[(2*rep+1)*curve_length: 2*(rep+1)*curve_length,1][::-1]/ncurves
            joined[:,1] += fp
            pylab.plot(fp)
        pylab.legend(map(str, range(ncurves)))
        #insert correction value for out of range intensities
        joined = joined.tolist()
        if self.experiment_config.INTENSITY_RANGE[0] > 0.0:
            joined.insert(0, [0.0, joined[0][1]])
        if self.experiment_config.INTENSITY_RANGE[1] < 1.0:
            joined.append([1.0, joined[-1][1]])
        joined = numpy.array(joined)
        return joined

if __name__=='__main__':
    if getattr(argparser.parse_args(), 'find_linear_range'):
        expname = 'FindLinearRangeParameters'
    else:
        expname = 'ProjectorCalibrationParameters'
    v = visexp_runner.VisionExperimentRunner('zoltan', 'ProjectorCalibrationSetup')
    v.run_experiment(expname)
    v.experiment_config.runnable.calculate_gamma_correction()
#    hdf5io.lockman.__del__()
    
