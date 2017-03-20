from visexpman.engine.vision_experiment import experiment
import numpy

class SpeedWait(experiment.MetaStimulus):
    def run(self):
        stimnames = ['MovingGratingNoMarchingConfig','MovingGratingNoMarch180Config'][::-1]
        sleeptime = [180]
        depth = self.read_depth()
        laser = self.read_laser(depth)
        nrepeats=1
        repeats = numpy.ones((len(depth),))*nrepeats
        for rep, las1, d1 in zip(repeats, laser, depth):
            for r1 in range(int(rep)):
                self.poller.printc((rep, las1, d1))
                for si1, sn1 in enumerate(stimnames):
                    self.start_experiment(sn1, depth=d1, laser = las1)
                    nextstimi = si1+1 if si1 < len(stimnames)-1 else 0
                    self.show_pre(stimnames[nextstimi])
                    self.sleep(sleeptime[0])
                
        self.poller.printc('Metastim finished')
        
class SpeedNoWait(experiment.MetaStimulus):
    def run(self):
        stimnames = ['MovingGratingNoMarchingConfig','MovingGratingNoMarch180Config'][::-1]
        sleeptime = [0]
        depth = self.read_depth()
        laser = self.read_laser(depth)
        nrepeats=1
        repeats = numpy.ones((len(depth),))*nrepeats
        for rep, las1, d1 in zip(repeats, laser, depth):
            for r1 in range(int(rep)):
                self.poller.printc((rep, las1, d1))
                for si1, sn1 in enumerate(stimnames):
                    self.start_experiment(sn1, depth=d1, laser = las1)
                    nextstimi = si1+1 if si1 < len(stimnames)-1 else 0
                    self.show_pre(stimnames[nextstimi])
                    self.sleep(sleeptime[0])
                
        self.poller.printc('Metastim finished')