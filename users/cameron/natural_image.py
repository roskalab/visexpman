from visexpman.engine.vision_experiment import experiment

class NaturalImage(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.PIXEL_SIZE=1
        self.FILENAME='c:\\Data\\Pebbleswithquarzite_grey.png'
        self.SHIFT=50#um
        self.SPEED=800#um/s
        self.YRANGE=None#[0,1000]
        self.runnable = 'NaturalExp'
        
class NaturalExp(experiment.Experiment):
    def run(self):
        ec=self.experiment_config
        self.show_rolling_image(ec.FILENAME,ec.PIXEL_SIZE,ec.SPEED,ec.SHIFT,ec.YRANGE)
