import numpy
import copy
import time
import random
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class ReceptiveFieldExploreNew(experiment.ExperimentConfig):
    def _create_parameters(self):
	# x = 4248 um,  y = 2389 um
        self.SHAPE = 'rect'
        self.COLORS = [1.0]
        self.BACKGROUND_COLOR = 0

#        self.DISPLAY_SIZE = min(self.machine_config.SCREEN_SIZE_UM['row'], self.machine_config.SCREEN_SIZE_UM['col'])
#        self.DISPLAY_SIZE = utils.rc((self.DISPLAY_SIZE, self.DISPLAY_SIZE))
        self.DISPLAY_SIZE=self.machine_config.SCREEN_SIZE_UM
#        self.SHAPE_SIZE = 325.0
#        self.NROWS = 7
#        self.NCOLUMNS = 13
        self.NROWS = 8  #303.42857142857144, 298.625
        self.NCOLUMNS = 14
        self.ON_TIME = 0.5*2
        self.OFF_TIME = 2.0*0
        self.REPEATS = 1
        self.REPEAT_SEQUENCE = 1
        self.ENABLE_RANDOM_ORDER =  not False
        self.runnable='ReceptiveFieldExplore'
        self._create_parameters_from_locals(locals())
        
        
class ReceptiveFieldExploreNewInverted(ReceptiveFieldExploreNew):
    def _create_parameters(self):
        ReceptiveFieldExploreNew._create_parameters(self)
        self.COLORS = [0.0]
        self.BACKGROUND_COLOR = 1.0

class ReceptiveFieldExploreNewAngle(ReceptiveFieldExploreNew):#This is the original one!!!!!!!!!!!!
    def _create_parameters(self):
        ReceptiveFieldExploreNew._create_parameters(self)
        self.NROWS = 6
        self.NCOLUMNS = 9
        self.SIZE_DIMENSION='angle'
        self.DISPLAY_SIZE = utils.rc((57.0,90.0))#degrees Overall size of display in angles
        self.DISPLAY_CENTER = utils.rc((41.5,45.0))#degrees Center
#        self.SHAPE_SIZE = 10
       # self.OFF_TIME = 0
        #self.ON_TIME = 2.0
        
       
class ReceptiveFieldExploreNewAngleAdrian(ReceptiveFieldExploreNew):#This is the original one!!!!!!!!!!!!
    def _create_parameters(self):
        ReceptiveFieldExploreNew._create_parameters(self)
        self.NROWS = 6
        self.NCOLUMNS = 9
        self.SIZE_DIMENSION='angle'
        self.DISPLAY_SIZE = utils.rc((57.0,90.0))#degrees Overall size of display in angles
        self.DISPLAY_CENTER = utils.rc((41.5,45.0))#degrees Center
#        self.SHAPE_SIZE = 10
        self.OFF_TIME = 2.0
        self.ON_TIME = 1.0
        
class ReceptiveFieldExploreNewAngleAdrianInverted(ReceptiveFieldExploreNewAngleAdrian):
    def _create_parameters(self):
        ReceptiveFieldExploreNew._create_parameters(self)
        self.COLORS = [0.0]
        self.BACKGROUND_COLOR = 1.0


class ReceptiveFieldFionaFine(ReceptiveFieldExploreNew):
    def _create_parameters(self):
        ReceptiveFieldExploreNew._create_parameters(self)
        self.COLORS = [1.0]
        self.NROWS = 10
        self.NCOLUMNS = 18
        self.SIZE_DIMENSION='angle'
        self.DISPLAY_SIZE = utils.rc((51.0,90.0))#degrees
        self.DISPLAY_CENTER = utils.rc((44.4,45.0))#degrees
#        self.SHAPE_SIZE = 10
        self.ON_TIME = 1.2
        self.OFF_TIME = 1.2
        self.REPEATS = 1 
        
class ReceptiveFieldFionaFineBW(ReceptiveFieldExploreNew):
    def _create_parameters(self):
        ReceptiveFieldExploreNew._create_parameters(self)
        self.COLORS = [0.27, 0.0]
        self.BACKGROUND_COLOR = 0.15
        self.NROWS = 10
        self.NCOLUMNS = 18
        self.SIZE_DIMENSION='angle'
        self.DISPLAY_SIZE = utils.rc((51.0,90.0))#degrees
        self.DISPLAY_CENTER = utils.rc((44.4,45.0))#degrees
#        self.SHAPE_SIZE = 10
        self.ON_TIME = 0.8
        self.OFF_TIME = 0.8
        self.REPEATS = 1 
        
class ReceptiveFieldExploreNewAngleFine(ReceptiveFieldExploreNew):
    def _create_parameters(self):
        ReceptiveFieldExploreNew._create_parameters(self)
        self.COLORS = [1.0]
        self.NROWS = 10
        self.NCOLUMNS = 18
        self.SIZE_DIMENSION='angle'
        self.DISPLAY_SIZE = utils.rc((51.0,90.0))#degrees
        self.DISPLAY_CENTER = utils.rc((44.4,45.0))#degrees20x36
#        self.SHAPE_SIZE = 10
        self.ON_TIME = 1.4
        self.OFF_TIME = 1.4
        self.REPEATS = 2

        
        
class ReceptiveFieldFionaExtraFine(ReceptiveFieldExploreNew):
    def _create_parameters(self):
        ReceptiveFieldExploreNew._create_parameters(self)
        self.COLORS = [1.0]
        self.NROWS = 20
        self.NCOLUMNS = 36
        self.SIZE_DIMENSION='angle'
        self.DISPLAY_SIZE = utils.rc((51.0,90.0))#degrees
        self.DISPLAY_CENTER = utils.rc((44.4,45.0))#degrees
#        self.SHAPE_SIZE = 10
        self.ON_TIME = 0.45
        self.OFF_TIME = 0.45
        self.REPEATS = 1
     
class ReceptiveFieldFionaSuperFine(ReceptiveFieldExploreNew):
    def _create_parameters(self):
        ReceptiveFieldExploreNew._create_parameters(self)
        self.COLORS = [1.0]
        self.NROWS = 30
        self.NCOLUMNS = 54
        self.SIZE_DIMENSION='angle'
        self.DISPLAY_SIZE = utils.rc((51.0,90.0))#degrees
        self.DISPLAY_CENTER = utils.rc((44.4,45.0))#degrees
#        self.SHAPE_SIZE = 10
        self.ON_TIME = 0.39
        self.OFF_TIME = 0.39 
         
class ReceptiveFieldFionaCoarse(ReceptiveFieldExploreNew):
    def _create_parameters(self):
        ReceptiveFieldExploreNew._create_parameters(self)
        self.NROWS = 5
        self.NCOLUMNS = 9
        self.SIZE_DIMENSION='angle'
        self.DISPLAY_SIZE = utils.rc((51.0,90.0))#degrees
        self.DISPLAY_CENTER = utils.rc((44.4,45.0))#degrees
#        self.SHAPE_SIZE = 10
        self.ON_TIME = 0.8
        self.OFF_TIME = 0.8     

class ReceptiveFieldExplore(experiment.Experiment):
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
