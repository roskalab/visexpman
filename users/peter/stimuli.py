from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
import time
import numpy
import os.path
import os
try:
    import winsound
except ImportError:
    pass
import shutil
import random
                                     
#######################################################################################################################################            
##-------------------------------------------------------------------------------------------------------------------------
class MoreSizeSpotsParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.POSITION = utils.rc((0,0)) # nice rc needs utils, ref to items: self.POSITION['row'], self.POSITION['col']
        
        self.RADIUS=[125, 250, 375, 500, 625, 1250, 4000] #125, 250, 375, 500, 625, inf microns: Karl's paper, fig. 2
        
        self.RADIUSinf=4000   #infty
        self.HIGHTIME=2.0     #standard
        self.LOWTIME=6.5     #minimum 6.5 sec
        self.runnable = 'MoreSizeSpotsExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory
#-------------------------------------------------------------------------------------------------------------------------------
class MoreSizeSpotsExperiment(experiment.Experiment): # this is an expt class, higher order, NO LIST, stimulus itself is written here
    def run(self): # compulsory
        self.trigger_pulse(self.machine_config.USER_PIN)
    
        self.show_fullscreen(color = 0.0, 
                            duration=self.experiment_config.LOWTIME,
                            frame_trigger = False)
                            
        for i in range(3):
        
            for j in range(len(self.experiment_config.RADIUS)):
            
                self.show_shape(shape = 'spot',  
                            pos = self.experiment_config.POSITION, # ref to the exp conf which called it
                            color = 1.0, 
                            background_color = 0.0,
                            size = self.experiment_config.RADIUS[j],
                            duration=self.experiment_config.HIGHTIME,
                            block_trigger = True)
                            
                self.show_fullscreen(color = 0.0, 
                            duration=self.experiment_config.LOWTIME,
                            frame_trigger = False)
         
        self.trigger_pulse(self.machine_config.USER_PIN)  
        
        winsound.PlaySound('C:\sounds\gray_wolf.wav', winsound.SND_ALIAS)  #end:guitar sound      
########################################################################################################################################                  
class CONTRASTParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.POSITION = utils.rc((0,0)) # nice rc needs utils, ref to items: self.POSITION['row'], self.POSITION['col']
        self.RADIUS2=40000
        self.HIGHTIME=2.0
        self.SPOTC=[0.2, 0.4, 0.6, 0.8, 1.0] # real values
        self.LOWTIME=6.5
        self.runnable = 'ContrastExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory      
#----------------------------------------------------------------------------------------------------------------------------------
class ContrastExperiment(experiment.Experiment): # this is an expt class, higher order, NO LIST, stimulus itself is written here
    def run(self): # compulsory
        self.trigger_pulse(self.machine_config.USER_PIN)
    
        self.show_fullscreen(color = 0.0, 
                            duration=8,
                            frame_trigger = False)
                           
        for i in range(3):
            
            for j in range(len(self.experiment_config.SPOTC)):
            
                 self.show_shape(shape = 'spot',  
                            pos = self.experiment_config.POSITION, # ref to the exp conf which called it
                            color = self.experiment_config.SPOTC[j], 
                            background_color = 0.0,
                            size = self.experiment_config.RADIUS2,
                            duration=self.experiment_config.HIGHTIME,
                            block_trigger = True) 
             
                 self.show_shape(shape = 'spot',  
                            pos = self.experiment_config.POSITION, # ref to the exp conf which called it
                            color = 0.0, 
                            background_color = 0.0,
                            size = self.experiment_config.RADIUS2,
                            duration=self.experiment_config.LOWTIME,
                            block_trigger = True) 
                            
        self.trigger_pulse(self.machine_config.USER_PIN)
                  
        winsound.PlaySound('C:\sounds\gray_wolf.wav', winsound.SND_ALIAS)  #end:guitar sound  
                        
#################################################################################################################################  
class FullFieldParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.POSITION = utils.rc((0,0)) # nice rc needs utils, ref to items: self.POSITION['row'], self.POSITION['col']
        self.RADIUS2=4000
        self.HIGHTIME=2.0
        self.LOWTIME=6.5
        self.runnable = 'FullFieldExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory
#--------------------------------------------------------------------------------------------------------------------------------
class MELAParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.POSITION = utils.rc((0,0)) # nice rc needs utils, ref to items: self.POSITION['row'], self.POSITION['col']
        self.RADIUS2=4000
        self.HIGHTIME=25.0
        self.LOWTIME=15.0
        self.runnable = 'FullFieldExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory      
#----------------------------------------------------------------------------------------------------------------------------------
class FullFieldExperiment(experiment.Experiment): # this is an expt class, higher order, NO LIST, stimulus itself is written here
    def run(self): # compulsory
        self.trigger_pulse(self.machine_config.USER_PIN)
    
        self.show_fullscreen(color = 0.0, 
                            duration=8,
                            frame_trigger = False)
                           
        for i in range(3):
            self.show_shape(shape = 'spot',  
                            pos = self.experiment_config.POSITION, # ref to the exp conf which called it
                            color = 1.0, 
                            background_color = 1.0,
                            size = self.experiment_config.RADIUS2,
                            duration=self.experiment_config.HIGHTIME,
                            block_trigger = True)  
            
            self.show_fullscreen(color = 0.0, duration=self.experiment_config.LOWTIME,
                            frame_trigger = False)
                            
        self.trigger_pulse(self.machine_config.USER_PIN)
                  
        winsound.PlaySound('C:\sounds\gray_wolf.wav', winsound.SND_ALIAS)  #end:guitar sound  
                        
####################################################################################################################################
class SpeedyShapeParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.SHAPE_COLOR = 1.0
        self.SHAPE_BACKGROUND = 0.0
        self.SHAPE_SIZE = utils.rc((600, 300)) #row col at 0 dir px 600 x 300 um
        self.DIRECTIONS = [0, 180]#, 45, 90, 135, 180, 225, 270, 315, 360] #degree
        self.SPEED = [100, 300, 800] #px/s that is in u/s 100 300 800
        self.PAUSE_BETWEEN_DIRECTIONS = 6.5
        self.runnable = 'MovingShapeExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory

#----------------------------------------------------------------------------------------------------------------------------------                    
class OctoShapeParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.SHAPE_COLOR = 1.0
        self.SHAPE_BACKGROUND = 0.0
        self.SHAPE_SIZE = utils.rc((600, 300)) #row col at 0 dir px 600 x 300 um
        self.DIRECTIONS = range(0, 360, 45) #[0, 45, 90, 135, 180, 225, 270, 315, 360] #degree
        self.SPEED = [800] #px/s that is in u/s 800
        self.PAUSE_BETWEEN_DIRECTIONS = 6.5
        self.runnable = 'MovingShapeExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory
####----------------------------------------------------------------------------------------------------------------------------------
class MovingShapeExperiment(experiment.Experiment): # this is an expt class, higher order, NO LIST, stimulus itself is written here
   
    def run(self): # compulsory
        self.trigger_pulse(self.machine_config.USER_PIN)
        
        self.show_fullscreen(color = 0.0, 
                            duration=8,
                            frame_trigger = False)
    
        for i in range (3):
            self.moving_shape(self.experiment_config.SHAPE_SIZE, self.experiment_config.SPEED, self.experiment_config.DIRECTIONS, 
                shape = self.experiment_config.SHAPE, 
                color = self.experiment_config.SHAPE_COLOR, 
                background_color = self.experiment_config.SHAPE_BACKGROUND, 
                pause=self.experiment_config.PAUSE_BETWEEN_DIRECTIONS,
                block_trigger = True)
        
        self.trigger_pulse(self.machine_config.USER_PIN)       
                            
###################################################################################################################################         
#
#class ProjectorCalibrationParameters(experiment.ExperimentConfig):
#    def _create_parameters(self):
#        self.CALIBRATION_POINTS = 100
#        self.SETTLING_TIME = 1.0
#        self.REPEATS = 1
#        self.INTENSITY_RANGE = [0.0, 1.0]
#        self.SAMPLES_PER_STEP = 10
#        self.runnable = 'ProjectorCalibration'        
#        self._create_parameters_from_locals(locals())
#-------------------------------------------------------------------------------------------------------------------------------
#
#class ProjectorCalibration(experiment.Experiment):
#
#    def run(self):
#            self.projector_calibration(intensity_range = self.experiment_config.INTENSITY_RANGE, 
#                                  npoints = self.experiment_config.CALIBRATION_POINTS, time_per_point = self.experiment_config.SETTLING_TIME, repeats = self.experiment_config.REPEATS)

##########################################################################################################################################        
class SpotFullParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.RADIUS=[200, 4000]
        self.REPEATS = 3
        self.HIGHTIME=2.0
        self.LOWTIME=6.5
        self.runnable = 'SpotFullExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory
#-------------------------------------------------------------------------------------------------------------------------------
class SpotFullExperiment(experiment.Experiment):

    def run(self):
        self.trigger_pulse(self.machine_config.USER_PIN)
        
        self.show_fullscreen(color = 0.0, 
                            duration=8.0,
                            frame_trigger = False)
                           
        for i in range(self.experiment_config.REPEATS):
            for radius in self.experiment_config.RADIUS:
                self.trigger_pulse(self.machine_config.USER_PIN)
                self.show_shape(shape = 'spot',  
                            color = 1.0, 
                            background_color = 0.0,
                            size = radius,
                            duration=self.experiment_config.HIGHTIME,
                            block_trigger = True)  
                self.trigger_pulse(self.machine_config.USER_PIN)
                self.show_fullscreen(color = 0.0, duration=self.experiment_config.LOWTIME,
                                frame_trigger = False)

        self.trigger_pulse(self.machine_config.USER_PIN) 
        
        winsound.PlaySound('C:\sounds\gray_wolf.wav', winsound.SND_ALIAS)  #end:guitar sound          
###########################################################################################################################################

class WhiteNoiseParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.DURATION = 3*60.0
        self.PIXEL_SIZE =100.0#Min 100 um
        self.FLICKERING_FREQUENCY = 15.0#Max 10 Hz
        self.N_WHITE_PIXELS = None
        self.COLORS = [0.0, 1.0]
        self.runnable = 'WhiteNoiseExperiment'
        self._create_parameters_from_locals(locals())

class WhiteNoiseExperiment(experiment.Experiment):
    def run(self):
        random.seed(0)
        self.white_noise(duration = self.experiment_config.DURATION,
            pixel_size = self.experiment_config.PIXEL_SIZE, 
            flickering_frequency = self.experiment_config.FLICKERING_FREQUENCY, 
            colors = self.experiment_config.COLORS,
            n_on_pixels = self.experiment_config.N_WHITE_PIXELS)
        self.show_fullscreen(color=0.0,duration=0)


###########################################################################################################################################        
class ASquare16testParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.RADIUS=1600
        self.COLOR1 = [1.0, 0.0, 0.0]
        self.COLOR2 = [0.0, 0.0, 0.0]
        self.runnable = 'SquareXtestExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory
#-------------------------------------------------------------------------------------------------------------------------------
class XSquareFulParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.RADIUS=1900000
        self.COLOR1 = [1.0, 1.0,1.0]
        self.COLOR2 = [0.0, 0.0, 0.0]
        self.runnable = 'SquareXtestExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory
#-------------------------------------------------------------------------------------------------------------------------------
class SquareXtestExperiment(experiment.Experiment):

    def run(self):
        
        for i in range (40):
            self.show_shape(shape = 'rectangle',  
                    color = self.experiment_config.COLOR1,
                    size = self.experiment_config.RADIUS,
                    duration=10.0,
                    orientation = 0.0)#,
                    #flip = False)  
            if self.abort:
                    self.abort=False   
                    break #after
        
        for i in range (40):
            self.show_shape(shape = 'rectangle',  
                    color = self.experiment_config.COLOR2,
                    size = self.experiment_config.RADIUS,
                    duration=10.0,
                    orientation = 0.0)#,
                    #flip = False)  
            if self.abort:
                    break #before
                    self.abort=False
     
