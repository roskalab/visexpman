from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class MovingBar(experiment.Stimulus):
    def configuration(self):
        self.BAR_WIDTH=1000.0#um on retina
        self.BAR_HEIGHT=500.0#um on retina
        self.SPEED=800#um/s on retina
        self.DIRECTIONS=[0, 45, 90, 135, 180, 225, 270, 315]
        self.COLOR=1.0
        self.BACKGROUND=0.0
        self.PAUSE_BETWEEN_SWEEPS=0.0#seconds
        self.WAIT=0.5#wait time in seconds at beginning and end of stimulus
        self.REPETITIONS=6
#Do not edit below this!
        
    def run(self):
        self.show_fullscreen(color=self.BACKGROUND, duration=self.WAIT)
        for r in range(self.REPETITIONS):
            for d in self.DIRECTIONS:
                self.block_start(('sweep',d))
                self.moving_shape(utils.rc((self.BAR_HEIGHT, self.BAR_WIDTH)), 
                            [self.SPEED], [d], 'rect',
                            self.COLOR, self.BACKGROUND, shape_starts_from_edge=True)
                self.block_end()
                self.show_fullscreen(color=self.BACKGROUND, duration=self.PAUSE_BETWEEN_SWEEPS)
        self.show_fullscreen(color=self.BACKGROUND, duration=self.WAIT)

