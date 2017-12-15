from __future__ import generators
import numpy
import unittest
import utils
from PIL import Image
from visexpman.engine.generic.utils import nan2value
from scipy.ndimage.interpolation import shift, rotate
from visexpman.engine.generic.utils import nd, rc, cr

## {{{ http://code.activestate.com/recipes/117225/ (r2)
# convex hull (Graham scan by x-coordinate) and diameter of a set of points
# David Eppstein, UC Irvine, 7 Mar 2002

precision = 10

def get_closest(rcref,rcothers):
    distances = [numpy.abs(rcref['col']-c['col'])+numpy.abs(rcref['row']-c['row']) for c in rcothers]
    return numpy.argmin(distances)

def orientation(p,q,r):
    '''Return positive if p-q-r are clockwise, neg if ccw, zero if colinear.'''
    return (q[1]-p[1])*(r[0]-p[0]) - (q[0]-p[0])*(r[1]-p[1])

def hulls(Points):
    '''Graham scan to find upper and lower convex hulls of a set of 2d points.'''
    U = []
    L = []
    Points.sort()
    for p in Points:
        while len(U) > 1 and orientation(U[-2],U[-1],p) <= 0: U.pop()
        while len(L) > 1 and orientation(L[-2],L[-1],p) >= 0: L.pop()
        U.append(p)
        L.append(p)
    return U,L

def rotatingCalipers(Points):
    '''Given a list of 2d points, finds all ways of sandwiching the points
between two parallel lines that touch one point each, and yields the sequence
of pairs of points touched by each pair of lines.'''
    U,L = hulls(Points)
    i = 0
    j = len(L) - 1
    while i < len(U) - 1 or j > 0:
        yield U[i],L[j]
        
        # if all the way through one side of hull, advance the other side
        if i == len(U) - 1: j -= 1
        elif j == 0: i += 1
        
        # still points left on both lists, compare slopes of next hull edges
        # being careful to avoid divide-by-zero in slope calculation
        elif (U[i+1][1]-U[i][1])*(L[j][0]-L[j-1][0]) > \
                (L[j][1]-L[j-1][1])*(U[i+1][0]-U[i][0]):
            i += 1
        else: j -= 1

def diameter(Points):
    '''Given a list of 2d points, returns the pair that's farthest apart.'''
    diam,pair = max([((p[0]-q[0])**2 + (p[1]-q[1])**2, (p,q))
                     for p,q in rotatingCalipers(Points)])
    return pair
## end of http://code.activestate.com/recipes/117225/ }}}


def Haffine_from_points(fp,tp):
    """ find H, affine transformation, such that 
        tp is affine transf of fp. From Solem'blog"""
        #could not make it work yet
    fp=numpy.array(fp)
    tp=numpy.array(tp)
    if fp.shape != tp.shape:
        raise RuntimeError, 'number of points do not match'
    if fp.shape[0]!=2 and fp.shape[1]==2:
        fp = fp.T
    if fp.shape[0]!=2:
        raise RuntimeError,'points must be given as a 2,n array'
    if tp.shape[0]!=2 and tp.shape[1]==2:
        tp = tp.T
    if tp.shape[0]!=2:
        raise RuntimeError,'points must be given as a 2,n array'
    fp = numpy.r_[fp,numpy.ones((1,fp.shape[1],))]
    tp = numpy.r_[tp,numpy.ones((1,tp.shape[1],))]
    #condition points
    #-from points-
    m = numpy.mean(fp[:2], axis=1)
    maxstd = numpy.max(numpy.std(fp[:2], axis=1))+1e-9
    C1 = numpy.diag([1/maxstd, 1/maxstd, 1]) 
    C1[0][2] = -m[0]/maxstd
    C1[1][2] = -m[1]/maxstd
    fp_cond = numpy.dot(C1,fp)

    #-to points-
    m = numpy.mean(tp[:2], axis=1)
    C2 = C1.copy() #must use same scaling for both point sets
    C2[0][2] = -m[0]/maxstd
    C2[1][2] = -m[1]/maxstd
    tp_cond = numpy.dot(C2,tp)

    #conditioned points have mean zero, so translation is zero
    A = numpy.concatenate((fp_cond[:2],tp_cond[:2]), axis=0)
    U,S,V = numpy.linalg.svd(A.T)

    #create B and C matrices as Hartley-Zisserman (2:nd ed) p 130.
    tmp = V[:2].T
    B = tmp[:2]
    C = tmp[2:4]

    tmp2 = numpy.concatenate((numpy.dot(C,numpy.linalg.pinv(B)),numpy.zeros((2,1))), axis=1) 
    H = numpy.vstack((tmp2,[0,0,1]))

    #decondition
    H = numpy.dot(numpy.linalg.inv(C2),numpy.dot(H,C1))

    return H / H[2][2]
    
def procrustes(X, Y, scaling=True, reflection='best'):
    """
    Procrustes analysis determines a linear transformation (translation,
    reflection, orthogonal rotation and scaling) of the points in Y to best
    conform them to the points in matrix X, using the sum of squared errors
    as the goodness of fit criterion.

        d, Z, [tform] = procrustes(X, Y)

    Inputs:
    ------------
    X, Y    
        matrices of target and input coordinates. they must have equal
        numbers of  points (rows), but Y may have fewer dimensions
        (columns) than X.

    scaling 
        if False, the scaling component of the transformation is forced
        to 1

    reflection
        if 'best' (default), the transformation solution may or may not
        include a reflection component, depending on which fits the data
        best. setting reflection to True or False forces a solution with
        reflection or no reflection respectively.

    Outputs
    ------------
    d       
        the residual sum of squared errors, normalized according to a
        measure of the scale of X, ((X - X.mean(0))**2).sum()

    Z
        the matrix of transformed Y-values

    tform   
        a dict specifying the rotation, translation and scaling that
        maps X --> Y

    """
    np = numpy
    n,m = X.shape
    ny,my = Y.shape

    muX = X.mean(0)
    muY = Y.mean(0)

    X0 = X - muX
    Y0 = Y - muY

    ssX = (X0**2.).sum()
    ssY = (Y0**2.).sum()

    # centred Frobenius norm
    normX = np.sqrt(ssX)
    normY = np.sqrt(ssY)

    # scale to equal (unit) norm
    X0 /= normX
    Y0 /= normY

    if my < m:
        Y0 = np.concatenate((Y0, np.zeros(n, m-my)),0)

    # optimum rotation matrix of Y
    A = np.dot(X0.T, Y0)
    U,s,Vt = np.linalg.svd(A,full_matrices=False)
    V = Vt.T
    T = np.dot(V, U.T)

    if reflection is not 'best':

        # does the current solution use a reflection?
        have_reflection = np.linalg.det(T) < 0

        # if that's not what was specified, force another reflection
        if reflection != have_reflection:
            V[:,-1] *= -1
            s[-1] *= -1
            T = np.dot(V, U.T)

    traceTA = s.sum()

    if scaling:

        # optimum scaling of Y
        b = traceTA * normX / normY

        # standarised distance between X and b*Y*T + c
        d = 1 - traceTA**2

        # transformed coords
        Z = normX*traceTA*np.dot(Y0, T) + muX

    else:
        b = 1
        d = 1 + ssY/ssX - 2 * traceTA * normY / normX
        Z = normY*np.dot(Y0, T) + muX

    # transformation matrix
    if my < m:
        T = T[:my,:]
    c = muX - b*np.dot(muY, T)

    tform = {'rotation':T, 'scale':b, 'translation':c}

    return d, Z, tform

def divide_vectors(v1, v2):
    if v2[0] != 0.0 and v2[1] != 0.0 and v2[2] != 0.0:
        return v1/v2
    else:
        v_div = numpy.zeros(3)
        for i in range(3):
            if v2[i] !=0.0:
                v_div[i] = v1[i] / v2[i]
            else:
                v_div[i] = numpy.inf
        return v_div

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
        #check if line start point - intersection direction is the same that is defined by line_direction
        for item in (divide_vectors((intersection - line_start_point) ,  line_direction)):
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
                      
    #round to precision - does not work
#    intersection = numpy.round(intersection, precision)
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

        if utils.in_range(intersection[0], ray_point[0], ray_range[0], precision = precision) and\
        utils.in_range(intersection[1], ray_point[1], ray_range[1], precision = precision) and\
        utils.in_range(intersection[2], ray_point[2], ray_range[2], precision = precision) and\
        utils.in_range(intersection[0], line_point1[0], line_point2[0], precision = precision) and\
        utils.in_range(intersection[1], line_point1[1], line_point2[1], precision = precision) and\
        utils.in_range(intersection[2], line_point1[2], line_point2[2], precision = precision):
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
    tolerance = 10.0 ** -precision
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
    tolerance = 10.0 ** -(precision-1)
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
        intersection = numpy.round(intersection, precision)
        
#    if distance_between_lines < tolerance:
#        intersection_exists = True
    return intersection_exists, intersection
    
def are_vectors_parallel(v1, v2):
    vector_ratio = divide_vectors(v1, v2)    
    
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
    
def rotate_point(point,angle,origin):
    if origin.dtype.names is None:
        r = numpy.sqrt((point[0]-origin[0])**2+(point[1]-origin[1])**2)
        phi = numpy.arctan2(point[1],point[0])
    else:
        r = numpy.sqrt((point['col']-origin['col'])**2+(point['row']-origin['row'])**2)
        phi = numpy.arctan2(point['row'],point['col'])
    phi += numpy.radians(angle)
    return point_coordinates(r, phi, origin)
    
    
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

def rotate_around_center(inarray, angle, center=None, reshape=False):
    '''Extends rotate function of scipy with user definable center. Uses larger image with NaN values
    to prevent data loss. NaNs are converted to a mask at the end'''
    if angle > numpy.pi*2:
        print('Warning:angle is greater than 2*Pi, angle should be supplied as radians')
    if hasattr(inarray, 'size') and inarray.size>2:
        origin = numpy.array(inarray.shape)/2
        if center is not None:
            i_dbg=inarray.copy()
            cshift = origin-nd(center)
            if numpy.any(cshift!=0):
                bord = numpy.ceil(numpy.abs(cshift))
                ext_im = numpy.nan*numpy.ones(inarray.shape+bord*2) #larger image in all directions, shift will not loose data and center remains
                ext_im[bord[0]:ext_im.shape[0]-bord[0], bord[1]:ext_im.shape[1]-bord[1]] = inarray
                inarray = shift(ext_im,  cshift,  cval=numpy.nan, order=0)
        rot = rotate(inarray, numpy.degrees(angle), cval=numpy.nan,  order=1, reshape=reshape) # if reshape=True this rotation can enlarge the image, we do not crop back this enlargement, only the center displacement!
        if center is not None and numpy.any(cshift!=0): # shift back to original center
            rot = shift(rot, -cshift, cval=numpy.nan, order=0)[bord[0]:rot.shape[0]-bord[0], bord[1]:rot.shape[1]-bord[1]]
        rot = numpy.ma.array(rot, mask=numpy.isnan(rot))
        return rot
    else: # single point
    # if using with point in left handed coordinate system (numpy), positive angles rotate in clockwise direction
        apoint = numpy.array(inarray).astype(numpy.float64)
        if center is not None:
            apoint -= center # move center to origo
        ca = numpy.cos(angle)
        sa = numpy.sin(angle)
        rotated = numpy.empty(apoint.shape, apoint.dtype) # keeps same type as input
        rotated[0] = numpy.around(apoint[0]*ca - apoint[1]*sa, decimals = 15) #around needed for the case when angle = 45 degrees: sin and cos will not be the same number
        rotated[1] = numpy.around(apoint[0]*sa + apoint[1]*ca, decimals=15)
        if center is not None:
            rotated += center
        rotated = rotated.astype(apoint.dtype)
        if not hasattr(inarray, 'shape'): # input was list
            rotated = rotated.tolist()
        return rotated
                             
def rotate_around_center_pil(data,  angle, center=None,  **kwargs):
    '''Rotates a point around a center. Coordinate 0 denotes columns, coordinate 1
    denotes rows (Cartesian coordinate system). Column index grows to the right, row index grows upwards.
    Positive angle rotates counter-clockwise'''
    if hasattr(data, 'size') and hasattr(data, 'shape') and data.size >2: #numpy image
        return_masked = kwargs.get('return_masked', True)
        if return_masked:
            mask = Image.fromarray(0*data+1)
        data = Image.fromarray(data)
        if center is not None:
            tr=utils.rc_add(utils.rc_x_const(utils.cr(data.size), 0.5), utils.rc_x_const(center, -1))
            data = data.transform(data.size, Image.AFFINE, (1, 0, tr['col'], 0, 1, tr['row']), Image.BICUBIC)
            if return_masked:
                mask = mask.transform(mask.size, Image.AFFINE, (1, 0, tr['col'], 0, 1, tr['row']))
        rot = data.rotate(numpy.degrees(angle), Image.BICUBIC)
        if return_masked:
            mask_rot = mask.rotate(numpy.degrees(angle))
        if center is not None:
            rot = rot.transform(data.size, Image.AFFINE, (1, 0, -tr['col'], 0, 1, -tr['row']), Image.BICUBIC)
            if return_masked:
                mask_rot = mask_rot.transform(data.size, Image.AFFINE, (1, 0, -tr['col'], 0, 1, -tr['row']))
        rotated = numpy.array(rot)
        if return_masked:
            rotated = numpy.ma.array(rotated, mask=1-numpy.array(mask_rot))
    else: # single point
        apoint = numpy.array(data).astype(numpy.float64)
        if center is not None:
            apoint -= center # move center to origo
        ca = numpy.cos(angle)
        sa = numpy.sin(angle)
        rotated = numpy.empty(apoint.shape, apoint.dtype) # keeps same type as input
        rotated[0] = numpy.around(apoint[0]*ca - apoint[1]*sa, decimals = 15) #around needed for the case when angle = 45 degrees: sin and cos will not be the same number
        rotated[1] = numpy.around(apoint[0]*sa + apoint[1]*ca, decimals=15)
        if center is not None:
            rotated += center
        rotated = rotated.astype(apoint.dtype)
        if not hasattr(data, 'shape'): # input was list
            rotated = rotated.tolist()
    return rotated

def estimate_rotation(points1, points2):
    return numpy.arctan((points2[:, 0]*points1[:, 1]-points2[:, 1]*points1[:, 0]).sum()/(points2[:, 0]*points1[:, 0]+points2[:, 1]*points1[:, 1]).sum())
 
def centered_rigid_transform2d(data,  **kwargs):
    '''Transforms a point or image with a rotation about user defined center followed by translation.
    angle: radians
    translation: pixels
    origin: pixels. The origin is the center of the image in most cases, i.e. (32,32) for an image sized  64x64  pixels
    center: pixels, around which the rotation will take place. If you want to rotate around the image center, this should be None or the same value as the origin.
               Otherwise center must be absolute pixel number, e.g. 28,24 in a 64x64 image.
    '''
    translation = kwargs.get('translation', rc((0, 0)))
    angle = kwargs.get('angle', 0)
    debug = kwargs.get('debug', 0)
    origin = kwargs.get('origin', None)
    center = kwargs.get('center', None)
    reshape = kwargs.get('reshape',False)
    adata = numpy.array(data)
    if adata.size==2: # single point
        if origin is None:
            if center is None:
                raise ValueError('You must supply either the coordinates of the origin,  or the rotation center')
            else:
                origin = rc((0, 0))
                print('Warning! Point will be rotated around (0, 0). If this is not what you wanted,  supply rotation center in keyword "origin"')
        if center is None: center = origin
        if 1: # rotation followed by translation
            res = rotate_around_center(adata, angle, nd(origin, True))
            offs = calc_offset(angle, center,  translation,  origin)
            res += nd(offs, True)
        else:
            offs = calc_offset(angle, center,  translation,  origin)
            adata += nd(offs, True)
            res = rotate_around_center(adata, angle, nd(origin, True))
        if not hasattr(data, 'shape'): res = res.tolist()
    else: # image input
        if origin is None: 
            origin = rc(numpy.array(adata.shape)/2)
        if center is None:
            center = origin
        if 1:
            res = rotate_around_center(adata, angle, center, reshape=reshape)
            offset = calc_offset(angle, center, translation, origin)
            if debug:
                from visexpA.engine.datadisplay.imaged import imshow
               # imshow(res, offset)
                imshow(res, translation)
            res = op_masked(shift, res, (offset['row'], offset['col']), order=0, cval=numpy.nan)
        else:
            offset = calc_offset(angle, center, translation, origin)
            if debug:
                from visexpA.engine.datadisplay.imaged import imshow
               # imshow(res, offset)
                imshow(res, translation)
            res = op_masked(shift, adata, (-offset['row'], offset['col']), order=0, cval=numpy.nan)
            res = rotate_around_center(res, angle, origin,  reshape=kwargs.get('reshape', False))
    return res

def calc_offset(angle, center, translation,  image_center):
    '''Calculates the offset value : offset = -RC+C+T where R is the rotation matrix,
    C is the rotation center, T is the translation vector.'''
    RC = rotate_around_center(nd(center, True), angle,  nd(image_center, True)) #use -angle, since point rotation by default rotates positive degrees counter clockwise
    return rc(-RC+nd(center)+nd(translation))
    
def op_masked(function, inarray,  *args,  **kwargs):
    '''Wrapper function for a function that introduces shape change to the array. Thanks to 
    the wrapping, scipy.ndimage.interpolation and ..shift handles masked arrays.'''
    if hasattr(inarray, 'mask'):
        mask = inarray.mask
        kw2= kwargs.copy()
        kw2['cval']=numpy.nan
        kw2['order']=0
        outmask = nan2value(function(mask.astype(numpy.float),  *args, **kw2), numpy.nanmax)
    inarray = function(inarray, *args, **kwargs)
    if 'outmask' in locals():
        inarray = numpy.ma.array(inarray, mask=outmask)
    return inarray

def rectangular_roi(center, radius, imshape):
    '''Input: rc value with row and col dtype.
    Returns rowstart,rowend,colstart,colend cropped at image shape
    '''
    return [max(0, center['row']-radius), min(center['row']+radius, imshape[0]), max(0, center['col']-radius), min(center['col']+radius, imshape[1])]
    
def match_sizes_centered(images):
    '''Crops the borders of two images to make both the same size. Their center remains aligned, i.e. the borders are trimmed symmetrically.'''
    z=numpy.array((0, 0))
    shapes = numpy.r_[[i.shape for i in images]]
    cs = shapes.min(axis=0) # minimum shape across all images
    imout= []
    for im in images:
        ims = numpy.array(im.shape).astype(float)
        bord = numpy.maximum(z, (ims-cs)/2)
        imout.append(im[numpy.floor(bord[0]):ims[0]-numpy.ceil(bord[0]), numpy.floor(bord[1]):ims[1]-numpy.ceil(bord[1])])
    return imout

def plane(params, coords):
    c0, c1, c2 = params
    x, y,z = coords
    #return c0*x + c1*y + c2*z  = c3#)
    
def polygon2filled(polygon, color=None):
    '''Converts a polygon object into a list of coordinates of the entire polyon
    '''
    import Polygon,  Polygon.Utils
    try:
        import Image, ImageDraw
    except ImportError:
        from PIL import Image, ImageDraw
    pts2=numpy.round(numpy.array(Polygon.Utils.pointList(polygon)))
    li = Image.fromarray(numpy.zeros(numpy.max(pts2, axis=0)+2), mode='I')
    draw= ImageDraw.Draw(li)
    pts3 = [(item[1],  item[0], ) for item in pts2.tolist()]
    draw.polygon(pts3,outline=color, fill=color) 
    allpts= numpy.array(numpy.nonzero(numpy.array(li))).T
    return allpts

def overlap(p1, p2,  thr=0.25):
    #polygon based overlap causes spurious segfaults
    if hasattr(p1, 'nPoints'):
        if p1.nPoints()==45 and p2.nPoints()==66:
            pass
        int_sec = p1&p2
        if int_sec.area()==0:
            return 0
        diffs = [p1-p2, p2-p1]
        #decide whether the two components are spatially distinct
        proportions = numpy.array([int_sec.area()/d.area() for d in diffs if d.area()>0])
    else:
        p1s=set([tuple([int(i1) for i1 in i]) for i in p1])
        p2s=set([tuple([int(i1) for i1 in i]) for i in p2])
        int_sec= p1s& p2s
        if len(int_sec)==0:
            return 0
        diffs=[p1s-p2s, p2s-p1s]
        if len(diffs[0])==0 or len(diffs[1])==0:
            return 1
        proportions = numpy.array([float(len(int_sec))/len(d) for d in diffs])
    if numpy.any(proportions>thr):
        return max(proportions)
    else:
        return 0

def versor2angle_axis(versor):
    '''From a versor computes the angle of the rotation'''
    if len(versor)!=3:
        raise TypeError('Versor must be a list or numpy array with 3 values')
    K =numpy.sqrt(sum([versor[i]**2 for i in range(3)]))
    angle = 2.0*numpy.arcsin(K)
    axis = numpy.array(versor)/K
    return angle,axis
    
def point_coordinates(distance, angle, origin):
    '''
    calculate the coordinates of a point which is in a certain distance and angle from origin
    '''
    if origin.dtype.names is None:
        x=numpy.cos(angle)*distance+origin[0]
        y=numpy.sin(angle)*distance+origin[1]
        return numpy.array([x,y])
    else:
        x=numpy.cos(angle)*distance+origin['col']
        y=numpy.sin(angle)*distance+origin['row']
        return cr((x,y))
        
def circle_mask(center,radius, size):
    mask=numpy.zeros(size)
    xcoo,ycoo=numpy.meshgrid(numpy.arange(size[0]), numpy.arange(size[1]))
    xcoo = xcoo.flatten()
    ycoo = ycoo.flatten()
    indexes=numpy.where(numpy.sqrt((xcoo-center[0])**2+(ycoo-center[1])**2)<radius)[0]
    mask[xcoo[indexes],ycoo[indexes]]=1
    return mask
    
def numpy_circle(diameter, center = (0,0), color = 1.0, array_size = (100, 100)):
    radius_sq = (diameter * 0.5) ** 2
    circle = numpy.ones(array_size)
    coords = numpy.nonzero(circle)
    distance_x = coords[0] - (center[0] + int(0.5 * array_size[0]))
    distance_y = coords[1] - (center[1] + int(0.5 * array_size[1]))
    
    distance_x = distance_x ** 2
    distance_y = distance_y ** 2
    distance = distance_x + distance_y
    active_pixel_mask = numpy.where(distance <= radius_sq, 1, 0)
    circle = circle * 0
    for i in range(len(active_pixel_mask)):
        if active_pixel_mask[i] == 1:
            circle[coords[0][i], coords[1][i]] = color
    return circle
    
def numpy_circles(radii,  centers,  array_size,  colors = None):
    if 0:
        from visexpA.engine.datadisplay.imaged import imshow

    a = numpy.zeros(array_size).astype('uint8')
    if not isinstance(radii, (list, tuple)) or  (hasattr(radii, 'shape') and radii.shape[1]==1):
        # either a numpy array of row, col pairs, or a list of numpy arrays with 1 row,col pair is accepted
        radii = [radii]
    if colors is None: colors = 255
    if not isinstance(colors, (tuple, list)) or (len(colors)==1 and len(radii)>1):
        colors = [colors]*len(radii)
    
    from PIL import Image, ImageDraw
    im=Image.fromarray(a)
    draw = ImageDraw.Draw(im)
    im_center = numpy.array(array_size).astype(float)/2
    for c, r, color in zip(centers, radii, colors):
        if 0:
            r_l = numpy.clip(c['row']-r, 0, array_size[0]) # lower limit for row coords
            r_h = numpy.clip(c['row']+r+1, 0, array_size[0])
            c_l = numpy.clip(c['col']-r, 0, array_size[1])
            c_h = numpy.clip(c['col']+r+1, 0, array_size[1]+1)
            row, col = numpy.ogrid[r_l-c['row']+(r-1)%2: r_h-c['row'], c_l-c['col']+(r-1)%2: c_h-c['col']]
            index = row**2 + col**2 <= r**2
            a[r_l:r_h+(r%2),c_l:c_h+(r%2)][index] = color
        else:
            bbox =  (c['col']-r,  c['row']-r,c['col']+r, c['row']+r)
            draw.ellipse(bbox, fill=color)
    return numpy.array(im)
    
def triangle_vertices(size, orientation = 0):
    orientation -= 90
    vertices = numpy.zeros((3,2))
    vertices[0,0] = 0.5*size*numpy.cos(numpy.radians(orientation))
    vertices[0,1] = 0.5*size*numpy.sin(numpy.radians(orientation))
    vertices[1] = -vertices[0]
    height=0.5*numpy.sqrt(3)*size
    angle = numpy.radians(90-orientation)
    vertices[2,0] = -height*numpy.cos(angle)
    vertices[2,1] = height*numpy.sin(angle)
    return vertices
    
def star_vertices(radius, ncorners, orientation=0, inner_radius = None):
    if inner_radius is None:
        inner_radius = 0.5*radius
    vertices = numpy.zeros((2*ncorners,2))
    current_angle = numpy.radians(orientation)
    angle_step = 2*numpy.pi/(2*ncorners)
    for corner in range(ncorners):
        #calculate outer point
        pouter=point_coordinates(radius, current_angle, rc((0,0)))
        vertices[2*corner,0]=pouter['col']
        vertices[2*corner,1]=pouter['row']
        current_angle += angle_step
        pinner=point_coordinates(inner_radius, current_angle, rc((0,0)))
        vertices[2*corner+1,0]=pinner['col']
        vertices[2*corner+1,1]=pinner['row']
        current_angle += angle_step
    return vertices

def arc_vertices(diameter, n_vertices,  angle,  angle_range,  pos = [0, 0]):
    if not isinstance(diameter,  list):
        diameter_list = [diameter, diameter]
    else:
        diameter_list = diameter   
    
    start_angle = (angle - 0.5 * angle_range)  * numpy.pi / 180.0
    end_angle = (angle + 0.5 * angle_range) * numpy.pi / 180.0
    angles = numpy.linspace(start_angle, end_angle,  n_vertices)
#    angles = angles[1:]
    vertices = numpy.zeros((angles.shape[0],  2))    
    vertices[:, 0] = 0.5 * numpy.cos(angles)
    vertices[:, 1] = 0.5 * numpy.sin(angles)
    return vertices * numpy.array(diameter_list) + numpy.array(pos)
    
def rectangle_vertices(size, orientation = 0):
    alpha = numpy.arctan(float(size['row'])/float(size['col']))
    angles = numpy.array([alpha, numpy.pi - alpha, numpy.pi + alpha, - alpha])
    angles += orientation * numpy.pi / 180.0
    half_diagonal = 0.5 * numpy.sqrt(size['row'] ** 2 + size['col'] ** 2)
    vertices = []
    for angle in angles:
        vertice = [numpy.cos(angle), numpy.sin(angle)]
        vertices.append(vertice)
    vertices = numpy.array(vertices)
    vertices *= half_diagonal
    return vertices    

def circle_vertices(diameter,  resolution = 1.0,  start_angle = 0,  end_angle = 360, pos = (0,0),  arc_slice = False):
    '''
    Resolution is in steps / degree
    radius is a list of x and y
    '''
    output_list = False
    if not isinstance(diameter,list):
        diameter = [diameter,diameter]
    if output_list:
        vertices = []
    else:
        n_vertices_arc = int((end_angle - start_angle) * resolution + 1)
        if abs(start_angle - end_angle) < 360 and arc_slice:
            n_vertices = n_vertices_arc + 1
        else:
            n_vertices = n_vertices_arc
        vertices = numpy.zeros(shape = (n_vertices,  2))
        
    if output_list:
        for i in range(int(start_angle * resolution),  int(end_angle * resolution)):
                    angle = (float(i)*numpy.pi / 180.0) / resolution
                    vertice = [0.5 * diameter[0] * numpy.cos(angle) + pos[0],  0.5 * diameter[1] * numpy.sin(angle) + pos[1]]
                    vertices.append(vertice)
    else:
        start_angle_rad = start_angle * numpy.pi / 180.0
        end_angle_rad = end_angle * numpy.pi / 180.0
        angle = numpy.linspace(start_angle_rad,  end_angle_rad, n_vertices_arc)        
        x = 0.5 * diameter[0] * numpy.cos(angle) + pos[0]
        y = 0.5 * diameter[1] * numpy.sin(angle) + pos[1]
        vertices[0:n_vertices_arc, 0] = x
        vertices[0:n_vertices_arc, 1] = y      
    
    if abs(start_angle - end_angle) < 360:
        if output_list:
            if arc_slice:
                vertices.append([0,  0])
        else:
            if arc_slice:                
                vertices[-1] = numpy.array([0,  0])
    return vertices
    
def vertices2image(vertices):
    '''
    Vertice locations are visualized on an image with small +s
    '''
    from pylab import show, imshow
    height=int(vertices[:,0].max()-vertices[:,0].min())+1
    width=int(vertices[:,1].max()-vertices[:,1].min())+1
    im=numpy.zeros((height,width))
    coo=numpy.cast['int'](vertices-vertices.min(axis=0))
    for c in coo:
        for i in range(-3,4):
            try:
                im[c[0]+i, c[1]]=1
                im[c[0], c[1]+i]=1
            except IndexError:
                pass
    imshow(im,cmap='gray')
    show()

class TestGeometry(unittest.TestCase):
    def setUp(self):
        self.test_data = [
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
        result = are_vectors_parallel(self.test_data[case]['direction1'], self.test_data[case]['direction2'])
        self.assertEqual(result,self.test_data[case]['parallel?'])
        
    def test_01_parallel(self):
        case = 1
        result = are_vectors_parallel(self.test_data[case]['direction1'], self.test_data[case]['direction2'])
        self.assertEqual(result,self.test_data[case]['parallel?'])

    def test_02_parallel(self):
        case = 2
        result = are_vectors_parallel(self.test_data[case]['direction1'], self.test_data[case]['direction2'])
        self.assertEqual(result,self.test_data[case]['parallel?'])
        
    def test_03_parallel(self):
        case = 3
        result = are_vectors_parallel(self.test_data[case]['direction1'], self.test_data[case]['direction2'])
        self.assertEqual(result,self.test_data[case]['parallel?'])
        
    def test_04_lines_intersecting(self):
        case = 4        
        result = line_intersection(self.test_data[case]['line1_point'], self.test_data[case]['line1_direction'],self.test_data[case]['line2_point'], self.test_data[case]['line2_direction'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.test_data[case]['result'][0],self.test_data[case]['result'][1][0],self.test_data[case]['result'][1][1],self.test_data[case]['result'][1][2]))

    def test_05_lines_intersecting(self):
        case = 5
        result = line_intersection(self.test_data[case]['line1_point'], self.test_data[case]['line1_direction'],self.test_data[case]['line2_point'], self.test_data[case]['line2_direction'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.test_data[case]['result'][0],self.test_data[case]['result'][1][0],self.test_data[case]['result'][1][1],self.test_data[case]['result'][1][2]))        
    
    def test_06_lines_intersecting(self):
        case = 6
        result = line_intersection(self.test_data[case]['line1_point'], self.test_data[case]['line1_direction'],self.test_data[case]['line2_point'], self.test_data[case]['line2_direction'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.test_data[case]['result'][0],self.test_data[case]['result'][1][0],self.test_data[case]['result'][1][1],self.test_data[case]['result'][1][2]))        
        
    def test_07_lines_intersecting(self):
        case = 7
        result = line_intersection(self.test_data[case]['line1_point'], self.test_data[case]['line1_direction'],self.test_data[case]['line2_point'], self.test_data[case]['line2_direction'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.test_data[case]['result'][0],self.test_data[case]['result'][1][0],self.test_data[case]['result'][1][1],self.test_data[case]['result'][1][2]))        
        
    def test_08_lines_intersecting(self):
        case = 8
        result = line_intersection(self.test_data[case]['line1_point'], self.test_data[case]['line1_direction'],self.test_data[case]['line2_point'], self.test_data[case]['line2_direction'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.test_data[case]['result'][0],self.test_data[case]['result'][1][0],self.test_data[case]['result'][1][1],self.test_data[case]['result'][1][2]))        

    @unittest.skip('Could not make it work correctly')
    def test_09_lines_intersecting(self):
        case = 9
        result = line_intersection(self.test_data[case]['line1_point'], self.test_data[case]['line1_direction'],self.test_data[case]['line2_point'], self.test_data[case]['line2_direction'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.test_data[case]['result'][0],self.test_data[case]['result'][1][0],self.test_data[case]['result'][1][1],self.test_data[case]['result'][1][2]))        

    def test_10_lines_not_intersecting(self):
        case = 10
        result = line_intersection(self.test_data[case]['line1_point'], self.test_data[case]['line1_direction'],self.test_data[case]['line2_point'], self.test_data[case]['line2_direction'])
        self.assertEqual(result,self.test_data[case]['result'])
        
    def test_11_lines_not_intersecting(self):
        case = 11
        result = line_intersection(self.test_data[case]['line1_point'], self.test_data[case]['line1_direction'],self.test_data[case]['line2_point'], self.test_data[case]['line2_direction'])
        self.assertEqual(result,self.test_data[case]['result'])
        
    def test_12_line_segments_intersecting(self):
        case = 12
        result = line_segment_intersection(self.test_data[case]['line1_point1'],self.test_data[case]['line1_point2'],self.test_data[case]['line2_point1'],self.test_data[case]['line2_point2'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.test_data[case]['result'][0],self.test_data[case]['result'][1][0],self.test_data[case]['result'][1][1],self.test_data[case]['result'][1][2]))        
        
    def test_13_line_segments_intersecting(self):
        case = 13
        result = line_segment_intersection(self.test_data[case]['line1_point1'],self.test_data[case]['line1_point2'],self.test_data[case]['line2_point1'],self.test_data[case]['line2_point2'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.test_data[case]['result'][0],self.test_data[case]['result'][1][0],self.test_data[case]['result'][1][1],self.test_data[case]['result'][1][2]))        

    def test_14_line_segments_not_intersecting(self):
        case = 14
        result = line_segment_intersection(self.test_data[case]['line1_point1'],self.test_data[case]['line1_point2'],self.test_data[case]['line2_point1'],self.test_data[case]['line2_point2'])
        self.assertEqual(result,self.test_data[case]['result'])
        
    def test_15_line_segments_not_intersecting(self):
        case = 15
        result = line_segment_intersection(self.test_data[case]['line1_point1'],self.test_data[case]['line1_point2'],self.test_data[case]['line2_point1'],self.test_data[case]['line2_point2'])
        self.assertEqual(result,self.test_data[case]['result'])
        
    def test_16_line_segment_ray_intersecting(self):
        case = 16
        result = line_segment_ray_intersection(self.test_data[case]['line_point1'],self.test_data[case]['line_point2'],self.test_data[case]['ray_point'],self.test_data[case]['ray_direction'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.test_data[case]['result'][0],self.test_data[case]['result'][1][0],self.test_data[case]['result'][1][1],self.test_data[case]['result'][1][2]))        

    def test_17_line_segment_ray_not_intersecting(self):
        case = 17
        result = line_segment_ray_intersection(self.test_data[case]['line_point1'],self.test_data[case]['line_point2'],self.test_data[case]['ray_point'],self.test_data[case]['ray_direction'])
        self.assertEqual(result,self.test_data[case]['result'])
        
    def test_18_line_segment_ray_not_intersecting(self):
        case = 18
        result = line_segment_ray_intersection(self.test_data[case]['line_point1'],self.test_data[case]['line_point2'],self.test_data[case]['ray_point'],self.test_data[case]['ray_direction'])
        self.assertEqual(result,self.test_data[case]['result'])
        
    def test_19_line_segment_ray_not_intersecting(self):
        case = 19
        result = line_segment_ray_intersection(self.test_data[case]['line_point1'],self.test_data[case]['line_point2'],self.test_data[case]['ray_point'],self.test_data[case]['ray_direction'])
        self.assertEqual(result,self.test_data[case]['result'])

    def test_20_line_plane_intersecting(self):
        case = 20
        result = plane_line_intersection(self.test_data[case]['line_start_point'],self.test_data[case]['line_direction'],self.test_data[case]['polygon'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.test_data[case]['result'][0],self.test_data[case]['result'][1][0],self.test_data[case]['result'][1][1],self.test_data[case]['result'][1][2]))        

    def test_21_line_plane_intersecting(self):
        case = 21
        result = plane_line_intersection(self.test_data[case]['line_start_point'],self.test_data[case]['line_direction'],self.test_data[case]['polygon'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.test_data[case]['result'][0],self.test_data[case]['result'][1][0],self.test_data[case]['result'][1][1],self.test_data[case]['result'][1][2]))        

    def test_22_line_plane_not_intersecting(self):
        case = 22
        result = plane_line_intersection(self.test_data[case]['line_start_point'],self.test_data[case]['line_direction'],self.test_data[case]['polygon'])
        self.assertEqual(result,self.test_data[case]['result'])
        
    def test_23_ray_plane_intersecting(self):
        case = 23
        result = plane_ray_intersection(self.test_data[case]['line_start_point'],self.test_data[case]['line_direction'],self.test_data[case]['polygon'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.test_data[case]['result'][0],self.test_data[case]['result'][1][0],self.test_data[case]['result'][1][1],self.test_data[case]['result'][1][2]))        

    def test_24_ray_plane_intersecting(self):
        case = 24
        result = plane_ray_intersection(self.test_data[case]['line_start_point'],self.test_data[case]['line_direction'],self.test_data[case]['polygon'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.test_data[case]['result'][0],self.test_data[case]['result'][1][0],self.test_data[case]['result'][1][1],self.test_data[case]['result'][1][2]))        

    def test_25_ray_plane_not_intersecting(self):
        case = 25
        result = plane_ray_intersection(self.test_data[case]['line_start_point'],self.test_data[case]['line_direction'],self.test_data[case]['polygon'])
        self.assertEqual(result,self.test_data[case]['result'])
        
    def test_26_point_is_in_polygon(self):
        case = 26
        result = is_point_in_polygon(self.test_data[case]['point'],self.test_data[case]['polygon'])
        self.assertEqual(result,self.test_data[case]['result'])
        
    def test_27_point_is_not_in_polygon(self):
        case = 27
        result = is_point_in_polygon(self.test_data[case]['point'],self.test_data[case]['polygon'])
        self.assertEqual(result,self.test_data[case]['result'])
        
    def test_28_point_is_not_in_polygon(self):
        case = 28
        result = is_point_in_polygon(self.test_data[case]['point'],self.test_data[case]['polygon'])
        self.assertEqual(result,self.test_data[case]['result'])
        
    def test_29_ray_polygon_intersecting(self):
        case = 29
        result = ray_polygon_intersection(self.test_data[case]['ray_starting_point'],self.test_data[case]['ray_direction'],self.test_data[case]['polygon'])
        self.assertEqual((result[0], result[1][0], result[1][1], result[1][2]), (self.test_data[case]['result'][0],self.test_data[case]['result'][1][0],self.test_data[case]['result'][1][1],self.test_data[case]['result'][1][2]))        

    def test_30_ray_polygon_not_intersecting(self):
        case = 30
        result = ray_polygon_intersection(self.test_data[case]['ray_starting_point'],self.test_data[case]['ray_direction'],self.test_data[case]['polygon'])
        self.assertEqual(result,self.test_data[case]['result'])

    def test_31_ray_polygon_not_intersecting(self):
        case = 31
        result = ray_polygon_intersection(self.test_data[case]['ray_starting_point'],self.test_data[case]['ray_direction'],self.test_data[case]['polygon'])
        self.assertEqual(result,self.test_data[case]['result'])

    @unittest.skip('Needs update')
    def test_32_plane_rotation(self):
        point = [1, 1]
        angle = 45.0/180*numpy.pi
        res1= rotate_around_center(point, angle)
        center = [0.5, 0.5]
        point = [1.0, 1.0]
        res2= rotate_around_center(point, angle, center)
        good = sum([numpy.around(i, decimals=15)-numpy.around(j, decimals=15) for i, j in zip(res2, [0.5, 0.5+numpy.sqrt(2)/2])])
        self.assertTrue(res1==[0, 1] and good==0.0)

    def test_33_match_sizes_centered(self):
        im1= numpy.zeros((16,16))
        im2= numpy.zeros((20,16))
        im3= numpy.zeros((20,21))
        images = match_sizes_centered([im1,im2,im3])
        self.assertEqual(sum([1 for i in images if i.shape==(16,16)]),len(images))
        pass
    
        
    @unittest.skip('Could not make it work correctly')
    def test_34_HAffine_from_points(self):
        from scipy.ndimage import affine_transform
        im1 = numpy.zeros((256,256),numpy.uint8)
        im1[32:37,32] = 255
        im1[67:69,45:64] = 255
        im1[32,33]=255
        im1[120,99]=255
        a = numpy.radians(-45)
        A = numpy.array([[numpy.cos(a), numpy.sin(a)], [-numpy.sin(a), numpy.cos(a)]]).T
        im2  =affine_transform(im1,A,[0,0],order=0)
        A2 = Haffine_from_points(zip(*im2.nonzero()),zip(*im1.nonzero()))
        pass
    
    def test_36_triangle(self):
        expected_vertices = numpy.array([
            [[ 0.5 ,  0.  ],
            [-0.5 , 0.  ],
            [0.  ,  0.87]],
            [[ 0.35,  0.35],
            [-0.35, -0.35],
            [-0.61,  0.61]],
            [[ 0.  ,  0.5 ],
            [0.  , -0.5 ],
            [-0.87,  0.  ]],
            [[ -0.5 ,  0.  ],
            [0.5 , 0.  ],
            [0.  ,  -0.87]],
        ])
        
        angles = [0,45,90,180]
        size = 1.2
        for i in range(len(angles)):
            numpy.testing.assert_almost_equal(numpy.round(triangle_vertices(size, angles[i]),2), size*expected_vertices[i], 2)
        pass
        
    def test_37_star(self):
        import itertools
        for r,c,o in itertools.product([1.0, 10.0], range(2,10), [0, 45, 90]):
            v=star_vertices(r,c,o)
            self.assertEqual(v.shape, (2*c,2))
            rs=numpy.sqrt(v[:,0]**2+v[:,1]**2)
            numpy.testing.assert_almost_equal(rs[::2], numpy.ones(c)*r)
            numpy.testing.assert_almost_equal(rs[1::2], numpy.ones(c)*r*0.5)
            angles = numpy.arctan2(v[:,1],v[:,0])#-numpy.radians(o)
            angles = numpy.where(angles<0, angles+2*numpy.pi,angles)
            try:
                numpy.testing.assert_almost_equal(numpy.diff(numpy.sort(angles)).std(), 0)
            except:
                pass
            
            
    def test_38_rotate_point(self):
        res= rotate_point(cr((1,0)),90, rc((0,0)))
        numpy.testing.assert_almost_equal(res['col'],0)
        numpy.testing.assert_almost_equal(res['row'],1)
        
    def test_39_circle_mask(self):
        from pylab import imshow,show
        imshow(circle_mask([5,5],5, [20,30]));show()
        
    def test_40_vertices2image(self):
        v=numpy.array([[ -9.39692621e+01,   2.88000000e+02],
           [ -5.12000000e+02,   2.88000000e+02],
           [ -5.12000000e+02,  -2.88000000e+02],
           [ -9.39692621e+01,  -2.88000000e+02],
           [  5.12000000e+02,   2.88000000e+02],
           [  9.39692621e+01,   2.88000000e+02],
           [  9.39692621e+01,  -2.88000000e+02],
           [  5.12000000e+02,  -2.88000000e+02],
           [  7.66044443e+01,   6.42787610e+01],
           [  1.73648178e+01,   9.84807753e+01],
           [  1.73648178e+01,   2.88000000e+02],
           [  7.66044443e+01,   2.88000000e+02],
           [  1.73648178e+01,   9.84807753e+01],
           [ -5.00000000e+01,   8.66025404e+01],
           [ -5.00000000e+01,   2.88000000e+02],
           [  1.73648178e+01,   2.88000000e+02],
           [ -5.00000000e+01,   8.66025404e+01],
           [ -9.39692621e+01,   3.42020143e+01],
           [ -9.39692621e+01,   2.88000000e+02],
           [ -5.00000000e+01,   2.88000000e+02],
           [ -9.39692621e+01,  -3.42020143e+01],
           [ -5.00000000e+01,  -8.66025404e+01],
           [ -5.00000000e+01,  -2.88000000e+02],
           [ -9.39692621e+01,  -2.88000000e+02],
           [ -5.00000000e+01,  -8.66025404e+01],
           [  1.73648178e+01,  -9.84807753e+01],
           [  1.73648178e+01,  -2.88000000e+02],
           [ -5.00000000e+01,  -2.88000000e+02],
           [  1.73648178e+01,  -9.84807753e+01],
           [  7.66044443e+01,  -6.42787610e+01],
           [  7.66044443e+01,  -2.88000000e+02],
           [  1.73648178e+01,  -2.88000000e+02],
           [  7.66044443e+01,  -6.42787610e+01],
           [  1.00000000e+02,  -2.44929360e-14],
           [  1.00000000e+02,  -2.88000000e+02],
           [  7.66044443e+01,  -2.88000000e+02]])
        vertices2image(v)
        

def test_estimate_rotation():
    a = [[1, 1], [1, 5]]
    angle= 90.0/180*numpy.pi
    b= rotate_around_center(a, angle)
    a2 = estimate_rotation(numpy.array(a), numpy.array(b))
    pass
  
def test_procrustes():
    points1 = numpy.array([[1,1],[1,0]])
    points2 = numpy.array([[1,2],[1,1]])
    r1= procrustes(points1,points2)
    points2 = numpy.array([[1,0],[1,-1]])
    r2= procrustes(points1,points2)
    
    pass

if __name__ == "__main__":
    test_procrustes()
    unittest.main()
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
    

if __name__ == '__main__':
    unittest.main()
