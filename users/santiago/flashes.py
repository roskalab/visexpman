import PyDAQmx
import PyDAQmx.DAQmxConstants as DAQmxConstants
import PyDAQmx.DAQmxTypes as DAQmxTypes
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import colors
import numpy,time,inspect
        
class FlashConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
#### EDIT FROM HERE
        self.PRE_TIME=10.0
        self.OFFTIME=5.0
        self.ONTIME=5.0
        self.NFLASHES = 1
        self.REPETITIONS=6
        self.POLARITY=-1#-1
        self.ENABLE_LED=True#False = no LED stim during visual stimulation
        self.LED_FLASH_DURATION=0.5
        self.LED_CURRENT = 950#mA
        self.LED_FLASH_DELAY=-.1#if negative, led flashes start earlier than screen
        self.LED_FLASH_RATE=2#1=led in all repetition, 2: led flash in every second repetition
#### EDIT UNTIL HERE
        self.LED_CURRENT2VOLTAGE=0.005
        self.OUTPATH='#OUTPATH'
        self.runnable = 'FlashStimulation'
        self._create_parameters_from_locals(locals())
        
class FlashStimulation(experiment.Experiment):
    def prepare(self):
        self.trig_time=1e-3
        intensity_range=[0.38,1.0]#specific for Santiago's setup
        delta=0.5*(intensity_range[1]-intensity_range[0])
        mid=intensity_range[0]+delta
        self.mid=mid
        if self.experiment_config.NFLASHES==1:
            self.intensities=numpy.array([mid+self.experiment_config.POLARITY*delta])
        else:
            self.intensities=numpy.linspace(mid, mid+self.experiment_config.POLARITY*delta, self.experiment_config.NFLASHES)
        self.duration=self.experiment_config.PRE_TIME+self.experiment_config.REPETITIONS*(self.intensities.shape[0]*(self.experiment_config.ONTIME+self.experiment_config.OFFTIME)+self.experiment_config.OFFTIME)
        self.fsample=1000
        self.amplitude=self.experiment_config.LED_CURRENT2VOLTAGE*self.experiment_config.LED_CURRENT
        
    def led_and_screen_flash(self,intensities, offtime,ontime,led_delay, led_flash_duration):
        self._save_stimulus_frame_info(inspect.currentframe())
        led_delay_samples=int(led_delay*self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
        offtime_samples=int(offtime*self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
        ontime_samples=int(ontime*self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
        led_flash_duration_samples=int(led_flash_duration*self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
        color_values=numpy.concatenate([numpy.concatenate((i*numpy.ones(ontime_samples),numpy.zeros(offtime_samples))) for i in intensities])
        color_values=numpy.concatenate((numpy.zeros(offtime_samples),color_values))
        led_start_indexes=numpy.where(numpy.diff(color_values)>0)[0]+1+led_delay_samples
        led_end_indexes=led_start_indexes+led_flash_duration_samples
        led_flash_index=0
        self._set_voltage(0)
        led_state=False
        for frame_i in range(color_values.shape[0]):
            if color_values[frame_i]==0:
                c=self.mid
            else:
                c=color_values[frame_i]
            self.screen.clear_screen(color = colors.convert_color(c, self.config))
            self._flip(trigger = True)                  
            if led_start_indexes.shape[0]<=led_flash_index:
                pass
            elif frame_i==led_start_indexes[led_flash_index] and led_flash_duration>0:
                self._set_voltage(self.amplitude)
                led_state=True
                if color_values[frame_i]>0:
                    self.parallel_port.set_data_bit(self.config.BLOCK_TIMING_PIN, 0)
                    time.sleep(self.trig_time)
                self.parallel_port.set_data_bit(self.config.BLOCK_TIMING_PIN, 1)
            elif frame_i==led_end_indexes[led_flash_index] and led_flash_duration>0:
                self._set_voltage(0)
                led_state=False
                led_flash_index+=1
                self.parallel_port.set_data_bit(self.config.BLOCK_TIMING_PIN, 0)
                if color_values[frame_i]>0:
                    time.sleep(self.trig_time)
                    self.parallel_port.set_data_bit(self.config.BLOCK_TIMING_PIN, 1)
            if frame_i>0:
                if color_values[frame_i]>0 and color_values[frame_i-1]==0:
                    if led_state:
                        self.parallel_port.set_data_bit(self.config.BLOCK_TIMING_PIN, 0)
                        time.sleep(self.trig_time)
                    self.parallel_port.set_data_bit(self.config.BLOCK_TIMING_PIN, 1)
                elif color_values[frame_i-1]>0 and color_values[frame_i]==0:
                    self.parallel_port.set_data_bit(self.config.BLOCK_TIMING_PIN, 0)
                    if  led_state:
                        time.sleep(self.trig_time)
                        self.parallel_port.set_data_bit(self.config.BLOCK_TIMING_PIN, 1)
        self._save_stimulus_frame_info(inspect.currentframe(), is_last = True)

    def run(self, fragment_id = 0):
        self._init_ao()
        self.show_fullscreen(color=self.mid, duration=self.experiment_config.PRE_TIME)
        for r in range(self.experiment_config.REPETITIONS):
            if self.experiment_config.ENABLE_LED:
                flash_duration=self.experiment_config.LED_FLASH_DURATION
                if r%self.experiment_config.LED_FLASH_RATE!=1:
                    flash_duration=0
            else:
                flash_duration=0
            self.led_and_screen_flash(self.intensities, 
                            self.experiment_config.ONTIME,
                            self.experiment_config.OFFTIME,
                            self.experiment_config.LED_FLASH_DELAY,
                            flash_duration)
        self._close_ao()
            
    def _set_voltage(self,v):
        timeout=1
        self.analog_output.WriteAnalogF64(1,
                                        True,
                                        timeout,
                                        DAQmxConstants.DAQmx_Val_GroupByChannel,
                                        numpy.ones((1,1))*v,
                                        None,
                                        None)
            
    def _init_ao(self):
        self.analog_output = PyDAQmx.Task()
        self.analog_output.CreateAOVoltageChan('Dev1/ao0',
                                    'ao',
                                    0, 
                                    5, 
                                    DAQmxConstants.DAQmx_Val_Volts,
                                    None)
        self._set_voltage(0)
        
    def _close_ao(self):
        self.analog_output.WaitUntilTaskDone(1.0)
        self.analog_output.StopTask()
        self.analog_output.ClearTask()


