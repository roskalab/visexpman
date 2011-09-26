import time

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

import numpy
import sys
import os
import os.path
import multiprocessing
import pickle
import visexpman
import generic.graphics
import generic.utils as utils
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
        self.number_of_shape_vertices = 3
        #create objects for simulation and calculate light reflections
        if len(sys.argv) > 1:
            self.load_simulation_data(sys.argv[1])
            self.enable_plane_mirror = True
            self.enable_aam_mirror = True
            self.enable_toroid = True
            self.enable_projector = True
        else:
            self.alignment()

        #enable blending to display transparent objects
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA) 
        self.scale = 0.8   
        self.show_rays = True        
        
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
        mesh_size = [0.5*0.2 * toroid_screen_data.horizontal_perimeter_endcap*1, 0.5*0.1 * toroid_screen_data.vertical_perimeter]
        #high resolution
        #mesh_size = [0.1 * toroid_screen_data.horizontal_perimeter_endcap , 0.05 * toroid_screen_data.vertical_perimeter]

        self.screen, self.number_of_toroid_shapes = surface_meshes.toroid_mesh(horizontal_radius, horizontal_angle_range, vertical_radius, vertical_angle_range, mesh_size)
        if center != None:
            self.screen = self.screen + center
                
                
    def alignment(self):
        #main parameters:
        d_fi = 45.0
        config = {'n_rays': [20, 20],
                        'mirror_tilt' : 22.5 - 5.5 + 0.5 * d_fi,
                        'mirror_size' : [50, 50],
                        'projector_angle' : 45.0 - d_fi, 
                        'projected_image_size' : 2030.0 * 0.36,
                        'projector_plane_mirror_distance' : 220, 
                        'only_image_boundary': False,
                        'image_boundary_size': 2,
                        'aam_angle_resolution' : 30, #30
                        'mesh_size' : 0.510141 * 100*0.2,  #*0.2
                        'aspect_ratio' : 0.75,
                        }
        self.simulation_config = config
        
        st = time.time()
        #== General settings for optical simulation ==
        reflect = True
        number_of_reflections = 3
        self.line_color_step = 1.0 / 0.8        
        #== Enable optical objects ==
        self.enable_plane_mirror = True
        self.enable_aam_mirror = True
        self.enable_toroid = True
        self.enable_projector = True
        #== Size / position of optical objects ==
        #== Angular amplification mirror ==
        aam_position = numpy.array([0, 360, -40])
        amplification = 12.0
        focal_distance = 14500.0
        mesh_size = config['mesh_size']
#         mesh_size = 0.5 * 100*1.4
        angle_range = [0.0, 0.3]
        ang_res = 8
        ang_res = config['aam_angle_resolution']    
        mirror_profile, invalid_angles = angular_amplification_mirror.calculate_angular_amplification_mirror_profile(amplification, focal_distance, angle_range =angle_range, angular_resolution = ang_res)
        self.aam, self.number_of_aam_shapes = surface_meshes.aam_mesh(focal_distance, amplification, mesh_size, mirror_profile, angle_range = [0*numpy.pi, 2*numpy.pi])
        self.aam = self.aam + aam_position        
        
        
        #==Plane mirror ==
        relative_position_to_aam = numpy.array([0.0, -90.0, 0.0])
        mirror_position = aam_position + relative_position_to_aam
        mirror_size = [80.0, 80.0]
        mirror_size = config['mirror_size']
        mirror_tilt = 22.5-9.0
        mirror_tilt = config['mirror_tilt']
        mirror_tilt = (mirror_tilt + 0.0) * numpy.pi / 180.0
        z_adjustment = round(0.5 * mirror_size[1] * numpy.cos(mirror_tilt), visexpman.users.zoltan.configurations.GEOMETRY_PRECISION)
        y_adjustment = round(0.5 * mirror_size[1] * numpy.sin(mirror_tilt), visexpman.users.zoltan.configurations.GEOMETRY_PRECISION)
        self.plane_mirror = numpy.array([[-0.5 * mirror_size[0], - y_adjustment, -z_adjustment],
                                                            [0.5 * mirror_size[0],  - y_adjustment, -z_adjustment],
                                                            [0.5 * mirror_size[0], y_adjustment, z_adjustment],
                                                            [-0.5 * mirror_size[0], y_adjustment, z_adjustment]])
        self.plane_mirror = self.plane_mirror + mirror_position
#        self.plane_mirror = self.plane_mirror[0:3]

        #== Projector configuration ==
        distance_from_plane_mirror = 110.0
        distance_from_plane_mirror = config['projector_plane_mirror_distance']
        #to ensure that the projected image on the aam is not changed, the projector angle shall be 90-2*mirror_tilt
        projector_angle = 45.0
        projector_angle = config['projector_angle']
        projector_angle = -projector_angle * numpy.pi / 180.0 + numpy.pi
        projector_orientation = -numpy.array([0.0, numpy.sin(projector_angle), numpy.cos(projector_angle)])
        relative_position_to_plane_mirror = -projector_orientation * distance_from_plane_mirror
        projector_position = relative_position_to_plane_mirror + mirror_position

        self.projector_size = [30, 30, 30] #The realistic sizes of Acer k11: [120.0, 40.0, 115.0]
        self.projector = self.cuboid_vertices(self.projector_size)
        self.projector = self.projector + numpy.array(projector_position)        
        projection_distance = 3400.0
        projected_image_size  = 1000.0
        projected_image_size  = config['projected_image_size']
        aspect_ratio = 1.3333
        aspect_ratio = config['aspect_ratio']
        half_angle_rays = False        
        s = [1.0, 1.0]
        offset = [0.0, 0.0]
        n_rays = [5, 5]
        n_rays = config['n_rays']
        #generate list for projected image points (represented by rays)
        corners = []
        for row in range(n_rays[0]):
            for col in range(n_rays[1]):
                if n_rays[0] == 1:
                    corner = [0 + offset[0], 2 * s[1] * col / (n_rays[1] - 1) - s[1] + offset[1]]
                elif n_rays[1] == 1:
                    corner = [2 * s[0] * row / (n_rays[0] - 1) - s[0] + offset[0], 0 + offset[1]]
                else:
                    corner = [2 * s[0] * row / (n_rays[0] - 1) - s[0] + offset[0], 2 * s[1] * col / (n_rays[1] - 1) - s[1] + offset[1]]
                if config['only_image_boundary']:
                    if row < config['image_boundary_size']  or row >= n_rays[0] - config['image_boundary_size'] or col < config['image_boundary_size'] or col >= n_rays[1] - config['image_boundary_size']:
                        corners.append(corner)
                else:
                    corners.append(corner)        
        #The projected image with the beamer's lens form a pyramid. The vector pointing from the apex to the vertices of the base are calculated here:
        corner_rays = ray_reflection.pyramid_projection(projector_position, projector_orientation, projection_distance, projected_image_size, aspect_ratio, half_angle_rays = half_angle_rays, corners = corners)        
        initial_ray_start_point = []
        for i in range(len(corner_rays)):
            initial_ray_start_point.append(projector_position)
        initial_ray_direction = []
#        initial_ray_direction.append(projector_orientation)
        for i in range(len(corner_rays)):
            initial_ray_direction.append(corner_rays[i])
        initial_ray_start_point = numpy.array(initial_ray_start_point)
        initial_ray_direction = numpy.array(initial_ray_direction)        
#         ind = 0
#         initial_ray_start_point = initial_ray_start_point[ind:ind+1]
#         initial_ray_direction = initial_ray_direction[ind:ind+1]
        
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
        
        if self.enable_plane_mirror:
            self.mirrors.append(numpy.delete(self.plane_mirror, 3, 0))
            self.mirrors.append(numpy.delete(self.plane_mirror, 1, 0))
                
        if self.enable_aam_mirror:
            for i in range(self.number_of_aam_shapes):
                self.mirrors.append(self.aam[i * self.number_of_shape_vertices: (i+1) * self.number_of_shape_vertices])
            
        if self.enable_toroid:
            toroid_mirrors = []
            for i in range(self.number_of_toroid_shapes):
                self.mirrors.append(self.screen[i * self.number_of_shape_vertices: (i+1) * self.number_of_shape_vertices])
                toroid_mirrors.append(self.screen[i * self.number_of_shape_vertices: (i+1) * self.number_of_shape_vertices])           
        
        #== Calculate reflections ==
        print 'number of mirrors %i'%len(self.mirrors)
        self.rays = []
        if reflect:
            pool = multiprocessing.Pool()
            map_string = 'reflection_results = pool.map(multiple_reflections_wrapper, parameters)'
            parameters = []
            for i in range(initial_ray_start_point.shape[0]):
                parameters.append({
                              'mirrors' : self.mirrors, 
                              'initial_ray_start_point' : initial_ray_start_point[i], 
                              'initial_ray_direction' : initial_ray_direction[i], 
                              'number_of_reflections' : number_of_reflections
                              })
                              
            exec(map_string)
            pool.close()
            pool.join()
            for reflection_result in reflection_results:
                print reflection_result[0]
                self.rays.append(reflection_result[1])
                
            

        flatten_rays = []
        self.ray_chain_mask = []
        for ray_chain in self.rays:
            for ray in ray_chain:
                flatten_rays.append(ray)            
                self.ray_chain_mask.append(True)
            self.ray_chain_mask[-1] = False
        self.rays = numpy.array(flatten_rays)
        
        #== find reflection points on screen ==        
            
        points_on_screen = []        
        if self.enable_toroid: 
            pool = multiprocessing.Pool()        
            map_string = 'points = pool.map(ray_incidence_on_mirror_wrapper, parameters)'
            parameters = []
            for toroid_mirror in toroid_mirrors:
                parameters.append({
                              'mirror' : toroid_mirror, 
                              'rays' : self.rays, 
                              })
                              
            exec(map_string)
            pool.close()
            pool.join()
            for point in points:
                if len(point) > 0 and not utils.is_vector_in_array(numpy.array(points_on_screen),  point[0]):                    
                    points_on_screen.append(point[0])                    

        self.points_on_screen = numpy.array(points_on_screen)
#        print self.points_on_screen

        #== put together vertexes ==
        self.vertices = numpy.concatenate((self.axis, self.rays, self.plane_mirror, self.aam, self.screen, self.projector, mouse_visual_range_boundaries, self.points_on_screen))
        self.vertex_pointers = numpy.array([6, self.rays.shape[0], self.plane_mirror.shape[0], self.number_of_aam_shapes * self.number_of_shape_vertices, self.number_of_toroid_shapes * self.number_of_shape_vertices, self.projector.shape[0], 
                                     4, self.points_on_screen.shape[0]])
        
        if self.points_on_screen.shape != (0,):
            self.vertices = numpy.concatenate((self.vertices, self.points_on_screen))
            
        #save: self.vertices, self.vertex_pointers, self.ray_chain_mask
        folder_to_save = utils.generate_foldername(self.config.SIMULATION_DATA_PATH + os.sep + 'simulation')
        self.save_simulation_data(folder_to_save)
#        self.load_simulation_data(folder_to_save)
            
        print 'number of rays %d, number of rays hit the screen %d'%(len(corners), self.points_on_screen.shape[0])
        
        #display runtime
        print time.time() - st
        
    def save_simulation_data(self, foldername):
        if not os.path.isdir(foldername):
            os.mkdir(foldername)
        numpy.savetxt(foldername + os.sep + 'vertices.txt',  self.vertices)
        numpy.savetxt(foldername + os.sep + 'vertex_pointers.txt',  self.vertex_pointers)
        numpy.savetxt(foldername + os.sep + 'ray_chain_mask.txt',  self.ray_chain_mask)
        #TODO: save self.simulation_config
        
    def load_simulation_data(self, foldername):
        self.vertices = numpy.loadtxt(foldername + os.sep + 'vertices.txt')
        self.vertex_pointers = numpy.loadtxt(foldername + os.sep + 'vertex_pointers.txt', dtype = int)
        ray_chain_mask_f = numpy.loadtxt(foldername + os.sep + 'ray_chain_mask.txt')
        self.ray_chain_mask = numpy.where(ray_chain_mask_f == 0.0,  False,  True)
        
    def user_keyboard_handler(self, key_pressed):
        if key_pressed == 'space':
            self.show_rays = self.show_rays ^ True
    
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
        vertex_array_offset = self.vertex_pointers[0]
        
        #== Draw light rays ==
        if self.show_rays:
            glLineWidth(1)
            for i in range(int(self.vertex_pointers[1]-1)):
                intensity = 0.5 + float(i+1)/(2*self.vertex_pointers[1])
#                if i == 0 or i == 1:
#                    glColor3fv((intensity, 0, 0))
#                else:
                glColor3fv((intensity, intensity, intensity))
                if self.ray_chain_mask[i]:
                    glDrawArrays(GL_LINES, vertex_array_offset + i, 2)
        vertex_array_offset = vertex_array_offset + self.vertex_pointers[1]
        
        #== Draw optical objects ==
        #draw plane mirror
        if self.enable_plane_mirror:
            glColor4fv((0.5, 0.5, 0.5, 0.7))
            glDrawArrays(GL_POLYGON, vertex_array_offset, self.vertex_pointers[2])
        vertex_array_offset = vertex_array_offset + self.vertex_pointers[2]
        #draw aam mirror
        if self.enable_aam_mirror:
            for i in range(int(self.vertex_pointers[3] / self.number_of_shape_vertices)):
                r = float(i) / (self.vertex_pointers[3] / self.number_of_shape_vertices)
                g = 1.0 - r
                b = 1.0
                alpha = 0.5
                glColor4fv((r, g, b,  alpha))
                glDrawArrays(GL_POLYGON, vertex_array_offset + i*self.number_of_shape_vertices ,  self.number_of_shape_vertices)
        vertex_array_offset = vertex_array_offset + self.vertex_pointers[3]
        #draw toroid screen
        if self.enable_toroid:
            for i in range(int(self.vertex_pointers[4] / self.number_of_shape_vertices)):
                r = float(i) / (self.vertex_pointers[4] / self.number_of_shape_vertices)
                g = 1.0 - r
                b = 1.0 - r
                alpha = 0.5
                glColor4fv((r, g, b,  alpha))
                glDrawArrays(GL_POLYGON, vertex_array_offset + i*self.number_of_shape_vertices ,  self.number_of_shape_vertices)
        vertex_array_offset = vertex_array_offset + self.vertex_pointers[4]
        
        #== Draw other objects == 
        #draw projector
        if self.enable_projector:
            glColor4fv((0.2, 0.5, 0.9, 0.5))
            for i in range(6):
                glDrawArrays(GL_POLYGON, vertex_array_offset + i*4, 4)
        vertex_array_offset = vertex_array_offset +self.vertex_pointers[5]
                
        #draw mouse vision boundaries
        glLineWidth(1)
        glColor4fv((0.0, 1.0, 0.0, 0.5))
        glDrawArrays(GL_LINES, vertex_array_offset, 2)
        glDrawArrays(GL_LINES, vertex_array_offset + 2, 2)
        vertex_array_offset = vertex_array_offset + self.vertex_pointers[6]
        
        #draw projection boundaries on screen
        if self.vertex_pointers[7] > 0:
            glColor4fv((1.0, 1.0, 0.0, 0.5))
            glPointSize(7.0)
            glDrawArrays(GL_POINTS, vertex_array_offset, self.vertex_pointers[7])
        vertex_array_offset = vertex_array_offset + self.vertex_pointers[7]
        #== End of drawing objects ==
        glDisableClientState(GL_VERTEX_ARRAY)

    def render_before_set_view(self):
        msg = str(self.position) + "%2.0f, %2.0f, %2.0f, %2.1f,%2.2f, %f"%(self.heading,  self.roll, self.pitch, self.scale, self.frame_rate, self.wait_time_left)
        self.render_text(msg, color = (0.8, 0.8, 0.8), position = utils.cr((-400, -250)))

def multiple_reflections_wrapper(parameters):
#        is_reflection, rays = ray_reflection.multiple_reflections(self.mirrors,  initial_ray_start_point[i], initial_ray_direction[i], number_of_reflections)
        is_reflection, rays = ray_reflection.multiple_reflections(parameters['mirrors'],  parameters['initial_ray_start_point'], parameters['initial_ray_direction'], parameters['number_of_reflections'])
        return is_reflection, rays
        
def ray_incidence_on_mirror_wrapper(parameters):
    rays = parameters['rays']
    mirror = parameters['mirror']
    points_on_screen = []
    i = 0
    for point in rays:
        if geometry.is_point_in_polygon(point, mirror):
            points_on_screen.append(point)
        i = i + 1
    return points_on_screen

if __name__ == "__main__":
    config = visexpman.users.zoltan.configurations.GraphicsTestConfig()
    g = VirtualRealityOpticalAlignment(config, graphics_mode = 'standalone')
    g.run()
    g.close_screen()
