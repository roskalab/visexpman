
#This module shall be renamed, because all optical calculations are to be kept here
import numpy
#import visual as v
import visexpman.engine.generic.geometry as geometry

last_ray_length = 0.0

def reflection(ray_start_point,  ray_direction, polygon):
    '''
    polygon is at least three vertexes in x,y,z format
    '''
    if geometry.is_point_in_polygon(ray_start_point, polygon):
        #If ray is starting from a point inside the polygon, no reflection will take place
        return None, None
    else:
        intersection_exists, intersection  = geometry.ray_polygon_intersection(ray_start_point,  ray_direction, polygon)
        if intersection_exists:
            light = ray_direction
            normalized_plane_normal =  geometry.normalize_vector(geometry.plane_normal_vector(polygon))
            reflected_ray_vector = 2 * numpy.dot(-light, normalized_plane_normal) * normalized_plane_normal + light
            return intersection, reflected_ray_vector
        else:
            return None, None
            
def multiple_reflections(mirrors,  initial_ray_start_point, initial_ray_direction, number_of_reflections):
    '''
    Tracks the reflection of a single ray on multiple mirrors
    Format of mirrors: list of numpy.arrays
    '''
    is_reflection = False
    reflected_ray_start_points = [initial_ray_start_point]
    reflected_ray_directions = []
    for reflection_count in range(number_of_reflections):
        if reflection_count == 0:
            ray_start_point = initial_ray_start_point
            ray_direction = initial_ray_direction
        else:
            if len(reflected_ray_start_points) > 0 and len(reflected_ray_directions) > 0:
                ray_start_point = reflected_ray_start_points[-1]
                ray_direction = reflected_ray_directions[-1]

        mirrors_hit = 0
        for mirror_count in range(len(mirrors)):
            reflected_ray_start_point, reflected_ray_direction  = reflection(ray_start_point, ray_direction, mirrors[mirror_count])
#            print reflected_ray_start_point, reflected_ray_direction, ray_start_point, ray_direction
            if reflected_ray_start_point != None and reflected_ray_direction != None:
                mirrors_hit = mirrors_hit + 1
                if mirrors_hit >= 2:
                    distance1 = geometry.vector_length(ray_start_point - reflected_ray_start_point)
                    distance2 = geometry.vector_length(ray_start_point - reflected_ray_start_points[-1])
                    #the closer is chosen
                    if distance1 < distance2:
                        reflected_ray_directions[-1] = reflected_ray_direction
                        reflected_ray_start_points[-1] = reflected_ray_start_point
                else:
                    is_reflection = True
                    reflected_ray_start_points.append(reflected_ray_start_point)
                    reflected_ray_directions.append(reflected_ray_direction)

    if len(reflected_ray_directions) > 0:
        reflected_ray_start_points.append(reflected_ray_start_points[-1] + last_ray_length * reflected_ray_directions[-1])
    else:
        reflected_ray_start_points.append(initial_ray_start_point + last_ray_length * initial_ray_direction)
    rays = numpy.array(reflected_ray_start_points)    
    return is_reflection, rays
    
def pyramid_projection(apex, direction, height, base_hypotenuse, aspect_ratio, half_angle_rays = False, corners = [[0, 1], [0, -1], [-1, 0], [1, 0]]):
    '''
    calculates the direction vectors to the four corners of a projected image from the projector
    '''
    unit = numpy.sqrt(base_hypotenuse ** 2 / (1 + aspect_ratio ** 2))
    side1 = unit
    side2 = aspect_ratio * unit
    direction_normalized = geometry.normalize_vector(direction)
    center_of_base = apex + direction_normalized * height
    
    #assuming that the projection heads always to z axis
    base_vector1 = direction_normalized
    base_vector2 = numpy.array([1.0, 0.0, 0.0])
    base_vector3 = geometry.normalize_vector(numpy.cross(base_vector1, base_vector2))
    
    #angles of rotation
    angle2 = numpy.arctan(0.5 * side1 / height)
    angle3 = numpy.arctan(0.5 * side2 / height)    
    
    pyramid_base_vertices = []
    for corner in corners:
        pyramid_base_vertices.append(center_of_base + corner[0] * base_vector2 * 0.5 * side1 + corner[1] * base_vector3 * 0.5 * side2)
        
    if half_angle_rays:
        for corner in corners:
            pyramid_base_vertices.append(center_of_base + corner[0] * base_vector2 * 0.7 * side1 + corner[1] * base_vector3 * 0.7 * side2)
            
        for corner in corners:
            pyramid_base_vertices.append(center_of_base + corner[0] * base_vector2 * 0.3 * side1 + corner[1] * base_vector3 * 0.3 * side2)
            
        for corner in corners:
            pyramid_base_vertices.append(center_of_base + corner[0] * base_vector2 * 0.1 * side1 + corner[1] * base_vector3 * 0.1 * side2)
        
    pyramid_base_vertices = numpy.array(pyramid_base_vertices) - apex
    return pyramid_base_vertices
    
if __name__ == "__main__": 
#    apex = numpy.array([0,1, 0])
#    direction = numpy.array([-1, -1, 0])
#    height = 1.0
#    base_hypotenuse = 1.414
#    aspect_ratio = 1.0
#    print pyramid_projection(apex, direction, height, base_hypotenuse, aspect_ratio)
    depth1 = -3.0
    depth2 = -10.0
    mirrors = numpy.array([
                           [[0.0, depth1, 10.0], [10.0, depth1, -10.0], [-10.0, depth1, -10.0]], 
                           [[0.0, depth2, 10.0], [10.0, depth2, -10.0], [-10.0, depth2, -10.0]]
                           ])
    initial_ray_start_point = numpy.array([0.0, 1.0, 0.0])
    initial_ray_direction = numpy.array([0.0, -1.0, 0.0])
    print multiple_reflections(mirrors,  initial_ray_start_point, initial_ray_direction, 1)
    
    #Config 1:
#    ray_start_point = numpy.array([0.0, 100.0, 50.0])
#    ray_direction = numpy.array([100.0, -100.0, 0.0]) #check if ray goes to opposite direction how the algorithm work
#    polygon = numpy.array([[0.0, 100.0, 0.0], 
#                                                   [0.0, 100.0, 100.0], 
#                                                   [1000.0, 100.0, 100.0], 
#                                                   [1000.0, 100.0, 0.0], 
#                                                  ] )
                                                  
    #Config 2:
#    ray_start_point = numpy.array([2.0, 1.0, 0.5])
#    ray_direction = numpy.array([1.0, -1.0, 0.0]) #check if ray goes to opposite direction how the algorithm work
#    polygon = numpy.array([[0.0, 0.0, 0.0], 
#                                                   [0.0, 0.0, 1.0], 
#                                                   [10.0, 0.0, 1.0], 
#                                                   [10.0, 0.0, 0.0], 
#                                                  ] )
#
#    print reflection(ray_start_point,  ray_direction, polygon), ray_start_point,  ray_direction
