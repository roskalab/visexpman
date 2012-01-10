import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner
from visexpman.engine.generic.parameter import Parameter
from visexpman.engine.visual_stimulation.configuration import VisionExperimentConfig
import visexpman.engine.visual_stimulation.experiment as experiment
import visexpman.engine.hardware_interface.daq_instrument as daq_instrument
import visexpman.engine.generic.utils as utils
import visexpman.engine.generic.timing as timing
import os
import serial
import numpy
import time

class GratingConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        #Timing
        #directions shall be in one fragment
        #Standing: n different phases shall be shown, phases equally distributed, vegen 0 fazisba all vissza 3 sec-ig
        #save grating pars to hdf5 including frame index based on duration
        #pre experiment: show first frame (static)
        self.GRATING_MOVE_TIME = 5.0#timing shall depend on duty cycle. Egy pont felett nn-szer kell a csiknak athaladnia
        self.GRATING_STAND_TIME = 1.0
        self.PAUSE = 1.0
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 45)
        self.WHITE_BAR_WIDTHS = [300.0]
        self.VELOCITIES = [1800.0]
        self.DUTY_CYCLES = [1.0, 0.5]
        self.runnable = 'GratingExperiment'
        self._create_parameters_from_locals(locals())
        
class ShortGratingConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        #Timing
        self.GRATING_MOVE_TIME = 5.0
        self.GRATING_STAND_TIME = 0.0
        self.PAUSE = 0.0
        #Grating parameters
        self.ORIENTATIONS = range(0, 90, 45)
        self.WHITE_BAR_WIDTHS = [200.0]
        self.VELOCITIES = [100.0]
        self.DUTY_CYCLES = [1.0]
        
        self.runnable = 'GratingExperiment'
        self._create_parameters_from_locals(locals())

class GratingExperiment(experiment.Experiment):
    def prepare(self):        
        self.stimulus_units = []
        for white_bar_width in self.experiment_config.WHITE_BAR_WIDTHS:
            for velocity in self.experiment_config.VELOCITIES:
                for duty_cycle in self.experiment_config.DUTY_CYCLES:
                    for orientation in self.experiment_config.ORIENTATIONS:
                        stimulus_unit = {}
                        stimulus_unit['white_bar_width'] = white_bar_width
                        stimulus_unit['velocity'] = velocity
                        stimulus_unit['duty_cycle'] = duty_cycle
                        stimulus_unit['orientation'] = orientation
                        self.stimulus_units.append(stimulus_unit)
        self.period_time = self.experiment_config.GRATING_MOVE_TIME + 2 * self.experiment_config.GRATING_STAND_TIME + self.experiment_config.PAUSE
        self.fragment_durations, self.fragment_repeats = timing.schedule_fragments(self.period_time, len(self.stimulus_units), self.machine_config.MAXIMUM_RECORDING_DURATION)
        self.number_of_fragments = len(self.fragment_durations)
        #Group stimulus units into fragments
        segment_pointer = 0
        self.fragmented_stimulus_units = []
        for fragment_repeats in self.fragment_repeats:            
            self.fragmented_stimulus_units.append(self.stimulus_units[segment_pointer:segment_pointer + int(fragment_repeats)])
            segment_pointer += int(fragment_repeats)

    def run(self, fragment_id):
#         self.show_fullscreen(color = 0.0, duration = self.experiment_config.PAUSE)
        for stimulus_unit in self.fragmented_stimulus_units[fragment_id]:
            self.show_grating(duration = self.experiment_config.GRATING_STAND_TIME, 
                        orientation = stimulus_unit['orientation'], 
                        velocity = 0, white_bar_width = stimulus_unit['white_bar_width'],
                        duty_cycle = stimulus_unit['duty_cycle'])
            self.show_grating(duration = self.experiment_config.GRATING_MOVE_TIME, 
                        orientation = stimulus_unit['orientation'], 
                        velocity = stimulus_unit['velocity'], white_bar_width = stimulus_unit['white_bar_width'],
                        duty_cycle = stimulus_unit['duty_cycle'])
            time.sleep(self.experiment_config.GRATING_STAND_TIME)
#             self.show_fullscreen(color = 0.0, duration = self.experiment_config.PAUSE)

class PixelSizeCalibrationConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'PixelSizeCalibration'
        self._create_parameters_from_locals(locals())

class PixelSizeCalibration(experiment.Experiment):
    '''
    Helps pixel size calibration by showing 50 and 20 um circles
    '''
    def run(self):
        pattern = 0
        self.add_text('Circle at 100,100 um, diameter is 20 um.', color = (1.0,  0.0,  0.0), position = utils.cr((10.0, 30.0)))        
        while True:
            if pattern == 0:
                self.change_text(0, text = 'Circle at 100,100 um, diameter is 20 um.\n\nPress \'n\' to switch, \'s\' to stop.')
                self.show_shape(shape = 'circle', size = 20.0, pos = utils.cr((100, 100)))
            elif pattern == 1:
                self.change_text(0, text = 'Circle at 50,50 um, diameter is 50 um.\n\nPress \'n\' to switch, \'s\' to stop.')
                self.show_shape(shape = 'circle', size = 50.0, pos = utils.cr((50, 50)))
            else:
                pass
            if 'stop' in self.command_buffer:
                break
            elif 'next' in self.command_buffer:
                pattern += 1
                if pattern == 2:
                    pattern = 0
                self.command_buffer = ''
                
class LedStimulationConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.PAUSE_BETWEEN_FLASHES = 10.0 #10.0
        self.NUMBER_OF_FLASHES = 9.0
        self.FLASH_DURATION = 500e-3
        self.FLASH_AMPLITUDE = 10.0 #10.0
        self.runnable = 'LedStimulation'
        self._create_parameters_from_locals(locals())
                
class LedStimulation(experiment.Experiment):
    '''
    10 villanas 500ms hosszan, a villanasok kozott 10s szunet, a villanasok 10V-osak.
    '''
    def prepare(self):
        self.period_time = self.experiment_config.FLASH_DURATION + self.experiment_config.PAUSE_BETWEEN_FLASHES
        self.stimulus_duration = self.experiment_config.NUMBER_OF_FLASHES * self.period_time
        self.fragment_durations, self.fragment_repeats = timing.schedule_fragments(self.period_time, self.experiment_config.NUMBER_OF_FLASHES, self.machine_config.MAXIMUM_RECORDING_DURATION)
        self.number_of_fragments = len(self.fragment_durations)
    
    def run(self, fragment_id):
        self.show_fullscreen(color = 0.0, duration = 0.0)
        number_of_flashes_in_fragment = self.fragment_repeats[fragment_id]
        fragment_duration = self.fragment_durations[fragment_id]
        offsets = numpy.linspace(0, self.period_time * (number_of_flashes_in_fragment -1), number_of_flashes_in_fragment)        
        self.devices.led_controller.set([[offsets, self.experiment_config.FLASH_DURATION, self.experiment_config.FLASH_AMPLITUDE]], fragment_duration)
        self.devices.led_controller.start()
        time.sleep(fragment_duration)
