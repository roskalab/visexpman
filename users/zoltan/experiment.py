import numpy
from visexpman.users.common import grating_base
from visexpman.engine.vision_experiment import experiment

class MyMovingGratingConfig(grating_base.MovingGratingNoMarchingConfig):
    pass

class ZoltanMovingGratingConfig(grating_base.MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        grating_base.MovingGratingNoMarchingConfig._create_parameters(self)
        self.ENABLE_FLASH = False
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 6
        self.MARCH_TIME = 3
        self.GRATING_STAND_TIME = 0.5
        #Grating parameters        
        self.ORIENTATIONS = [0,45,90,135,180,225,270,315][::2]
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.PAUSE_BEFORE_AFTER = 0.0
        self.REPEATS = 1
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'BlackPre'
        self._create_parameters_from_locals(locals())   

class ZoltanMovingGratingConfig1(ZoltanMovingGratingConfig):
    def _create_parameters(self):
        ZoltanMovingGratingConfig._create_parameters(self)
        self.ORIENTATIONS = [0,45,90,135,180,225,270,315]


class PhasesGratingConfig(grating_base.MovingGratingConfig):
    def _create_parameters(self):
        grating_base.MovingGratingConfig._create_parameters(self)
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.MARCH_TIME = 4.0
        self.GRATING_STAND_TIME = 4.0
        #Grating parameters
        self.ORIENTATIONS = [0, 180]
        self.STARTING_PHASES = [0]*len(self.ORIENTATIONS)
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.DUTY_CYCLES = [3.0] #put 1.0 to a different config
        self.REPEATS = 2
        self.PAUSE_BEFORE_AFTER = 3.0
        self.PHASES={}
        for o in self.ORIENTATIONS:
            duration=5.0#sec
            f=1
            self.PHASES[o]=100*numpy.sin(f*numpy.linspace(0,1,int(duration*self.machine_config.SCREEN_EXPECTED_FRAME_RATE))*numpy.pi*2)
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
        self._create_parameters_from_locals(locals())

from visexpman.engine.generic import utils
class ReceptiveFieldTest(experiment.ExperimentConfig):
    def _create_parameters(self):
	# x = 4248 um,  y = 2389 um
        self.SHAPE = 'rect'
        self.COLORS = [1.0]
        self.BACKGROUND_COLOR = 0
        self.NROWS = 3#10
        self.NCOLUMNS = 6#18
        self.SIZE_DIMENSION='angle'
        self.DISPLAY_SIZE = utils.rc((50.0,90.0))
        self.DISPLAY_CENTER = utils.rc((25,45.0))
        self.ON_TIME = 2.0#0.8
        self.OFF_TIME = 0#0.8
        self.REPEATS = 1 
        self.REPEAT_SEQUENCE = 1
        self.ENABLE_RANDOM_ORDER =  False
        self.runnable='ReceptiveFieldExploreZ'
        self._create_parameters_from_locals(locals())


class ReceptiveFieldExploreZ(experiment.Experiment):
    '''
    Repeats: flash or sequence
    
    Supported use cases: fixed size squares are presented with no gaps and no overlaps. Fractional squares are not shown at the edges
    '''
    def prepare(self):
#	print self.machine_config.SCREEN_SIZE_UM
        shape_size, nrows, ncolumns, display_size, shape_colors, background_color = \
                self._parse_receptive_field_parameters(self.experiment_config.SHAPE_SIZE if hasattr(self.experiment_config, 'SHAPE_SIZE') else None,
                                                    self.experiment_config.NROWS if hasattr(self.experiment_config, 'NROWS') else None,
                                                    self.experiment_config.NCOLUMNS if hasattr(self.experiment_config, 'NCOLUMNS') else None,
                                                    self.experiment_config.DISPLAY_SIZE if hasattr(self.experiment_config, 'DISPLAY_SIZE') else None,
                                                    self.experiment_config.COLORS,
                                                    self.experiment_config.BACKGROUND_COLOR)
        self.stimulus_duration, positions= self.receptive_field_explore_durations_and_positions(shape_size=shape_size, 
                                                                            nrows = nrows,
                                                                            ncolumns = ncolumns,
                                                                            shape_colors = shape_colors,
                                                                            flash_repeat = self.experiment_config.REPEATS,
                                                                            sequence_repeat = self.experiment_config.REPEAT_SEQUENCE,
                                                                            on_time = self.experiment_config.ON_TIME,
                                                                            off_time = self.experiment_config.OFF_TIME)
        self.fragment_durations=[self.stimulus_duration]
        
            
    def run(self):
        self.receptive_field_explore(self.experiment_config.SHAPE_SIZE if hasattr(self.experiment_config, 'SHAPE_SIZE') else None, 
                                    self.experiment_config.ON_TIME,
                                    self.experiment_config.OFF_TIME,
                                    nrows = self.experiment_config.NROWS if hasattr(self.experiment_config, 'NROWS') else None,
                                    ncolumns = self.experiment_config.NCOLUMNS if hasattr(self.experiment_config, 'NCOLUMNS') else None,
                                    display_size = self.experiment_config.DISPLAY_SIZE if hasattr(self.experiment_config, 'DISPLAY_SIZE') else None,
                                    flash_repeat = self.experiment_config.REPEATS, 
                                    sequence_repeat = self.experiment_config.REPEAT_SEQUENCE,
                                    background_color = self.experiment_config.BACKGROUND_COLOR, 
                                    shape_colors = self.experiment_config.COLORS, 
                                    random_order = self.experiment_config.ENABLE_RANDOM_ORDER)
        self.show_fullscreen(color = self.experiment_config.BACKGROUND_COLOR)
        #print self.shape_size,self.machine_config.SCREEN_SIZE_UM,self.ncolumns,self.nrows
        self.user_data = { 'nrows':self.nrows,  'ncolumns': self.ncolumns,  'shape_size':self.shape_size}
