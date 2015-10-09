from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
import os
import numpy
import time

class IRLaserConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.BEEP_AT_EXPERIMENT_START_STOP = True
        self.PAUSE_BETWEEN_FLASHES = 10.0
        self.NUMBER_OF_FLASHES = 3.0
        self.FLASH_DURATION = 20.0e-3
        self.FLASH_AMPLITUDE = 5.0 #max 10.0
        self.DELAY_BEFORE_FIRST_FLASH = 10.0
        self.runnable = 'IRLaserStimulation'
        self._create_parameters_from_locals(locals())
                
class IRLaserStimulation(experiment.Experiment):
    '''
    Flashes externally connected blue led controller by generating analog control signals using daq analog output
    '''
    def prepare(self):
        self.period_time = 0*self.experiment_config.FLASH_DURATION + self.experiment_config.PAUSE_BETWEEN_FLASHES
        self.fragment_repeats = [self.experiment_config.NUMBER_OF_FLASHES]
        self.fragment_durations = [self.experiment_config.DELAY_BEFORE_FIRST_FLASH + self.experiment_config.NUMBER_OF_FLASHES*self.period_time]
        self.number_of_fragments = len(self.fragment_durations)
    
    def run(self, fragment_id = 0):
        self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
        if hasattr(self.experiment_config, 'BEEP_AT_EXPERIMENT_START_STOP') and self.experiment_config.BEEP_AT_EXPERIMENT_START_STOP:
            import winsound
            winsound.PlaySound('SystemHand',winsound.SND_ALIAS)
        self.show_fullscreen(color = 0.0, duration = 0.0)
        number_of_flashes_in_fragment = self.fragment_repeats[fragment_id]
        fragment_duration = self.fragment_durations[fragment_id]
        offsets = numpy.linspace(0, self.period_time * (number_of_flashes_in_fragment -1), number_of_flashes_in_fragment)
        if len(offsets)>2:
            offsets[2] = offsets[2]-JITTER # add a little jitter to check if brain respons periodically and not to the acutual stimulation
        if len(offsets)>3:
            offsets[4] = offsets[4] +JITTER
        time.sleep(self.experiment_config.DELAY_BEFORE_FIRST_FLASH)
        self.led_controller.set([[offsets, self.experiment_config.FLASH_DURATION, self.experiment_config.FLASH_AMPLITUDE]], fragment_duration)
        self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
        self.led_controller.start()
        self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
        for i in range(int(numpy.ceil(fragment_duration))):
            if utils.is_abort_experiment_in_queue(self.queues['gui']['in']):
                break
            else:
                time.sleep(1.0)
        if hasattr(self.experiment_config, 'BEEP_AT_EXPERIMENT_START_STOP') and self.experiment_config.BEEP_AT_EXPERIMENT_START_STOP:
            import winsound
            winsound.PlaySound('ExitWindows',winsound.SND_ALIAS)
