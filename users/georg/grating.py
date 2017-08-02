import numpy
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
class GeorgGratingParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPEEDS=[150, 200,600,1200]
        self.BAR_WIDTH=300
        self.INITIAL_WAIT=5
        self.FREEZE_TIME=2
        self.DUTY_CYCLE=0.5
        self.REPEATS=1#n sweeps
        self.PATTERN='off'#on 'off', 'curtain', 'grating'
        self.runnable='GeorgGrating'
        self._create_parameters_from_locals(locals())
        
class GeorgGrating(experiment.Experiment):
    def prepare(self):
        #calculate mean gray
        self.orientation=0
        ec=self.experiment_config
        period=ec.BAR_WIDTH/ec.DUTY_CYCLE
        nperiods=self.machine_config.SCREEN_SIZE_UM['col']/period
        nfull_periods=numpy.floor(nperiods)
        fract_period_size=nperiods-nfull_periods
        if fract_period_size>ec.BAR_WIDTH/period:
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
            self.show_grating(orientation=self.orientation, 
                                white_bar_width =ec.BAR_WIDTH,
                               duty_cycle=self.duty_cycle,
                               duration=ec.FREEZE_TIME,
                               display_area=self.machine_config.SCREEN_SIZE_UM,
                               velocity=0)
            self.show_grating(orientation=self.orientation, 
                                white_bar_width =ec.BAR_WIDTH,
                               duty_cycle=self.duty_cycle,
                               duration=duration,
                               display_area=self.machine_config.SCREEN_SIZE_UM,
                               velocity=spd)
            
    def curtain(self):
        ec=self.experiment_config
        for i in range(len(ec.SPEEDS)):
            spd=ec.SPEEDS[i]
            duration=self.durations[i]
            contrast=1.0-self.gray
            offset=0.5*contrast+self.gray
            w=self.machine_config.SCREEN_SIZE_UM['col']
            h=self.machine_config.SCREEN_SIZE_UM['row']
            sf=(h-0.5*(w-h))/(2*h)*360
            self.show_fullscreen(color=self.gray, duration=ec.FREEZE_TIME)
            self.show_grating(orientation=270,
                                white_bar_width =self.machine_config.SCREEN_SIZE_UM['row'], 
                                duty_cycle=1,
                                duration=duration,
                                display_area=utils.rc((self.machine_config.SCREEN_SIZE_UM['col'],self.machine_config.SCREEN_SIZE_UM['col'])),
                                velocity=spd,
                                color_contrast = contrast,  
                                color_offset = offset,
                               starting_phase=sf 
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
            self.show_grating(orientation=self.orientation, 
                                white_bar_width =ec.BAR_WIDTH,
                                duty_cycle=duty_cycle,
                                duration=ec.FREEZE_TIME,
                                velocity=0,
                                display_area=self.machine_config.SCREEN_SIZE_UM,
                                color_contrast = contrast,  
                                color_offset = offset)
            self.show_grating(orientation=self.orientation, 
                                white_bar_width =ec.BAR_WIDTH,
                               duty_cycle=duty_cycle,
                               duration=duration,
                               velocity=spd,
                               display_area=self.machine_config.SCREEN_SIZE_UM,
                                color_contrast = contrast,  
                                color_offset = offset)
                                
    def run(self):
        self.screen.start_frame_capture=True
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
        self.screen.start_frame_capture=False
        
def test_gray(folder):
    from pylab import plot, show,ylabel,xlabel,savefig,ylim
    from visexpman.engine.generic import fileop
    from PIL import Image
    import os
    gray=[numpy.asarray(Image.open(f))[:,:,0].mean()/255 for f in fileop.listdir(folder)]
    t=numpy.arange(len(gray))/60.
    plot(t,gray)
    xlabel('time [s]')
    ylabel('mean gray level, 1.0=white')
    ylim([0.2,0.8])
    #show()
    
def pngs2video(folder):
    import subprocess,os
    c='avconv -y -r 60 -f image2 -i /tmp/{0}/captured_%10d.png /tmp/{0}.mp4'.format(os.path.basename(folder))
    subprocess.call(c, shell = True)
        
if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    if 1:
        protocols=['on', 'off', 'grating','curtain']
        for sn in protocols:
            test_gray('/tmp/'+sn)
            pngs2video('/tmp/'+sn)
        from pylab import savefig,legend
        legend(protocols)
        savefig('/tmp/means.png',dpi=200)
    else:
        stimulation_tester('georg', 'StimulusDevelopment', 'GeorgGratingParameters',ENABLE_FRAME_CAPTURE=True)
