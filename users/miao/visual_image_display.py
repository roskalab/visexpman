import os
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import fileop

class VisualImageDisplay(experiment.Stimulus):
    def configuration(self):
        self.IMAGE_FOLDER=os.path.join(fileop.visexpman_package_path(), 'data', 'stimulus', 'visual_image_display')
        self.IMAGE_ON_TIME=12.0
        self.IMAGE_OFF_TIME=3.0
        self.REPEATS=10
        self.BACKGROUND=0.0
        self.FILES=fileop.listdir(self.IMAGE_FOLDER)
        self.FILES.sort()
        
    def calculate_stimulus_duration(self):
        self.duration=len(self.FILES)*(self.IMAGE_ON_TIME+self.IMAGE_OFF_TIME)+self.IMAGE_OFF_TIME        
        
    def run(self):
        self.show_fullscreen(self.IMAGE_OFF_TIME, color=self.BACKGROUND)
        for rep in range(self.REPEATS):
            for f in self.FILES:
                self.block_start('image')
                self.show_image(f,  duration = self.IMAGE_ON_TIME,  stretch=1.0)
                self.block_end('image')
                self.show_fullscreen(self.IMAGE_OFF_TIME, color=self.BACKGROUND)
                if self.abort:
                    break
            if self.abort:
                break
                
