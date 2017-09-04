from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class NaturalBarsExperiment1(experiment.Stimulus):
    def configuration(self):
        self.SPEED = [800, 400,1500.0]#um/s
        self.SPEED = [400]
        self.REPEATS = 2 #5
        self.DIRECTIONS = [0] #range(0,360,90)
        self.DURATION = 5
        self.BACKGROUND_TIME = 0
        self.BACKGROUND_COLOR = 0.5
        self.ALWAYS_FLY_IN_OUT = not False

    def calculate_stimulus_duration(self):
        self.duration = self.DURATION*3*2
        
    def run(self):
        for i in range(3):
            self.show_fullscreen(duration = self.DURATION/2, color =  self.BACKGROUND_COLOR)
            self.block_start()
            self.show_fullscreen(duration = self.DURATION, color =  1.0)
            self.block_end()
            self.show_fullscreen(duration = self.DURATION/2, color =  self.BACKGROUND_COLOR)

class Flash(experiment.Stimulus):
    def configuration(self):
        self.DURATION=0.5
        
    def calculate_stimulus_duration(self):
        self.duration=self.DURATION*3
        
    def run(self):
        self.show_fullscreen(color=0.0,duration=self.DURATION)
        self.show_fullscreen(color=0.5,duration=self.DURATION)
        self.show_fullscreen(color=1.0,duration=self.DURATION)

if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('zoltan', 'StimulusDevelopment', 'NaturalBarsConfig1')
