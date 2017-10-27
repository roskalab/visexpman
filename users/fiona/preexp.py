from visexpman.engine.vision_experiment import experiment

class GreyPre(experiment.PreExperiment):    
    def run(self):
        self.show_fullscreen(color = 0.42, duration = 0,flip=False)
