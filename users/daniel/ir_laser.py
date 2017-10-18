from visexpman.users.common import stimuli
import numpy
class IRLaser(stimuli.LaserPulseC):
    def _create_parameters(self):
        stimuli.LaserPulseC._create_parameters(self)
        self.INITIAL_DELAY=1
        self.PULSE_DURATION=[100E-3]
        self.PERIOD_TIME=[10.0]
        self.NPULSES=5
        self.LASER_AMPLITUDE=[0.3, 0.5, 0.7, 0.9, 1.1, 1.3] #

class IRLaser1Rep(stimuli.LaserPulseC):
    def _create_parameters(self):
        stimuli.LaserPulseC._create_parameters(self)
        self.INITIAL_DELAY=1
        self.PULSE_DURATION=[100E-3]
        self.PERIOD_TIME=[10.0]
        self.NPULSES=1
        self.LASER_AMPLITUDE=[0.3, 0.5, 0.7, 0.9, 1.1, 1.3] #

