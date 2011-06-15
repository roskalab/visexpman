import time
import numpy
import Image
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import pygame

class SceneGenerator(object):

    def __init__(self, screen_resolution = (800, 600), fullscreen = False, frame_rate = 60.0, path = 'pattern.jpg'):
        
        self.mouse_positions = []
        self.range_of_interest = [0, 100, 0, 100]
        
        self.screen_resolution = screen_resolution
        self.pixel_size = numpy.array([2.0, 2.0]) / numpy.array(screen_resolution)
        self.delay = 1.0/frame_rate
        #initialize screen
        flags = pygame.DOUBLEBUF | pygame.HWSURFACE | pygame.OPENGL
        if fullscreen:
            flags = flags | pygame.FULLSCREEN
        self.screen = pygame.display.set_mode(screen_resolution, flags)
        glutInit()
        glClearColor(0.0, 0.0, 0.0, 0.0)
        
        #initialize texturing
        texture_coordinates = numpy.array(
                             [
                             [1.0, 1.0],
                             [1.0, 0.0],
                             [0.0, 0.0],
                             [0.0, 1.0],
                             ])
                             
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glTexCoordPointerf(texture_coordinates)
        
        #create 2D texture for displaying image
        im = Image.open(path)
        im = im.convert('RGBX')
        self.image_size = im.size
        ix, iy, image = im.size[0], im.size[1], im.tostring('raw', 'RGBX', 0, -1)
        self.image_texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.image_texture_id)
        glPixelStorei(GL_UNPACK_ALIGNMENT,1)
        glTexImage2D(GL_TEXTURE_2D, 0, 3, ix, iy, 0, GL_RGBA, GL_UNSIGNED_BYTE, image)
        
    def run(self):
        run_loop = True
        while run_loop:
            glClear (GL_COLOR_BUFFER_BIT)
            self.draw_scene()
            self.flip()            
            for event in pygame.event.get():
                if event.type == 5 or event.type == 6:
                    if pygame.mouse.get_pressed() == (0, 0, 1):
                        run_loop = False
                    elif pygame.mouse.get_pressed() == (1, 0, 0) and self.is_roi_clicked(self.range_of_interest, pygame.mouse.get_pos()):
                        print 'OK'
                if event.type == 4:
                    self.mouse_positions.append(pygame.mouse.get_pos())
            self.state_machine()
            
    def state_machine(self):
        #placeholder for statemachine controlling the experiment flow
        pass
        
    def is_roi_clicked(self, range_of_interest, mouse_position):
        """
        range_of_interest: [roi min x, roi max x, roi min y, roi max y]
        mouse_position: x, y
        """
        if range_of_interest[0] < mouse_position[0] and range_of_interest[1] > mouse_position[0] and range_of_interest[2] < mouse_position[1] and range_of_interest[3] > mouse_position[1]:
            return True
        else:
            return False
        
            
    def draw_scene(self):
        self.show_image_file_stimulus()
        self.draw_rectangle([0.2, 1.0], (-0.5, 0), (1.0,  0.0, 0.0))
        self.draw_rectangle([0.2, 1.0], (0.5, 0), (0.0,  0.0, 1.0))
        self.render_text_message('Click on red', position = (0.0, -0.9))
        
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
            
if __name__ == "__main__":
    sg = SceneGenerator()
    sg.run()
    sg.close()
    sg.save_mouse_positions('coords.txt')
