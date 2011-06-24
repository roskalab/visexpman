import numpy
import unittest
import utils
#def point_inside_polygon(point, polygon):

def angle_between_vectors(v1, v2):
        '''
        '''
        return numpy.arccos(numpy.dot(v1, v2))
        
def vector_length(vector):
    return numpy.sqrt(vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2)
    
def normalize_vector(vector):
    return vector / vector_length(vector)
    
def plane_normal_vector(plane_vertex):    
    x1 = plane_vertex[0, 0]
    y1 = plane_vertex[0, 1]
    z1 = plane_vertex[0, 2]
    x2 = plane_vertex[1, 0]
    y2 = plane_vertex[1, 1]
    z2 = plane_vertex[1, 2]
    x3 = plane_vertex[2, 0]
    y3 = plane_vertex[2, 1]
    z3 = plane_vertex[2, 2]
    
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
    
def is_point_in_polygon(point, polygon):
    '''
    Ray casting algorithm:
    - intersection of line segment with a ray
    '''
    
# line: intersection with other line, line types: infinite, half line, section
# 
# plane:
    pass

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
                
        if utils.in_range(intersection[0], ray_point[0], ray_range[0]) and\
        utils.in_range(intersection[1], ray_point[1], ray_range[1]) and\
        utils.in_range(intersection[2], ray_point[2], ray_range[2]):            
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
    2. calculate s and t parameters
    3. check if substitution results equal z coordinates
    4. calculate x,y and z coordinates of intersection
    '''
    #check if lines are not parallel: direction vectors shall not be the multiple of each other
    intersection = None
    intersection_exists = False
    if are_vectors_parallel(line1_direction, line2_direction):
        intersection_exists = False
    else:
        A = numpy.matrix([[line1_direction[0], -line2_direction[0]], [line1_direction[1], -line2_direction[1]]])
        b = numpy.matrix([line2_point[0] - line1_point[0], line2_point[1] - line1_point[1]])
        result = numpy.linalg.inv(A) * b.transpose()
        result = numpy.asarray(result).reshape(-1)
        z1 = line1_point[2] + line1_direction[2] * result[0]
        z2 = line2_point[2] + line2_direction[2] * result[1]        
        if z1 != z2:
            intersection_exists = False
        else:
            intersection_exists = True        
            x = line1_point[0] + line1_direction[0] * result[0]
            y = line1_point[1] + line1_direction[1] * result[0]
            intersection = numpy.array([x, y, z1])            
    return intersection_exists, intersection
    
def are_vectors_parallel(v1, v2):
    vector_ratio = v1/v2
    vector_ratio_test = vector_ratio - vector_ratio[0]
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
                 }
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

if __name__ == "__main__":
    unittest.main()

    data = {#????
                 'line1_point': numpy.array([0.0, 1.0, 0.0]), 
                 'line2_point': numpy.array([1.0, 0.0, 0.0]), 
                 'line1_direction': numpy.array([1.0, 1.0, 0.0]), 
                 'line2_direction': numpy.array([0.0, 1.0, 0.0]), 
                 'result' : (True,  numpy.array([1.0, 2.0, 0.0]))              
                 }
                 
                 
#    data =  {
#                 'line1_point': numpy.array([0.0, 1.0, 0.0]), 
#                 'line2_point': numpy.array([1.0, 0.0, 0.0]), 
#                 'line1_direction': numpy.array([1.0, 1.0, 0.0]), 
#                 'line2_direction': numpy.array([0.0, 1.0, 0.0]), 
#                 'result' : (True,  numpy.array([1.0, 2.0, 0.0]))
#                 }

#    data = {
#                 'line1_point': numpy.array([0.0, 0.0, 0.0]), 
#                 'line2_point': numpy.array([0.0, 1.0, 0.0]), 
#                 'line1_direction': numpy.array([1.0, 1.0, 0.0]), 
#                 'line2_direction': numpy.array([1.0, -1.0, 0.0]), 
#                 'result' : (True,  numpy.array([0.5, 0.5, 0.0]))
#                 } 
#    
#    print line_intersection( data['line1_point'],  data['line1_direction'], data['line2_point'], data['line2_direction'])
