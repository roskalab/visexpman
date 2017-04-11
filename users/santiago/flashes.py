import PyDAQmx
import PyDAQmx.DAQmxConstants as DAQmxConstants
import PyDAQmx.DAQmxTypes as DAQmxTypes
from visexpman.engine.vision_experiment import experiment
import numpy
        
class FlashConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
#### EDIT FROM HERE
        self.PRE_TIME=10.0
        self.OFFTIME=5.0
        self.ONTIME=5.0
        self.NFLASHES = 1
        self.REPETITIONS=6
        self.POLARITY=-1#-1
        self.ENABLE_LED=True
        self.LED_FLASH_DURATION=0.5
        self.LED_CURRENT = 950#mA
        self.LED_FLASH_DELAY=0.1#if negative, led flashes earlier than screen
        self.LED_FLASH_RATE=2#1=led in all repetition, 2: led flash in every second repetition
#### EDIT UNTIL HERE
        self.LED_CURRENT2VOLTAGE=0.005
        self.OUTPATH='#OUTPATH'
        self.runnable = 'FlashStimulation'
        self._create_parameters_from_locals(locals())
        
class FlashStimulation(experiment.Experiment):
    def prepare(self):
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
        on=numpy.ones((self.machine_config.SCREEN_EXPECTED_FRAME_RATE*self.experiment_config.ONTIME))
        off=numpy.zeros((self.machine_config.SCREEN_EXPECTED_FRAME_RATE*self.experiment_config.OFFTIME))
        screen_state=numpy.tile(numpy.concatenate((off,numpy.tile(numpy.concatenate((on,off)), self.intensities.shape[0]))),self.experiment_config.REPETITIONS)
        
        
        

    def run(self, fragment_id = 0):
        if self.experiment_config.ENABLE_LED:
            self._init_ao()
        self.show_fullscreen(color=self.mid, duration=self.experiment_config.PRE_TIME)
        for r in range(self.experiment_config.REPETITIONS):
            self.show_fullscreen(color=self.mid, duration=self.experiment_config.OFFTIME)
            for i in self.intensities:
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 1)
                self.show_fullscreen(color=i, duration=self.experiment_config.ONTIME)
                self.parallel_port.set_data_bit(self.config.BLOCK_TRIGGER_PIN, 0)
                self.show_fullscreen(color=self.mid, duration=self.experiment_config.OFFTIME)
        if self.experiment_config.ENABLE_LED:
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


