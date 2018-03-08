from visexpman.engine.vision_experiment import experiment

class WhiteNoise(experiment.Stimulus):
    def configuration(self):
        self.DURATION = 1#min
        self.PIXEL_SIZE =75.0#um
        self.BACKGROUND=0.0
        self.WAIT=0.5#wait time in seconds at beginning and end of stimulus
        self.COLORS = [0.0, 1.0]
#Do not edit below this!
 
    def run(self):
        self.show_fullscreen(color=self.BACKGROUND, duration=self.WAIT)
        self.show_white_noise(duration = self.DURATION*60,
                square_size = self.PIXEL_SIZE)
        self.show_fullscreen(color=self.BACKGROUND, duration=self.WAIT)


