from visexpman.engine.vision_experiment import experiment

class NaturalBarsConfig(experiment.Stimulus):
    def stimulus_configuration(self):
        self.SPEED = 800
        self.REPEATS = 10 #5
        self.DIRECTIONS = [0,45,90,135,180,225,270,315] #range(0,360,90)
        self.DURATION = 24
        
        self.BACKGROUND_TIME = 5
        self.BACKGROUND_COLOR = 0.5

        self.WAIT_TIME = 3        
        #Advanced/Tuning
        self.MINIMAL_SPATIAL_PERIOD= 120 #None
        self.SCALE= 1.0
        self.OFFSET=0.0
        
    def calculate_stimulus_duration(self):
        self.duration=self.BACKGROUND_TIME
        for rep in range(self.REPEATS):
            for directions in self.DIRECTIONS:
                fly_in = True
                fly_out = True
                self.duration+=self.show_natural_bars(speed = self.SPEED, duration=self.DURATION, minimal_spatial_period = self.MINIMAL_SPATIAL_PERIOD, spatial_resolution = self.machine_config.SCREEN_PIXEL_TO_UM_SCALE, 
                        background=self.BACKGROUND_COLOR,
                        scale=self.SCALE,
                        offset=self.OFFSET,
                        intensity_levels = 255, direction = directions, fly_in = fly_in, fly_out = fly_out,duration_calc_only=True)
                self.duration+=self.WAIT_TIME
        if 0:
            fitime=self.machine_config.SCREEN_SIZE_UM['col']/self.SPEED
            self.duration = [(self.DURATION+2*fitime)*self.REPEATS*len(self.DIRECTIONS)]
        
    def run(self):
        self.show_fullscreen(duration = self.BACKGROUND_TIME, color =  self.BACKGROUND_COLOR, flip=True)
        for rep in range(self.REPEATS):
            if self.abort:
                break

            for directions in self.DIRECTIONS:
                import serial
                s=serial.Serial(port='COM1',baudrate=9600)
                s.write('e')
                s.close()
                if self.abort:
                    break
                fly_in = True
                fly_out = True
                self.show_natural_bars(speed = self.SPEED, duration=self.DURATION, minimal_spatial_period = self.MINIMAL_SPATIAL_PERIOD, spatial_resolution = self.machine_config.SCREEN_PIXEL_TO_UM_SCALE, 
                        background=self.BACKGROUND_COLOR,
                        scale=self.SCALE,
                        offset=self.OFFSET,
                        intensity_levels = 255, direction = directions, fly_in = fly_in, fly_out = fly_out,is_block=True)
                self.show_fullscreen(duration = self.WAIT_TIME, color =  self.BACKGROUND_COLOR, flip=True)
                    
class NaturalBarsDebug(NaturalBarsConfig):
    def stimulus_configuration(self):
        NaturalBarsConfig.stimulus_configuration(self)
        self.SPEED = 800
        self.REPEATS = 2 #5
        self.DIRECTIONS = [0,90]
        self.DURATION = 24
        


