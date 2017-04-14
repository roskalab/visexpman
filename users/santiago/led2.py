import PyDAQmx
import PyDAQmx.DAQmxConstants as DAQmxConstants
from visexpman.engine.vision_experiment import experiment
import numpy
import time

        
class Led2Config(experiment.ExperimentConfig):
    def _create_parameters(self):
#### EDIT FROM HERE
        self.REPEATS=6 # how many repetitions of stim
        self.SCREEN_COLOR=0.0
        self.MAIN_LED_CURRENT_RANGE=[0, 900]#Change this to limit max led current
        self.PRE_TIME=10.0
        self.OFFTIME=5.0 #visual LED off time
        self.ONTIME=2.0	#visual LED on time
        self.NFLASHES = 1 #number of steps between current_range above
        self.ENABLE_LED=True #False, this is to enable LGN LED blue one
        self.FLASH_DURATION=.5 # for LGN LED
        self.LED_CURRENT = 950 #mA also for LGN LED
        self.LED_FLASH_DELAY=-0.1 #if negative, led flashes start earlier than screen
        self.LED_FLASH_RATE=2#1=led in all repetition, 2: led flash in every second repetition
#### EDIT UNTIL HERE
        self.LED_CURRENT2VOLTAGE=0.005
        self.OUTPATH='#OUTPATH'
        self.runnable = 'Led2Stimulation'
        self._create_parameters_from_locals(locals())
        
        
        
class Led2Stimulation(experiment.Experiment):
    '''
    Flashes externally connected blue led controller by generating analog control signals using daq analog output
    '''
    def prepare(self):
        if 0:
            ontime=self.experiment_config.ONTIME
            offtime=self.experiment_config.OFFTIME
            flash_offset=self.experiment_config.LED_FLASH_DELAY
            flash_duration=self.experiment_config.FLASH_DURATION
            self.mid=numpy.array(self.experiment_config.MAIN_LED_CURRENT_RANGE).mean()
            self.fsample=1000
            end_val=self.experiment_config.MAIN_LED_CURRENT_RANGE[1 if self.experiment_config.POLARITY else 0]
            if self.experiment_config.NFLASHES==1:
                intensities=numpy.array([end_val])
            else:
                intensities=numpy.linspace(self.mid, end_val, self.experiment_config.NFLASHES)
            stim_led=numpy.ones(offtime*self.fsample)*self.mid
            for i in intensities:
                stim_led=numpy.concatenate((stim_led,i*numpy.ones(ontime*self.fsample),self.mid*numpy.ones(offtime*self.fsample)))
            stim_led=numpy.tile(stim_led, self.experiment_config.REPETITIONS)
            blue_led_stim_times=(numpy.arange(intensities.shape[0])*(offtime+ontime)+offtime+flash_offset)*self.fsample
            blue_led=numpy.zeros_like(stim_led)
            if self.experiment_config.ENABLE_LED:
                for i in blue_led_stim_times:
                    blue_led[i:i+self.fsample*flash_duration]=self.experiment_config.LED_CURRENT
            self.waveform=numpy.array([stim_led,blue_led])
            self.waveform*=self.experiment_config.LED_CURRENT2VOLTAGE
            self.duration=stim_led.shape[0]/self.fsample
            self.fragment_durations = [self.duration]
            self.number_of_fragments = 1
        else:
            self.duration=self.experiment_config.PRE_TIME+self.experiment_config.REPEATS*(self.experiment_config.NFLASHES*(self.experiment_config.ONTIME+self.experiment_config.OFFTIME)+self.experiment_config.OFFTIME)
            self.mid=numpy.array(self.experiment_config.MAIN_LED_CURRENT_RANGE).mean()
            ontime=self.experiment_config.ONTIME
            offtime=self.experiment_config.OFFTIME
            flash_offset=self.experiment_config.LED_FLASH_DELAY
            flash_duration=self.experiment_config.FLASH_DURATION
            end_val=self.experiment_config.MAIN_LED_CURRENT_RANGE[1]
            if self.experiment_config.NFLASHES==1:
                intensities=numpy.array([end_val])
            else:
                intensities=numpy.linspace(self.mid, end_val, self.experiment_config.NFLASHES)
            stim_times=numpy.arange(intensities.shape[0])*(ontime+offtime)+offtime
            length=intensities.shape[0]*(ontime+offtime)+offtime
            offsets=(numpy.arange(self.experiment_config.REPEATS)*length).tolist()
            intensities=numpy.tile(intensities,self.experiment_config.REPEATS)
            self.intensities=intensities
            stim_times_all=[]
            led_times_all=[]
            for o in offsets:
                stim_times_all.append(stim_times+o)
                if offsets.index(o)%self.experiment_config.LED_FLASH_RATE==1 and self.experiment_config.ENABLE_LED:
                    led_times_all.append(stim_times+o+flash_offset)
            stim_times=numpy.array(stim_times_all).flatten()
            stim_times_end=stim_times+ontime
            led_times=numpy.array(led_times_all).flatten()
            led_times_end=led_times+flash_duration
            self.commands=[[0.0,'ledoff'], [0.0, 'stimoff']]
            self.commands.extend([[l, 'ledon'] for l in led_times])
            self.commands.extend([[l, 'ledoff'] for l in led_times_end])
            self.commands.extend([[l,'stimon'] for l in stim_times])
            self.commands.extend([[l,'stimoff'] for l in stim_times_end])
            tend=self.duration-self.experiment_config.PRE_TIME
            self.commands.extend([[tend,'ledoff'], [tend, 'stimoff']])
            self.commands.sort()
            self.times= list(set([c[0] for c in self.commands]))
            self.times.sort()
            self.trigger_pulse_width=1e-3
            print self.commands,self.times
            
        
    def _set_voltage(self,v1,v2):
        timeout=1
        v=numpy.ones((1,2))
        v[0,0]=v1
        v[0,1]=v2
        self.analog_output.WriteAnalogF64(1,
                                        True,
                                        timeout,
                                        DAQmxConstants.DAQmx_Val_GroupByChannel,
                                        v,
                                        None,
                                        None)
    
    def run(self, fragment_id = 0):
        self.analog_output = PyDAQmx.Task()
        self.analog_output.CreateAOVoltageChan('Dev1/ao0:1',
                                        'ao',
                                        0, 
                                        5, 
                                        DAQmxConstants.DAQmx_Val_Volts,
                                        None)
        self._set_voltage(0,0)
        self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
        self.show_fullscreen(color=self.experiment_config.SCREEN_COLOR,duration=self.experiment_config.PRE_TIME)
        intensity_index=0
        val1=0
        val2=0
        for i in range(len(self.times)-1):
            commands=[cmd[1] for cmd in self.commands if cmd[0] ==self.times[i]]
            val1prev=val1
            val2prev=val2
            for cmd in commands:
                if 'stimon' == cmd:
                    val2=self.intensities[intensity_index]
                    intensity_index+=1
                elif 'stimoff'==cmd:
                    val2=0
                elif 'ledon'==cmd:
                    val1=self.experiment_config.LED_CURRENT
                elif 'ledoff'==cmd:
                    val1=0
            if val2prev==0 and val1prev==0 and (val1!=0 or val2!=0):
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
            elif val2==0 and val1==0 and (val1prev!=0 or val2prev!=0):
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
            elif (val1!=0 or val2!=0) and (val1prev!=0 or val2prev!=0):
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
                time.sleep(self.trigger_pulse_width)
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
            val1*=self.experiment_config.LED_CURRENT2VOLTAGE
            val2*=self.experiment_config.LED_CURRENT2VOLTAGE
            self._set_voltage(val1,val2)
            wait=self.times[i+1]-self.times[i]
            time.sleep(wait)
            if self.abort:
                break
            
        
        
        #daq_instrument.set_waveform('Dev1/ao0:1',self.waveform,sample_rate = self.fsample)
        self.show_fullscreen(color=self.experiment_config.SCREEN_COLOR)
        self.analog_output.WaitUntilTaskDone(1.0)
        self.analog_output.StopTask()
        self.analog_output.ClearTask()
    

