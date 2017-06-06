import numpy
import time
import random
import copy

from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils

class MovingGratingConfigFindOrientation(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.REPEATS = 5
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 2
        self.TUNING_SPEEDS = [800.0, 400.0,100.0]
        self.TUNING_WHITE_BAR_WIDTHS = [150.0, 300.0, 600.0, 1000.0]
        self.TUNING_ORIENTATION = 90.0
        self.MARCH_TIME = 1.0
        self.GREY_INSTEAD_OF_MARCHING=True
        
        self.NUMBER_OF_MARCHING_PHASES = 0
        self.GRATING_STAND_TIME = 0
        self.ORIENTATIONS = range(0, 360, 45)
        self.WHITE_BAR_WIDTHS = [300.0]
        self.VELOCITIES = [800.0]
        self.DUTY_CYCLES = [self.machine_config.SCREEN_SIZE_UM['col']*1.414/self.WHITE_BAR_WIDTHS] 
        self.PAUSE_BEFORE_AFTER = 0.0
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
        self._create_parameters_from_locals(locals())
        
class MovingGratingTuning(MovingGratingConfigFindOrientation):
    def _create_parameters(self):
        MovingGratingConfigFindOrientation._create_parameters(self)
        self.VELOCITIES = self.TUNING_SPEEDS
        self.WHITE_BAR_WIDTHS = self.TUNING_WHITE_BAR_WIDTHS
        self.ORIENTATIONS = [self.TUNING_ORIENTATION]
        self.DUTY_CYCLES = [1.0]
        self.REPEATS = 3
        self._create_parameters_from_locals(locals())

class MovingGratingConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        #Timing        
        self.NUMBER_OF_MARCHING_PHASES = 4
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.MARCH_TIME = 2.5
        self.GRATING_STAND_TIME = 2.0
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 45)
        self.WHITE_BAR_WIDTHS = [300.0]
        self.VELOCITIES = [1200.0]
        self.DUTY_CYCLES = [2.5]
        self.REPEATS = 3
        self.PAUSE_BEFORE_AFTER = 5.0
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
        self._create_parameters_from_locals(locals())
        
class MovingGratingNoMarchingConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 4
        self.MARCH_TIME = 4.0
        self.GRATING_STAND_TIME = 4.0
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 45)
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.VELOCITIES = [1200.0]#1800
        self.DUTY_CYCLES = [3.0] #put 1.0 to a different config
        self.REPEATS = 2
        self.PAUSE_BEFORE_AFTER = 5.0
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
        self._create_parameters_from_locals(locals())
        

class MovingGratingNoMarchingConfigSpeedTuning(MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        MovingGratingNoMarchingConfig._create_parameters(self)
        self.REPEATS = 1
        #self.MARCH_TIME = 4.0
        #self.GRATING_STAND_TIME = 4.0
        #self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 4
        self._create_parameters_from_locals(locals())
                
class MovingGratingNoMarchingConfigSpeedTuning100(MovingGratingNoMarchingConfigSpeedTuning):
    def _create_parameters(self):
        MovingGratingNoMarchingConfig._create_parameters(self)
        self.VELOCITIES = [100.0]
        self.DUTY_CYCLES = [1.0]
        self.REPEATS = 1
        self._create_parameters_from_locals(locals())
        
class MovingGratingNoMarchingConfigSpeedTuning300(MovingGratingNoMarchingConfigSpeedTuning):
    def _create_parameters(self):
        MovingGratingNoMarchingConfig._create_parameters(self)
        self.VELOCITIES = [300.0]
        self.DUTY_CYCLES = [1.0]
        self.REPEATS = 1
        self._create_parameters_from_locals(locals())

class MovingGratingNoMarchingConfigSpeedTuning800(MovingGratingNoMarchingConfigSpeedTuning):
    def _create_parameters(self):
        MovingGratingNoMarchingConfig._create_parameters(self)
        self.VELOCITIES = [800.0]
        self.REPEATS = 1
        self._create_parameters_from_locals(locals())

class MovingGratingWithFlashConfig(MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        MovingGratingNoMarchingConfig._create_parameters(self)
        #Flash config
        self.ENABLE_FLASH = True
        self.FLASH_DURATION = 0.1
        self.TIMING = [2.0, self.FLASH_DURATION, 7.0, self.FLASH_DURATION, 7.0]
        self.FLASH_REPEATS = 1
        self.BLACK = 0.0
        self.WHITE = 1.0
        self.PAUSE_BEFORE_AFTER = 12.0
        
class MovingGratingSineConfig(MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        MovingGratingNoMarchingConfig._create_parameters(self)
        self.PROFILE = 'sin'
        self.DUTY_CYCLES = [1.0] #put 1.0 to a different config
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
#         self._create_parameters_from_locals(locals())
        
if 0:
    class MovingGratingNoMarchingNoStandingConfig(experiment.ExperimentConfig):
        def _create_parameters(self):
            #Timing
            self.NUMBER_OF_MARCHING_PHASES = 1
            self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 4
            self.MARCH_TIME = 0.0
            self.GRATING_STAND_TIME = 0.0
            #Grating parameters
            self.ORIENTATIONS = range(0, 360, 90)
            self.WHITE_BAR_WIDTHS = [300.0]#300
            self.VELOCITIES = [1000.0]#1800
            self.DUTY_CYCLES = [3.0] #put 1.0 to a different config
            self.REPEATS = 1
            self.PAUSE_BEFORE_AFTER = 0.0
            
            self.runnable = 'MovingGrating'
            self.pre_runnable = 'MovingGratingPre'
            self._create_parameters_from_locals(locals())

class ShortMovingGratingConfig(MovingGratingWithFlashConfig):
    def _create_parameters(self):
        MovingGratingWithFlashConfig._create_parameters(self)
        self.ENABLE_FLASH = False
        #Timing
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 1
        self.MARCH_TIME = 0.5
        self.GRATING_STAND_TIME = 0.5
        #Grating parameters        
        self.ORIENTATIONS = [0]
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.PAUSE_BEFORE_AFTER = 0.0
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
        self._create_parameters_from_locals(locals())
        
class MovingGratingConfig16Directions(MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        MovingGratingNoMarchingConfig._create_parameters(self)
        self.NUMBER_OF_MARCHING_PHASES = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 4
        self.MARCH_TIME = 4.0
        self.GRATING_STAND_TIME = 4.0
        #Grating parameters
        self.ORIENTATIONS = numpy.arange(0, 360, 22.5).tolist()
        self.WHITE_BAR_WIDTHS = [300.0]#300
        self.VELOCITIES = [1200.0]#1800
        self.DUTY_CYCLES = [3.0] #put 1.0 to a different config
        self.REPEATS = 2
        self.PAUSE_BEFORE_AFTER = 5.0
        self.runnable = 'MovingGrating'
        self.pre_runnable = 'MovingGratingPre'
        self._create_parameters_from_locals(locals())

class ATestStim(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.DURATION=10
        self.runnable = 'ATestStimE'
        self._create_parameters_from_locals(locals())

class ATestStimE(experiment.Experiment):
    def run(self):
        self.show_grating(orientation=45, duty_cycle=4, white_bar_width=200, velocity=200.0,duration=self.experiment_config.DURATION,display_area=utils.rc((400,600)),
                flicker={'frequency':5, 'modulation_size':50})

    

#Support for old config classes
#class GratingConfig(MovingGratingConfig):
#    pass

if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    import traceback,pdb
    from visexpman.engine.generic.introspect import full_exc_info
    try:
        stimulation_tester('daniel', 'IntrinsicDevelopment', 'TestStim')#'''ShortMovingGratingConfig')
    except:
        traceback.print_exc()
        pdb.post_mortem(full_exc_info()[2])
        raise
    finally:
        pass
