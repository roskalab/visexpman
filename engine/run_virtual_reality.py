#== This module shall be removed ==
#  because virtual reality related code will be executed from run_visual_stimulation.py.
# For behavioural training probably the run_visual_stimulation.py will be called too.

#from OpenGL.GL import *
#from OpenGL.GLU import *
#from OpenGL.GLUT import *
#import pygame
#import generic.utils
#import time
#import numpy
#import Image
#import sys
#sys.path.append('..')
#import users.zoltan.configurations
#
#texture_size = 1000
#class VirtualReality(object):
#    def __init__(self):
#        import sys
#        from PyQt4 import QtGui
#
##        app = QtGui.QApplication(sys.argv)
##
##        widget = QtGui.QWidget()
##        widget.resize(250, 150)
##        widget.setWindowTitle('simple')
##        widget.show()
##
##        sys.exit(app.exec_())
#
#        self.config = users.zoltan.configurations.VRConfig()
#        flags = pygame.DOUBLEBUF | pygame.HWSURFACE | pygame.OPENGL
#        if self.config.FULLSCR:
#            flags = flags | pygame.FULLSCREEN
#        self.screen = pygame.display.set_mode([self.config.SCREEN_RESOLUTION['col'], self.config.SCREEN_RESOLUTION['row']], flags)
#        pygame.mouse.set_visible(False)
#        print pygame.display.list_modes()
#        glEnable(GL_DEPTH_TEST)
#        glClearColor(self.config.BACKGROUND_COLOR[0], self.config.BACKGROUND_COLOR[1], self.config.BACKGROUND_COLOR[2], 0.0)
#        
#        glMatrixMode (GL_PROJECTION)
#        glLoadIdentity()
#        glOrtho(1.0, -1.0, -1.0, 1.0, -10.0, 10.0)
##        glFrustum(1.0,  -1.0, 1.0,  -1.0,  0.11,  10.0)
##        glOrtho(0.5 * self.config.SCREEN_RESOLUTION[0], -0.5 * self.config.SCREEN_RESOLUTION[0], -0.5 * self.config.SCREEN_RESOLUTION[1], 0.5 * self.config.SCREEN_RESOLUTION[1], -1.0, 1.0)
#        
##        print glGetFloatv(GL_PROJECTION_MATRIX)
#        
#        glMatrixMode(GL_MODELVIEW)
##        gluLookAt (0.0, 1.0, -1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)
#        glutInit()
#        
#        size = 0.3
#        distance = 0.7
#        z = 0.0
#        vertices = numpy.array([[0.5 * size,  0.0,  0.5 * size],
#                                [0.5 * size,  0.0,  -0.5 * size],
#                                [-0.5 * size,  0.0, -0.5 * size],
#                                [-0.5 * size, 0.0, 0.5 * size],
#                                
#                                [0.5 * size,  0.0,  0.5 * size],
#                                [-0.5 * size, 0.0, 0.5 * size],
#                                [-0.5 * size, size, 0.5 * size],
#                                [0.5 * size, size, 0.5 * size],
#                                
#                                [-0.5 * size,  0.0,  distance], 
#                                [0.5 * size,  0.0,  distance], 
#                                [0.5 * size,  size,  distance], 
#                                [-0.5 * size, size,  distance], 
#                                
#                                ])
#                                
#        texture_coords = numpy.array([[1.0,  1.0], 
#                                      [1.0,  0.0], 
#                                      [0.0,  0.0], 
#                                      [0.0,  1.0],
#                                      [1.0,  1.0], 
#                                      [1.0,  0.0], 
#                                      [0.0,  0.0], 
#                                      [0.0,  1.0],
#                                      
#                                      [1.0,  1.0], 
#                                      [1.0,  0.0], 
#                                      [0.0,  0.0], 
#                                      [0.0,  1.0],
#                                      ]
#                                     )
#        
#        glEnableClientState(GL_VERTEX_ARRAY)
#        glVertexPointerf(vertices)
#        i = 0
#        
#        #set up texture
#        self.create_texture()
#        self.create_2dtexture()        
#        
#        self.ID3 = glGenTextures(1)
#        glBindTexture(GL_TEXTURE_2D, self.ID3)
#    
#        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
#        glTexCoordPointerf(texture_coords)
#        
#        position = [0, 0, 0]
#        roll = 0.0
#        pitch = 0.0
#        heading = 0.0
#        user_projection = False
#        while True:
#        
##            glMatrixMode (GL_PROJECTION)
##            glLoadIdentity()            
##            if user_projection:
##                m = numpy.array([
##                         [0.9,  0.1,  0.0,  0.0], 
##                         [0.1,  0.9,  0.0,  0.0], 
##                         [0.0,  0.0,  1.0,  0.0], 
##                         [0.0,  0.0,  0.0,  1.0], 
##                         ])
##                glLoadMatrixf(m)
##            
#            glMatrixMode (GL_MODELVIEW)
#            glLoadIdentity()
#            glRotatef(roll,  0.0,  0.0,  1.0)
#            glRotatef(pitch,  0.0,  1.0,  0.0)
#            glRotatef(heading,  1.0,  0.0,  0.0)
#            glTranslatef(position[0],  position[1],  position[2])
#            
#
#            
#            glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
#            glColor3fv ((1.0, 0.0, 0.0) )
#            
#            glEnable(GL_TEXTURE_2D)
#            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
#            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
#            glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)
#            glBindTexture(GL_TEXTURE_2D, self.ID2)            
#            glDrawArrays(GL_POLYGON, 0, 4)
#            
#            glDisable(GL_TEXTURE_2D)
#            
##            glColor3fv ((0.0, 1.0, 0.0) )
##            glutSolidCube(0.5* size)
##
##            glColor3fv ((0.0, 0.0, 1.0) )
##            glTranslatef(0.0,  0.2,  0.0)
##            glutSolidCube(0.2* size)
#            
#            
##            glTranslatef(0.0,  0.1,  0.1)
#            glEnable(GL_TEXTURE_1D)
#            glTexParameterf(GL_TEXTURE_1D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
#            glTexParameterf(GL_TEXTURE_1D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
#            glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)
#            glBindTexture(GL_TEXTURE_1D, self.ID)
#            glDrawArrays(GL_POLYGON, 4, 4)
#            
##            self.drawCube()
#            glDisable(GL_TEXTURE_1D)           
#            
#            glEnable(GL_TEXTURE_GEN_S)
#            glEnable(GL_TEXTURE_GEN_T)
#            glTexGenf(GL_S,  GL_TEXTURE_GEN_MODE,     GL_REFLECTION_MAP)
#            glTexGenf(GL_T,  GL_TEXTURE_GEN_MODE,     GL_REFLECTION_MAP)
#            glEnable(GL_TEXTURE_2D)
#            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
#            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
#            glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)
#            glBindTexture(GL_TEXTURE_2D, self.ID3)
#            
#        
#            glDrawArrays(GL_POLYGON, 8, 4)
#            
#            glDisable(GL_TEXTURE_2D)            
#            glDisable(GL_TEXTURE_GEN_S)
#            glDisable(GL_TEXTURE_GEN_T)
#            
#            generic.utils.flip_screen(1.0/60.0)
#            
##            generic.utilities.text_to_screen('hello')
#            
#            
#            key_pressed = ''
#            pos_step = 0.1
#            angle_step = 1.0
#            for event in pygame.event.get():
#                if event.type == pygame.KEYDOWN:
#                    key_pressed = pygame.key.name(event.key)
#            if key_pressed == 'q':
#                break
#            elif key_pressed == 'a':
#                position[0] = position[0] + pos_step
#            elif key_pressed == 's':
#                position[1] = position[1] + pos_step
#            elif key_pressed == 'd':
#                position[2] = position[2] + pos_step
#            elif key_pressed == 'z':
#                position[0] = position[0] - pos_step
#            elif key_pressed == 'x':
#                position[1] = position[1] - pos_step
#            elif key_pressed == 'c':
#                position[2] = position[2] - pos_step
#            elif key_pressed == 'f':
#                roll = roll + angle_step
#            elif key_pressed == 'g':
#                pitch = pitch + angle_step
#            elif key_pressed == 'h':
#                heading = heading + angle_step
#            elif key_pressed == 'v':
#                roll = roll - angle_step
#            elif key_pressed == 'b':
#                pitch = pitch - angle_step
#            elif key_pressed == 'n':
#                heading = heading - angle_step
#            elif key_pressed == 'm':
#                user_projection = user_projection ^ True
#                
##            print position,  roll,  pitch,  heading
#        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
#        glDisableClientState(GL_VERTEX_ARRAY)
#        pygame.quit ()
#        
#    def create_texture(self):
#        self.texture = numpy.sin(numpy.linspace(0.5,  1.75,  texture_size))
#        self.ID = glGenTextures(1)
#        glBindTexture(GL_TEXTURE_1D, self.ID)
#        glPixelStorei(GL_UNPACK_ALIGNMENT,1)
#        glTexImage1D(GL_TEXTURE_1D, 0, 3, texture_size, 0, GL_LUMINANCE, GL_FLOAT, self.texture)
#        
#    def create_2dtexture(self):
#        self.texture2d = numpy.linspace(0.0,  numpy.pi,  texture_size)        
#        self.texture2d = numpy.concatenate((numpy.sin(self.texture2d),  numpy.cos(self.texture2d[::-1])))
#        im = Image.open('../data/textures/wood.jpg')
#        ix, iy, image = im.size[0], im.size[1], im.tostring('raw', 'RGBX', 0, -1)
#        self.ID2 = glGenTextures(1)
#        glBindTexture(GL_TEXTURE_2D, self.ID2)
#        glPixelStorei(GL_UNPACK_ALIGNMENT,1)
#        glTexImage2D(GL_TEXTURE_2D, 0, 3, ix, iy, 0, GL_RGBA, GL_UNSIGNED_BYTE, image)
#        
#        
#    def drawCube( self ):
#        """Draw a cube with texture coordinates"""
#        size = 0.5
#        glBegin(GL_QUADS)
#        glColor3fv ((1.0, 0.0, 0.0) )
#        glTexCoord2f(0.0, 0.0); glVertex3f(-size, -size,  size)
#        glTexCoord2f(1.0, 0.0); glVertex3f( size, -size,  size)
#        glTexCoord2f(1.0, 1.0); glVertex3f( size,  size,  size)
#        glTexCoord2f(0.0, 1.0); glVertex3f(-size,  size,  size)
#
#        glColor3fv ((1.0, 1.0, 0.0) )
#        glTexCoord2f(1.0, 0.0); glVertex3f(-size, -size, -size)
#        glTexCoord2f(1.0, 1.0); glVertex3f(-size,  size, -size)
#        glTexCoord2f(0.0, 1.0); glVertex3f( size,  size, -size)
#        glTexCoord2f(0.0, 0.0); glVertex3f( size, -size, -size)
#
#        glColor3fv ((1.0, 0.0, 1.0) )
#        glTexCoord2f(0.0, 1.0); glVertex3f(-size,  size, -size)
#        glTexCoord2f(0.0, 0.0); glVertex3f(-size,  size,  size)
#        glTexCoord2f(1.0, 0.0); glVertex3f( size,  size,  size);
#        glTexCoord2f(1.0, 1.0); glVertex3f( size,  size, -size);
#        
#        glColor3fv ((0.0, 1.0, 1.0) )
#        glTexCoord2f(1.0, 1.0); glVertex3f(-size, -size, -size);
#        glTexCoord2f(0.0, 1.0); glVertex3f( size, -size, -size);
#        glTexCoord2f(0.0, 0.0); glVertex3f( size, -size,  size);
#        glTexCoord2f(1.0, 0.0); glVertex3f(-size, -size,  size);
#
#        glColor3fv ((0.0, 1.0, 0.0) )
#        glTexCoord2f(1.0, 0.0); glVertex3f( size, -size, -size);
#        glTexCoord2f(1.0, 1.0); glVertex3f( size,  size, -size);
#        glTexCoord2f(0.0, 1.0); glVertex3f( size,  size,  size);
#        glTexCoord2f(0.0, 0.0); glVertex3f( size, -size,  size);
#
#        glColor3fv ((1.0, 1.0, 1.0) )
#        glTexCoord2f(0.0, 0.0); glVertex3f(-size, -size, -size);
#        glTexCoord2f(1.0, 0.0); glVertex3f(-size, -size,  size);
#        glTexCoord2f(1.0, 1.0); glVertex3f(-size,  size,  size);
#        glTexCoord2f(0.0, 1.0); glVertex3f(-size,  size, -size);
#        glEnd()        
#
#if __name__ == "__main__": 
#    vr = VirtualReality()
