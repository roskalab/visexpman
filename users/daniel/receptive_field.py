import numpy
import copy
import time
import random
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

class ReceptiveFieldExploreBWG(experiment.ExperimentConfig):
    def _create_parameters(self):
	# x = 4248 um,  y = 2389 um
        self.SHAPE = 'rect'
        self.COLORS = [1.0,0.0]
        self.BACKGROUND_COLOR = 0.5

#        self.DISPLAY_SIZE = min(self.machine_config.SCREEN_SIZE_UM['row'], self.machine_config.SCREEN_SIZE_UM['col'])
#        self.DISPLAY_SIZE = utils.rc((self.DISPLAY_SIZE, self.DISPLAY_SIZE))
        self.DISPLAY_SIZE=self.machine_config.SCREEN_SIZE_UM
#        self.SHAPE_SIZE = 325.0
#        self.NROWS = 7
#        self.NCOLUMNS = 13
        self.NROWS = 8  #303.42857142857144, 298.625
        self.NCOLUMNS = 14
        self.ON_TIME = 0.5
        self.OFF_TIME = 2.0
        self.REPEATS = 1
        self.REPEAT_SEQUENCE = 1
        self.ENABLE_RANDOM_ORDER =  not False
        self.runnable='ReceptiveFieldExplore'
        self._create_parameters_from_locals(locals())
        
        
class ReceptiveFieldExploreNewInverted(ReceptiveFieldExploreBWG):
    def _create_parameters(self):
        ReceptiveFieldExploreNew._create_parameters(self)
        self.COLORS = [0.0]
        self.BACKGROUND_COLOR = 1.0

class ReceptiveFieldExploreNewAngle(ReceptiveFieldExploreBWG):
    def _create_parameters(self):
        ReceptiveFieldExploreNew._create_parameters(self)
        self.DISPLAY_SIZE = utils.rc((57.0,90.0))
        self.NROWS = 6
        self.NCOLUMNS = 9
        self.DISPLAY_CENTER = utils.rc((41.5,45.0))
        self.SIZE_DIMENSION='angle'
       # self.OFF_TIME = 0
        #self.ON_TIME = 2.0

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
        if self.stimulus_duration>400:
            self.printl('WARNING: stimulus is too long and memory error can happen at saving sync data')
        
            
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
                                    random_order = self.experiment_config.ENABLE_RANDOM_ORDER,is_block=True)
        self.show_fullscreen(color = self.experiment_config.BACKGROUND_COLOR)
        #print self.shape_size,self.machine_config.SCREEN_SIZE_UM,self.ncolumns,self.nrows
        self.user_data = { 'nrows':self.nrows,  'ncolumns': self.ncolumns,  'shape_size':self.shape_size}
