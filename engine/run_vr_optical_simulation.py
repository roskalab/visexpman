import time

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

import numpy
import visexpman
import generic.graphics
import visexpman.users.zoltan.configurations
import visexpman.engine.optics.ray_reflection as ray_relfection
import visexpman.engine.generic.geometry as geometry

class RayReflection(generic.graphics.Screen):
    def initialization(self):
        self.alignment()
        
    def alignment(self):
        unit = 10.0
        number_of_mirror_vertices = 4
        number_of_reflections = 3
        number_of_mirrors = 2

        initial_ray_start_point = numpy.array([0.0 * unit, 1.0 * unit, 0.5 * unit])
        initial_ray_direction = numpy.array([1.0 * unit, -1.0 * unit, 0.0])
        self.mirror = numpy.array([
                              [0.0, 0.0, 0.0], 
                              [0.0, 0.0, unit], 
                              [10 * unit, 0.0, unit], 
                              [10 * unit, 0.0, 0.0], 
                              [0.0, unit, 0.0], 
                              [0.0, unit, unit], 
                              [10 * unit, unit, unit], 
                              [10 * unit, unit, 0.0],
                              ])

        self.mirrors = [self.mirror[:4],  self.mirror[4:]]
        st = time.time()
        reflected_ray_start_points = [initial_ray_start_point]
        reflected_ray_directions = []
        
        mirror_i = 0
        for reflection_count in range(number_of_reflections):
            if reflection_count == 0:
                ray_start_point = initial_ray_start_point
                ray_direction = initial_ray_direction
            else:
                ray_start_point = reflected_ray_start_points[-1]
                ray_direction = reflected_ray_directions[-1]
                
            for mirror_count in range(number_of_mirrors):
                reflected_ray_direction, reflected_ray_start_point = ray_relfection.reflection(ray_start_point, ray_direction, self.mirrors[mirror_count])
                #TODO: here the right reflection must be selected
#                print reflected_ray_direction, reflected_ray_start_point, ray_direction, ray_start_point#, geometry.distance_between_points(reflected_ray_start_point, ray_start_point)
                if reflected_ray_start_point != None and reflected_ray_direction != None:
                    if geometry.distance_between_points(reflected_ray_start_point, ray_start_point) > 1.0e-4:
                        print mirror_count
                        reflected_ray_start_points.append(reflected_ray_start_point)
                        reflected_ray_directions.append(reflected_ray_direction)

        if len(reflected_ray_directions) > 0:
            reflected_ray_start_points.append(reflected_ray_start_points[-1] + 3.0 * unit * reflected_ray_directions[-1])
        self.rays = numpy.array(reflected_ray_start_points)
#        print self.rays
#        self.rays = None
        

#        mirror_i = 0
#        reflected_ray_direction, reflected_ray_start_point = ray_relfection.reflection(ray_start_point,  ray_direction, self.mirror[mirror_i * number_of_mirror_vertices:(mirror_i + 1) * number_of_mirror_vertices-1])
#        print ray_start_point, ray_direction, reflected_ray_start_point, reflected_ray_direction
#        for i in range(number_of_reflections):
#            if i == 0:
#                ray_start_point = initial_ray_start_point
#                ray_direction = initial_ray_direction
#            else:
#                ray_start_point = reflected_ray_start_points[-1]
#                ray_direction = reflected_ray_directions[-1]
#                
#            for mirror_i in range(number_of_mirrors):
#                reflected_ray_direction, reflected_ray_start_point = ray_relfection.reflection(ray_start_point,  ray_direction, self.mirror[mirror_i * number_of_mirror_vertices:(mirror_i + 1) * number_of_mirror_vertices-1])
#                print reflected_ray_direction, reflected_ray_start_point, ray_start_point, ray_direction#, self.mirror[mirror_i * number_of_mirror_vertices:(mirror_i + 1) * number_of_mirror_vertices]
##                print self.mirror[mirror_i * number_of_mirror_vertices:(mirror_i + 1) * number_of_mirror_vertices]
#                if reflected_ray_direction != None and reflected_ray_start_point != None:
#                    reflected_ray_start_points.append(reflected_ray_start_point)
#                    reflected_ray_directions.append(reflected_ray_direction)
#                    break
#
#        reflected_ray_start_points.append(reflected_ray_start_points[-1] + reflected_ray_direction[-1] * 100.0)
#        self.reflected_ray_start_points = numpy.array(reflected_ray_start_points)
#        print self.reflected_ray_start_points
        print time.time() - st
#        if reflected_ray_vector == None:
#            self.rays = numpy.array([ray_start_point, ray_start_point+ ray_direction * 50.0, ray_start_point + ray_direction * 100.0])
#        else:
#            self.rays = numpy.array([ray_start_point, intersection, intersection + reflected_ray_vector * 200.0])
#            
#        if reflected1_ray_vector == None:
#            self.rays1 = None
#        else:
#            self.rays1 = numpy.array([intersection1, intersection1 + reflected1_ray_vector * 200.0])

    def draw_scene(self):
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointerf(self.mirror)
        glColor3fv((1.0, 0.7, 1.0))
        glDrawArrays(GL_POLYGON, 0, 4)
        glColor3fv((1.0, 1.0, 0.7))
        glDrawArrays(GL_POLYGON, 4, 4)
        if self.rays != None:
            glLineWidth(2)
            glVertexPointerf(self.rays)
            for i in range(self.rays.shape[0]-1):
                glColor3fv((1.0, float(i) * 0.2, 0.0))
                glDrawArrays(GL_LINES, i, 2)

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
