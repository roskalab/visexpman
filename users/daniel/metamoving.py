from visexpman.engine.vision_experiment import experiment
import numpy

class SpeedWait(experiment.MetaStimulus):
    def run(self):
        depth = range(-100, -200, -20*2)
        laser = numpy.linspace(30, 50, len(depth))
        repeats = numpy.ones((len(depth),))*1
        for rep, las1, d1 in zip(repeats, laser, depth):
            for r1 in range(int(rep)):
                self.poller.printc((rep, las1, d1))
                self.start_experiment('ZoltanMovingGratingConfig', depth=d1, laser = las1)
                self.show_pre('ZoltanMovingGratingConfig')
                self.sleep(180/50)
                self.start_experiment('ZoltanMovingGratingConfig', depth=d1, laser=las1)
                break
            break
