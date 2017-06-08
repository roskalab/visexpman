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
        self.DISPLAY_SIZE = utils.rc((50.5,87.25))#degrees Overall size of display in angles
        self.DISPLAY_CENTER = utils.rc((50.5-3.45,87.25-33.35))#degrees Center
#        self.SHAPE_SIZE = 10
       # self.OFF_TIME = 0
        #self.ON_TIME = 2.0
        
       
class ReceptiveFieldExploreNewAngleAdrian(ReceptiveFieldExploreNewAngle):#This is the original one!!!!!!!!!!!!
    def _create_parameters(self):
        ReceptiveFieldExploreNewAngle._create_parameters(self)
        self.NROWS = 6
        self.NCOLUMNS = 9
        self.SIZE_DIMENSION='angle'
#        self.SHAPE_SIZE = 10
        self.OFF_TIME = 2.0
        self.ON_TIME = 1.0
        
class ReceptiveFieldExploreNewAngleAdrianInverted(ReceptiveFieldExploreNewAngleAdrian):
    def _create_parameters(self):
        ReceptiveFieldExploreNew._create_parameters(self)
        self.COLORS = [0.0]
        self.BACKGROUND_COLOR = 1.0
        
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
