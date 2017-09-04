from visexpman.engine.hardware_interface import instrument
from visexpman.engine.vision_experiment import experiment
import time

class FlashWithShutter(experiment.Stimulus):
    def configuration(self):
        self.FLASH_DURATIONS = [100e-3]
        self.REPEATS = 100
        self.PAUSE_BETWEEN_FLASHES = 0.3
        
    def calculate_stimulus_duration(self):
        self.duration=sum(self.FLASH_DURATIONS*self.REPEATS)+(len(self.FLASH_DURATIONS)*self.REPEATS)*self.PAUSE_BETWEEN_FLASHES

    def prepare(self):
        self.shutter=instrument.ProScanIIIShutter('COM6', timeout=0.2)        

    def run(self):
        self.show_fullscreen(color=0.0)
        for d in self.FLASH_DURATIONS:
            for r in range(self.REPEATS):
                time.sleep(0.5*self.PAUSE_BETWEEN_FLASHES)
                self.show_shape(shape='r', color=1.0, size=30)
                self.block_start()#Toggles the block trigger pin
                self.shutter.flash(d)
                self.block_end()
                self.show_fullscreen(color=0.0)
                time.sleep(0.5*self.PAUSE_BETWEEN_FLASHES)
                if self.abort:
                    break
            if self.abort:
                break
        self.shutter.close()

if __name__ == "__main__":
    pass
