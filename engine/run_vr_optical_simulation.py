import time

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

import numpy
import visexpman
import generic.graphics
import visexpman.users.zoltan.configurations
import visexpman.engine.optics.ray_reflection as ray_relfection

class RayReflection(generic.graphics.Screen):
    def initialization(self):
        self.optics = ray_relfection.Optics()
        self.alignment()
        
    def alignment(self):
        mirror_size = 30.0
        ray_start_point = numpy.array([- mirror_size, 0.5 * mirror_size, 0.5 * mirror_size])
        ray_direction = numpy.array([0.0, -1.0, 0.0])
        self.mirror = numpy.array([
                              [0.0, 0.0, 0.0],
                              [0.0, 0.0, mirror_size],
                              [mirror_size, 0.5 * mirror_size, mirror_size],
                              [mirror_size, 0.5 * mirror_size, 0.0],
                              ])

        st = time.time()        
        reflected_ray_vector, intersection = self.optics.reflection(ray_start_point,  ray_direction, self.mirror)        
        print time.time() - st
        self.rays = numpy.array([ray_start_point, intersection, intersection + reflected_ray_vector * 100.0])        
        


    def draw_scene(self):
        
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointerf(self.mirror)
        glColor3fv((1.0, 1.0, 1.0))
        glDrawArrays(GL_POLYGON, 0, 4)
        
        glLineWidth(2)
        glVertexPointerf(self.rays)
        glColor3fv((1.0, 0.0, 0.0))
        glDrawArrays(GL_LINES, 0, 2)
        glColor3fv((0.0, 0.0, 1.0))
        glDrawArrays(GL_LINES, 1, 2)
        
        glDisableClientState(GL_VERTEX_ARRAY) 
        
    def render_before_set_view(self):
        msg = str(self.position) + "%2.0f, %2.0f, %2.0f,%2.2f, %f"%(self.heading,  self.roll, self.pitch, self.frame_rate, self.wait_time_left)
        self.render_text(msg, color = (0.8, 0.8, 0.8), position = (-400, -250))

#class OpticSimulationScreen(generic.graphics.Screen):
#    def draw_hole_cubes(self):
#        hole_size = 10
#        frame_width = 100        
#        glTranslatef(frame_width,  0,  0)
#        glutSolidCube(frame_width)
#        glTranslatef(0, frame_width,  0)
#        glutSolidCube(frame_width)
#        glTranslatef(-frame_width, 0, 0)
#        glutSolidCube(frame_width)
#        glTranslatef(-frame_width, 0, 0)
#        glutSolidCube(frame_width)
#        glTranslatef(0, -frame_width, 0)
#        glutSolidCube(frame_width)
#        glTranslatef(0, -frame_width, 0)
#        glutSolidCube(frame_width)
#        glTranslatef(frame_width, 0, 0)
#        glutSolidCube(frame_width)
#        glTranslatef(frame_width, 0, 0)
#        glutSolidCube(frame_width)
#
#    
#    def draw_scene(self):
##        self.light()
##        self.draw_hole()
##        glColor3fv((0.2, 0.2, 0.2))
##        glRectf(-300.0, -300.0, 300.0, 300.0)
#
#        
##        glMatrixMode(GL_MODELVIEW)
##        glPushMatrix()
#        
#        
##        glutSolidCube(100)
##        glTranslatef(-150,  0,  0) 
##        glutSolidSphere(100, 200, 200)
##        glTranslatef(100,  0,  -200) 
##        glutSolidSphere(150, 200, 200)
#        
#
##        glColorMask(0,0,0,0)
##        glDisable(GL_DEPTH_TEST)
#        self.draw_hole_cubes()
##        glEnable(GL_DEPTH_TEST)
##        glColorMask(1,1,1,1)
##        
##        glPushMatrix()
##        glScalef(1.0, -1.0, 1.0)
##        
##        glTranslatef(0.0, 0.0, 100.0)
##        
#        glColor3fv((1.0, 0.0, 0.0))
#        glTranslatef(0,  0,  -300)
#        glutSolidSphere(150, 200, 200)
#        glTranslatef(0,  0,  300)        
#        
##        glPopMatrix()
##        
###        glEnable(GL_BLEND)
##        glColor4f(1.0, 1.0, 1.0, 0.5)
###        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)        
##        self.draw_hole_cubes()        
###        glDisable(GL_BLEND)
##        glTranslatef(0.0, 0.0, 100.0)
##        
##        glColor3fv((1.0, 0.0, 0.0))
##        glTranslatef(0, 0, -300)
##        glutSolidSphere(150, 200, 200)
##        glTranslatef(0, 0, 300)        
##
##    #blend test
##        
##        
##        
##        
##        
##        glPopMatrix()
##        
#        
#        
#        
#
##        color = (1.0, 0.0, 0.0)
##        glColor3fv(color)
##        glRectf(-10.0, -10.0, 10.0, 10.0)
##        glColor3fv((0.0, 1.0, 0.0))
##        glRectf(90.0, 90.0, 110.0, 110.0)
##        glRectf(-140.0, 140.0, -160.0, 160.0)
##        glRectf(-190.0, -190.0, -210.0, -210.0)
##        glRectf(240.0, -240.0, 260.0, -260.0)
##        
##        glColor3fv((0.0, 0.0, 1.0))
##        glRectf(240.0, 240.0, 260.0, 260.0)
#    
#    
#    def render_before_set_view(self):
#        msg = str(self.position) + "%2.0f, %2.0f, %2.0f,%2.2f, %f"%(self.heading,  self.roll, self.pitch, self.frame_rate, self.wait_time_left)
#        #glDisable(GL_LIGHTING)
#        self.render_text(msg, color = (0.8, 0.8, 0.8), position = (-400, -250))
#        #glEnable(GL_LIGHTING)
##        self.render_imagefile('../data/images/vision_spatial_resolution.png')
#
#    def initialization(self):
#        glEnable(GL_NORMALIZE)
#        glShadeModel(GL_SMOOTH)
#        glMaterialfv(GL_FRONT, GL_DIFFUSE, (1.0, 1.0, 1.0, 0.0))
#        glMaterialfv(GL_FRONT, GL_AMBIENT, (1.0, 1.0, 1.0, 0.0))       
#        
#        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.4,0.4,0.4))
#        
#        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.6, 0.6, 0.6))        
#        glLightModelfv(GL_LIGHT_MODEL_LOCAL_VIEWER, 1)
#        
#        glEnable(GL_LIGHT0)
#        glEnable(GL_LIGHTING)


        
#    def light(self):
#        glLightfv(GL_LIGHT0, GL_POSITION, (0.0,0.0,100.0, 1.0))
#
#
#
#        
#        
#
#        
#    def draw_hole(self):
#        glMatrixMode(GL_MODELVIEW)
#        glPushMatrix()
#        
#        glRotatef(0,  0.0, 0.0, 1.0)
#        glTranslatef(0,  0,  100) 
#        size = (200, 200)
#        hole = (50, 50)
#        hole_position = (75, 75)
#        vertices = numpy.array([
#                                [0, 0, 0],
#                                [hole_position[0], 0, 0],
#                                [hole_position[0], size[1], 0],
#                                [0,  size[1], 0],
#                                [hole_position[0], 0, 0],
#                                [hole_position[0]+hole[0], 0, 0],
#                                [hole_position[0]+hole[0], hole_position[1], 0],
#                                [hole_position[0], hole_position[1], 0],
#                                [hole_position[0], hole_position[1] + hole[1], 0],
#                                [hole_position[0] + hole[0], hole_position[1] + hole[1], 0],
#                                [hole_position[0] + hole[0], size[1], 0],
#                                [hole_position[0], size[1], 0],
#                                [hole_position[0] + hole[0], 0, 0],
#                                [size[0], 0, 0],
#                                [size[0], size[1], 0],
#                                [hole_position[0] + hole[0], size[1], 0],
#                                ])
#                                
#        normals = numpy.array([
#                                [0, 0, 1],
#                                [0, 0, 1],
#                                [0, 0, 1],
#                                [0, 0, 1],
#                                [0, 0, 1],
#                                [0, 0, 1],
#                                [0, 0, 1],
#                                [0, 0, 1],
#                                [0, 0, 1],
#                                [0, 0, 1],
#                                [0, 0, 1],
#                                [0, 0, 1],
#                                [0, 0, 1],
#                                [0, 0, 1],
#                                [0, 0, 1],
#                                [0, 0, 1],                               
#                               ])
#
#        glColor3fv((1.0, 0.0, 0.0))
#        glEnableClientState(GL_NORMAL_ARRAY)
#        glEnableClientState(GL_VERTEX_ARRAY)
#        glVertexPointerf(vertices)
#        glNormalPointerf(normals)
#        for i in range(4):
#            glColor3fv((1.0, 0.0, i * 0.23))
#            glDrawArrays(GL_POLYGON, i * 4, 4)
#
#        glDisableClientState(GL_VERTEX_ARRAY)
#        glDisableClientState(GL_NORMAL_ARRAY)
#        
#        glPopMatrix()
#        
#    def draw_rect(self):
#        position = (200, 150)
#        position = (0, 0)
#        size = [400 , 300]
#        color = (1.0,  1.0, 1.0)
#        vertices = numpy.array(
#                            [
#                            [0.5 * size[0] + position[0], 0.5 * size[1] + position[1], 0.0],
#                            [0.5 * size[0] + position[0], -0.5 * size[1] + position[1], 0.0],
#                            [-0.5 * size[0] + position[0], -0.5 * size[1] + position[1], 0.0],
#                            [-0.5 * size[0] + position[0], 0.5 * size[1] + position[1], 0.0],
#                            [0.5 * size[0] + position[0], 0.0, 0.5 * size[1] + position[1]],
#                            [0.5 * size[0] + position[0], 0.0, -0.5 * size[1] + position[1]],
#                            [-0.5 * size[0] + position[0], 0.0, -0.5 * size[1] + position[1]],
#                            [-0.5 * size[0] + position[0], 0.0, 0.5 * size[1] + position[1]],
#                            ])
#                            
#        vertices = numpy.array([
#                               [0, 0, 0], 
#                               [100, 0, 0],
#                               [100, 100, 0],
#                               [0, 100, 0], 
#                               [0, 0, 0], 
#                               [100, 0, 0],
#                               [100, 0, 100],
#                               [0, 0, 100],
#                               [0, 0, 0], 
#                               [0, 100, 0], 
#                               [0, 100, 100], 
#                               [0, 0, 100]
#                               
#                               ])
#
#        glColor3fv(color)
#        glEnableClientState(GL_VERTEX_ARRAY)
#        glVertexPointerf(vertices)
#        glDrawArrays(GL_POLYGON, 0, 4)
#        glColor3fv((1.0, 0.0, 0.0))
#        glDrawArrays(GL_POLYGON, 4, 4)
#        glColor3fv((0.0, 0.0, 1.0))
#        glDrawArrays(GL_POLYGON, 8, 4)
#        glDisableClientState(GL_VERTEX_ARRAY)

config = visexpman.users.zoltan.configurations.GraphicsTestConfig()
g = RayReflection(config, graphics_mode = 'standalone')
g.run()
g.close_screen()
