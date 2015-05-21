import numpy
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment

NHP_DIRECTIONS = [135, 90, 315, 0, 180, 45, 225, 270,
                90,   180,   270,   135,    45,   315,     0,   225,
               315,     0,    90,   270,    45,   135,   180,   225,
               270,    90,     0,   315,   180,   135,    45,   225,
                90,   270,     0,   315,   135,   180,   225,    45]
                

class NHP1MovingGrating120(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        try:
            self.VELOCITY = int(self.__class__.__name__.split('MovingGrating')[1])
        except (ValueError, IndexError) as e:
            self.VELOCITY = 0.0
        self.ORIENTATIONS = NHP_DIRECTIONS
        self.PERIOD = 600.0#um
        self.STAND_TIME = 1.0
        self.REPEATS = 1
        self.PAUSE_BEFORE_AFTER = 3.0
        self.runnable='NHPMovingGrating'
        self._create_parameters_from_locals(locals())

class NHP0AdoptationStimulus(NHP1MovingGrating120):
    def _create_parameters(self):
        NHP1MovingGrating120._create_parameters(self)
        self.VELOCITY = 500.0
        self.ORIENTATIONS = NHP_DIRECTIONS[:8]
        self.STAND_TIME = 1.0
        self.PAUSE_BEFORE_AFTER = 0.0
        self.REPEATS = 1
        self.runnable='NHPMovingGrating'
        self._create_parameters_from_locals(locals())
        
class NHP2MovingGrating1200(NHP1MovingGrating120):
    pass


class NHP3FullfieldFlashConf(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.REPEATS = 5
        self.COLORS = [0.5, 1.0, 0.5, 0.0, 0.5]
        self.TIMES = [1.0, 2.0, 2.0, 2.0, 2.0]
        self.runnable = 'NHPFullfieldFlashExp'
        self._create_parameters_from_locals(locals())
        
class NHP4MovingBar120(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE_SIZE = utils.cr((1000, 500)) #um
        self.SPEEDS = [int(self.__class__.__name__.split('MovingBar')[1])] #um/s
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self.REPETITIONS = 1
        self.DIRECTIONS = NHP_DIRECTIONS
        self.SHAPE_BACKGROUND=0.0
        self.runnable = 'MovingShapeExperiment'        
        self._create_parameters_from_locals(locals())
        
class NHP5MovingBar1200(NHP4MovingBar120):
    pass

class NHP6MarchingSquares(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.COLORS = [1.0]
        self.BACKGROUND_COLOR = 0.5
        self.SHAPE_SIZE = 200.0
        self.ON_TIME = 1.0
        self.OFF_TIME = 1.0
        self.PAUSE_BEFORE_AFTER = 2.0
        self.REPEATS = 5
        self.REPEAT_SEQUENCE = 1
        self.ENABLE_RANDOM_ORDER = False
        self.runnable='ReceptiveFieldExplore'
        self._create_parameters_from_locals(locals())


class NHPSpots(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SIZES = [25, 50, 100, 200, 400, 800,1600]
        self.ON_TIME = 2
        self.OFF_TIME = 4
        self.runnable = 'IncreasingSpotExperiment'        
        self._create_parameters_from_locals(locals())
                    
class NHPFullfieldFlashExp(experiment.Experiment):
    def run(self):
        for i in range(self.experiment_config.REPEATS):
            for j in range(len(self.experiment_config.TIMES)):
                self.show_fullscreen(color = self.experiment_config.COLORS[j], duration = self.experiment_config.TIMES[j])


class NHPMovingGrating(experiment.Experiment):
    def prepare(self):
        if self.experiment_config.VELOCITY == 1200:
            self.sweep_duration = 8.0
        else:
            self.sweep_duration = self.experiment_config.PERIOD * self.experiment_config.NUMBER_OF_BAR_ADVANCE_OVER_POINT/self.experiment_config.VELOCITY

    def run(self):
        if self.experiment_config.PAUSE_BEFORE_AFTER>0:
            self.show_fullscreen(color = 0.5, duration = self.experiment_config.PAUSE_BEFORE_AFTER)
        for ori in self.experiment_config.ORIENTATIONS:
            for r in range(self.experiment_config.REPEATS):
                if self.experiment_config.STAND_TIME>0:
                    self.show_grating(duration = self.experiment_config.STAND_TIME,
                                        white_bar_width = 0.5 * self.experiment_config.PERIOD,
                                        orientation = ori,
                                        velocity = 0.0,
                                        is_block = False)
                self.show_grating(duration = self.sweep_duration,
                                        white_bar_width = 0.5 * self.experiment_config.PERIOD,
                                        orientation = ori,
                                        velocity = self.experiment_config.VELOCITY,
                                        is_block = True)
        if self.experiment_config.PAUSE_BEFORE_AFTER>0:
            self.show_fullscreen(color = 0.5, duration = self.experiment_config.PAUSE_BEFORE_AFTER)

class NHPBatchConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.MOVING_SPEEDS = [120,1200]
        self.GRATING_PERIOD = 600.0
        self.DIRECTIONS = NHP_DIRECTIONS
        self.SWEEP_REPETITION = 3/3
        
        ### Adoptation ###
        self.ADAPTATION_GRATING_SPEED = 500.0
        self.ADAPTATION_GRATING_DIRECTIONS = range(0,360,45)
        self.ADAPTATION_GRATING_REPETITIONS = 1
        
        ### Moving grating ###
        self.MOVING_GRATING_STAND_TIME = 1.0
        self.MOVING_GRATING_PAUSE_BEFORE_AFTER = 3.0
        
        ### Moving bar ###
        self.MOVING_SHAPE_SIZE = utils.cr((1000, 500)) #um
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self.DIRECTIONS = NHP_DIRECTIONS
        self.SHAPE_BACKGROUND=0.0
        self.OVERLAP = 100
        
        ### Marching square ###
        self.SHAPE = 'rect'
        self.COLORS = [1.0]
        self.BACKGROUND_COLOR = 0.5
        self.SHAPE_SIZE = 200.0
        self.ON_TIME = 1.0
        self.OFF_TIME = 1.0
        self.PAUSE_BEFORE_AFTER = 2.0
        self.REPEATS = 5
        self.REPEAT_SEQUENCE = 1
        self.ENABLE_RANDOM_ORDER = False
        self.runnable = 'NHPBatch'        
        self._create_parameters_from_locals(locals())

class NHPBatch(experiment.Experiment):
    def run(self):
        block_names=['adaptation','moving_grating','moving_bar','marching_square']
        for bn in block_names:
            print bn
            getattr(self, bn)()
            if self.abort:
                break
    
    def adaptation(self):
        duration = self.experiment_config.GRATING_PERIOD * self.experiment_config.ADAPTATION_GRATING_REPETITIONS/self.experiment_config.ADAPTATION_GRATING_SPEED
        for dir in self.experiment_config.ADAPTATION_GRATING_DIRECTIONS:
            self.show_grating(duration = duration,
                                        white_bar_width = 0.5 * self.experiment_config.GRATING_PERIOD,
                                        orientation = dir,
                                        velocity = self.experiment_config.ADAPTATION_GRATING_SPEED,
                                        is_block = True)
    def moving_grating(self):
        if self.experiment_config.PAUSE_BEFORE_AFTER>0:
            self.show_fullscreen(color = 0.5, duration = self.experiment_config.MOVING_GRATING_PAUSE_BEFORE_AFTER)
        for speed in self.experiment_config.MOVING_SPEEDS:
            if speed == 1200:
                self.sweep_duration = 8.0
            else:
                self.sweep_duration = self.experiment_config.GRATING_PERIOD * self.experiment_config.SWEEP_REPETITION/speed
            for dir in self.experiment_config.DIRECTIONS:
                self.show_grating(duration = self.experiment_config.MOVING_GRATING_STAND_TIME,
                                    white_bar_width = 0.5 * self.experiment_config.GRATING_PERIOD,
                                        orientation = dir,
                                        velocity = 0,
                                        is_block = False)
                self.show_grating(duration = self.sweep_duration,
                                    white_bar_width = 0.5 * self.experiment_config.GRATING_PERIOD,
                                        orientation = dir,
                                        velocity = speed,
                                        is_block = True)
            if self.experiment_config.PAUSE_BEFORE_AFTER>0:
                self.show_fullscreen(color = 0.5, duration = self.experiment_config.MOVING_GRATING_PAUSE_BEFORE_AFTER)

    def moving_bar(self):
        for speed in self.experiment_config.MOVING_SPEEDS:
            for dir in self.experiment_config.DIRECTIONS:
                for center in self._calculate_moving_bar_centers(dir):
                    self.moving_shape(self.experiment_config.MOVING_SHAPE_SIZE, speed, [dir], shape = 'rect', 
                                        color = 1.0, background_color = self.experiment_config.SHAPE_BACKGROUND,
                                        repetition = self.experiment_config.SWEEP_REPETITION, center = center, block_trigger = True, shape_starts_from_edge=True)
                    if self.abort:
                        break
                if self.abort:
                    break
            if self.abort:
                break
        
    def _calculate_moving_bar_positions(self,screen_range):
        nsteps = numpy.ceil((screen_range-self.experiment_config.OVERLAP)/(self.experiment_config.MOVING_SHAPE_SIZE['row']-self.experiment_config.OVERLAP))
        return numpy.arange(nsteps)*(self.experiment_config.MOVING_SHAPE_SIZE['row']-self.experiment_config.OVERLAP)+0.5*self.experiment_config.MOVING_SHAPE_SIZE['row']-0.5*screen_range
    
    def _calculate_moving_bar_centers(self,direction):
        #find out whether the direction of horizontal, vertical or diagonal
        hpos = self._calculate_moving_bar_positions(self.machine_config.SCREEN_SIZE_UM['col'])
        vpos = self._calculate_moving_bar_positions(self.machine_config.SCREEN_SIZE_UM['row'])
        if (direction/45)%2==1:#diagonal
            centers = utils.rc(numpy.array([hpos, numpy.zeros_like(hpos)]).T)
        elif (direction/45)%4==0:#horizontal
            centers = utils.cr(numpy.array([numpy.zeros_like(vpos), vpos]).T)
        else:#vertical
            centers = utils.cr(numpy.array([hpos, numpy.zeros_like(hpos)]).T)
        return centers
        
    def marching_square(self):
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
        self.user_data = { 'nrows':self.nrows,  'ncolumns': self.ncolumns,  'shape_size':self.shape_size}
                

if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('test', 'StimulusDevelopment', 'NHPBatchConfig')
