from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
import pylab

class GaussContrastConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.REPEATS = 1
        self.SPOT_SIZE = 275.0 #um
        self.FLICKERING_TIME = 33.3333#16.6 # ms  = 60 Hz this depends on projector refresh rate
        self.INTENSITY_AMPLITUDE = [0.09, 0.35, 0.09]
        self.INTENSITY_OFFSET = 0.5
        self.BACKGOUND_COLOR = 0.5
        self.TIME_COURSE =100000 #ms
        self.WAVEFORM = 'flicker'
        self.SIN_FREQUENCY = 0.33 #Hz
        self.RANDOM_FLICKERING = True #False
        self.FLICKER_PROBABILITY = 0.5 #0.0...1.0
        self.USER_FRAGMENT_NAME = 'FILENAME'
        self.runnable = 'GaussContrastExperiment'
        self._create_parameters_from_locals(locals())
        
        
class GaussContrastExperiment(experiment.Experiment):
    def prepare(self):
        random.seed()
        self.intensities = []
        if self.experiment_config.WAVEFORM == 'flicker':
            number_of_flicker_per_intensity_step = int(numpy.round(self.experiment_config.TIME_COURSE / self.experiment_config.FLICKERING_TIME, 0))
            for intensity_amplitude in self.experiment_config.INTENSITY_AMPLITUDE:
                    number_of_samples = int(self.experiment_config.TIME_COURSE /  self.experiment_config.FLICKERING_TIME)
                    intensities = [random.gauss(self.experiment_config.INTENSITY_OFFSET, intensity_amplitude * self.experiment_config.INTENSITY_OFFSET) for i in range(number_of_samples)]
                    intensities = numpy.array(intensities)
                    intensities = numpy.where(self.intensities < 0.0, 0.0, intensities)
                    intensities = numpy.where(intensities > 1.0, 1.0, intensities)
                    self.intensities.extend(intensities.tolist())

#                     print self.intensities
        elif self.experiment_config.WAVEFORM == 'sin':
            number_of_points = self.experiment_config.TIME_COURSE/1000.0 * self.machine_config.SCREEN_EXPECTED_FRAME_RATE
            self.intensities = numpy.sin(numpy.arange(number_of_points)*2*numpy.pi*self.experiment_config.SIN_FREQUENCY/self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
            print self.intensities
            pylab.plot(self.intensities)
            pylab.show()
        self.intensities = numpy.array([self.intensities]).T
            
    def run(self):
       
        for r in range(self.experiment_config.REPEATS):
            self.show_shape(shape = 'spot', 
                            duration = self.experiment_config.FLICKERING_TIME/1000.0,
                            pos = utils.rc((0,0)), 
                            color = self.intensities, 
                            background_color = self.experiment_config.BACKGOUND_COLOR,
                            size = self.experiment_config.SPOT_SIZE)
            if self.abort:
               break
        self.show_fullscreen(duration = 0, color = 0.5)