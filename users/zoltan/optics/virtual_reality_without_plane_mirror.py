import time

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

import numpy
import visexpman
import generic.graphics
import visexpman.users.zoltan.configurations
import visexpman.users.zoltan.optics.ray_reflection as ray_reflection
import visexpman.users.zoltan.optics.angular_amplification_mirror as angular_amplification_mirror
import visexpman.users.zoltan.optics.surface_meshes as surface_meshes
import visexpman.engine.generic.geometry as geometry
import visexpman.users.zoltan.optics.toroid_screen as toroid_screen


class VirtualRealityOpticalAlignment(generic.graphics.Screen):
    '''
    1 unit = 1mm
    '''
    def initialization(self):
        #Define axis to display
        axis_length = 1000.0
        self.axis = numpy.array([[0.0, 0.0, 0.0], [axis_length, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, axis_length, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, axis_length]])
        #create objects for simulation and calculate light reflections
        self.alignment()
        #enable blending to display transparent objects
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)        
        
    def toroid(self,  center = None):
        viewing_angle = 180.0
        height = 800.0
        inner_radius = 170.0
        horizontal_radius = 440.0
        toroid_screen_data = toroid_screen.ToroidScreen(viewing_angle,  height,  inner_radius,  horizontal_radius)
        
        #== High resolution toroid ==
        unit = 200.0
        horizontal_radius = 3.0 * unit
        horizontal_angle_range = [-90.0, 90.0]
        vertical_radius = 2.0 * unit
        vertical_angle_range = [-90.0, 90.0]
        mesh_size = [0.31 * 1.0 * unit, 0.21 * 1.0 * unit]

        #== Very low resolution toroid (four triangles) ==
        horizontal_radius = 3.0 * unit
        horizontal_angle_range = [-30.0, 30.0]
        vertical_radius = 2.0 * unit
        vertical_angle_range = [-30.0, 30.0]
        mesh_size = [1.0 * unit, 1.0 * unit]

        #== Low resolution toroid ==
        horizontal_radius = toroid_screen_data.horizontal_radius
        horizontal_angle_range = [-0.5 * viewing_angle, 0.5 * viewing_angle]
        vertical_radius = toroid_screen_data.vertical_radius
        vertical_angle_range = toroid_screen_data.vertical_angle_range
        #medium resolution
        mesh_size = [0.2 * toroid_screen_data.horizontal_perimeter_endcap , 0.1 * toroid_screen_data.vertical_perimeter]
        #high resolution
        #mesh_size = [0.1 * toroid_screen_data.horizontal_perimeter_endcap , 0.05 * toroid_screen_data.vertical_perimeter]

        self.screen, self.number_of_toroid_shapes = surface_meshes.toroid_mesh(horizontal_radius, horizontal_angle_range, vertical_radius, vertical_angle_range, mesh_size)
        if center != None:
            self.screen = self.screen + center
                
                
    def alignment(self):
        st = time.time()
        #== General settings for optical simulation ==
        reflect = True
        number_of_reflections = 2
        self.line_color_step = 1.0 / 0.8
        self.number_of_shape_vertices = 3
        #== Enable optical objects ==
        self.enable_plane_mirror = False
        self.enable_aam_mirror = True
        self.enable_toroid = True
        self.enable_projector = True
        #== Size / position of optical objects ==
        #== Angular amplification mirror ==
        aam_position = numpy.array([0, 410, 0])
        amplification = 12.0
        focal_distance = 14500.0
        mesh_size = 0.510141 * 100*0.7
        angle_range = [0.0, 0.3]
        ang_res = 10
        mirror_profile, invalid_angles = angular_amplification_mirror.calculate_angular_amplification_mirror_profile(amplification, focal_distance, angle_range =angle_range, angular_resolution = ang_res)
        self.aam, self.number_of_aam_shapes = surface_meshes.aam_mesh(focal_distance, amplification, mesh_size, mirror_profile)
        self.aam = self.aam + aam_position
        
        #==Plane mirror ==
        relative_position_to_aam = numpy.array([0.0, 0*-90.0, 0.0])
        mirror_position = aam_position + relative_position_to_aam
        mirror_size = 70
        mirror_tilt = 0.0
        mirror_tilt = (mirror_tilt + 0.0) * numpy.pi / 180.0
        z_adjustment = round(0.5 * mirror_size * numpy.cos(mirror_tilt), visexpman.users.zoltan.configurations.GEOMETRY_PRECISION)
        y_adjustment = round(0.5 * mirror_size * numpy.sin(mirror_tilt), visexpman.users.zoltan.configurations.GEOMETRY_PRECISION)
        self.plane_mirror = numpy.array([[-0.5 * mirror_size, - y_adjustment, -z_adjustment],
                                                            [0.5 * mirror_size,  - y_adjustment, -z_adjustment],
                                                            [0.5 * mirror_size, y_adjustment, z_adjustment],
                                                            [-0.5 * mirror_size, y_adjustment, z_adjustment]])
        self.plane_mirror = self.plane_mirror + mirror_position
#        self.plane_mirror = self.plane_mirror[0:3]

        #== Projector configuration ==
        relative_position_to_plane_mirror = numpy.array([0.0, -90.0, 0.0])
        projector_position = relative_position_to_plane_mirror + mirror_position
        projector_orientation = [0.0, 1.0 ,0.0 ]
        self.projector_size = [30, 30,30] #The realistic sizes of Acer k11: [120.0, 40.0, 115.0]
        self.projector = self.cuboid_vertices(self.projector_size)
        self.projector = self.projector + numpy.array(projector_position)
        projection_distance = 600.0
        projected_image_size  = 380.0
        aspect_ratio = 1.3333
        half_angle_rays = True
        #The projected image with the beamer's lens form a pyramid. The vector pointing from the apex to the vertices of the base are calculated here:
        corner_rays = ray_reflection.pyramid_projection(projector_position, projector_orientation, projection_distance, projected_image_size, aspect_ratio, half_angle_rays = half_angle_rays)

        if half_angle_rays:
            n_rays = 3
            initial_ray_start_point = []
            for i in range(n_rays+1):
                initial_ray_start_point.append(projector_position)
            initial_ray_direction = []
            initial_ray_direction.append(projector_orientation)
            for i in range(n_rays):
                initial_ray_direction.append(corner_rays[i])
            initial_ray_start_point = numpy.array(initial_ray_start_point)
            initial_ray_direction = numpy.array(initial_ray_direction)
        else:
            initial_ray_start_point = numpy.array([projector_position, projector_position, projector_position, projector_position, projector_position])
            initial_ray_direction = numpy.array([projector_orientation, corner_rays[0], corner_rays[1], corner_rays[2], corner_rays[3]])
#        initial_ray_start_point = numpy.array([projector_position])
#        initial_ray_direction = numpy.array([ray1])
#        ind = 3
#        initial_ray_start_point = initial_ray_start_point[ind:ind+1]
#        initial_ray_direction = initial_ray_direction[ind:ind+1]

        
        
        #== Toroid screen ==
        screen_position = numpy.array([0, 0, 0])
        self.toroid(screen_position)
        
        #mouse parameters
        mouse_position = numpy.array([0.0, -230.0, 0.0])
        mouse_viewing_angle_range = [-20.0, 60.0]
        ray_length = 1000.0
        mouse_visual_range_boundaries = []
        for mouse_viewing_angle in mouse_viewing_angle_range:
            x = mouse_position[0]
            y = -ray_length * numpy.cos(mouse_viewing_angle) + mouse_position[1]
            z = -ray_length * numpy.sin(mouse_viewing_angle) + mouse_position[2]
            mouse_visual_range_boundaries.append(mouse_position.tolist())
            mouse_visual_range_boundaries.append([x, y, z])
        mouse_visual_range_boundaries = numpy.array(mouse_visual_range_boundaries)
        
        #== Collect all mirror objects ==
        self.mirrors = []
        if self.enable_aam_mirror:
            for i in range(self.number_of_aam_shapes):
                self.mirrors.append(self.aam[i * self.number_of_shape_vertices: (i+1) * self.number_of_shape_vertices])
        
        if self.enable_plane_mirror:
            self.mirrors.append(numpy.delete(self.plane_mirror, 3, 0))
            self.mirrors.append(numpy.delete(self.plane_mirror, 1, 0))
            
        if self.enable_toroid:
            for i in range(self.number_of_toroid_shapes):
                self.mirrors.append(self.screen[i * self.number_of_shape_vertices: (i+1) * self.number_of_shape_vertices])
            
        #== Calculate reflections ==
        self.rays = []
        if reflect:
            for i in range(initial_ray_start_point.shape[0]):
                is_reflection, rays = ray_reflection.multiple_reflections(self.mirrors,  initial_ray_start_point[i], initial_ray_direction[i], number_of_reflections)
                print(is_reflection)
                self.rays.append(rays)

        flatten_rays = []
        self.ray_chain_mask = []
        for ray_chain in self.rays:
            for ray in ray_chain:
                flatten_rays.append(ray)            
                self.ray_chain_mask.append(True)
            self.ray_chain_mask[-1] = False
        self.rays = numpy.array(flatten_rays)
        #== put together vertexes ==
        self.vertices = numpy.concatenate((self.axis, self.rays, self.plane_mirror, self.aam, self.screen, self.projector, mouse_visual_range_boundaries))
        
#        print self.rays
        print(time.time() - st)
    
    def draw_scene(self):
        #draw x,y and z axis 
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointerf(self.vertices)
        glLineWidth(1)
        glColor4fv((1.0, 0.0, 0.0, 1.0))
        glDrawArrays(GL_LINES, 0 , 2)
        glColor4fv((0.0, 1.0, 0.0, 1.0))
        glDrawArrays(GL_LINES, 2, 2)
        glColor4fv((0.0, 0.0, 1.0, 1.0))
        glDrawArrays(GL_LINES, 4, 2)
        vertex_array_offset = 6
        
        #== Draw light rays ==
        glLineWidth(2)
        for i in range(int(self.rays.shape[0]-1)):
            intensity = 0.5 + float(i+1)/(2*self.rays.shape[0])
            if i == 0:
                glColor3fv((intensity, 0, 0))
            else:
                glColor3fv((intensity, intensity, intensity))
            if self.ray_chain_mask[i]:
                glDrawArrays(GL_LINES, vertex_array_offset + i, 2)
        vertex_array_offset = vertex_array_offset + self.rays.shape[0]
        
        #== Draw optical objects ==
        #draw plane mirror
        if self.enable_plane_mirror:
            glColor4fv((0.5, 0.5, 0.5, 0.7))
            glDrawArrays(GL_POLYGON, vertex_array_offset, self.plane_mirror.shape[0])
        vertex_array_offset = vertex_array_offset + self.plane_mirror.shape[0]
        #draw aam mirror
        if self.enable_aam_mirror:
            for i in range(self.number_of_aam_shapes):
                r = float(i) / self.number_of_aam_shapes
                g = 1.0 - r
                b = 1.0
                alpha = 0.5
                glColor4fv((r, g, b,  alpha))
                glDrawArrays(GL_POLYGON, vertex_array_offset + i*self.number_of_shape_vertices ,  self.number_of_shape_vertices)
        vertex_array_offset = vertex_array_offset + self.number_of_aam_shapes * self.number_of_shape_vertices
        #draw toroid screen
        if self.enable_toroid:
            for i in range(self.number_of_toroid_shapes):
                r = float(i) / self.number_of_toroid_shapes
                g = 1.0 - r
                b = 1.0 - r
                alpha = 0.5
                glColor4fv((r, g, b,  alpha))
                glDrawArrays(GL_POLYGON, vertex_array_offset + i*self.number_of_shape_vertices ,  self.number_of_shape_vertices)
        vertex_array_offset = vertex_array_offset + self.number_of_toroid_shapes * self.number_of_shape_vertices
        
        #== Draw other objects == 
        #draw projector
        if self.enable_projector:
            glColor4fv((0.2, 0.5, 0.9, 0.5))
            for i in range(6):
                glDrawArrays(GL_POLYGON, vertex_array_offset + i*4, 4)
        vertex_array_offset = vertex_array_offset + self.projector.shape[0]
                
        #draw mouse vision boundaries
        glLineWidth(1)
        glColor4fv((0.0, 1.0, 0.0, 0.5))
        glDrawArrays(GL_LINES, vertex_array_offset, 2)
        glDrawArrays(GL_LINES, vertex_array_offset + 2, 2)
        
        #== End of drawing objects ==
        glDisableClientState(GL_VERTEX_ARRAY)

    def render_before_set_view(self):
        msg = str(self.position) + "%2.0f, %2.0f, %2.0f, %2.1f,%2.2f, %f"%(self.heading,  self.roll, self.pitch, self.scale, self.frame_rate, self.wait_time_left)
        self.render_text(msg, color = (0.8, 0.8, 0.8), position = (-400, -250))


config = visexpman.users.zoltan.configurations.GraphicsTestConfig()
g = VirtualRealityOpticalAlignment(config, graphics_mode = 'standalone')
g.run()
g.close_screen()
