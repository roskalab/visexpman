import numpy
import visexpman.engine.generic.geometry as geometry

  
def reflection(ray_start_point,  ray_direction, polygon):
    '''
    polygon is at least three vertexes in x,y,z format
    '''
    
    intersection_exists, intersection  = geometry.ray_polygon_intersection(ray_start_point,  ray_direction, polygon)    
    if intersection_exists:
        light = ray_direction
        normalized_plane_normal =  geometry.normalize_vector(geometry.plane_normal_vector(polygon))
        reflected_ray_vector = 2 * numpy.dot(-light, normalized_plane_normal) * normalized_plane_normal + light
        return reflected_ray_vector, intersection
    else:
        return None, None

if __name__ == "__main__": 
    ray_start_point = numpy.array([200.0, 100.0, 50.0])
    ray_direction = numpy.array([100.0, -100.0, 0.0]) #check if ray goes to opposite direction how the algorithm work
    polygon = numpy.array([[0.0, 0.0, 0.0], 
                                                   [0.0, 0.0, 100.0], 
                                                   [1000.0, 0.0, 100.0], 
                                                   [1000.0, 0.0, 0.0], 
                                                  ] )
                                                      
    print reflection(ray_start_point,  ray_direction, polygon)
