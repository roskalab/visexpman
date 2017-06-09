from visexpman.users.common import stimuli
import numpy

class IRLaser(stimuli.LaserPulse):
    def stimulus_configuration(self):
        stimuli.LaserPulse.stimulus_configuration(self)
        self.INITIAL_DELAY=1
        self.PULSE_DURATION=[100E-3]
        self.PERIOD_TIME=[5.0]
        self.NPULSES=5
        self.LASER_AMPLITUDE=[5.0]

class LEDVoltageSeries(IRLaser):
    def stimulus_configuration(self):
        IRLaser.stimulus_configuration(self)
        self.LASER_AMPLITUDE=[ 0.01, 0.04, 0.16, 0.64, 0.256, 1.024, 4.096, 8.0]
        self.ZERO_VOLTAGE=-0.1

class LEDFrequencySeries(IRLaser):
    def stimulus_configuration(self):
        IRLaser.stimulus_configuration(self)
        self.NPULSES=10
        self.LASER_AMPLITUDE=[8.0]
        self.PULSE_DURATION=[2.0, 1.0, 0.5, 0.25, 0.125, 0.06]
        self.PERIOD_TIME=[4.0, 2.0, 1.0, 0.5, 0.25, 0.125]

class LEDVoltageLongDelay(IRLaser):
    def stimulus_configuration(self):
        IRLaser.stimulus_configuration(self)
        self.NPULSES=6
        self.LASER_AMPLITUDE=[8.0]
        self.PULSE_DURATION=[100E-3]
        self.PERIOD_TIME=[20.0]

class IRLaserVoltageSeries(IRLaser):
    def stimulus_configuration(self):
        IRLaser.stimulus_configuration(self)
        self.LASER_AMPLITUDE=[ 0.01563, 0.06, 0.08, 0.1, 0.4, .6, .9, 1.1, 2, 4]
        self.ZERO_VOLTAGE=-0.1


