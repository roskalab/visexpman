from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils

class WhiteNoise(experiment.Stimulus):
    def configuration(self):
        self.DURATION = 15#min
        self.PIXEL_SIZE =50.0#um
        self.ILLUMINATED_AREA=1000#um
        self.BACKGROUND=0.0
        self.WAIT=0.5#wait time in seconds at beginning and end of stimulus
        self.COLORS = [0.0, 1.0]
#Do not edit below this!
 
    def run(self):
        import numpy
        numpy.random.seed(0)
        self.show_fullscreen(color=self.BACKGROUND, duration=self.WAIT)
        self.show_white_noise(duration = self.DURATION*60,
                square_size = self.PIXEL_SIZE, screen_size=utils.rc((self.ILLUMINATED_AREA, self.ILLUMINATED_AREA)))
        self.show_fullscreen(color=self.BACKGROUND, duration=self.WAIT)


