import numpy
import visexpman.engine.generic.geometry as geometry

class Optics(object):
    def __init__(self):
        pass
        
    def plane_ray_intersection(self, ray_start_point,  ray_direction, plane_vertex):
        
        x1 = plane_vertex[0, 0]
        y1 = plane_vertex[0, 1]
        z1 = plane_vertex[0, 2]
        x2 = plane_vertex[1, 0]
        y2 = plane_vertex[1, 1]
        z2 = plane_vertex[1, 2]
        x3 = plane_vertex[2, 0]
        y3 = plane_vertex[2, 1]
        z3 = plane_vertex[2, 2]
        
        self.plane_normal = geometry.plane_normal_vector(plane_vertex)
        
        line_parameter_numerator = numpy.array([
                                                [1.0, 1.0, 1.0, 1.0], 
                                                [x1, x2, x3, ray_start_point[0]], 
                                                [y1, y2, y3, ray_start_point[1]], 
                                                [z1, z2, z3, ray_start_point[2]], 
                                                ])
                                                
        line_parameter_denominator = numpy.array([
                                                [1.0, 1.0, 1.0, 0.0], 
                                                [x1, x2, x3, ray_direction[0]], 
                                                [y1, y2, y3, ray_direction[1]], 
                                                [z1, z2, z3, ray_direction[2]], 
                                                ])
        line_parameter = numpy.linalg.det(line_parameter_numerator) / numpy.linalg.det(line_parameter_denominator)
        #intersection of line and plane
        intersection = numpy.array([
                                    ray_start_point[0] - ray_direction[0] * line_parameter, 
                                    ray_start_point[1] - ray_direction[1] * line_parameter, 
                                    ray_start_point[2] - ray_direction[2] * line_parameter, 
                                    ])
                                    
        #check wether the intersection exists
        intersection_exists = True
        for item in intersection:
            if numpy.isnan(item) or numpy.isinf(item):
                intersection_exists = False
                break
        return intersection, intersection_exists
    
    def reflection(self, ray_start_point,  ray_direction, plane_vertex):
        '''
        plane_vertex is at least three vertexes in x,y,z format
        '''
        
        intersection, intersection_exists = self.plane_ray_intersection(ray_start_point,  ray_direction, plane_vertex)        
        if intersection_exists:
            light = ray_direction
            normalized_plane_normal =  geometry.normalize_vector(self.plane_normal)
            reflected_ray_vector = 2 * numpy.dot(-light,normalized_plane_normal) * normalized_plane_normal + light
            return reflected_ray_vector, intersection
        else:
            return None

if __name__ == "__main__": 
    ray_start_point = numpy.array([0.5, 1.0, 0.5])
    ray_direction = numpy.array([0.0, -0.5, 0.0]) #check if ray goes to opposite direction how the algorithm work
    plane_vertex = numpy.array([[0.0, 0.0, 0.0], 
                                                   [0.0, 0.0, 1.0], 
                                                   [1.0, 1.0, 1.0], 
                                                   [1.0, 1.0, 0.0], 
                                                  ] )
                                                  
    o = Optics()
    print o.reflection(ray_start_point,  ray_direction, plane_vertex)
