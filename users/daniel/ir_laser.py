from visexpman.users.common import stimuli
from visexpman.engine.vision_experiment import experiment
import numpy

class LaserPulseC(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.INITIAL_DELAY=5
        self.PULSE_DURATION=[100e-3]
        self.PERIOD_TIME=[10.0]
        self.NPULSES=3
        self.LASER_AMPLITUDE=[1.0]
        self.SAMPLE_RATE=1000
        self.ZERO_VOLTAGE=0.0
        self.runnable = 'LaserPulseE'
        self._create_parameters_from_locals(locals())

class IRLaser(stimuli.LaserPulseC):
    def _create_parameters(self):
        stimuli.LaserPulseC._create_parameters(self)
        self.INITIAL_DELAY=5 #
        self.PULSE_DURATION=[100E-3]
        self.PERIOD_TIME=[10.0]
        self.NPULSES=5
        self.LASER_AMPLITUDE=[0.3, 0.5, 0.7, 0.9, 1.1, 1.3] #

class IRLaser980(stimuli.LaserPulseC):
    def _create_parameters(self):
        stimuli.LaserPulseC._create_parameters(self)
        self.INITIAL_DELAY=5 #
        self.PULSE_DURATION=[100E-3]
        self.PERIOD_TIME=[10.0]
        self.NPULSES=5
        self.LASER_AMPLITUDE=[1.35, 1.5, 1.75, 2.05, 2.25, 2.47] #

class IRLaser980a(stimuli.LaserPulseC):
    def _create_parameters(self):
        stimuli.LaserPulseC._create_parameters(self)
        self.INITIAL_DELAY=5 #
        self.PULSE_DURATION=[100E-3]
        self.PERIOD_TIME=[10.0]
        self.NPULSES=5
        self.LASER_AMPLITUDE=[1.5, 1.75, 2.05, 2.25, 2.47, 2.8] #

class IRLaser1Rep(stimuli.LaserPulseC):
    def _create_parameters(self):
        stimuli.LaserPulseC._create_parameters(self)
        self.INITIAL_DELAY=5 #
        self.PULSE_DURATION=[100E-3]
        self.PERIOD_TIME=[10.0]
        self.NPULSES=1
        self.LASER_AMPLITUDE=[0.3, 0.5, 0.7, 0.9, 1.1, 1.3] #
