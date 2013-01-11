from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
import pylab
            
class MovingShapeParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'spot'
        self.SHAPE_COLOR = 0.9
        self.SHAPE_BACKGROUND = 0.1
        self.SHAPE_SIZE = utils.rc((100, 100)) #um
        self.DIRECTIONS = [0, 45, 90, 135, 180, 225, 360] #degree
        self.SPEED = 200 #um/s
        self.PAUSE_BETWEEN_DIRECTIONS = 0.0
        self.runnable = 'MovingShapeExperiment'        
        self._create_parameters_from_locals(locals())

class MovingShapeExperiment(experiment.Experiment):
    def prepare(self):
        #calculate movement path
        if hasattr(self.experiment_config.SHAPE_SIZE, 'dtype'):
            shape_size = self.experiment_config.SHAPE_SIZE['col']
        else:
            shape_size = self.experiment_config.SHAPE_SIZE
        self.movement = min(self.machine_config.SCREEN_SIZE_UM['row'], self.machine_config.SCREEN_SIZE_UM['col']) - shape_size
        self.trajectories = []
        for direction in self.experiment_config.DIRECTIONS:
            start_point = utils.cr((0.5 * self.movement * numpy.cos(numpy.radians(direction)), 0.5 * self.movement * numpy.sin(numpy.radians(direction))))
            end_point = utils.cr((0.5 * self.movement * numpy.cos(numpy.radians(direction - 180.0)), 0.5 * self.movement * numpy.sin(numpy.radians(direction - 180.0))))
            spatial_resolution = self.experiment_config.SPEED/self.machine_config.SCREEN_EXPECTED_FRAME_RATE
            self.trajectories.append(utils.calculate_trajectory(start_point,  end_point,  spatial_resolution))

    def run(self):
        for i in range(len(self.trajectories)):
            for position in self.trajectories[i]:
                self.show_shape(shape = self.experiment_config.SHAPE,  
                            pos = position, 
                            color = self.experiment_config.SHAPE_COLOR, 
                            background_color = self.experiment_config.SHAPE_BACKGROUND,
                            orientation = self.experiment_config.DIRECTIONS[i], 
                            size = self.experiment_config.SHAPE_SIZE)
                if self.abort:
                    break
            self.show_fullscreen(duration = self.experiment_config.PAUSE_BETWEEN_DIRECTIONS,  color = self.experiment_config.SHAPE_BACKGROUND)
            if self.abort:
                break

class SlowContrastAdaptationParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.REPEATS = 2
        self.SPOT_SIZE = 275.0 #um
        self.FLICKERING_TIME = 30#14.2 # ms  = 70 Hz this depends on projector refresh rate
        self.INTENSITY_AMPLITUDE = [0.1, 0.4]
        self.INTENSITY_OFFSET = 0.5
        self.BACKGOUND_COLOR = 0.5
        self.TIME_COURSE = 50000 #ms
        self.WAVEFORM = 'flicker'
        self.SIN_FREQUENCY = 0.33 #Hz
        self.RANDOM_FLICKERING = True #False
        self.FLICKER_PROBABILITY = 0.5 #0.0...1.0
        self.runnable = 'SlowContrastAdaptation'
        self._create_parameters_from_locals(locals())
        
class SlowContrastAdaptation(experiment.Experiment):
    def prepare(self):
        random.seed(0)
        self.intensities = []
        if self.experiment_config.WAVEFORM == 'flicker':
            number_of_flicker_per_intensity_step = int(numpy.round(self.experiment_config.TIME_COURSE / self.experiment_config.FLICKERING_TIME, 0))
            for intensity_amplitude in self.experiment_config.INTENSITY_AMPLITUDE:
                high_intensity = self.experiment_config.INTENSITY_OFFSET + 0.5 * intensity_amplitude
                low_intensity = self.experiment_config.INTENSITY_OFFSET - 0.5 * intensity_amplitude
                if intensity_amplitude == 0.1:
                    high_intensity = 0.746
                    low_intensity = 0.676
                elif intensity_amplitude == 0.4:
                    high_intensity = 0.81+0.05
                    low_intensity = 0.622-0.05
                if self.experiment_config.RANDOM_FLICKERING:
                    for i in range(number_of_flicker_per_intensity_step):
                        if len(self.intensities) == 0:
                            last_intensity = high_intensity
                        else:
                            last_intensity = self.intensities[-1]
                        if random.random() < self.experiment_config.FLICKER_PROBABILITY:
                            if last_intensity == high_intensity:
                                self.intensities.append(low_intensity)
                            else:
                                self.intensities.append(high_intensity)
                        else:
                            self.intensities.append(last_intensity)
                else:
                    for i in range(int(0.5*number_of_flicker_per_intensity_step)):
                        self.intensities.extend([high_intensity, low_intensity])
#             print self.intensities
        elif self.experiment_config.WAVEFORM == 'sin':
            number_of_points = self.experiment_config.TIME_COURSE/1000.0 * self.machine_config.SCREEN_EXPECTED_FRAME_RATE
            self.intensities = numpy.sin(numpy.arange(number_of_points)*2*numpy.pi*self.experiment_config.SIN_FREQUENCY/self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
            print self.intensities
            #pylab.plot(self.intensities)
            #pylab.show()
            
    def run(self):
        self.show_fullscreen(duration = 1.0, color = 1.0)
        self.show_fullscreen(duration = 1.0, color = 0.0)
        for r in range(self.experiment_config.REPEATS):
            for intensity_amplitude in self.intensities:
                self.show_shape(shape = 'spot', 
                                duration = self.experiment_config.FLICKERING_TIME/1000.0,
                                pos = utils.rc((0,0)), 
                                color = intensity_amplitude, 
                                background_color = self.experiment_config.BACKGOUND_COLOR,
                                size = self.experiment_config.SPOT_SIZE)
                if self.abort:
                    break
        self.show_fullscreen(duration = 0, color = 0.0)
                            
class SinewaveContrastAdaptationParameters(SlowContrastAdaptationParameters):
    def _create_parameters(self):
        SlowContrastAdaptationParameters._create_parameters(self)
        self.WAVEFORM = 'sin'
        self._create_parameters_from_locals(locals())
        
        
class ProjectorCalibrationParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.CALIBRATION_POINTS = 32
        self.WAIT_TIME = 0.5
        self.REPEATS = 3
        self.INTENSITY_RANGE = [0.0, 0.6]
        self.runnable = 'ProjectorCalibration'        
        self._create_parameters_from_locals(locals())

class ProjectorCalibration(experiment.Experiment):
    def run(self):
        self.projector_calibration(intensity_range = self.experiment_config.INTENSITY_RANGE, 
                                  npoints = self.experiment_config.CALIBRATION_POINTS, time_per_point = self.experiment_config.WAIT_TIME, repeats = self.experiment_config.REPEATS)
