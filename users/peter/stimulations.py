from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
            
#######################################################################################################################################      
class OldSpotParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
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
        
            self.show_shape(shape = 'spot',  
                            pos = utils.rc((self.experiment_config.basx+3*174, self.experiment_config.basy+3*160)), # ref to the exp conf which called it
                            color = [1.0, 0, 0], 
                            background_color = 0.0,
                            size = self.experiment_config.RADIUS1,
                            duration=20.0)   
    
            for i in range(4):
                for j in range(4):
                    for k in range (2):
                    
                        self.show_shape(shape = 'spot',  
                            pos = utils.rc((self.experiment_config.basx+i*174,self.experiment_config.basy+j*160)), # ref to the exp conf which called it
                            color = 1.0, 
                            background_color = 0.0,
                            size = self.experiment_config.RADIUS1,
                            duration=self.experiment_config.HIGHTIME)
                            
                        self.show_shape(shape = 'spot',  
                            pos = utils.rc((0,0)), # ref to the exp conf which called it
                            color = 0.0, 
                            background_color = 0.0,
                            size = self.experiment_config.RADIUS2,
                            duration=self.experiment_config.LOWTIME)            
                            
                                      
#######################################################################################################################################            
class MoreSpotParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.POSITION = utils.rc((0,0)) # nice rc needs utils, ref to items: self.POSITION['row'], self.POSITION['col']
        
        self.RADIUS=[80, 160, 240, 320, 4000] #100, 200, 300, 400, inf
        
        self.RADIUSinf=4000 #infty
        self.HIGHTIME=2.0
        self.LOWTIME=6.0
        self.runnable = 'MoreSpotsExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory
#-------------------------------------------------------------------------------------------------------------------------------
class MoreSpotsExperiment(experiment.Experiment): # this is an expt class, higher order, NO LIST, stimulus itself is written here
    def run(self): # compulsory
    
        self.show_shape(shape = 'spot',  
                            pos = self.experiment_config.POSITION, # ref to the exp conf which called it
                            color = 0.0, 
                            background_color = 0.0,
                            size = self.experiment_config.RADIUSinf,
                            duration=self.experiment_config.LOWTIME)
                            
        for i in range(3):
            for j in range(len(self.experiment_config.RADIUS)):
            
                self.show_shape(shape = 'spot',  
                            pos = self.experiment_config.POSITION, # ref to the exp conf which called it
                            color = 1.0, 
                            background_color = 0.0,
                            size = self.experiment_config.RADIUS[j],
                            duration=self.experiment_config.HIGHTIME)
                            
                self.show_shape(shape = 'spot',  
                            pos = self.experiment_config.POSITION, # ref to the exp conf which called it
                            color = 0.0, 
                            background_color = 0.0,
                            size = self.experiment_config.RADIUSinf,
                            duration=self.experiment_config.LOWTIME)         
         
                            
#######################################################################################################################################                  
class ContrastSpotParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.POSITION = utils.rc((0,0)) # nice rc needs utils, ref to items: self.POSITION['row'], self.POSITION['col']
        
        self.RADIUS=240 #300
        self.SPOTC=[0.6, 0.4, 0.7, 0.3, 0.8, 0.2, 0.9, 0.1, 1.0, 0.0]
        self.BGCOL=0.5
        self.RADIUSinf=4000 #infty
        self.HIGHTIME=2.0
        self.LOWTIME=6.0
        self.runnable = 'ContrastSpotExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory
#-------------------------------------------------------------------------------------------------------------------------------
class ContrastSpotExperiment(experiment.Experiment): # this is an expt class, higher order, NO LIST, stimulus itself is written here
    def run(self): # compulsory
    
        self.show_shape(shape = 'spot',  
                            pos = self.experiment_config.POSITION, # ref to the exp conf which called it
                            color = self.experiment_config.BGCOL, 
                            background_color = self.experiment_config.BGCOL,
                            size = self.experiment_config.RADIUSinf,
                            duration=self.experiment_config.LOWTIME)
                            
        for i in range(3):
            for j in range(len(self.experiment_config.SPOTC)):
            
                self.show_shape(shape = 'spot',  
                            pos = self.experiment_config.POSITION, # ref to the exp conf which called it
                            color = self.experiment_config.SPOTC[j], 
                            background_color = self.experiment_config.BGCOL,
                            size = self.experiment_config.RADIUS,
                            duration=self.experiment_config.HIGHTIME)
                            
                self.show_shape(shape = 'spot',  
                            pos = self.experiment_config.POSITION, # ref to the exp conf which called it
                            color = 0.5, 
                            background_color = self.experiment_config.BGCOL,
                            size = self.experiment_config.RADIUSinf,
                            duration=self.experiment_config.LOWTIME)         
         
                               
#######################################################################################################################################      

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
        self.HIGHTIME=10.0
        self.LOWTIME=12.0
        self.runnable = 'FullFieldExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory       
        
##-------------------------------------------------------------------------------------------------------------------------------        
class FullFieldExperiment(experiment.Experiment): # this is an expt class, higher order, NO LIST, stimulus itself is written here
    def run(self): # compulsory
    
        self.show_shape(shape = 'spot',  
                            pos = self.experiment_config.POSITION, # ref to the exp conf which called it
                            color = 0.0, 
                            background_color = 0.0,
                            size = self.experiment_config.RADIUS2,
                            duration=25)
                                              
                            
        for i in range(4):
         
            self.show_shape(shape = 'spot',  
                            pos = self.experiment_config.POSITION, # ref to the exp conf which called it
                            color = 1.0, 
                            background_color = 0.0,
                            size = self.experiment_config.RADIUS2,
                            duration=self.experiment_config.HIGHTIME)    
                               
            self.show_shape(shape = 'spot',  
                            pos = self.experiment_config.POSITION, # ref to the exp conf which called it
                            color = 0.0, 
                            background_color = 0.0,
                            size = self.experiment_config.RADIUS2,
                            duration=self.experiment_config.LOWTIME)      
      
                                                            
################################################################################################################################  
class GridParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.POSITION = utils.rc((0,0)) # nice rc needs utils, ref to items: self.POSITION['row'], self.POSITION['col']
        self.runnable = 'GridExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory

#---------------------------------------------------------------------------------------------------------------------------
class GridExperiment(experiment.Experiment): # this is an expt class, higher order, NO LIST, stimulus itself is written here
    def run(self): # compulsory

        while True:
            if 'next' in self.command_buffer:
                self.command_buffer = ''
                break
            self.show_shape(shape = 'rect',  
                            color = 1.0, 
                            background_color = 0.0,
                            size = utils.rc((self.machine_config.SCREEN_SIZE_UM['row'], 20)),
                            duration=0.0)
            self.show_shape(shape = 'rect',  
                            color = 1.0, 
                            background_color = 0.0,
                            size = utils.rc((20, self.machine_config.SCREEN_SIZE_UM['col'])),
                            duration=0.0)
                            
################################################################################################################################        
        
class SpeedyShapeParameters(experiment.ExperimentConfig): # this is an exp config, lower order, IN LIST, calls the higher
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.SHAPE_COLOR = 1.0
        self.SHAPE_BACKGROUND = 0.0
        self.SHAPE_SIZE = utils.rc((480, 240)) #row col at 0 dir px 600 x 300 um !!!
        self.DIRECTIONS = [0]#, 45, 90, 135, 180, 225, 270, 315, 360] #degree
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
        self.DIRECTIONS = [0, 45, 90, 135, 180, 225, 270, 315, 360] #degree
        self.SPEED = [640] #px/s that is in u/s 800
        self.PAUSE_BETWEEN_DIRECTIONS = 1.0
        self.runnable = 'MovingShapeExperiment'     # compulsory write here the name of the expt class   
        self._create_parameters_from_locals(locals()) # compulsory
####----------------------------------------------------------------------------------------------------------------------------------
class MovingShapeExperiment(experiment.Experiment): # this is an expt class, higher order, NO LIST, stimulus itself is written here
   
    def prepare(self):
        #calculate movement path
        if hasattr(self.experiment_config.SHAPE_SIZE, 'dtype'):
            shape_size = self.experiment_config.SHAPE_SIZE['col']
        else:
            shape_size = self.experiment_config.SHAPE_SIZE
        self.movement = min(self.machine_config.SCREEN_SIZE_UM['row'], self.machine_config.SCREEN_SIZE_UM['col']) - shape_size # ref to machine conf which was started
        self.trajectories = []
        self.diratspeed = []
        for spd in self.experiment_config.SPEED:
            for direction in self.experiment_config.DIRECTIONS:
                start_point = utils.cr((0.5 * self.movement * numpy.cos(numpy.radians(direction)), 0.5 * self.movement * numpy.sin(numpy.radians(direction))))
                end_point = utils.cr((0.5 * self.movement * numpy.cos(numpy.radians(direction - 180.0)), 0.5 * self.movement * numpy.sin(numpy.radians(direction - 180.0))))
                spatial_resolution = spd/self.machine_config.SCREEN_EXPECTED_FRAME_RATE
                self.trajectories.append(utils.calculate_trajectory(start_point,  end_point,  spatial_resolution))
                self.diratspeed.append(direction)

    def run(self): # compulsory
        self.show_shape(shape = 'spot',  # pause at the beginning
                        pos = utils.rc((0,0)), # ref to the exp conf which called it
                        color = 0.0, 
                        background_color = 0.0,
                        size = 4000,
                        duration=2.0)
        for kt in range(3):
            for i in range(len(self.trajectories)):   #bar            
                for position in self.trajectories[i]:
                    self.show_shape(shape = self.experiment_config.SHAPE,  # ref to the exp conf which called it
                            pos = position, 
                            color = self.experiment_config.SHAPE_COLOR, 
                            background_color = self.experiment_config.SHAPE_BACKGROUND,
                            orientation = self.diratspeed[i], 
                            size = self.experiment_config.SHAPE_SIZE)
                    if self.abort:
                        break
                    
                  
                self.show_fullscreen(duration = self.experiment_config.PAUSE_BETWEEN_DIRECTIONS,  color = self.experiment_config.SHAPE_BACKGROUND)
            
        
        self.stimulus_frame_info = []
      
                            
###################################################################################################################################         