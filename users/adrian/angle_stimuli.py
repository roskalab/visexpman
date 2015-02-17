import numpy
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils

class AngleTest(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPEEDS = [400]
        self.LOOM_START_SIZE = 300
        self.LOOMING_SHAPES = ['rect', 'spot', 'triangle', 'star4', 'star5']
        self.PAUSE = 4.0
        self.REPEATS = 2/2
        self.TOOTH_PROFILES = ['sawtooth', 'square']
        self.BAR_WIDTH = 100
        self.TOOTH_SIZE = 100
        self.LT_ANGLES = [45,90,135]
        self.LT_POSITIONS = ['start','middle','end']
        self.LT_SHORTER_SIDE = 200
        self.SECOND_MOVING_BAR_SPEEDS = [0]
        self.SECOND_MOVING_BAR_ANGLES = [45,90,135]
        self.runnable = 'AngleStimulus'
        self._create_parameters_from_locals(locals())

class AngleStimulus(experiment.Experiment):
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
        for bg, col in [[0.0, 1.0], [1.0, 0.0]]:
            for shape in self.experiment_config.LOOMING_SHAPES:
                if self.abort:
                    break
                for shape_size_per_speed in shape_sizes:
                    for d in [1, -1]:
                        if self.abort:
                            break
                        shape_size_per_speed_dir = shape_size_per_speed[::d]
                        for rep in range(self.experiment_config.REPEATS):
                            for s in shape_size_per_speed_dir:
                                if self.abort:
                                    break
                                if 'star' in shape:
                                    self.show_shape(shape=shape[:-1], ncorners = int(shape[-1]), size = s*0.5, orientation = direction, background_color = bg, color = col)
                                else:
                                    self.show_shape(shape=shape, size = s, orientation = direction, background_color = bg, color = col)
                        
    def moving_combs(self, direction):
        for spd in self.experiment_config.SPEEDS:
            for profile in self.experiment_config.TOOTH_PROFILES:
                for rep in range(self.experiment_config.REPEATS):
                    self.pause()
                    self.moving_comb(speed=spd, orientation=direction, bar_width=self.experiment_config.BAR_WIDTH,
                                tooth_size=self.experiment_config.TOOTH_SIZE, tooth_type=profile, contrast=1.0, background=0.0)
                    self.pause()
        
    def moving_T_and_L(self, direction):
        self.lt_longer_side = 0.7*min(self.machine_config.SCREEN_SIZE_UM['col'], self.machine_config.SCREEN_SIZE_UM['row'])
        for spd in self.experiment_config.SPEEDS:
            positions = self.moving_shape_trajectory(self.experiment_config.BAR_WIDTH, spd, [direction],1,pause=0.0,shape_starts_from_edge=True)
            for sh in ['X', 'L']:
                for ltangle in self.experiment_config.LT_ANGLES:
                    for ltpos in self.experiment_config.LT_POSITIONS:
                        for rep in range(self.experiment_config.REPEATS):
                            Lconfig = {'shorter_side':self.experiment_config.LT_SHORTER_SIDE, 'longer_side':self.lt_longer_side, 
                            'shorter_position': ltpos, 'angle' : ltangle, 'width': self.experiment_config.BAR_WIDTH}
                            self.pause()
                            if sh == 'L':
                                self.show_shape(shape=sh, orientation = direction+90,L_shape_config = Lconfig,pos = positions[0][0])
                            else:
                                self.show_shape(shape=sh,  size = utils.cr((Lconfig['longer_side'], Lconfig['width'])), orientation = direction+90,X_shape_angle = Lconfig['angle'],pos = positions[0][0])
                            self.pause()
                            if self.abort:
                                break
                        if sh == 'X':
                            break
        
    def moving_bars(self, direction):
        for spd in self.experiment_config.SPEEDS:
            for spd2 in self.experiment_config.SECOND_MOVING_BAR_SPEEDS:
                for angle in self.experiment_config.SECOND_MOVING_BAR_ANGLES:
                    second_bar_positions = [self.machine_config.SCREEN_CENTER, 
                                        ]
                    for pos2 in second_bar_positions:
                        self.static_bar(direction+angle, pos2)
                        self.moving_cross(speeds = [spd, spd2], sizes = [self.experiment_config.BAR_WIDTH, self.experiment_config.BAR_WIDTH], 
                                        position = pos2,
                                        movement_directions=[direction, direction+angle])
                        self.static_bar(direction+angle, pos2)
                        if self.abort:
                            break
    
    def static_bar(self, ori, pos):
        self.show_shape(shape='rect', duration = self.experiment_config.PAUSE, 
                                size = utils.rc((self.machine_config.SCREEN_SIZE_UM['col']*2, self.experiment_config.BAR_WIDTH)), pos = pos,
                                orientation = ori)
        
    
    def run(self):
        d=45
        self.looming_block(d)
        self.moving_bars(d)
        self.moving_T_and_L(d)
        self.moving_combs(d)
        self.export2video('/tmp/{0}_angle_stimulus.mp4'.format(d))
        
        
        
if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    stimulation_tester('adrian', 'StimulusDevelopment', 'AngleTest', ENABLE_FRAME_CAPTURE=True)
