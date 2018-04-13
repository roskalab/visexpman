from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils

class Fullfield(experiment.Stimulus):
    def configuration(self):
        self.WIDTH=600#pixel
        self.HEIGHT=600#pixel
        self.ONTIME=2.0#seconds
        self.OFFTIME=2.0#seconds
        self.REPEATS=6
        self.WAIT=0.5#wait time in seconds at beginning and end of stimulus
        self.BACKGROUND=0.0
#Do not edit below this!
  
    def run(self):
        self.show_fullscreen(color=self.BACKGROUND, duration=self.WAIT)
        for r in range(self.REPEATS):
            self.block_start(('on',))
            size=utils.rc((self.HEIGHT/self.machine_config.SCREEN_UM_TO_PIXEL_SCALE,self.WIDTH/self.machine_config.SCREEN_UM_TO_PIXEL_SCALE))
            self.show_shape(shape='rect', color=1.0, duration=self.ONTIME,background_color=self.BACKGROUND,size=size)
            self.block_end()
            self.show_fullscreen(color=self.BACKGROUND, duration=self.OFFTIME)
            if self.abort:
                break
        self.show_fullscreen(color=self.BACKGROUND, duration=self.WAIT)
