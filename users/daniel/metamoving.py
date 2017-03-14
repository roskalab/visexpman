from visexpman.engine.vision_experiment import experiment
import numpy

class SpeedWait(experiment.MetaStimulus):
    def run(self):
        depth = range(-100, -200, 20)
        laser = numpy.linspace(30, 50, len(depth))
        repeats = numpy.ones((len(depth),))*3
        for rep, las1, d1 in zip(repeats, laser, depth):
                for r1 in range(rep):
                        self.start_experiment('MovingGratingNoMarching', depth=d1, laser = las1)
                        self.sleep(180)
                        self.start_experiment('MovingGratingFast', depth=d1, laser=las1)
