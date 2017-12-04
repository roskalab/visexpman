import numpy,time
from visexpman.engine.generic import utils,geometry,colors
from visexpman.engine.vision_experiment import experiment
from visexpman.users.common import stimuli
from visexpman.users.common.grating import MovingGratingNoMarchingConfig
        
class MovingGratingTest(MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        MovingGratingNoMarchingConfig._create_parameters(self)
        self.GRATING_STAND_TIME = 0.5
        self.MARCH_TIME = 3.0#
        self.PAUSE_BEFORE_AFTER = 1.0
        self.REPEATS = 3
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.WHITE_BAR_WIDTHS=[150]

class ReceptiveFieldTest(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.COLORS = [1.0]
        self.BACKGROUND_COLOR = 0
        self.NROWS = 5
        self.NCOLUMNS = 9
        self.SIZE_DIMENSION='angle'
        if 'rc' in self.machine_config.PLATFORM:
            self.DISPLAY_SIZE = utils.rc((51.77,91.0))
            self.DISPLAY_CENTER = utils.rc((4.96,43.0))
        elif 'ao' in self.machine_config.PLATFORM:
            self.DISPLAY_SIZE = utils.rc((50.5,87.25))#degrees Overall size of display in angles
            self.DISPLAY_CENTER = utils.rc((3.45,33.35))#degrees Center
        else:
            self.DISPLAY_SIZE = utils.rc((51.0,90.0))
            self.DISPLAY_CENTER = utils.rc((25.5,24.0))
        self.DISPLAY_SIZE = utils.rc((51.77,91.0))
        self.DISPLAY_CENTER = utils.rc((4.96,43.0))
        self.ON_TIME = 0.1*10#0.8
        self.OFF_TIME = 0#0.8
        self.REPEATS = 1 
        self.REPEAT_SEQUENCE = 1
        self.ENABLE_RANDOM_ORDER =  False
        self.runnable='ReceptiveFieldExploreZ'
        self._create_parameters_from_locals(locals())

class IRLaserTest(stimuli.LaserPulse):
    def configuration(self):
        stimuli.LaserPulse.configuration(self)
        self.INITIAL_DELAY=1
        self.PULSE_DURATION=[100E-3]
        self.PERIOD_TIME=[5.0]
        self.NPULSES=5
        self.LASER_AMPLITUDE=[1.0, 2.0]


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
        self.duration=self.stimulus_duration
        
            
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

class NaturalBarsTest(experiment.Stimulus):
    def configuration(self):
        self.SPEED = [800, 400,1500.0]#um/s
        self.SPEED = [400]
        self.REPEATS = 2 #5
        self.DIRECTIONS = [0] #range(0,360,90)
        self.DURATION = 5
        self.BACKGROUND_TIME = 0
        self.BACKGROUND_COLOR = 0.5
        self.ALWAYS_FLY_IN_OUT = not False

    def calculate_stimulus_duration(self):
        self.duration = self.DURATION*3*2
        
    def run(self):
        for i in range(3):
            self.show_fullscreen(duration = self.DURATION/2, color =  self.BACKGROUND_COLOR)
            self.block_start()
            self.show_fullscreen(duration = self.DURATION, color =  1.0)
            self.block_end()
            self.show_fullscreen(duration = self.DURATION/2, color =  self.BACKGROUND_COLOR)

class Flash(experiment.Stimulus):
    def configuration(self):
        self.DURATION=8
        
    def calculate_stimulus_duration(self):
        self.duration=self.DURATION*3
        
    def run(self):
        self.block_start()
        self.show_fullscreen(color=0.5,duration=self.DURATION)
        self.block_end()
        self.show_fullscreen(color=0.5,duration=self.DURATION)
        self.block_start()
        self.show_fullscreen(color=1.0,duration=self.DURATION)
        self.block_end()
        
class TestStim(experiment.Stimulus):
    def configuration(self):
        self.DURATION=3
        
    def calculate_stimulus_duration(self):
        self.duration=self.DURATION*3
        
    def _approach(self):
        initial_wait=2.0
        mask_size=400.
        bar_width=60.
        speed=80
        motion=['expand','shrink','left','right']
        for m in motion:
            self.show_approach_stimulus(m, bar_width, speed, mask_size=mask_size)
            
    def _moving_grating(self):
        #Variable speed
        ph=numpy.tile(numpy.sin(numpy.arange(100)/100.*2*3.14)*300,10)
        self.show_grating(white_bar_width =100,  phases=ph, duty_cycle=3)
        #Flickering
        self.show_grating(duty_cycle=4, white_bar_width=200, velocity=100.0,duration=self.DURATION,display_area=utils.rc((400,600)),
                flicker={'frequency':5, 'modulation_size':50})
        self.show_grating(duty_cycle=4, white_bar_width=200, velocity=100.0,duration=self.DURATION*3)
        self.show_grating(duty_cycle=4, white_bar_width=200, velocity=100.0,duration=self.DURATION*2,
                flicker={'frequency':5, 'modulation_size':50})
        
    def _rolling_image(self):
        pixel_size=10.0/5#um/pixel
        shift=400.0#um
        speed=1200*1
        yrange=[1000,2000]
        fn='/tmp/Pebbleswithquarzite_grey.png'
        fn='/home/rz/1.jpg'
        self.show_rolling_image(fn,pixel_size,speed,shift,yrange,axis='vertical')
            
    def _plaid_stim(self):
        duration=10
        direction=90
        relative_angle=50
        velocity=100
        line_width=50
        duty_cycle=10
        mask_size=600
        contrast=0.7
        background_color=0.5
        sinusoid=True
        self.show_moving_plaid(duration, direction, relative_angle, velocity,line_width, duty_cycle, mask_size, contrast, background_color,  sinusoid)

    def run(self):
        self.show_grating(duration=4,velocity=300, mask_size=90,white_bar_width=40)
        return
        #self._approach()
        self._plaid_stim()
        return
        
        self._rolling_image()
        self._moving_grating()
        

def receptive_field_calculator():
    height=265
    width=470
    height_deg=51
    width_deg=90
    nrows=5
    ncols=9
    distance=280
    closest_point_from_left=24#Deg
    closest_point_from_left=45#Deg
    closest_point_from_bottom=25.5#Deg
    sizev=height_deg/float(nrows)
    sizeh=width_deg/float(ncols)
    angles_h=numpy.linspace(-closest_point_from_left,-closest_point_from_left+width_deg,ncols+1)
    angles_v=numpy.linspace(-closest_point_from_bottom,-closest_point_from_bottom+height_deg,nrows+1)
    xd=numpy.tan(numpy.radians(angles_h))*distance
    yd=numpy.tan(numpy.radians(angles_v))*distance
    x, y = numpy.meshgrid(xd, yd)
    pass
    

if __name__ == "__main__":
    #receptive_field_calculator()
    from visexpman.engine.visexp_app import stimulation_tester
    #stimulation_tester('zoltan', 'StimulusDevelopment', 'ReceptiveFieldTest')
    stimulation_tester('zoltan', 'StimulusDevelopment', 'TestStim')
