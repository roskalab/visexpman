from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
import os
import numpy
import time

JITTER = 0.0
if 0:
    class Led1min5x100msStimulationConfig(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.PAUSE_BETWEEN_FLASHES = 60.0 #10.0
            self.NUMBER_OF_FLASHES = 5.0
            self.FLASH_DURATION = 100e-3
            self.FLASH_AMPLITUDE = 10.0 #10.0
            self.DELAY_BEFORE_FIRST_FLASH = 15
            self.runnable = 'LedStimulation'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
            
    class Led1min3x100ms7VStimulationConfig(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.PAUSE_BETWEEN_FLASHES = 60.0 #10.0
            self.NUMBER_OF_FLASHES = 3.0
            self.FLASH_DURATION = 100e-3
            self.FLASH_AMPLITUDE = 7.0 #10.0
            self.DELAY_BEFORE_FIRST_FLASH = 15.0
            self.runnable = 'LedStimulation'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
    
    class Led2min3x10msStimulationConfig(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.PAUSE_BETWEEN_FLASHES = 120.0 #10.0
            self.NUMBER_OF_FLASHES = 3.0
            self.FLASH_DURATION = 10e-3
            self.FLASH_AMPLITUDE = 10.0 #10.0
            self.DELAY_BEFORE_FIRST_FLASH = 15.0
            self.runnable = 'LedStimulation'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
    
    class Led3x100ms1VStimulationConfig(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.PAUSE_BETWEEN_FLASHES = 30.0 #10.0
            self.NUMBER_OF_FLASHES = 3.0
            self.FLASH_DURATION = 100e-3
            self.FLASH_AMPLITUDE = 1.0 #10.0
            self.DELAY_BEFORE_FIRST_FLASH = 15.0
            self.runnable = 'LedStimulation'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
    
    class Led3x100ms2VStimulationConfig(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.PAUSE_BETWEEN_FLASHES = 30.0 #10.0
            self.NUMBER_OF_FLASHES = 3.0
            self.FLASH_DURATION = 100e-3
            self.FLASH_AMPLITUDE = 2.0 #10.0
            self.DELAY_BEFORE_FIRST_FLASH = 15.0
            self.runnable = 'LedStimulation'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
    
    
    class Led3x100ms4VStimulationConfig(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.PAUSE_BETWEEN_FLASHES = 30.0 #10.0
            self.NUMBER_OF_FLASHES = 3.0
            self.FLASH_DURATION = 100e-3
            self.FLASH_AMPLITUDE = 4.0 #10.0
            self.DELAY_BEFORE_FIRST_FLASH = 15.0
            self.runnable = 'LedStimulation'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
            
    class Led3x100ms7VStimulationConfig(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.PAUSE_BETWEEN_FLASHES = 30.0 #10.0
            self.NUMBER_OF_FLASHES = 3.0
            self.FLASH_DURATION = 100e-3
            self.FLASH_AMPLITUDE = 7.0 #10.0
            self.DELAY_BEFORE_FIRST_FLASH = 15.0
            self.runnable = 'LedStimulation'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
    
    class Led3x100ms10VStimulationConfig(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.PAUSE_BETWEEN_FLASHES = 30.0 #10.0
            self.NUMBER_OF_FLASHES = 3.0
            self.FLASH_DURATION = 100e-3
            self.FLASH_AMPLITUDE = 10.0 #10.0
            self.DELAY_BEFORE_FIRST_FLASH = 15.0
            self.runnable = 'LedStimulation'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
    
    class Led3x100ms0p4VStimulationConfig(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.PAUSE_BETWEEN_FLASHES = 30.0 #10.0
            self.NUMBER_OF_FLASHES = 3.0
            self.FLASH_DURATION = 100e-3
            self.FLASH_AMPLITUDE = 0.4 #10.0
            self.DELAY_BEFORE_FIRST_FLASH = 30.0
            self.runnable = 'LedStimulation'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())

class LedKamill2Config(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.BEEP_AT_EXPERIMENT_START_STOP = True
        self.PAUSE_BETWEEN_FLASHES = 30.0
        self.NUMBER_OF_FLASHES = 5.0
        self.FLASH_DURATION = 5.0
        self.FLASH_AMPLITUDE = 2.0 #max 10.0
        self.DELAY_BEFORE_FIRST_FLASH = 10.0
        self.runnable = 'LedStimulation'
        self.pre_runnable = 'LedPre'
        self._create_parameters_from_locals(locals())
        
class LedKamill10Config(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.BEEP_AT_EXPERIMENT_START_STOP = True
        self.PAUSE_BETWEEN_FLASHES = 20.0
        self.NUMBER_OF_FLASHES = 3.0
        self.FLASH_DURATION = 10.0
        self.FLASH_AMPLITUDE = 2.0 #max 10.0
        self.DELAY_BEFORE_FIRST_FLASH = 10.0
        self.runnable = 'LedStimulation'
        self.pre_runnable = 'LedPre'
        self._create_parameters_from_locals(locals())
        
        
class LedPre(experiment.PreExperiment):
    def run(self):
        self.show_fullscreen(color = 0.0, duration = 0.0, flip = False)
                
class LedStimulation(experiment.Experiment):
    '''
    Flashes externally connected blue led controller by generating analog control signals using daq analog output
    '''
    def prepare(self):
        self.period_time = self.experiment_config.FLASH_DURATION + self.experiment_config.PAUSE_BETWEEN_FLASHES
#        self.stimulus_duration = self.experiment_config.NUMBER_OF_FLASHES * self.period_time
#        self.fragment_durations, self.fragment_repeats = timing.schedule_fragments(self.period_time, self.experiment_config.NUMBER_OF_FLASHES, self.machine_config.MAXIMUM_RECORDING_DURATION)
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
        if len(offsets)>1:
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

            class KamillLedStimulation(experiment.Experiment):
    '''
    Flashes externally connected blue led controller by generating analog control signals using daq analog output
    '''
    def prepare(self):
        self.period_time = self.experiment_config.FLASH_DURATION + self.experiment_config.PAUSE_BETWEEN_FLASHES
#        self.stimulus_duration = self.experiment_config.NUMBER_OF_FLASHES * self.period_time
#        self.fragment_durations, self.fragment_repeats = timing.schedule_fragments(self.period_time, self.experiment_config.NUMBER_OF_FLASHES, self.machine_config.MAXIMUM_RECORDING_DURATION)
        self.fragment_repeats = [self.experiment_config.NUMBER_OF_FLASHES]
        self.fragment_durations = [100.0]%[42.0]
        self.number_of_fragments = len(self.fragment_durations)
    
    def run(self, fragment_id = 0):
        self.show_fullscreen(color = 0.0, duration = 0.0)
        number_of_flashes_in_fragment = self.fragment_repeats[fragment_id]
        fragment_duration = self.fragment_durations[fragment_id]
        offsets = numpy.linspace(0, self.period_time * (number_of_flashes_in_fragment -1), number_of_flashes_in_fragment)
        self.led_controller.set([[[10.0], 2.0, self.experiment_config.FLASH_AMPLITUDE]], 12.0)
        self.led_controller.start()
        self.led_controller.set([[[20.0], 10.0, self.experiment_config.FLASH_AMPLITUDE]], 30.0)
        self.led_controller.start()
                  
LED_DELAY = 1.5
if 0:
    class uLedA75um1sUpDown(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.DURATION = 15.0
            self.runnable = 'uLedPilotExp'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
            
    class uLedA75um1sLeftRight(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.DURATION = 15.0
            self.runnable = 'uLedPilotExp'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
            
    class uLedA75um1sULBR(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.DURATION = 15.0
            self.runnable = 'uLedPilotExp'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
            
    class uLedA75um1sBLUR(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.DURATION = 15.0
            self.runnable = 'uLedPilotExp'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
    
    class uLedA75um2sUpDown(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.DURATION = 25.0
            self.runnable = 'uLedPilotExp'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
            
    class uLedA75um2sLeftRight(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.DURATION = 25.0
            self.runnable = 'uLedPilotExp'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
            
    class uLedA75um2sULBR(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.DURATION = 25.0
            self.runnable = 'uLedPilotExp'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
            
    class uLedA75um2sBLUR(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.DURATION = 25.0
            self.runnable = 'uLedPilotExp'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
            
            
    class uLedA75um3sUpDown(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.DURATION = 40.0
            self.runnable = 'uLedPilotExp'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
            
    class uLedA75um3sLeftRight(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.DURATION = 40.0
            self.runnable = 'uLedPilotExp'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
            
    class uLedA75um3sULBR(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.DURATION = 40.0
            self.runnable = 'uLedPilotExp'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
            
    class uLedA75um3sBLUR(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.DURATION = 40.0
            self.runnable = 'uLedPilotExp'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
            
    class uLedA75um5sUpDown(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.DURATION = 60.0
            self.runnable = 'uLedPilotExp'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
            
    class uLedA75um5sLeftRight(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.DURATION = 60.0
            self.runnable = 'uLedPilotExp'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
            
    class uLedA75um5sULBR(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.DURATION = 60.0
            self.runnable = 'uLedPilotExp'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
            
    class uLedA75um5sBLUR(experiment.ExperimentConfig):
        def _create_parameters(self):
            self.DURATION = 60.0
            self.runnable = 'uLedPilotExp'
            self.pre_runnable = 'LedPre'
            self._create_parameters_from_locals(locals())
    
    
    class uLedPilotExp(experiment.Experiment):
        def prepare(self):
            self.fragment_durations = [self.experiment_config.DURATION+LED_DELAY * 3]
        def run(self):
            self.add_text('LED array experiment', color = (1.0,  0.0,  0.0), position = utils.cr((400,300)))
            self.show_fullscreen(color = 0.0, duration = 0.0)
            time.sleep(self.experiment_config.DURATION)
