from visexpman.engine.vision_experiment import experiment

# -----------------------------------------------------------------------------
class StimScan01MarchingSquaresSmall(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable='ReceptiveFieldExplore'
        self.SHAPE = 'rect'
        self.COLORS = [1.0, 0.0] # black, white
        self.BACKGROUND_COLOR = 0.5 # grey
        self.SHAPE_SIZE = 100.0 # um
        self.ON_TIME = 1.0 
        self.OFF_TIME = 1.0
        self.PAUSE_BEFORE_AFTER = 2.0
        self.REPEATS = 2
        self.REPEAT_SEQUENCE = 2
        self.ENABLE_RANDOM_ORDER = True
        self._create_parameters_from_locals(locals())

## -----------------------------------------------------------------------------
#class StimScan01MovingDot(experiment.ExperimentConfig):
#    def _create_parameters(self):
#        self.runnable='MovingShapeStimulus'
#    
#        self.REPETITIONS = 1 
#        self.SHAPE = 'circle'
#        self.SHAPE_CONTRAST = 1.0 
#        self.SHAPE_BACKGROUND = 0.5
#        self.SHAPE_SIZE = 10
#        self.PAUSE_BETWEEN_DIRECTIONS = 0.0
#        self.RANDOM_SPEEDS = False
#        self.RANDOM_DIRECTIONS = True
#        self.SPEEDS  = [160]
#        self.DIRECTIONS = range(0, 360, 5)
#        self._create_parameters_from_locals(locals())
#
## -----------------------------------------------------------------------------
#class StimScan01RamdomDots(experiment.ExperimentConfig):
#    def _create_parameters(self):
#        self.runnable='RandomDots'
#    
#        self.REPEATS = 1
#        self.DURATION = 10
#        '''self.SHAPE = 'circle'
#        self.SHAPE_CONTRAST = 1.0 
#        self.SHAPE_BACKGROUND = 0.5
#        self.SHAPE_SIZE = 10
#        self.PAUSE_BETWEEN_DIRECTIONS = 0.0
#        self.RANDOM_SPEEDS = False
#        self.RANDOM_DIRECTIONS = True
#        self.SPEEDS  = [160]
#        self.DIRECTIONS = range(0, 360, 5)'''
#        self._create_parameters_from_locals(locals())

# -----------------------------------------------------------------------------
class StimScan01WhiteNoise(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'WhiteNoiseStimulus'
        self.DURATION_MINS = 30.0 #30 min
        self.PIXEL_SIZE = 40.0
        #self.FLICKERING_FREQUENCY = 60.0
        self.N_WHITE_PIXELS = False
        self.COLORS = [[0.0, 0.0, 0.0],[0.0, 1.0, 1.0]]
        
        
        self._create_parameters_from_locals(locals())

# ------------------------------------------------------------------------------
class StimScan01ChirpSweep(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'ChirpSweep'
        self.DURATION_BREAKS = 1.5
        self.DURATION_FULLFIELD = 4
        self.DURATION_FREQ = 8
        self.DURATION_CONTRAST = 8
        self.CONTRAST_RANGE = [0.0, 1.0]
        self.FREQUENCY_RANGE = [1.0, 4.0]
        self.STATIC_FREQUENCY = 2.0
        self.REPEATS = 5
        self.COLOR = [0, 1, 1]
        
        self._create_parameters_from_locals(locals())
        
# ------------------------------------------------------------------------------
class StimScan01MovingGrating(experiment.ExperimentConfig):
    
    def _create_parameters(self):
        self.runnable = 'MovingGratingStimulus'
        self.REPEATS = 2
        self.N_BAR_ADVANCES_OVER_POINT = 20
        self.MARCH_TIME = 0.0
        self.GREY_INSTEAD_OF_MARCHING = False
        self.NUMBER_OF_MARCHING_PHASES = 1.0
        self.GRATING_STAND_TIME = 1.0
        self.ORIENTATIONS = range(0,360, 45)
        self.WHITE_BAR_WIDTHS = [100]
        self.VELOCITIES = [300, 1500]
        self.DUTY_CYCLES = [1]
        self.PAUSE_BEFORE_AFTER = 1.0
        
        self._create_parameters_from_locals(locals())

# ------------------------------------------------------------------------------
class StimScan01FingerPrinting(experiment.ExperimentConfig):
    
    def _create_parameters(self):
        self.runnable = 'FingerPrintingStimulus'
        
        self.FF_PAUSE_DURATION = 1.0
        self.FF_PAUSE_COLOR = 0.5
        self.DIRECTIONS = [0.0, 90.0]
        self.SPEEDS = [300.0]    
        self.DURATION = 15.0
        self.INTENSITY_LEVELS = 255
        self.REPEATS = 15
        self._create_parameters_from_locals(locals())
        
