from visexpman.engine.vision_experiment import experiment
import numpy
class SpeedWait(experiment.MetaStimulus):
    def run(self):
        self.fault_inject=True
        depth = self.read_depth()
        laser = self.read_laser(depth)
        nrepeats=1
        repeats = numpy.ones((len(depth),))*nrepeats
        for rep, las1, d1 in zip(repeats, laser, depth):
            for r1 in range(int(rep)):
                self.poller.printc((rep, las1, d1))
                #self.start_experiment('ZoltanMovingGratingConfig', depth=d1, laser = las1)
                self.show_pre('ZoltanMovingGratingConfig')
                self.sleep(180/20)
                #self.start_experiment('ZoltanMovingGratingConfig', depth=d1, laser=las1)


