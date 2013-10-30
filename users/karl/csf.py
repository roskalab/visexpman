#--------------- Import Class Library ---------------#
import time
import sys
import os
import random
import numpy
import Image
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import pygame

#--------------- Define Classes ---------------#
class SceneGenerator(object):
    
    #---------- Define Window for Stimulus Presentation ----------#
    def __init__(self, screen_resolution = (1280, 720), fullscreen = False, frame_rate = 60.0, path = 'CSFchart1280x720.tif', number_of_color_choice_experiments = 5):
        
        self.number_of_color_choice_experiments = number_of_color_choice_experiments
        #generate list of colors to be shown
        self.generate_color_choices(0)
        self.experiment_counter = 0
        self.UserEvent='No Event'
        self.ExperimentState='BlackScreen'
        self.ColourCounter=0
        self.choice1=0
        self.choice2=0
        self.mouse_positions = []
        self.color_choices = []
        
        #initialize file names
        if len(sys.argv) == 1:
            self.experiment_name = 'unspecified'
        else:
            self.experiment_name = sys.argv[1]
        self.experiment_folder = self.experiment_name + '_' + str(time.time()).replace('.', '')
        os.mkdir(self.experiment_folder)
        
        self.csf_path = self.experiment_folder + os.sep + 'CSF.csv'
        self.color_path = self.experiment_folder + os.sep + 'Color.csv'
        
        self.screen_resolution = screen_resolution
        self.pixel_size = numpy.array([2.0, 2.0]) / numpy.array(screen_resolution)
        self.delay = 1.0/frame_rate
        #----- Initialize Screen -----#
        flags = pygame.DOUBLEBUF | pygame.HWSURFACE | pygame.OPENGL
        if fullscreen:
            flags = flags | pygame.FULLSCREEN
        self.screen = pygame.display.set_mode(screen_resolution, flags)
        glutInit()
        glClearColor(0.0, 0.0, 0.0, 0.0)
        
        #----- Initialize Texturing -----#
        texture_coordinates = numpy.array(
                             [
                             [1.0, 1.0],
                             [1.0, 0.0],
                             [0.0, 0.0],
                             [0.0, 1.0],
                             ])
                             
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glTexCoordPointerf(texture_coordinates)
        
        #----- create 2D texture for displaying image -----#
        im = Image.open(path)
        im = im.convert('RGBX')
        self.image_size = im.size
        ix, iy, image = im.size[0], im.size[1], im.tostring('raw', 'RGBX', 0, -1)
        self.image_texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.image_texture_id)
        glPixelStorei(GL_UNPACK_ALIGNMENT,1)
        glTexImage2D(GL_TEXTURE_2D, 0, 3, ix, iy, 0, GL_RGBA, GL_UNSIGNED_BYTE, image)
        
    #---------- Define Run Sequence for Experiment ----------#
    def run(self):
        self.run_loop = True
        
        #----- Loop Where Everything Happens -----#
        while self.run_loop:
            glClear (GL_COLOR_BUFFER_BIT)
            
            #----- Decide Which Test to Perform -----#            
            if self.ExperimentState == 'DisplayCSF' or self.ExperimentState == 'RunCSF':
                self.draw_CSF()
            elif self.ExperimentState == 'DisplayColour':
                self.draw_Colour()
            elif self.ExperimentState == 'RunColour':
                self.draw_Colour(color = self.color_presented[self.ColourCounter])
            elif self.ExperimentState == 'BlackScreen':
                pass
            self.flip()                                                                                       # Actual Command to display image                
            
            #----- Check for Mouse and Keyboard Input -----#
            self.UserEvent='No Event'
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    key_pressed = pygame.key.name(event.key)
                    if key_pressed == 'space':
                        self.UserEvent='SpacePressed'
                    elif key_pressed == 'escape':                        
                        self.UserEvent='EscapePressed'
                    elif key_pressed == 'left shift':
                        self.UserEvent='LeftShiftPressed'
                    elif key_pressed == 'left':                        
                        self.UserEvent='Choice1'
                    elif key_pressed == 'right':
                        self.UserEvent='Choice2'
                        
                #--- Capture Mouse Position for CSF Test ---#
                if event.type == 4 and self.ExperimentState == 'RunCSF':            # event.type == 4 => mouse movement
                        self.mouse_positions.append(pygame.mouse.get_pos())
                        
            #--- Capture Arrow Pressed Events for Colour Discrimination Test ---#
            if self.UserEvent == 'Choice1':
                self.choice1=self.choice1+1
            elif self.UserEvent == 'Choice2':
                self.choice2=self.choice2+1                                
            
            #----- Control of Experiment Flow -----#
            self.state_machine()
            
    def state_machine(self):
        #if self.UserEvent == 'No Event'
        
        if self.ExperimentState == 'BlackScreen':            
            self.choice1=0
            self.choice2=0
            if self.UserEvent == 'EscapePressed':
                self.run_loop = False
            elif self.UserEvent == 'SpacePressed':                
                self.ExperimentState='DisplayCSF'
                print self.ExperimentState
        elif self.ExperimentState == 'DisplayCSF':
            if self.UserEvent == 'SpacePressed':
                self.ExperimentState='RunCSF'                
                print self.ExperimentState
        elif self.ExperimentState == 'RunCSF':
            if self.UserEvent == 'SpacePressed':
                self.ExperimentState='DisplayColour'
                print self.ExperimentState
            elif self.UserEvent == 'LeftShiftPressed':
                self.ExperimentState='RunCSF'
                print self.ExperimentState
                self.mouse_positions = []
                # Need to Clear Data
        elif self.ExperimentState == 'DisplayColour':
            if self.UserEvent == 'SpacePressed':
                self.ColourCounter=0
                self.ExperimentState = 'RunColour'
                print self.ExperimentState
        elif self.ExperimentState == 'RunColour':
            if self.UserEvent == 'Choice1' or self.UserEvent == 'Choice2':
                self.ColourCounter=self.ColourCounter+1
                if self.UserEvent == 'Choice1':
                    self.color_choices.append('red')
                elif self.UserEvent == 'Choice2':
                    self.color_choices.append('blue')                    
            print self.ColourCounter
            if self.ColourCounter>=self.number_of_color_choice_experiments:
                self.ExperimentState = 'BlackScreen'
                self.experiment_counter = self.experiment_counter + 1
                self.generate_color_choices(self.experiment_counter)
                print self.ExperimentState
                # Need to Save Data
                #save CSF 
                csf_path_indexed = self.csf_path.replace('.', str(self.experiment_counter) + '.')
                self.save_mouse_positions(csf_path_indexed)
                self.mouse_positions = []
                #save color choice
                color_path_indexed = self.color_path.replace('.', str(self.experiment_counter) + '.')
                numpy.savetxt(color_path_indexed, numpy.array([self.color_presented, self.color_choices]).transpose(), '%s')
                self.color_choices = []
                
            elif self.UserEvent == 'EscapePressed':
                self.run_loop = False
                
            
    def is_roi_clicked(self, range_of_interest, mouse_position):
        """
        range_of_interest: [roi min x, roi max x, roi min y, roi max y]
        mouse_position: x, y
        """
        if range_of_interest[0] < mouse_position[0] and range_of_interest[1] > mouse_position[0] and range_of_interest[2] < mouse_position[1] and range_of_interest[3] > mouse_position[1]:
            return True
        else:
            return False
        
    #---------- Define Functions to Show CSF or Coloured Rectangles for Colour Discrimination ---------#
    def draw_CSF(self):
        self.show_image_file_stimulus()
        
    def draw_Colour(self, color = 'both'):
        if color == 'both':
            self.draw_rectangle([0.2, 1.0], (-0.5, 0), (1.0,  0.0, 0.0))
            self.draw_rectangle([0.2, 1.0], (0.5, 0), (0.0,  0.0, 1.0))
        elif color == 'red':
            self.draw_rectangle([0.2, 1.0], (0.0, 0.0), (1.0,  0.0, 0.0))
        elif color == 'blue':
            self.draw_rectangle([0.2, 1.0], (0.0, 0.0), (0.0,  0.0, 1.0))
        else:
            print 'invalid'
        
    def show_image_file_stimulus(self):
        glEnable(GL_TEXTURE_2D)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)
        glBindTexture(GL_TEXTURE_2D, self.image_texture_id)
        size = self.pixel_size * numpy.array(self.image_size)
        self.draw_rectangle(size, (0,0), (1.0, 1.0, 1.0))
        glDisable(GL_TEXTURE_2D)
        
    def draw_rectangle(self, size, position, color):
        vertices = numpy.array(
                            [
                            [0.5 * size[0] + position[0], 0.5 * size[1] + position[1], 0.0],
                            [0.5 * size[0] + position[0], -0.5 * size[1] + position[1], 0.0],
                            [-0.5 * size[0] + position[0], -0.5 * size[1] + position[1], 0.0],
                            [-0.5 * size[0] + position[0], 0.5 * size[1] + position[1], 0.0],
                            ])                               

        glColor3fv(color)
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointerf(vertices)
        glDrawArrays(GL_POLYGON, 0, 4)
        glDisableClientState(GL_VERTEX_ARRAY)       

    def flip(self):
        time.sleep(self.delay)
        pygame.display.flip()
        
    def close(self):
        pygame.quit()
        
    def save_mouse_positions(self, path):
        numpy.savetxt(path, numpy.array(self.mouse_positions), '%d')
        
    def render_text_message(self, message, position = (0, 0)):       
        glColor3fv((1.0,  1.0,  1.0))
        for i in range(len(message)):
            glRasterPos2f(position[0] + 0.05 * i, position[1])
            glutBitmapCharacter(GLUT_BITMAP_TIMES_ROMAN_24, ord(message[i]))
            
    def generate_color_choices(self, seed):
        self.color_presented = []
        random.seed(seed)
        for i in range(self.number_of_color_choice_experiments):
            choice = random.random()
            if choice > 0.5:
                self.color_presented.append('red')
            else:
                self.color_presented.append('blue')
            
            
if __name__ == "__main__":
    sg = SceneGenerator(fullscreen = False, number_of_color_choice_experiments = 5)
    sg.run()
    sg.close()
#    sg.save_mouse_positions('coords.txt')
