import numpy
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils

class MarchingSquare(experiment.Stimulus):
    def configuration(self):
        self.STIMULUS_AREA_WIDTH=400#um
        self.STIMULUS_AREA_HEIGHT=400#um
        self.NROWS=5
        self.NCOLUMNS=5
        self.BACKGROUND=0.0
        self.COLOR=1.0
        self.ONTIME=2#sec, square is flashed for this duration
        self.OFFTIME=2#sec, blank screen is displayed between squares
        self.RANDOM_ORDER=True#True: order of square positions is randomized
        self.WAIT=0.5#wait time in seconds at beginning and end of stimulus
        self.REPEATS=6
#Do not edit below this!
        
    def calculate_positions(self):
        self.spacing_width=self.STIMULUS_AREA_WIDTH/self.NCOLUMNS
        self.spacing_height=self.STIMULUS_AREA_HEIGHT/self.NROWS
        rowmax=self.NROWS/2+1
        rowmin=-self.NROWS/2+1
        colmin=-self.NCOLUMNS/2+1
        colmax=self.NCOLUMNS/2+1
        if self.NROWS%2==0:
            rowmin-=0.5
            rowmax-=0.5
        if self.NCOLUMNS%2==0:
            colmin-=0.5
            colmax-=0.5
        row, col=numpy.meshgrid(numpy.arange(rowmin, rowmax),numpy.arange(colmin,colmax))
        row=numpy.cast['float'](row).flatten('F')[::-1]
        col=numpy.cast['float'](col).flatten('F')
        row*=self.spacing_height
        col*=self.spacing_width
        self.positions=utils.cr(numpy.array([col,row]))
        
 
    def prepare(self):
        self.calculate_positions()
        if self.RANDOM_ORDER:
            numpy.random.shuffle(self.positions)
        self.POSITIONS=self.positions
 
    def run(self):
        self.show_fullscreen(color=self.BACKGROUND, duration=self.WAIT)
        for r in range(self.REPEATS):
            for p in self.positions:
                self.block_start(('on',))
                self.show_shape(color=self.COLOR, shape='rect', duration=self.ONTIME,
                                        pos=utils.rc((p['row'],p['col'])), 
                                        size=utils.rc((self.spacing_height,  self.spacing_width)),
                                        background_color=self.BACKGROUND)
                self.block_end()
                self.show_fullscreen(color=self.BACKGROUND, duration=self.OFFTIME)
                if self.abort:
                    break
        self.show_fullscreen(color=self.BACKGROUND, duration=self.WAIT)
