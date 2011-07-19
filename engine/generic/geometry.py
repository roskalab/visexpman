import numpy
import unittest
import utils


if __name__ == "__main__":
    preceision = 3
else:
    try:
        import visexpman.users.zoltan.configurations
        preceision = visexpman.users.zoltan.configurations.GEOMETRY_PRECISION
    except:
        preceision = 3

def angle_between_vectors(v1, v2):
        '''
        '''
        return numpy.arccos(numpy.dot(v1, v2))
        
def distance_between_points(p1, p2):
    return numpy.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2)

def vector_length(vector):
    return numpy.sqrt(vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2)
    
def normalize_vector(vector):
    return vector / vector_length(vector)
      
def plane_normal_vector(polygon):    
    x1 = polygon[0, 0]
    y1 = polygon[0, 1]
    z1 = polygon[0, 2]
    x2 = polygon[1, 0]
    y2 = polygon[1, 1]
    z2 = polygon[1, 2]
    x3 = polygon[2, 0]
    y3 = polygon[2, 1]
    z3 = polygon[2, 2]
    
    #normal vector of plane:
    plane_normal_x = numpy.linalg.det(numpy.array([
                                                   [1.0, y1, z1], 
                                                   [1.0, y2, z2], 
                                                   [1.0, y3, z3], 
                                                   ]))
                                                   
    plane_normal_y = numpy.linalg.det(numpy.array([
                                                   [x1, 1.0, z1], 
                                                   [x2, 1.0, z2], 
                                                   [x3, 1.0, z3], 
                                                   ]))
                                                   
    plane_normal_z = numpy.linalg.det(numpy.array([
                                                   [x1, y1, 1.0], 
                                                   [x2, y2, 1.0], 
                                                   [x3, y3, 1.0], 
                                                   ]))
                                                   
    plane_normal = numpy.array([plane_normal_x, plane_normal_y, plane_normal_z])
    return plane_normal
    
def ray_polygon_intersection(ray_starting_point,  ray_direction,  polygon):
    intersection_exists, intersection = plane_ray_intersection(ray_starting_point,  ray_direction, polygon)
    if intersection_exists:
        if is_point_in_polygon(intersection, polygon):
            return (True, intersection)
        else:
            return (False, None)
    else:
        return (False, None)
    
def is_point_in_polygon(point, polygon):
#    print point, polygon
    '''
    The number of intersections between a ray starting from the point and the sides of the polygon are checked.
    If this number is odd, the point must be inside the polygon, otherwise outside.
    
    The direction of the ray is the direction of a line from the point to the first vertex of the polygon.
    
    Assuming that the point and the polygon are in the same plane
    '''
    debug = False
    if debug: print '---------------------------'
    testing_ray_starting_point = point
    testing_ray_direction = polygon[0] - point
    testing_ray_directions = [testing_ray_direction, -testing_ray_direction]
    
    #Checking intersection between test rays and polygon sides. Two test rays are generated which point
    #to the opposite direction. If the point is inside the polygon, then both rays have an odd number of intersections
    #with any of the sides of  the polygon
    number_of_vertices = polygon.shape[0]
    n_intersections = []
    for testing_ray_direction in testing_ray_directions:
        intersections = []
        for i in range(number_of_vertices):
            index = i + 1
            if index >= number_of_vertices:
                index = 0
            intersection_exists, intersection = line_segment_ray_intersection(polygon[i], polygon[index], testing_ray_starting_point, testing_ray_direction)
            #intersection is appended if that value is not yet in the list. This is necessary because ray points to one of the vertexes and that vertex is 
            #the endpoint of two line segments and therefore that would result a redundant intersection
            
            if debug: print polygon[i], polygon[index], testing_ray_direction, testing_ray_starting_point, intersection
            if debug: print '\n'
            if len(intersections) == 0 and intersection_exists:
                intersections.append(intersection)
            elif len(intersections) != 0 and intersection_exists:
                is_in_list = False
                for intersection_ in intersections:
                    test_array = abs(intersection_ - intersection)
#TODO:precision from parameter
                    if test_array[0] <= 1.0e-5 and test_array[1] <= 1.0e-5 and test_array[2] <= 1.0e-5:
                        is_in_list = True
                if not is_in_list:
                    intersections.append(intersection)

        n_intersections.append(len(intersections))
        
    if n_intersections[0] % 2 == 1 and n_intersections[1] % 2 == 1:
        return True
    else:
        return False

def plane_ray_intersection(line_start_point,  line_direction, polygon):
    intersection_exists, intersection = plane_line_intersection(line_start_point,  line_direction, polygon)
    if intersection_exists:
        #check if line start point - intersection direrction is the same that is defined by line_direction
        for item in ((intersection - line_start_point) / line_direction):
            if item < 0.0:
                intersection_exists = False
                intersection = None
    return intersection_exists, intersection

def plane_line_intersection(line_start_point,  line_direction, polygon):
    
    x1 = polygon[0, 0]
    y1 = polygon[0, 1]
    z1 = polygon[0, 2]
    x2 = polygon[1, 0]
    y2 = polygon[1, 1]
    z2 = polygon[1, 2]
    x3 = polygon[2, 0]
    y3 = polygon[2, 1]
    z3 = polygon[2, 2]
    
    plane_normal = plane_normal_vector(polygon)
    
    line_parameter_numerator = numpy.array([
                                            [1.0, 1.0, 1.0, 1.0], 
                                            [x1, x2, x3, line_start_point[0]], 
                                            [y1, y2, y3, line_start_point[1]], 
                                            [z1, z2, z3, line_start_point[2]], 
                                            ])
                                            
    line_parameter_denominator = numpy.array([
                                            [1.0, 1.0, 1.0, 0.0], 
                                            [x1, x2, x3, line_direction[0]], 
                                            [y1, y2, y3, line_direction[1]], 
                                            [z1, z2, z3, line_direction[2]], 
                                            ])
    line_parameter = numpy.linalg.det(line_parameter_numerator) / numpy.linalg.det(line_parameter_denominator)
    #intersection of line and plane
    intersection = numpy.array([
                                line_start_point[0] - line_direction[0] * line_parameter, 
                                line_start_point[1] - line_direction[1] * line_parameter, 
                                line_start_point[2] - line_direction[2] * line_parameter, 
                                ])
                      
    #round to preceision - does not work
#    intersection = numpy.round(intersection, preceision)
    #check wether the intersection exists
    intersection_exists = True
    for item in intersection:
        if numpy.isnan(item) or numpy.isinf(item):
            intersection_exists = False
            break
    if not intersection_exists:
        intersection = None
    return intersection_exists, intersection

def line_segment_ray_intersection(line_point1, line_point2, ray_point, ray_direction):
    line_point = line_point1
    line_direction = line_point1 - line_point2
    intersection_exists, intersection = line_intersection(line_point, line_direction, ray_point, ray_direction)
    if intersection_exists:
        ray_range = []
        #determine ranges for checking if intersection of line is on the ray and line segment.
        #range is set to -inf if ray_direction is less than 0, otherwise inf
        for component in ray_direction:
            if component > 0:
                ray_range.append(float('inf'))
            else:
                ray_range.append(float('-inf'))

        if utils.in_range(intersection[0], ray_point[0], ray_range[0], preceision = preceision) and\
        utils.in_range(intersection[1], ray_point[1], ray_range[1], preceision = preceision) and\
        utils.in_range(intersection[2], ray_point[2], ray_range[2], preceision = preceision) and\
        utils.in_range(intersection[0], line_point1[0], line_point2[0], preceision = preceision) and\
        utils.in_range(intersection[1], line_point1[1], line_point2[1], preceision = preceision) and\
        utils.in_range(intersection[2], line_point1[2], line_point2[2], preceision = preceision):
            return intersection_exists, intersection
        else:
            return False, None
        
    else:
        return False, None

def line_segment_intersection(line1_point1, line1_point2, line2_point1, line2_point2):
    '''
    line range: 2x3 numpy array, each row is the min,max pair on one axis
    '''
    line1_point = line1_point1
    line1_direction = line1_point1 - line1_point2
    line2_point = line2_point1
    line2_direction = line2_point1 - line2_point2
    intersection_exists, intersection = line_intersection(line1_point, line1_direction, line2_point, line2_direction)
    if intersection_exists:
        if utils.in_range(intersection[0], line1_point1[0], line1_point2[0]) and\
        utils.in_range(intersection[1], line1_point1[1], line1_point2[1]) and\
        utils.in_range(intersection[2], line1_point1[2], line1_point2[2]):
            return intersection_exists, intersection
        else:
            return False, None
    else:
        return False, None
    
def line_intersection(line1_point, line1_direction, line2_point, line2_direction):
    '''
    1. check if lines are parallel
    2. find closest points
    The parameter values of each line are calculated as follows:
    M1 = a - x , u, u x v (M1 is a 3x3 matrix)
    s = det M1 / |u x v| **2
    
    M2 = a - x , v, u x v (M2 is a 3x3 matrix)
    t = det M2 / |u x v| **2
    
    Where:
    a: line1_point
    v: line1_direction
    x: line2_point
    u: line2_direction
    s: parameter of line1
    t: parameter of line2
    
    Substituting s and t into the line equations, the closest points are given
    
    3. Check if distance closest points is below tolerance
    4. If exists, the intersection is the halfway point between closest points
    '''
    debug = False
    intersection = None
    intersection_exists = False
    tolerance = 10.0 ** -preceision
    if are_vectors_parallel(line1_direction, line2_direction):
        intersection_exists = False
    else:
        vector_orthogonal_to_both_lines = numpy.cross(line2_direction, line1_direction)
        square_of_lenght_of_vector_orthogonal_to_both_lines = (vector_orthogonal_to_both_lines ** 2).sum()
        #calculate parameter of lines where the closest point is
        par1 = numpy.matrix([line1_point - line2_point, line2_direction,vector_orthogonal_to_both_lines])
        par1 = numpy.linalg.det(par1) / square_of_lenght_of_vector_orthogonal_to_both_lines
        par2 = numpy.matrix([line1_point - line2_point, line1_direction,vector_orthogonal_to_both_lines])
        par2 = numpy.linalg.det(par2) / square_of_lenght_of_vector_orthogonal_to_both_lines
        line1_closest_point = line1_point + line1_direction * par1
        line2_closest_point = line2_point + line2_direction * par2
        distance_between_lines = numpy.sqrt(((line1_closest_point - line2_closest_point) ** 2).sum())
        if distance_between_lines < tolerance:
            intersection = line1_closest_point + (line2_closest_point - line1_closest_point)/2
            intersection_exists = True

        if debug:
            print line1_closest_point
            print line2_closest_point
            print distance_between_lines
            print intersection
        
    return intersection_exists, intersection
        
    
def line_intersection_old(line1_point, line1_direction, line2_point, line2_direction):
    '''
    1. check if lines are parallel
    2. calculate s and t parameters
    3. check if substitution results equal z coordinates
    4. calculate x,y and z coordinates of intersection
    '''
    debug = False
    intersection = None
    intersection_exists = False
    tolerance = 10.0 ** -(preceision-1)
    tolerance = 10.0 ** -5
    
    #==calculate distance between lines==
    # distance = (a-c) dot (bxd) / |bxd| where a and c are arbitrary points of the lines, b and d are the direction vectors
    dir_cross = numpy.cross(line1_direction, line2_direction)
    distance_between_lines = numpy.dot((line1_point - line2_point), dir_cross) / numpy.sqrt((dir_cross ** 2).sum())
    print distance_between_lines
    
    if are_vectors_parallel(line1_direction, line2_direction):
        intersection_exists = False
    else:
        A = numpy.matrix([[line1_direction[0], -line2_direction[0]], [line1_direction[1], -line2_direction[1]]])
        try:
            A_inv = numpy.linalg.inv(A)
            b = numpy.matrix([line2_point[0] - line1_point[0], line2_point[1] - line1_point[1]])
            result = A_inv * b.transpose()
            result = numpy.asarray(result).reshape(-1)
            z1 = line1_point[2] + line1_direction[2] * result[0]
            z2 = line2_point[2] + line2_direction[2] * result[1]
            if debug: print 'z: %f,%f'%(z1, z2)
            if abs(z1 - z2) > tolerance:
                intersection_exists = False
            else:
                intersection_exists = True        
                x = line1_point[0] + line1_direction[0] * result[0]
                y = line1_point[1] + line1_direction[1] * result[0]
                intersection = numpy.array([x, y, z1])
        except numpy.linalg.LinAlgError:
            #When parametric equation cannot be solved for x and y, try to solve it for x and z
            A = numpy.matrix([[line1_direction[0], -line2_direction[0]], [line1_direction[2], -line2_direction[2]]])
            try:
                A_inv = numpy.linalg.inv(A)
                b = numpy.matrix([line2_point[0] - line1_point[0], line2_point[2] - line1_point[2]])
                result = A_inv * b.transpose()
                result = numpy.asarray(result).reshape(-1)
                y1 = line1_point[1] + line1_direction[1] * result[0]
                y2 = line2_point[1] + line2_direction[1] * result[1]
                if debug: print 'y: %f,%f'%(y1, y2)
                if abs(y1 - y2) > tolerance:
                    intersection_exists = False
                else:
                    intersection_exists = True        
                    x = line1_point[0] + line1_direction[0] * result[0]
                    z = line1_point[2] + line1_direction[2] * result[0]
                    intersection = numpy.array([x, y1, z])
            except:
                A = numpy.matrix([[line1_direction[1], -line2_direction[1]], [line1_direction[2], -line2_direction[2]]])
                try:
                    A_inv = numpy.linalg.inv(A)
                    b = numpy.matrix([line2_point[1] - line1_point[1], line2_point[2] - line1_point[2]])
                    result = A_inv * b.transpose()
                    result = numpy.asarray(result).reshape(-1)
                    x1 = line1_point[0] + line1_direction[0] * result[0]
                    x2 = line2_point[0] + line2_direction[0] * result[1]
                    if debug: print 'x: %f,%f'%(x1, x2)
                    if abs(x1 - x2) > tolerance:
                        intersection_exists = False
                    else:
                        intersection_exists = True        
                        y = line1_point[1] + line1_direction[1] * result[0]
                        z = line1_point[2] + line1_direction[2] * result[0]
                        intersection = numpy.array([x1, y, z])
                except:
                    intersection_exists = False
    if intersection != None:
        intersection = numpy.round(intersection, preceision)
        
#    if distance_between_lines < tolerance:
#        intersection_exists = True
    return intersection_exists, intersection
    
def are_vectors_parallel(v1, v2):
    vector_ratio = v1/v2
    
    vector_ratio_offset = numpy.inf
    for component in vector_ratio:
        if not numpy.isnan(component) and component < vector_ratio_offset:
            vector_ratio_offset = component
        
    vector_ratio_test = vector_ratio - vector_ratio_offset
    if vector_ratio_test.sum() == 0.0:
        is_parallel = True
    elif numpy.isnan(vector_ratio_test.sum()):
        nan_count = 0
        zero_count = 0
        for v in vector_ratio_test:
            if v == 0:
                zero_count = zero_count + 1
            elif numpy.isnan(v):
                nan_count = nan_count + 1
        if zero_count + nan_count == 3:
            is_parallel = True
        else:
            is_parallel = False
    else:
        is_parallel = False
    return is_parallel
    
def rotate_vector(vector, angle):
    '''
    angle: about x, y and z axis, in radian
    '''
    rotation_matrix_x = numpy.matrix([
                                      [1.0, 0.0, 0.0],
                                      [0.0, numpy.cos(angle[0]), -numpy.sin(angle[0])],
                                      [0.0, numpy.sin(angle[0]), numpy.cos(angle[0])],
                                      ])
    rotation_matrix_y = numpy.matrix([
                                       [numpy.cos(angle[1]), 0.0, numpy.sin(angle[1])],
                                      [0.0, 1.0, 0.0],
                                      [-numpy.sin(angle[1]), 0.0, numpy.cos(angle[1])],
                                      ])
                                      
    rotation_matrix_z = numpy.matrix([
                                       [numpy.cos(angle[2]), -numpy.sin(angle[2]), 0.0],
                                      [numpy.sin(angle[2]), numpy.cos(angle[2]), 0.0],
                                      [0.0, 0.0, 1.0],
                                      ])
                                      
    vector_matrix = numpy.matrix(vector)
    vector_matrix = vector_matrix.transpose()
    return numpy.squeeze(numpy.asarray((rotation_matrix_x * rotation_matrix_y * rotation_matrix_z * vector_matrix).transpose()))
    
class testGeometry(unittest.TestCase):
    
    test_data = [
                 {
                 'direction1': numpy.array([1.0, 1.0, 1.0]), 
                 'direction2': numpy.array([1.0, 1.0, 1.0]), 
                 'parallel?':True, 
                 }, 
                 {
                 'direction1': numpy.array([1.0, 1.0, 1.0]),
                 'direction2': numpy.array([-1.0, -1.0, -1.0]),
                 'parallel?':True, 
                 }, 
                 {
                 'direction1': numpy.array([1.0, 0.0, 1.0]),
                 'direction2': numpy.array([1.0, 0.0, -1.0]),
                 'parallel?':False, 
                 }, 
                 {
                 'direction1': numpy.array([0.0, 0.0, 1.0]),
                 'direction2': numpy.array([-1.0, 0.0, -1.0]),
                 'parallel?':False, 
                 }, 
                 {
                 'line1_point': numpy.array([0.0, 0.0, 0.0]), 
                 'line2_point': numpy.array([0.0, 0.0, 0.0]), 
                 'line1_direction': numpy.array([1.0, 0.0, 0.0]), 
                 'line2_direction': numpy.array([0.0, 1.0, 0.0]), 
                 'result' : (True,  numpy.array([0.0, 0.0, 0.0]))
                 }, 
                {
                 'line1_point': numpy.array([1.0, 1.0, 0.0]), 
                 'line2_point': numpy.array([0.0, 1.0, 0.0]), 
                 'line1_direction': numpy.array([1.0, 1.0, 0.0]), 
                 'line2_direction': numpy.array([0.0, 1.0, 0.0]), 
                 'result' : (True,  numpy.array([0.0, 0.0, 0.0]))
                 }, 
                 {
                 'line1_point': numpy.array([0.0, 1.0, 0.0]), 
                 'line2_point': numpy.array([1.0, 0.0, 0.0]), 
                 'line1_direction': numpy.array([1.0, 1.0, 0.0]), 
                 'line2_direction': numpy.array([0.0, 1.0, 0.0]), 
                 'result' : (True,  numpy.array([1.0, 2.0, 0.0]))
                 }, 
                 {
                 'line1_point': numpy.array([0.0, 0.0, 0.0]), 
                 'line2_point': numpy.array([0.0, 1.0, 0.0]), 
                 'line1_direction': numpy.array([1.0, 1.0, 0.0]), 
                 'line2_direction': numpy.array([1.0, 0.0, 0.0]), 
                 'result' : (True,  numpy.array([1.0, 1.0, 0.0]))
                 }, 
                {
                 'line1_point': numpy.array([0.0, 0.0, 1.0]), 
                 'line2_point': numpy.array([0.0, 1.0, 1.0]), 
                 'line1_direction': numpy.array([1.0, 1.0, 0.0]), 
                 'line2_direction': numpy.array([1.0, 0.0, 0.0]), 
                 'result' : (True,  numpy.array([1.0, 1.0, 1.0]))
                 }, 
                {
                 'line1_point': numpy.array([0.0, 4.0, 3.0]), 
                 'line2_point': numpy.array([0.0, 0.0, 3.0]), 
                 'line1_direction': numpy.array([5.0, -4.0, -3.0]), 
                 'line2_direction': numpy.array([5.0, 4.0, -3.0]), 
                 'result' : (True,  numpy.array([2.5, 2.0, 1.5]))
                 }, 
                 {
                 'line1_point': numpy.array([0.0, 4.0, 3.0]), 
                 'line2_point': numpy.array([0.0, 0.0, 3.0]), 
                 'line1_direction': numpy.array([5.0, -4.0, -3.0]), 
                 'line2_direction': numpy.array([5.0, 4.0, 3.0]), 
                 'result' : (False,  None)
                 }, 
                 {
                 'line1_point': numpy.array([0.0, 0.0, 0.0]), 
                 'line2_point': numpy.array([0.0, 0.0, 1.0]), 
                 'line1_direction': numpy.array([0.0, 0.0, -1.0]), 
                 'line2_direction': numpy.array([0.0, 0.0, 0.0]), 
                 'result' : (False,  None)
                 }, 
                 {
                 'line1_point1': numpy.array([0.0, 0.0, 0.0]), 
                 'line1_point2': numpy.array([1.0, 1.0, 0.0]), 
                 'line2_point1': numpy.array([1.0, 0.0, 0.0]), 
                 'line2_point2': numpy.array([0.0, 1.0, 0.0]), 
                 'result' : (True, numpy.array([0.5, 0.5, 0.0]))
                 }, 
                 {
                 'line1_point1': numpy.array([0.0, 0.0, 0.0]), 
                 'line1_point2': numpy.array([0.0, 1.0, 0.0]), 
                 'line2_point1': numpy.array([-0.5, 0.0, 0.0]), 
                 'line2_point2': numpy.array([0.5, 0.0, 0.0]), 
                 'result' : (True, numpy.array([0.0, 0.0, 0.0]))
                 }, 
                 {
                 'line1_point1': numpy.array([0.0, 0.0, 0.0]), 
                 'line1_point2': numpy.array([1.0, 0.0, 0.0]), 
                 'line2_point1': numpy.array([2.0, 0.0, 0.0]), 
                 'line2_point2': numpy.array([2.0, 1.0, 0.0]), 
                 'result' : (False, None)
                 }, 
                 {
                 'line1_point1': numpy.array([0.0, 0.0, 0.0]), 
                 'line1_point2': numpy.array([1.0, 0.0, 0.0]), 
                 'line2_point1': numpy.array([2.0, 0.0, 0.0]), 
                 'line2_point2': numpy.array([3.0, 0.0, 0.0]), 
                 'result' : (False, None)
                 },
                 #line segment ray intersection
                 {
                 'line_point1': numpy.array([0.0, 0.0, 0.0]), 
                 'line_point2': numpy.array([1.0, 0.0, 0.0]), 
                 'ray_point': numpy.array([0.5, 0.5, 0.0]), 
                 'ray_direction': numpy.array([0.0, -1.0, 0.0]), 
                 'result' : (True, numpy.array([0.5, 0.0, 0.0]))
                 },
                 {
                 'line_point1': numpy.array([0.0, 0.0, 0.0]), 
                 'line_point2': numpy.array([1.0, 0.0, 0.0]), 
                 'ray_point': numpy.array([0.5, 0.5, 0.0]), 
                 'ray_direction': numpy.array([0.0, 1.0, 0.0]), 
                 'result' : (False, None)
                 },
                 {
                 'line_point1': numpy.array([0.0, 1.0, 0.0]), 
                 'line_point2': numpy.array([1.0, 1.0, 0.0]), 
                 'ray_point': numpy.array([-1.0, 1.0, 0.0]), 
                 'ray_direction': numpy.array([1.0, -1.0, 0.0]), 
                 'result' : (False, None)
                 },
                 {
                 'line_point1': numpy.array([1.0, 0.0, 0.0]), 
                 'line_point2': numpy.array([1.0, 1.0, 0.0]), 
                 'ray_point': numpy.array([-1.0, 1.0, 0.0]), 
                 'ray_direction': numpy.array([1.0, -1.0, 0.0]), 
                 'result' : (False, None)
                 },
                 #plane-line intersection
                 {
                 'polygon': numpy.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]),
                 'line_start_point': numpy.array([0.5, 0.5, 1.0]),
                 'line_direction': numpy.array([0.0, 0.0, 1.0]),
                 'result' : (True, numpy.array([0.5, 0.5, 0.0]))
                 },
                 {
                 'polygon': numpy.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]), 
                 'line_start_point': numpy.array([1.0, 0.0, 1.0]), 
                 'line_direction': numpy.array([-0.5, 0.5, -1.0]),
                 'result' : (True, numpy.array([0.5, 0.5, 0.0]))
                 }, 
                 {
                 'polygon': numpy.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]), 
                 'line_start_point': numpy.array([1.0, 0.0, 1.0]), 
                 'line_direction': numpy.array([1.0, 0.0, 0.0]),
                 'result' : (False, None)
                 }, 
                 #plane-ray intersection
                 {
                 'polygon': numpy.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]), 
                 'line_start_point': numpy.array([0.5, 0.5, 1.0]), 
                 'line_direction': numpy.array([0.0, 0.0, -1.0]),
                 'result' : (True, numpy.array([0.5, 0.5, 0.0]))
                 }, 
                 {
                 'polygon': numpy.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]), 
                 'line_start_point': numpy.array([1.0, 0.0, 1.0]), 
                 'line_direction': numpy.array([-0.5, 0.5, -1.0]),
                 'result' : (True, numpy.array([0.5, 0.5, 0.0]))
                 }, 
                 {
                 'polygon': numpy.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]), 
                 'line_start_point': numpy.array([0.5, 0.5, -1.0]), 
                 'line_direction': numpy.array([0.0, 0.0, -1.0]),
                 'result' : (False, None)
                 }, 
                 #is point in polygon
                 {
                 'polygon': numpy.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]), 
                 'point': numpy.array([0.5, 0.5, 0.0]),                  
                 'result' : True
                 }, 
                 {
                 'polygon': numpy.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]), 
                 'point': numpy.array([-0.5, -0.5, 0.0]),                  
                 'result' : False
                 }, 
                 {
                 'polygon': numpy.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]), 
                 'point': numpy.array([-1.0, 1.0, 0.0]),                  
                 'result' : False
                 }, 
                 #ray polygon intersection
                 {
                 'polygon': numpy.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]), 
                 'ray_starting_point': numpy.array([0.5, 0.5, 1.0]),
                 'ray_direction': numpy.array([0.0, 0.0, -1.0]),
                 'result' : (True, numpy.array([0.5, 0.5, 0.0]))
                 }, 
                 {
                 'polygon': numpy.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]), 
                 'ray_starting_point': numpy.array([0.5, 0.5, 1.0]),
                 'ray_direction': numpy.array([0.0, 0.0, 1.0]),
                 'result' : (False, None)
                 }, 
                 {
                 'polygon': numpy.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]), 
                 'ray_starting_point': numpy.array([2.0, 2.0, 1.0]),
                 'ray_direction': numpy.array([0.0, 0.0, -1.0]),
                 'result' : (False, None)
                 }, 
                 ]
    
    
    def test_00_parallel(self):
        case = 0
        result = are_vectors_parallel( self.__class__.test_data[case]['direction1'],  self.__class__.test_data[case]['direction2'])
        self.assertEqual(result, self.__class__.test_data[case]['parallel?'])
        
    def test_01_parallel(self):
        case = 1
        result = are_vectors_parallel( self.__class__.test_data[case]['direction1'],  self.__class__.test_data[case]['direction2'])
        self.assertEqual(result, self.__class__.test_data[case]['parallel?'])

    def test_02_parallel(self):
        case = 2
        result = are_vectors_parallel( self.__class__.test_data[case]['direction1'],  self.__class__.test_data[case]['direction2'])
        self.assertEqual(result, self.__class__.test_data[case]['parallel?'])
        
    def test_03_parallel(self):
        case = 3
        result = are_vectors_parallel( self.__class__.test_data[case]['direction1'],  self.__class__.test_data[case]['direction2'])
        self.assertEqual(result, self.__class__.test_data[case]['parallel?'])
        
    def test_04_lines_intersecting(self):
        case = 4        
        result = line_intersection( self.__class__.test_data[case]['line1_point'],  self.__class__.test_data[case]['line1_direction'], self.__class__.test_data[case]['line2_point'],  self.__class__.test_data[case]['line2_direction'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.__class__.test_data[case]['result'][0], self.__class__.test_data[case]['result'][1][0], self.__class__.test_data[case]['result'][1][1], self.__class__.test_data[case]['result'][1][2]))

    def test_05_lines_intersecting(self):
        case = 5
        result = line_intersection( self.__class__.test_data[case]['line1_point'],  self.__class__.test_data[case]['line1_direction'], self.__class__.test_data[case]['line2_point'],  self.__class__.test_data[case]['line2_direction'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.__class__.test_data[case]['result'][0], self.__class__.test_data[case]['result'][1][0], self.__class__.test_data[case]['result'][1][1], self.__class__.test_data[case]['result'][1][2]))        
    
    def test_06_lines_intersecting(self):
        case = 6
        result = line_intersection( self.__class__.test_data[case]['line1_point'],  self.__class__.test_data[case]['line1_direction'], self.__class__.test_data[case]['line2_point'],  self.__class__.test_data[case]['line2_direction'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.__class__.test_data[case]['result'][0], self.__class__.test_data[case]['result'][1][0], self.__class__.test_data[case]['result'][1][1], self.__class__.test_data[case]['result'][1][2]))        
        
    def test_07_lines_intersecting(self):
        case = 7
        result = line_intersection( self.__class__.test_data[case]['line1_point'],  self.__class__.test_data[case]['line1_direction'], self.__class__.test_data[case]['line2_point'],  self.__class__.test_data[case]['line2_direction'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.__class__.test_data[case]['result'][0], self.__class__.test_data[case]['result'][1][0], self.__class__.test_data[case]['result'][1][1], self.__class__.test_data[case]['result'][1][2]))        
        
    def test_08_lines_intersecting(self):
        case = 8
        result = line_intersection( self.__class__.test_data[case]['line1_point'],  self.__class__.test_data[case]['line1_direction'], self.__class__.test_data[case]['line2_point'],  self.__class__.test_data[case]['line2_direction'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.__class__.test_data[case]['result'][0], self.__class__.test_data[case]['result'][1][0], self.__class__.test_data[case]['result'][1][1], self.__class__.test_data[case]['result'][1][2]))        

    def test_09_lines_intersecting(self):
        case = 9
        result = line_intersection( self.__class__.test_data[case]['line1_point'],  self.__class__.test_data[case]['line1_direction'], self.__class__.test_data[case]['line2_point'],  self.__class__.test_data[case]['line2_direction'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.__class__.test_data[case]['result'][0], self.__class__.test_data[case]['result'][1][0], self.__class__.test_data[case]['result'][1][1], self.__class__.test_data[case]['result'][1][2]))        

    def test_10_lines_not_intersecting(self):
        case = 10
        result = line_intersection( self.__class__.test_data[case]['line1_point'],  self.__class__.test_data[case]['line1_direction'], self.__class__.test_data[case]['line2_point'],  self.__class__.test_data[case]['line2_direction'])
        self.assertEqual(result, self.__class__.test_data[case]['result'])
        
    def test_11_lines_not_intersecting(self):
        case = 11
        result = line_intersection( self.__class__.test_data[case]['line1_point'],  self.__class__.test_data[case]['line1_direction'], self.__class__.test_data[case]['line2_point'],  self.__class__.test_data[case]['line2_direction'])
        self.assertEqual(result, self.__class__.test_data[case]['result'])
        
    def test_12_line_segments_intersecting(self):
        case = 12
        result = line_segment_intersection( self.__class__.test_data[case]['line1_point1'], self.__class__.test_data[case]['line1_point2'], self.__class__.test_data[case]['line2_point1'], self.__class__.test_data[case]['line2_point2'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.__class__.test_data[case]['result'][0], self.__class__.test_data[case]['result'][1][0], self.__class__.test_data[case]['result'][1][1], self.__class__.test_data[case]['result'][1][2]))        
        
    def test_13_line_segments_intersecting(self):
        case = 13
        result = line_segment_intersection( self.__class__.test_data[case]['line1_point1'], self.__class__.test_data[case]['line1_point2'], self.__class__.test_data[case]['line2_point1'], self.__class__.test_data[case]['line2_point2'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.__class__.test_data[case]['result'][0], self.__class__.test_data[case]['result'][1][0], self.__class__.test_data[case]['result'][1][1], self.__class__.test_data[case]['result'][1][2]))        

    def test_14_line_segments_not_intersecting(self):
        case = 14
        result = line_segment_intersection( self.__class__.test_data[case]['line1_point1'], self.__class__.test_data[case]['line1_point2'], self.__class__.test_data[case]['line2_point1'], self.__class__.test_data[case]['line2_point2'])
        self.assertEqual(result, self.__class__.test_data[case]['result'])
        
    def test_15_line_segments_not_intersecting(self):
        case = 15
        result = line_segment_intersection( self.__class__.test_data[case]['line1_point1'], self.__class__.test_data[case]['line1_point2'], self.__class__.test_data[case]['line2_point1'], self.__class__.test_data[case]['line2_point2'])
        self.assertEqual(result, self.__class__.test_data[case]['result'])
        
    def test_16_line_segment_ray_intersecting(self):
        case = 16
        result = line_segment_ray_intersection( self.__class__.test_data[case]['line_point1'], self.__class__.test_data[case]['line_point2'], self.__class__.test_data[case]['ray_point'], self.__class__.test_data[case]['ray_direction'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.__class__.test_data[case]['result'][0], self.__class__.test_data[case]['result'][1][0], self.__class__.test_data[case]['result'][1][1], self.__class__.test_data[case]['result'][1][2]))        

    def test_17_line_segment_ray_not_intersecting(self):
        case = 17
        result = line_segment_ray_intersection( self.__class__.test_data[case]['line_point1'], self.__class__.test_data[case]['line_point2'], self.__class__.test_data[case]['ray_point'], self.__class__.test_data[case]['ray_direction'])
        self.assertEqual(result, self.__class__.test_data[case]['result'])
        
    def test_18_line_segment_ray_not_intersecting(self):
        case = 18
        result = line_segment_ray_intersection( self.__class__.test_data[case]['line_point1'], self.__class__.test_data[case]['line_point2'], self.__class__.test_data[case]['ray_point'], self.__class__.test_data[case]['ray_direction'])
        self.assertEqual(result, self.__class__.test_data[case]['result'])
        
    def test_19_line_segment_ray_not_intersecting(self):
        case = 19
        result = line_segment_ray_intersection( self.__class__.test_data[case]['line_point1'], self.__class__.test_data[case]['line_point2'], self.__class__.test_data[case]['ray_point'], self.__class__.test_data[case]['ray_direction'])
        self.assertEqual(result, self.__class__.test_data[case]['result'])

    def test_20_line_plane_intersecting(self):
        case = 20
        result = plane_line_intersection( self.__class__.test_data[case]['line_start_point'], self.__class__.test_data[case]['line_direction'], self.__class__.test_data[case]['polygon'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.__class__.test_data[case]['result'][0], self.__class__.test_data[case]['result'][1][0], self.__class__.test_data[case]['result'][1][1], self.__class__.test_data[case]['result'][1][2]))        

    def test_21_line_plane_intersecting(self):
        case = 21
        result = plane_line_intersection( self.__class__.test_data[case]['line_start_point'], self.__class__.test_data[case]['line_direction'], self.__class__.test_data[case]['polygon'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.__class__.test_data[case]['result'][0], self.__class__.test_data[case]['result'][1][0], self.__class__.test_data[case]['result'][1][1], self.__class__.test_data[case]['result'][1][2]))        

    def test_22_line_plane_not_intersecting(self):
        case = 22
        result = plane_line_intersection( self.__class__.test_data[case]['line_start_point'], self.__class__.test_data[case]['line_direction'], self.__class__.test_data[case]['polygon'])
        self.assertEqual(result, self.__class__.test_data[case]['result'])
        
    def test_23_ray_plane_intersecting(self):
        case = 23
        result = plane_ray_intersection( self.__class__.test_data[case]['line_start_point'], self.__class__.test_data[case]['line_direction'], self.__class__.test_data[case]['polygon'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.__class__.test_data[case]['result'][0], self.__class__.test_data[case]['result'][1][0], self.__class__.test_data[case]['result'][1][1], self.__class__.test_data[case]['result'][1][2]))        

    def test_24_ray_plane_intersecting(self):
        case = 24
        result = plane_ray_intersection( self.__class__.test_data[case]['line_start_point'], self.__class__.test_data[case]['line_direction'], self.__class__.test_data[case]['polygon'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.__class__.test_data[case]['result'][0], self.__class__.test_data[case]['result'][1][0], self.__class__.test_data[case]['result'][1][1], self.__class__.test_data[case]['result'][1][2]))        

    def test_25_ray_plane_not_intersecting(self):
        case = 25
        result = plane_ray_intersection( self.__class__.test_data[case]['line_start_point'], self.__class__.test_data[case]['line_direction'], self.__class__.test_data[case]['polygon'])
        self.assertEqual(result, self.__class__.test_data[case]['result'])
        
    def test_26_point_is_in_polygon(self):
        case = 26
        result = is_point_in_polygon( self.__class__.test_data[case]['point'], self.__class__.test_data[case]['polygon'])
        self.assertEqual(result, self.__class__.test_data[case]['result'])
        
    def test_27_point_is_not_in_polygon(self):
        case = 27
        result = is_point_in_polygon( self.__class__.test_data[case]['point'], self.__class__.test_data[case]['polygon'])
        self.assertEqual(result, self.__class__.test_data[case]['result'])
        
    def test_28_point_is_not_in_polygon(self):
        case = 28
        result = is_point_in_polygon( self.__class__.test_data[case]['point'], self.__class__.test_data[case]['polygon'])
        self.assertEqual(result, self.__class__.test_data[case]['result'])
        
    def test_29_ray_polygon_intersecting(self):
        case = 29
        result = ray_polygon_intersection( self.__class__.test_data[case]['ray_starting_point'], self.__class__.test_data[case]['ray_direction'], self.__class__.test_data[case]['polygon'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.__class__.test_data[case]['result'][0], self.__class__.test_data[case]['result'][1][0], self.__class__.test_data[case]['result'][1][1], self.__class__.test_data[case]['result'][1][2]))        

    def test_30_ray_polygon_not_intersecting(self):
        case = 30
        result = ray_polygon_intersection( self.__class__.test_data[case]['ray_starting_point'], self.__class__.test_data[case]['ray_direction'], self.__class__.test_data[case]['polygon'])
        self.assertEqual(result, self.__class__.test_data[case]['result'])

    def test_31_ray_polygon_not_intersecting(self):
        case = 31
        result = ray_polygon_intersection( self.__class__.test_data[case]['ray_starting_point'], self.__class__.test_data[case]['ray_direction'], self.__class__.test_data[case]['polygon'])
        self.assertEqual(result, self.__class__.test_data[case]['result'])


if __name__ == "__main__":
#    unittest.main()
    test_data =  [               {
                 'line_point1': numpy.array([0.0, 1.0, 0.0]), 
                 'line_point2': numpy.array([1.0, 1.0, 0.0]), 
                 'ray_point': numpy.array([-1.0, 1.0, 0.0]), 
                 'ray_direction': numpy.array([1.0, -1.0, 0.0]), 
                 'result' : (False, None)
                 },
                 {
                 'line_point1': numpy.array([1.0, 0.0, 0.0]), 
                 'line_point2': numpy.array([1.0, 1.0, 0.0]), 
                 'ray_point': numpy.array([-1.0, 1.0, 0.0]), 
                 'ray_direction': numpy.array([1.0, -1.0, 0.0]), 
                 'result' : (False, None)
                 },           
                                  {
                 'polygon': numpy.array([[0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [10.0, 0.0, 1.0], [10.0, 0.0, 0.0]]), 
                 'point': numpy.array([3.0, 0.0, 0.5]),                  
                 'result' : False
                 }, 
                 #LINE
                 {
                 'line1_point': numpy.array([0.0, 1.0, 0.0]), 
                 'line1_direction': numpy.array([0.0, 1.0, 0.0]), 
                 'line2_point': numpy.array([0.0, 0.0, 0.0]), 
                 'line2_direction': numpy.array([1.0, 0.0, 0.0]), 
                 },
                 {
                 'line_point1': numpy.array([-73.86058148,  -96.41814145,   88.02361333]), 
                 'line_point2': numpy.array([-73.86058148,   96.41814145,   88.02361333]), 
                 'ray_point': numpy.array([  0. ,          82.39527733,   88.02361333]), 
                 'ray_direction': numpy.array([ -7.38605815e+01,    1.40228641e+01,    2.84217094e-14]), 
                 'result' : (False, None)
                 },       
                                  {
                 'polygon': numpy.array( [[-73.86058148,   96.41814145,   88.02361333], 
                                             [ 73.86058148 ,  96.41814145,   88.02361333], 
                                             [ 73.86058148 , -96.41814145,   88.02361333], 
                                             [-73.86058148,  -96.41814145,   88.02361333]]), 
                 'point': numpy.array([  0.   ,        82.39527733,   88.02361333]),                  
                 'result' : False
                 }, 
                 
                 

                 ]
    index = 3
    
#    print line_segment_ray_intersection(test_data[index]['line_point1'], test_data[index]['line_point2'], test_data[index]['ray_point'], test_data[index]['ray_direction'])
#    print is_point_in_polygon(test_data[index]['point'], test_data[index]['polygon'])
#    print line_intersection(test_data[index]['line1_point'], test_data[index]['line1_direction'], test_data[index]['line2_point'], test_data[index]['line2_direction'])
    vector = numpy.array([0, 0, 1])
    angle = numpy.array([45, 45, 0])
    print rotate_vector(vector, angle * numpy.pi/180.0)
