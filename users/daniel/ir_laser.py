from visexpman.users.common import stimuli
import numpy
class IRLaser(stimuli.LaserPulseC):
    def _create_parameters(self):
        stimuli.LaserPulseC._create_parameters(self)
        self.INITIAL_DELAY=1
        self.PULSE_DURATION=[100E-3]
        self.PERIOD_TIME=[5.0]
        self.NPULSES=5
        self.LASER_AMPLITUDE=[1.0, 2.0, 5.0]


