import numpy
import visexpman.engine.generic.geometry as geometry

  
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
                if mirrors_hit == 2:
                    #two mirrors are hit when the ray is incident to a corner. This time the incident ray is reflected back
                    #if mirrors are not in the same plane, the relfection is calculated only one of the mirrors, the one that is earlier in the mirror list
                    pass
#                    reflected_ray_directions[-1] = -ray_direction
                else:
                    is_reflection = True
                    reflected_ray_start_points.append(reflected_ray_start_point)
                    reflected_ray_directions.append(reflected_ray_direction)

    if len(reflected_ray_directions) > 0:
        reflected_ray_start_points.append(reflected_ray_start_points[-1] + 30.0 * reflected_ray_directions[-1])
    else:
        reflected_ray_start_points.append(initial_ray_start_point + 30.0 * initial_ray_direction)
    rays = numpy.array(reflected_ray_start_points)
    return is_reflection, rays

if __name__ == "__main__": 
    
    #Config 1:
#    ray_start_point = numpy.array([0.0, 100.0, 50.0])
#    ray_direction = numpy.array([100.0, -100.0, 0.0]) #check if ray goes to opposite direction how the algorithm work
#    polygon = numpy.array([[0.0, 100.0, 0.0], 
#                                                   [0.0, 100.0, 100.0], 
#                                                   [1000.0, 100.0, 100.0], 
#                                                   [1000.0, 100.0, 0.0], 
#                                                  ] )
                                                  
    #Config 2:
    ray_start_point = numpy.array([2.0, 1.0, 0.5])
    ray_direction = numpy.array([1.0, -1.0, 0.0]) #check if ray goes to opposite direction how the algorithm work
    polygon = numpy.array([[0.0, 0.0, 0.0], 
                                                   [0.0, 0.0, 1.0], 
                                                   [10.0, 0.0, 1.0], 
                                                   [10.0, 0.0, 0.0], 
                                                  ] )

    print reflection(ray_start_point,  ray_direction, polygon), ray_start_point,  ray_direction
