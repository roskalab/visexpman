from visexpman.users.common import stimuli
import numpy

class IRLaser(stimuli.LaserPulse):
    def stimulus_configuration(self):
        stimuli.LaserPulse.stimulus_configuration(self)
        self.INITIAL_DELAY=1
        self.PULSE_DURATION=0.5
        self.PERIOD_TIME=5
        self.NPULSES=5
        self.LASER_AMPLITUDE=5.0
