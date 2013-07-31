import os
import os.path
import shutil
from visexpman.engine.generic import file
from visexpman.engine.vision_experiment import experiment
from visexpman.users.daniel import grating
from visexpA.engine.datadisplay import videofile

class MovingGratingConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        #Timing        
        self.NUMBER_OF_MARCHING_PHASES = 4
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.MARCH_TIME = 0.0
        self.GRATING_STAND_TIME = 0.0
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 90)
        self.WHITE_BAR_WIDTHS = [300.0]
        self.VELOCITIES = [1200.0]
        self.DUTY_CYCLES = [2.5] 
        self.REPEATS = 1
        self.PAUSE_BEFORE_AFTER = 0.0
        self.runnable = 'MovingGrating1'
        self._create_parameters_from_locals(locals())
        
class MovingGrating1(grating.MovingGrating):
    def run(self, fragment_id=0):
        shutil.rmtree(self.machine_config.CAPTURE_PATH)
        os.mkdir(self.machine_config.CAPTURE_PATH)
        self.machine_config.ENABLE_FRAME_CAPTURE = True
        grating.MovingGrating.run(self, fragment_id)
        #save captured frames to avi
        videofile.image_files2mpg(self.machine_config.CAPTURE_PATH, os.path.join(self.machine_config.VIDEO_PATH, '{0}.mpg'.format(self.experiment_name)), 
                                                                                                                                  fps = self.machine_config.SCREEN_EXPECTED_FRAME_RATE)
        self.machine_config.ENABLE_FRAME_CAPTURE = False
