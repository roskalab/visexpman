from visexpman.engine.vision_experiment import experiment
import numpy

class SpeedWait(experiment.MetaStimulus):
    def run(self):
        #self.fault_inject=True
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
        
class WaitInDepth(experiment.MetaStimulus):
    def run(self):
        stimnames = ['MovingGratingNoMarchingConfig','MovingGratingNoMarch180Config']
        sleeptime = [0, 180]
        depth = self.read_depth()
        laser = self.read_laser(depth)
        nrepeats=1
        repeats = numpy.ones((len(depth),))*nrepeats
        for rep, las1, d1 in zip(repeats, laser, depth):
            for r1 in range(int(rep)):
                self.poller.printc((rep, las1, d1))
                for st1 in sleeptime:
                    for si1, sn1 in enumerate(stimnames):
                        self.sleep(st1)    
                        self.start_experiment(sn1, depth=d1, laser = las1)
                        nextstimi = si1+1 if si1 < len(stimnames)-1 else 0
                        self.show_pre(stimnames[nextstimi])
                
        self.poller.printc('Metastim finished')
        
class WaitInDepthCardinal(experiment.MetaStimulus):
    def run(self):
        stimnames = ['MovingGrating3xCardinalConfig','MovingGrating3xCardinal180Config']
        sleeptime = [0, 180]
        depth = self.read_depth()
        laser = self.read_laser(depth)
        nrepeats=1
        repeats = numpy.ones((len(depth),))*nrepeats
        # show a few flashes to make first repetition not habituated to long shown pre image during setup
        for st1 in stimnames:
            self.show_pre(st1)
            self.sleep(2)
        self.show_pre(stimnames[0])
        for rep, las1, d1 in zip(repeats, laser, depth):
            for r1 in range(int(rep)):
                self.poller.printc((rep, las1, d1))
                for st1 in sleeptime:
                    for si1, sn1 in enumerate(stimnames):
                        self.sleep(st1)    
                        self.start_experiment(sn1, depth=d1, laser = las1)
                        nextstimi = si1+1 if si1 < len(stimnames)-1 else 0
                        self.show_pre(stimnames[nextstimi])
                
        self.poller.printc('Metastim finished')        
        
class WaitInDepthOneBar(experiment.MetaStimulus):
    def run(self):
        stimnames = ['MovingGratingQuickSpeedTuningConfig']
        sleeptime = [0, 60]
        depth = self.read_depth()
        laser = self.read_laser(depth)
        nrepeats=1
        repeats = numpy.ones((len(depth),))*nrepeats
        self.show_pre(stimnames[0])
        for rep, las1, d1 in zip(repeats, laser, depth):
            for r1 in range(int(rep)):
                self.poller.printc((rep, las1, d1))
                for st1 in sleeptime:
                    for si1, sn1 in enumerate(stimnames):
                        self.sleep(st1)    
                        self.start_experiment(sn1, depth=d1, laser = las1)
                        nextstimi = si1+1 if si1 < len(stimnames)-1 else 0
                        self.show_pre(stimnames[nextstimi])
                
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
