from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
                                     
#######################################################################################################################################      
class QuarterSpotParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.POSITION = utils.rc((0,0)) # nice rc needs utils, ref to items: self.POSITION['row'], self.POSITION['col']
        self.RADIUS1=160
        self.RADIUS2=4000
        self.HIGHTIME=2.0
        self.LOWTIME=6.0
        self.runnable = 'SpotsExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory
        self.basx=-400;
        self.basy=-300;
#-------------------------------------------------------------------------------------------------------------------------------
class SpotsExperiment(experiment.Experiment): # this is an expt class, higher order, NO LIST, stimulus itself is written here
    def run(self): # compulsory
        
            self.trigger_pulse(self.machine_config.USER_PIN)
            self.show_shape(shape = 'spot',  
                            pos = utils.rc((self.experiment_config.basx+3*174, self.experiment_config.basy+3*160)), # ref to the exp conf which called it
                            color = [1.0, 0, 0], 
                            background_color = 0.0,
                            size = self.experiment_config.RADIUS1,
                            duration=20.0,
                            block_trigger = True)   
    
            for i in range(4):
                for j in range(4):
                    for k in range (2):
                        self.trigger_pulse(self.machine_config.USER_PIN)
                        self.show_shape(shape = 'spot',  
                            pos = utils.rc((self.experiment_config.basx+i*174,self.experiment_config.basy+j*160)), # ref to the exp conf which called it
                            color = 1.0, 
                            background_color = 0.0,
                            size = self.experiment_config.RADIUS1,
                            duration=self.experiment_config.HIGHTIME,
                            block_trigger = True)
                        self.trigger_pulse(self.machine_config.USER_PIN)    
                        self.show_fullscreen(color = 0.0, 
                            duration=self.experiment_config.LOWTIME,
                            frame_trigger = False)
                                      
#######################################################################################################################################            

class MoreSizeSpotParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.POSITION = utils.rc((0,0)) # nice rc needs utils, ref to items: self.POSITION['row'], self.POSITION['col']
        
        self.RADIUS=[100, 200, 300, 400, 500, 4000 ] #125, 250, 375, 500, 625, inf microns: Karl's paper, fig. 2
        
        self.RADIUSinf=4000 #infty
        self.HIGHTIME=2.0
        self.LOWTIME=6.0
        self.runnable = 'MoreSpotsExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory
#-------------------------------------------------------------------------------------------------------------------------------
class MoreSpotsExperiment(experiment.Experiment): # this is an expt class, higher order, NO LIST, stimulus itself is written here
    def run(self): # compulsory
    
        self.trigger_pulse(self.machine_config.USER_PIN)
        self.show_fullscreen(color = 0.0, 
                            duration=self.experiment_config.LOWTIME,
                            frame_trigger = False)
                            
        for i in range(3):
        
            for j in range(len(self.experiment_config.RADIUS)):
            
                self.trigger_pulse(self.machine_config.USER_PIN)
                self.show_shape(shape = 'spot',  
                            pos = self.experiment_config.POSITION, # ref to the exp conf which called it
                            color = 1.0, 
                            background_color = 0.0,
                            size = self.experiment_config.RADIUS[j],
                            duration=self.experiment_config.HIGHTIME,
                            block_trigger = True)
                            
                self.trigger_pulse(self.machine_config.USER_PIN)            
                self.show_fullscreen(color = 0.0, 
                            duration=self.experiment_config.LOWTIME,
                            frame_trigger = False)
         
                            
#######################################################################################################################################                  
class ContrastSpotParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.POSITION = utils.rc((0,0)) # nice rc needs utils, ref to items: self.POSITION['row'], self.POSITION['col']
        
        self.RADIUS=240 #300
        self.SPOTC=                 [0.134, 0.465,    0.095, 0.66,    0.062, 1.0]
                  #      Michelson: [    0.3,0.3;       0.45,0.45;      0.6, 0.6]
                # CHANGED 4 april
        self.BGCOL=0.25  #computer 0.62 real 0.25
        self.RADIUSinf=4000 #infty
        self.HIGHTIME=2.0
        self.LOWTIME=6.0
        self.runnable = 'ContrastSpotExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory
#-------------------------------------------------------------------------------------------------------------------------------
class ContrastSpotExperiment(experiment.Experiment): # this is an expt class, higher order, NO LIST, stimulus itself is written here
    def run(self): # compulsory
    
        self.trigger_pulse(self.machine_config.USER_PIN)
        self.show_fullscreen(color = self.experiment_config.BGCOL, 
                            duration=self.experiment_config.LOWTIME,
                            frame_trigger = False)
                            
        for i in range(3):
            for j in range(len(self.experiment_config.SPOTC)):
            
                self.trigger_pulse(self.machine_config.USER_PIN)
                self.show_shape(shape = 'spot',  
                            pos = self.experiment_config.POSITION, # ref to the exp conf which called it
                            color = self.experiment_config.SPOTC[j], 
                            background_color = self.experiment_config.BGCOL,
                            size = self.experiment_config.RADIUS,
                            duration=self.experiment_config.HIGHTIME,
                            block_trigger = True)
                self.trigger_pulse(self.machine_config.USER_PIN)                    
                self.show_fullscreen(color = self.experiment_config.BGCOL, duration=self.experiment_config.LOWTIME,
                            frame_trigger = False)
                
                        
################################################################################################################################  
class FullFieldParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.POSITION = utils.rc((0,0)) # nice rc needs utils, ref to items: self.POSITION['row'], self.POSITION['col']
        self.RADIUS2=4000
        self.HIGHTIME=2.0
        self.LOWTIME=6.0
        self.runnable = 'FullFieldExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory
#--------------------------------------------------------------------------------------------------------------------------------
class MELAParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.POSITION = utils.rc((0,0)) # nice rc needs utils, ref to items: self.POSITION['row'], self.POSITION['col']
        self.RADIUS2=4000
        self.HIGHTIME=25.0
        self.LOWTIME=12.0
        self.runnable = 'FullFieldExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory      
##----        
class xTESTParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.POSITION = utils.rc((0,0)) # nice rc needs utils, ref to items: self.POSITION['row'], self.POSITION['col']
        self.RADIUS2=4000
        self.HIGHTIME=250.0
        self.LOWTIME=12.0
        self.runnable = 'FullFieldExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory                                           
##-------------------------------------------------------------------------------------------------------------------------------        
class FullFieldExperiment(experiment.Experiment): # this is an expt class, higher order, NO LIST, stimulus itself is written here
    def run(self): # compulsory
    
        self.trigger_pulse(self.machine_config.USER_PIN)
        self.show_fullscreen(color = 0.0, 
                            duration=8,
                            frame_trigger = False)
                           
        for i in range(3):
            self.trigger_pulse(self.machine_config.USER_PIN)
            self.show_shape(shape = 'spot',  
                            pos = self.experiment_config.POSITION, # ref to the exp conf which called it
                            color = 1.0, 
                            background_color = 1.0,
                            size = self.experiment_config.RADIUS2,
                            duration=self.experiment_config.HIGHTIME,
                            block_trigger = True)  
            
            self.trigger_pulse(self.machine_config.USER_PIN)
            self.show_fullscreen(color = 0.0, duration=self.experiment_config.LOWTIME,
                            frame_trigger = False)
                        
####################################################################################################################################
class SpeedyShapeParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.SHAPE_COLOR = 1.0
        self.SHAPE_BACKGROUND = 0.0
        self.SHAPE_SIZE = utils.rc((480, 240)) #row col at 0 dir px 600 x 300 um !!!
        self.DIRECTIONS = [0, 180]#, 45, 90, 135, 180, 225, 270, 315, 360] #degree
        self.SPEED = [80, 240, 640] #px/s that is in u/s 100 300 800
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self.runnable = 'MovingShapeExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory

#----------------------------------------------------------------------------------------------------------------------------------                    
class OctoShapeParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.SHAPE_COLOR = 1.0
        self.SHAPE_BACKGROUND = 0.0
        self.SHAPE_SIZE = utils.rc((480, 240)) #row col at 0 dir px 600 x 300 um !!!
        self.DIRECTIONS = range(0, 360, 45) #[0, 45, 90, 135, 180, 225, 270, 315, 360] #degree
        self.SPEED = [640] #px/s that is in u/s 800
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self.runnable = 'MovingShapeExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory
####----------------------------------------------------------------------------------------------------------------------------------
class MovingShapeExperiment(experiment.Experiment): # this is an expt class, higher order, NO LIST, stimulus itself is written here
   
    def run(self): # compulsory
    
        for i in range (3):
            self.moving_shape(self.experiment_config.SHAPE_SIZE, self.experiment_config.SPEED, self.experiment_config.DIRECTIONS, 
                shape = self.experiment_config.SHAPE, 
                color = self.experiment_config.SHAPE_COLOR, 
                background_color = self.experiment_config.SHAPE_BACKGROUND, 
                pause=self.experiment_config.PAUSE_BETWEEN_DIRECTIONS,
                block_trigger = True)
                            
###################################################################################################################################         

class ProjectorCalibrationParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.CALIBRATION_POINTS = 100
        self.SETTLING_TIME = 1.0
        self.REPEATS = 1
        self.INTENSITY_RANGE = [0.0, 1.0]
        self.SAMPLES_PER_STEP = 10
        self.runnable = 'ProjectorCalibration'        
        self._create_parameters_from_locals(locals())
#-------------------------------------------------------------------------------------------------------------------------------

class ProjectorCalibration(experiment.Experiment):

    def run(self):
            self.projector_calibration(intensity_range = self.experiment_config.INTENSITY_RANGE, 
                                  npoints = self.experiment_config.CALIBRATION_POINTS, time_per_point = self.experiment_config.SETTLING_TIME, repeats = self.experiment_config.REPEATS)
###########################################################################################################################################        
class SpotFullParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.RADIUS=[160, 4000]
        self.REPEATS = 3
        self.HIGHTIME=2.0
        self.LOWTIME=6.0
        self.runnable = 'SpotFullExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory
#-------------------------------------------------------------------------------------------------------------------------------
class SpotFullExperiment(experiment.Experiment):

    def run(self):
        self.trigger_pulse(self.machine_config.USER_PIN)
        self.show_fullscreen(color = 0.0, 
                            duration=7.0,
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
