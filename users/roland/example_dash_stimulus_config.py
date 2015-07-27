from visexpman.engine.vision_experiment import experiment

# ------------------------------------------------------------------------------
class ExampleDashStimulus(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.BARSIZE = [25, 100]
        self.GAPSIZE = [5, 20]
        self.MOVINGLINES = 3
        self.DURATION = 1
        self.SPEEDS = [1600]
        self.DIRECTIONS = range(0, 55, 5)
        self.BAR_COLOR = 0.5
        
        self.runnable='DashStimulus'
        self._create_parameters_from_locals(locals())
        
# -- Shouldn't be here:

#class NaturalMovie(experiment.ExperimentConfig):
#    def _create_parameters(self):
#        self.READ_ELECTRODE_COORDINATE =  False
#        self.JUMPING = False
#        self.FILENAME = '/home/rolandd/Videos/example_video.mov'
#        self.FRAME_RATE= 30.0
#        self.STRETCH = 4.573
#        self.runnable = 'NaturalMovieExperiment'
#        self.BACKGROUND_TIME = 0.5
#        self.BACKGROUND_COLOR = 0.5
#        self.REPETITIONS = 8
#        self._create_parameters_from_locals(locals())

class NaturalBarsConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPEED = 900.0#um/s
        self.REPEATS = 1 #5
        self.DIRECTIONS = [0] #range(0,360,90)
        self.DURATION = 1.0
        self.BACKGROUND_TIME = 0.5
        self.BACKGROUND_COLOR = 0.5
        self.runnable = 'NaturalBarsExperiment'
        self._create_parameters_from_locals(locals())





  
    