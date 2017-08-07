import PyDAQmx
import PyDAQmx.DAQmxConstants as DAQmxConstants
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
import numpy
import time

        
class Led2Config(experiment.ExperimentConfig):
    def _create_parameters(self):
#### EDIT FROM HERE
        self.REPEATS=6# how many repetitions of stim
        self.SCREEN_COLOR=0.0
        self.MAIN_LED_CURRENT_RANGE=[0, 500]#Change this to limit max led current ie [0, 10] for 10mA
        self.PRE_TIME=10.0
        self.OFFTIME=5.0 #visual LED off time
        self.ONTIME=5.0	#visual LED on time
        self.NFLASHES = 1 #number of steps between current_range above
        self.ENABLE_LED= True #False, this is to enable LGN LED blue one
        self.FLASH_DURATION=0.5 # for LGN LED
        self.LED_CURRENT = 0 #mA also for LGN LED
        self.LED_FLASH_DELAY=0.200 #if negative, led flashes start earlier than screen (in Seconds NOT MS)
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
        if 1:
            for vn in ['LED_FLASH_DELAY', 'FLASH_DURATION']:
                if abs(getattr(self.experiment_config, vn))>50:
                    raise RuntimeError('{1} must be in s dimension, not ms. Current value is {0}'.format(getattr(self.experiment_config, vn), vn))
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
                intensities=numpy.linspace(0, end_val, self.experiment_config.NFLASHES)
            stim_times=numpy.arange(intensities.shape[0])*(ontime+offtime)+offtime
            length=intensities.shape[0]*(ontime+offtime)+offtime
            offsets=(numpy.arange(self.experiment_config.REPEATS)*length).tolist()
            intensities=numpy.tile(intensities,self.experiment_config.REPEATS)
            self.intensities=intensities
            stim_times_all=[]
            led_times_all=[]
            for o in offsets:
                stim_times_all.append(stim_times+o)
                if (self.experiment_config.LED_FLASH_RATE ==1 or offsets.index(o)%self.experiment_config.LED_FLASH_RATE==1) and self.experiment_config.ENABLE_LED:
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
            #print self.commands,self.times
            
        
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
        self.block_trigger_order=[]
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
        self.block_trigger_order=[]
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
                if val1!=0 and val2!=0:
                    self.block_trigger_order.append('both')
                elif val1!=0:
                    self.block_trigger_order.append('led')
                elif val2!=0:
                    self.block_trigger_order.append('stim')
            elif val2==0 and val1==0 and (val1prev!=0 or val2prev!=0):
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
                if val1prev!=0 and val2prev!=0:
                    self.block_trigger_order.append('both')
                elif val1prev!=0:
                    self.block_trigger_order.append('led')
                elif val2prev!=0:
                    self.block_trigger_order.append('stim')
            elif (val1!=0 or val2!=0) and (val1prev!=0 or val2prev!=0):
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
                time.sleep(self.trigger_pulse_width)
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
                if val1!=val1prev:
                    self.block_trigger_order.append('led')
                elif val2!=val2prev:
                    self.block_trigger_order.append('stim')
            self._set_voltage(val1*self.experiment_config.LED_CURRENT2VOLTAGE,val2*self.experiment_config.LED_CURRENT2VOLTAGE)
            wait=self.times[i+1]-self.times[i]
            self.show_fullscreen(color=self.experiment_config.SCREEN_COLOR,duration=wait)
            if self.abort:
                break
        self.experiment_specific_data=utils.object2array(self.block_trigger_order)
            
        
        
        #daq_instrument.set_waveform('Dev1/ao0:1',self.waveform,sample_rate = self.fsample)
        self.show_fullscreen(color=self.experiment_config.SCREEN_COLOR)
        self.analog_output.WaitUntilTaskDone(1.0)
        self.analog_output.StopTask()
        self.analog_output.ClearTask()
    

