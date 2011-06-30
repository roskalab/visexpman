import time

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

import numpy
import visexpman
import generic.graphics
import visexpman.users.zoltan.configurations
import visexpman.engine.optics.ray_reflection as ray_relfection
import visexpman.engine.optics.surface_meshes as surface_meshes
import visexpman.engine.generic.geometry as geometry

class RayReflection(generic.graphics.Screen):
    #BUGS: 
    #1. ray is not reflected from some shapes with various alignment
    #2. ray is not reflected from the boundary of two adjacent mirrors  - FIXED
    def initialization(self):
        self.alignment()
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
#    def generate_rays(self):
#        grid = numpy.linspace(0.0,  1.0,  11)
        
    def alignment(self):
        
        st = time.time()
        unit = 100.0
        number_of_reflections = 1
        self.line_color_step = 1.0 / 0.8
        self.number_of_shape_vertices = 3
        
        initial_ray_start_point = numpy.array([[0.0 * unit, 0.0 * unit, 0.0 * unit], [0.0 * unit, 0.0 * unit, 0.0 * unit]])
        initial_ray_direction = numpy.array([[0.0 * unit, 0.1 * unit, 1.0 * unit], [0.0 * unit, 0.2 * unit, 1.0 * unit]])
        
        initial_ray_start_point = numpy.array([[0.0 * unit, 0.0 * unit, 0.0 * unit], [0.0 * unit, 0.0 * unit, 0.0 * unit], [0.0 * unit, 0.0 * unit, 0.0 * unit], [0.0 * unit, 0.0 * unit, 0.0 * unit]])
        initial_ray_direction = numpy.array([[0.0 * unit, 0.1 * unit, 1.0 * unit], [0.0 * unit, 0.2 * unit, 1.0 * unit], [0.1 * unit, 0.1 * unit, 1.0 * unit], [0.1 * unit, 0.2 * unit, 1.0 * unit]])
        
#        initial_ray_start_point = numpy.array([[0.5 * unit, 0.0 * unit, 0.0 * unit]])
#        initial_ray_direction = numpy.array([[0.0 * unit, 0.2 * unit, 1.0 * unit]])
        
        initial_ray_direction = -1 * initial_ray_direction
        initial_ray_start_point = initial_ray_start_point + numpy.array([0.0,  0.0, 5.0 * unit])
        
        horizontal_radius = 3.0 * unit
        horizontal_angle_range = [-90.0, 90.0]
        vertical_radius = 2.0 * unit
        vertical_angle_range = [-90.0, 90.0]
        mesh_size = [0.31 * 1.0 * unit, 0.21 * 1.0 * unit]
        
#        #four triangles
#        horizontal_radius = 3.0 * unit
#        horizontal_angle_range = [-30.0, 30.0]
#        vertical_radius = 2.0 * unit
#        vertical_angle_range = [-30.0, 30.0]
#        mesh_size = [1.0 * unit, 1.0 * unit]

        self.screen, self.number_of_shapes = surface_meshes.toroid_mesh(horizontal_radius, horizontal_angle_range, vertical_radius, vertical_angle_range, mesh_size)        
        
#        for i in range(1000):
#            if not self.test_reflection(0,  10):
#                print i
        #START OF TEST MIRROR
#        import random
#        preceision = 3
#        random.seed(0)
#        test_rotation = []
#        for i in range(2):
#            test_rotation.append(unit * round(random.random(), preceision))
#            
#        test_pitch = unit * round(random.random(), preceision)
#        
#        self.screen = numpy.array([[0.0, 0.0, 1.0 * unit], [1.0 * unit,  0.0,  1.0 * unit + test_rotation[0]], [0.0 * unit, 1.0 * unit, 1.0 * unit + test_pitch], [0.0, 0.0, 1.0 * unit], [-1.0 * unit,  0.0,  1.0 * unit + test_rotation[1]], [0.0 * unit, 1.0 * unit, 1.0 * unit + test_pitch]])
#        self.number_of_shapes = 1        
#        #END OF TEST MIRROR  
#        
        

        self.mirrors = []
        for i in range(self.number_of_shapes):
            self.mirrors.append(self.screen[i * self.number_of_shape_vertices: (i+1) * self.number_of_shape_vertices])
        self.mirrors = numpy.array(self.mirrors)
        
        self.rays = []
        for i in range(initial_ray_start_point.shape[0]):
            is_reflection, rays = ray_relfection.multiple_reflections(self.mirrors,  initial_ray_start_point[i], initial_ray_direction[i], number_of_reflections)
            self.rays.append(rays)
            
        
        
        self.axis = numpy.array([[0.0, 0.0, 0.0], [100.0 * unit, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 100.0 * unit, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 100.0 * unit]])
        
        print time.time() - st
        
    def test_reflection(self, seed_in,  prec):
        unit = 100.0
        number_of_reflections = 1
        self.line_color_step = 1.0 / 0.8
        self.number_of_shape_vertices = 3
        
        initial_ray_start_point = numpy.array([[0.5 * unit, 0.0 * unit, 0.0 * unit]])
        initial_ray_direction = numpy.array([[0.0 * unit, 0.2 * unit, 1.0 * unit]])
        
        #START OF TEST MIRROR
        import random
        preceision = prec
        random.seed(seed_in)
        test_rotation = []
        for i in range(2):
            test_rotation.append(1.0 * unit * round(random.random(), preceision))
            
        test_pitch = 1.0 * unit * round(random.random(), preceision)
        
        self.screen = numpy.array([[0.0, 0.0, 1.0 * unit], [1.0 * unit,  0.0,  1.0 * unit + test_rotation[0]], [0.0 * unit, 1.0 * unit, 1.0 * unit + test_pitch], [0.0, 0.0, 1.0 * unit], [-1.0 * unit,  0.0,  1.0 * unit + test_rotation[1]], [0.0 * unit, 1.0 * unit, 1.0 * unit + test_pitch]])
        self.number_of_shapes = 1        
        #END OF TEST MIRROR

        self.mirrors = []
        for i in range(self.number_of_shapes):
            self.mirrors.append(self.screen[i * self.number_of_shape_vertices: (i+1) * self.number_of_shape_vertices])
        self.mirrors = numpy.array(self.mirrors)
        
        self.rays = []
        for i in range(initial_ray_start_point.shape[0]):
            is_reflection, rays = ray_relfection.multiple_reflections(self.mirrors,  initial_ray_start_point[i], initial_ray_direction[i], number_of_reflections)
            self.rays.append(rays)
        return is_reflection

    def draw_scene(self):
        glEnableClientState(GL_VERTEX_ARRAY)
        for i in range(len(self.rays)):
            intensity = 0.5 + float(i+1)/(2*len(self.rays))
            glColor3fv((intensity, intensity, intensity))
#            glColor3fv((1.0, 1.0, 1.0))
            if self.rays[i] != None:
                glLineWidth(1)
                glVertexPointerf(self.rays[i])
                for i in range(self.rays[0].shape[0]-1):                    
                    glDrawArrays(GL_LINES, i, 2)
        glDisableClientState(GL_VERTEX_ARRAY) 

        #draw x,y and z axis
        glEnableClientState(GL_VERTEX_ARRAY)
        glLineWidth(1)
        glColor3fv((1.0, 0.0, 0.0))
        glVertexPointerf(self.axis)
        glDrawArrays(GL_LINES, 0, 2)
        glColor3fv((0.0, 1.0, 0.0))
        glVertexPointerf(self.axis)
        glDrawArrays(GL_LINES, 2, 2)
        glColor3fv((0.0, 0.0, 1.0))
        glVertexPointerf(self.axis)
        glDrawArrays(GL_LINES, 4, 2)
        glDisableClientState(GL_VERTEX_ARRAY) 
        
        
        #draw toroid screen
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointerf(self.screen)
        for i in range(self.number_of_shapes):
            r = float(i) / self.number_of_shapes
            g = 1.0 - r
            b = 1.0
            alpha = 0.5
#            if i == 2:
#                r = 0.5
#                b = 0.5
#                g = 0.5
#                print self.screen[i*4:(i+1)*4]
                
            glColor4fv((r, g, b,  alpha))
            glDrawArrays(GL_POLYGON, i*self.number_of_shape_vertices, self.number_of_shape_vertices)
            
        
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
