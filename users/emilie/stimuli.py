from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
import visexpman.users.common.stimuli as st

class Flash(experiment.Stimulus):
    def stimulus_configuration(self):
        self.BASELINE_TIME=5.0
        self.ON_TIME=0.5
        self.OFF_TIME=0.5
        self.NFLASHES=10
        self.ON_COLOR=1.0
        self.OFF_COLOR=0.0
        
    def calculate_stimulus_duration(self):
        self.duration=self.NFLASHES*(self.ON_TIME+self.OFF_TIME)+self.BASELINE_TIME
        
    def run(self):
        for i in range(self.NFLASHES):
            self.show_fullscreen(color=self.ON_COLOR,duration=self.ON_TIME,is_block=True)
            self.show_fullscreen(color=self.OFF_COLOR,duration=self.OFF_TIME)
            
class MovingBar(st.MovingBarTemplate):
    def stimulus_configuration(self):
        self.BAR_WIDTH=5000.0
        self.BAR_HEIGHT=300.0
        self.SPEED=1000
        self.DIRECTIONS=range(0,360,90)
        self.COLOR=1.0
        self.BACKGROUND=0.0
        self.PAUSE_BETWEEN_SWEEPS=1.0
        self.REPETITIONS=1
        
