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


class IRLaser755(stimuli.LaserPulseC):
    def _create_parameters(self):
        stimuli.LaserPulseC._create_parameters(self)
        self.INITIAL_DELAY=5 #
        self.PULSE_DURATION=[100E-3]
        self.PERIOD_TIME=[10.0]
        self.NPULSES=5
        self.LASER_AMPLITUDE=[0.2, 0.3, 0.5, 0.7, 0.9, 1.1, 1.3] #

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

class IRLaser980b(stimuli.LaserPulseC):
    def _create_parameters(self):
        stimuli.LaserPulseC._create_parameters(self)
        self.INITIAL_DELAY=5 #
        self.PULSE_DURATION=[100E-3]
        self.PERIOD_TIME=[10.0]
        self.NPULSES=5
        self.LASER_AMPLITUDE=[1.75, 2.05, 2.25, 2.47, 2.6, 2.8] #

class IRLaser910high(stimuli.LaserPulseC):
    def _create_parameters(self):
        stimuli.LaserPulseC._create_parameters(self)
        self.INITIAL_DELAY=5 #
        self.PULSE_DURATION=[100E-3]
        self.PERIOD_TIME=[10.0]
        self.NPULSES=5
        self.LASER_AMPLITUDE=[1.23, 1.365] #

class IRLaser980high(stimuli.LaserPulseC):
    def _create_parameters(self):
        stimuli.LaserPulseC._create_parameters(self)
        self.INITIAL_DELAY=5 #
        self.PULSE_DURATION=[100E-3]
        self.PERIOD_TIME=[10.0]
        self.NPULSES=5
        self.LASER_AMPLITUDE=[2.6, 2.8] #

class IRLaser980highwait(stimuli.LaserPulseC):
    def _create_parameters(self):
        stimuli.LaserPulseC._create_parameters(self)
        self.INITIAL_DELAY=5 #
        self.PULSE_DURATION=[100E-3]
        self.PERIOD_TIME=[30.0]
        self.NPULSES=5
        self.LASER_AMPLITUDE=[2.6, 2.8] #

class IRLaser1Rep(stimuli.LaserPulseC):
    def _create_parameters(self):
        stimuli.LaserPulseC._create_parameters(self)
        self.INITIAL_DELAY=5 #
        self.PULSE_DURATION=[100E-3]
        self.PERIOD_TIME=[10.0]
        self.NPULSES=1
        self.LASER_AMPLITUDE=[0.3, 0.5, 0.7, 0.9, 1.1, 1.3] #

class IRLaserCal910(stimuli.LaserPulseC):
    def _create_parameters(self):
        stimuli.LaserPulseC._create_parameters(self)
        self.INITIAL_DELAY=5 #
        self.PULSE_DURATION=[5]
        self.PERIOD_TIME=[10.0]
        self.NPULSES=1
        self.LASER_AMPLITUDE=[0.5, 0.7, 0.9, 1.1, 1.3, 1.4] #
        self.LASER_AMPLITUDE=[1.23]
        # Measured with ND2 filter and thorlabs s170c:
        # 0.008, 0.3, 0.5, 7.3, 14.9, 22.7

class IRLaserCal980(stimuli.LaserPulseC):
    def _create_parameters(self):
        stimuli.LaserPulseC._create_parameters(self)
        self.INITIAL_DELAY=5 #
        self.PULSE_DURATION=[5]
        self.PERIOD_TIME=[10.0]
        self.NPULSES=1
        self.LASER_AMPLITUDE=[2.8]#, 2.6, 2.8] #
#	self.LASER_AMPLITUDE=[1.75] #
        # Measured with ND2 fitler and thorlabd s170c:
        #                    0.04, 0.09, 4.5, 11.6, 19.4, 23.8, 27.2, 30.5
        # from:              0.03, 0.08, 2.8, 9.8, 16.9, 21.8, 24.1, 28.7

