import numpy
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils

class Angle0(experiment.ExperimentConfig):
    def _create_parameters(self):
        ##### IMPORTANT #####
        #If any parameter is changed the experiment duration might also change. The duration has to be measured and FRAGMENT_DURATION parameter needs to be updated.
        self.FRAGMENT_DURATION = 470
        self.POSITION = utils.rc((0, 0))#utils.rc((500,0))
        self.SPEEDS = [400]
        self.LOOM_START_SIZE = 50
        self.LOOMING_SHAPES = ['rect', 'spot', 'triangle', 'star4', 'star5']
        self.PAUSE = 4.0
        self.REPEATS = 1
        self.TOOTH_PROFILES = ['sawtooth', 'square']
        self.BAR_WIDTH = 100
        self.TOOTH_SIZE = 100
        self.LT_ANGLES = [45,90,135]
        self.LT_POSITIONS = ['start','middle','end']
        self.LT_SHORTER_SIDE = 300
        self.SECOND_MOVING_BAR_SPEEDS = [0]
        self.SECOND_MOVING_BAR_ANGLES = [45,90,135]
        self.DIRECTION = int(self.__class__.__name__.replace('Angle',  ''))
        self.runnable = 'AngleStimulus'
        self._create_parameters_from_locals(locals())
        
class Angle45(Angle0):
    pass
    
class Angle90(Angle0):
    pass

class Angle135(Angle0):
    pass
    
class Angle180(Angle0):
    pass
    
class Angle225(Angle0):
    pass
    
class Angle270(Angle0):
    pass
    
class Angle315(Angle0):
    pass
    
class AngleStimulus(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [self.experiment_config.FRAGMENT_DURATION]
    
    def pause(self):
        self.show_fullscreen(color = 0.0, duration = self.experiment_config.PAUSE*0.5)
        
    def looming_block(self, direction):
        #shapes: triangle, spot, rectangle, star 3, 4, 5 corners
        maxsize = min(self.machine_config.SCREEN_SIZE_UM['col'], self.machine_config.SCREEN_SIZE_UM['row'])
        shape_sizes = []
        for spd in self.experiment_config.SPEEDS:
            ds=spd/self.machine_config.SCREEN_EXPECTED_FRAME_RATE
            ss = numpy.arange(self.experiment_config.LOOM_START_SIZE+ds, maxsize, ds)
            block_start = numpy.ones(self.machine_config.SCREEN_EXPECTED_FRAME_RATE*self.experiment_config.PAUSE)*self.experiment_config.LOOM_START_SIZE
            block_end = numpy.ones(self.machine_config.SCREEN_EXPECTED_FRAME_RATE*self.experiment_config.PAUSE)*maxsize
            shape_sizes.append(numpy.concatenate((block_start, ss, block_end)))
        for bg, col in [[0.0, 1.0], [1.0, 0.0]][:1]:
            for shape in self.experiment_config.LOOMING_SHAPES:
                if self.abort:
                    break
                for shape_size_per_speed in shape_sizes:
                    for d in [1, -1]:
                        if self.abort:
                            break
                        shape_size_per_speed_dir = shape_size_per_speed[::d]
                        for rep in range(self.experiment_config.REPEATS):
                            self.block_start(block_name = 'loom')
                            for i in range(shape_size_per_speed_dir.shape[0]):
                                save_sfi = (i == 0 or  i == shape_size_per_speed_dir.shape[0]-1)
#                                self.printl((save_sfi, i))
                                s = shape_size_per_speed_dir[i]
                                if self.abort:
                                    break
                                p=utils.rc_add(self.experiment_config.POSITION, self.machine_config.SCREEN_CENTER)
                                if 'star' in shape:
                                    self.show_shape(shape=shape[:-1], ncorners = int(shape[-1]), size = s*0.5, orientation = direction, background_color = bg, color = col, pos = p, save_sfi= save_sfi)
                                else:
                                    self.show_shape(shape=shape, size = s, orientation = direction, background_color = bg, color = col, pos = p, save_sfi= save_sfi)
                            self.block_end(block_name = 'loom')
#                            return
                        
    def moving_combs(self, direction):
        for spd in self.experiment_config.SPEEDS:
            for profile in self.experiment_config.TOOTH_PROFILES:
                for rep in range(self.experiment_config.REPEATS):
                    self.block_start(block_name = 'comb')
                    self.pause()
                    self.moving_comb(speed=spd, orientation=direction, bar_width=self.experiment_config.BAR_WIDTH,
                                tooth_size=self.experiment_config.TOOTH_SIZE, tooth_type=profile, contrast=1.0, background=0.0, pos = self.experiment_config.POSITION)
                    self.pause()
                    self.block_end(block_name = 'comb')
        
    def moving_T_and_L(self, direction):
        self.lt_longer_side = 0.6*min(self.machine_config.SCREEN_SIZE_UM['col'], self.machine_config.SCREEN_SIZE_UM['row'])
        for spd in self.experiment_config.SPEEDS:
            positions = self.moving_shape_trajectory(self.experiment_config.BAR_WIDTH, spd, [direction],1,pause=0.0,shape_starts_from_edge=True)
            positions[0][0] = utils.rc_add(positions[0][0], self.experiment_config.POSITION)
            for sh in ['X', 'L']:
                for ltangle in self.experiment_config.LT_ANGLES:
                    for ltpos in self.experiment_config.LT_POSITIONS:
                        for rep in range(self.experiment_config.REPEATS):
                            Lconfig = {'shorter_side':self.experiment_config.LT_SHORTER_SIDE, 'longer_side':self.lt_longer_side, 
                            'shorter_position': ltpos, 'angle' : ltangle, 'width': self.experiment_config.BAR_WIDTH}
                            self.block_start(block_name = 'LT')
                            self.pause()
                            if sh == 'L':
                                self.show_shape(shape=sh, orientation = direction+90,L_shape_config = Lconfig,pos = positions[0][0])
                            else:
                                self.show_shape(shape=sh,  size = utils.cr((Lconfig['longer_side'], Lconfig['width'])), orientation = direction+90,X_shape_angle = Lconfig['angle'],pos = positions[0][0])
                            self.pause()
                            self.block_end(block_name = 'LT')
                            if self.abort:
                                break
                        if sh == 'X':
                            break
        
    def moving_bars(self, direction):
        for spd in self.experiment_config.SPEEDS:
            for spd2 in self.experiment_config.SECOND_MOVING_BAR_SPEEDS:
                for angle in self.experiment_config.SECOND_MOVING_BAR_ANGLES:
                    second_bar_positions = [utils.rc_add(self.machine_config.SCREEN_CENTER,self.experiment_config.POSITION), 
                                        ]
                    for pos2 in second_bar_positions:
                        self.block_start(block_name = 'movingbar')
                        self.static_bar(direction+angle, pos2)
                        self.moving_cross(speeds = [spd, spd2], sizes = [self.experiment_config.BAR_WIDTH, self.experiment_config.BAR_WIDTH], 
                                        position = pos2,
                                        movement_directions=[direction, direction+angle])
                        self.static_bar(direction+angle, pos2)
                        self.block_end(block_name = 'movingbar')
                        if self.abort:
                            break
    
    def static_bar(self, ori, pos):
        self.show_shape(shape='rect', duration = self.experiment_config.PAUSE, 
                                size = utils.rc((self.machine_config.SCREEN_SIZE_UM['col']*2, self.experiment_config.BAR_WIDTH)), pos = pos,
                                orientation = ori)

    def run(self):
        d=self.experiment_config.DIRECTION
        block_names = ['looming_block', 'moving_bars', 'moving_T_and_L', 'moving_combs']
        for bn in block_names:
            getattr(self, bn)(d)


if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('adrian', 'StimulusDevelopment', 'AngleTest', ENABLE_FRAME_CAPTURE=True)
