import numpy
from visexpman.engine.vision_experiment import experiment
#TODO: starting phase not OK, test grey
class GeorgGratingParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPEEDS=[150, 200,600,1200]
        self.BAR_WIDTH=300
        self.INITIAL_WAIT=5
        self.FREEZE_TIME=2
        self.DUTY_CYCLE=0.5
        self.REPEATS=1#n sweeps
        self.PATTERN='curtain'#on 'off', 'curtain', 'grating'
        self.runnable='GeorgGrating'
        self._create_parameters_from_locals(locals())
        
class GeorgGrating(experiment.Experiment):
    def prepare(self):
        #calculate mean gray
        ec=self.experiment_config
        period=ec.BAR_WIDTH/ec.DUTY_CYCLE
        nperiods=self.machine_config.SCREEN_SIZE_UM['col']/period
        nfull_periods=numpy.floor(nperiods)
        fract_period_size=nperiods-nfull_periods
        if fract_period_size>ec.BAR_WIDTH:
            fract_bar_width=ec.BAR_WIDTH
            fract_bg=fract_period_size-fract_bar_width
        else:
            fract_bar_width=fract_period_size
            fract_bg=0
        self.gray=(nfull_periods*ec.BAR_WIDTH+fract_bar_width)/self.machine_config.SCREEN_SIZE_UM['col']
        self.duty_cycle=1/ec.DUTY_CYCLE-1
        #Calculate sweep durations
        if ec.PATTERN=='curtain':
            self.durations=(self.machine_config.SCREEN_SIZE_UM['row'])/numpy.array(ec.SPEEDS)*ec.REPEATS
        else:
            self.durations=(self.machine_config.SCREEN_SIZE_UM['col']+ec.BAR_WIDTH)/numpy.array(ec.SPEEDS)*ec.REPEATS
        self.fragment_duration=[self.durations.sum()+self.durations.shape[0]*ec.FREEZE_TIME+ec.INITIAL_WAIT]
        self.duration=self.fragment_duration[0]
        
        
    def grating(self):
        ec=self.experiment_config
        for i in range(len(ec.SPEEDS)):
            spd=ec.SPEEDS[i]
            duration=self.durations[i]
            self.show_grating(orientation=0, 
                                white_bar_width =ec.BAR_WIDTH,
                               duty_cycle=self.duty_cycle,
                               duration=ec.FREEZE_TIME,
                               velocity=0)
            self.show_grating(orientation=0, 
                                white_bar_width =ec.BAR_WIDTH,
                               duty_cycle=self.duty_cycle,
                               duration=duration,
                               velocity=spd)
            
    def curtain(self):
        ec=self.experiment_config
        for i in range(len(ec.SPEEDS)):
            spd=ec.SPEEDS[i]
            duration=self.durations[i]
            contrast=1.0-self.gray
            offset=0.5*contrast+self.gray
            self.show_fullscreen(color=self.gray, duration=ec.FREEZE_TIME)
            self.show_grating(orientation=270,
                                white_bar_width =self.machine_config.SCREEN_SIZE_UM['row'], 
                                duty_cycle=1,
                                duration=duration,
                                velocity=spd,
                                color_contrast = contrast,  
                                color_offset = offset, 
                                )
    def bar(self, on=True):
        ec=self.experiment_config
        for i in range(len(ec.SPEEDS)):
            spd=ec.SPEEDS[i]
            duration=self.durations[i]
            duty_cycle=self.machine_config.SCREEN_SIZE_UM['col']/ec.BAR_WIDTH
            if on:
                bg=(self.gray*self.machine_config.SCREEN_SIZE_UM['col']-ec.BAR_WIDTH)/(self.machine_config.SCREEN_SIZE_UM['col']-ec.BAR_WIDTH)
                contrast=1.0-bg
                offset=0.5*contrast+bg
            else:
                bg=self.gray*self.machine_config.SCREEN_SIZE_UM['col']/(self.machine_config.SCREEN_SIZE_UM['col']-ec.BAR_WIDTH)
                contrast=-bg
                offset=0.5*bg
            self.show_grating(orientation=0, 
                                white_bar_width =ec.BAR_WIDTH,
                                duty_cycle=duty_cycle,
                                duration=ec.FREEZE_TIME,
                                velocity=0,
                                color_contrast = contrast,  
                                color_offset = offset)
            self.show_grating(orientation=0, 
                                white_bar_width =ec.BAR_WIDTH,
                               duty_cycle=duty_cycle,
                               duration=duration,
                               velocity=spd,
                                color_contrast = contrast,  
                                color_offset = offset)
                                
    def run(self):
        ec=self.experiment_config
        self.show_fullscreen(color=self.gray, duration=ec.INITIAL_WAIT)
        if ec.PATTERN=='grating':
            self.grating()
        elif ec.PATTERN=='on':
            self.bar(on=True)
        elif ec.PATTERN=='off':
            self.bar(on=False)
        elif ec.PATTERN=='curtain':
            self.curtain()
    
if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('georg', 'StimulusDevelopment', 'GeorgGratingParameters')
