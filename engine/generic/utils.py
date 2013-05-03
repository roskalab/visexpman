import sys
import math
import random
import numpy
import os.path
import os
import time
import unittest
import pkgutil
import inspect
import unittest
import tempfile
import copy
import select
import subprocess
import cPickle as pickle
if os.name == 'nt':
    import win32process
    import win32api

import file

import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner

def resample_array(array, factor):
    '''
    Increases sampling rate of array with factor
    '''
    if factor == 1:
        return array
    else:
        return numpy.array([array]*int(factor)).flatten('F')

def sinus_linear_range(error):
    def f(x, e):
        return x - numpy.sin(x)-e
    from scipy.optimize import fsolve
    sol = fsolve(f, numpy.pi/4, args=(error))
    #Between 0 and returned phase linearity error  is below specified
    return sol[0]
    
def generate_lut(x, min = 0.0, max = 1.0, gamma = 1.0, brightness = 0.5, contrast = 0.0):
    max_ = max - contrast
    min_ = min + contrast
    b =-min*(1.0/(max_-min_))
    b = b + brightness - 0.5
    a = (1.0/(max_-min_))
    y = a * x + b
    y = y ** gamma
    y = numpy.where(y < 0.0,  0.0,  y)
    y = numpy.where(y > 1.0,  1.0,  y)
    return y

######## Signals  ########
def signal2binary(signal):
    '''
    Signal is considered true/logic 1 when signal reached the 'high' voltage level (transient is considered as False)
    '''
    return numpy.where(signal > numpy.histogram(signal, bins = 10)[1][-2],  True,  False)

#== Coordinate geometry ==
#TODO: check for redundant functions in this section
def roi_center(roi):
    return rc((roi['row'].mean(), roi['col'].mean()))
    
def toRGBarray(array):
    rgb_array = numpy.array([array, array, array])
    rgb_array = numpy.rollaxis(rgb_array, 0, len(array.shape))
    return rgb_array
 
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

def circle_to_numpy(diameter,  resolution = 1.0,  image_size = (100,  100),  color = 1.0,  pos = (0, 0)):
    '''
    diameter: diameter of circle in pixels
    resolution: angle resolution of drawing circle
    image_size: x, y size of image/numpy array in pixels
    color: color of circle, greyscale, range 0...1
    pos : x, y position in pixels, center is 0, 0
    '''
    vertices = calculate_circle_vertices([diameter,  diameter],  resolution)
    import Image,  ImageDraw,  numpy
    image = Image.new('L',  image_size,  0)
    draw = ImageDraw.Draw(image)
    
    vertices_int = []
    for i in vertices:
        vertices_int.append(int(i[0] + image_size[0] * 0.5) + pos[0])
        vertices_int.append(int(i[1] + image_size[1] * 0.5) - pos[1])
    
    
    draw.polygon(vertices_int,  fill = int(color * 255.0))    
    #just for debug
    image.show()
    print numpy.asarray(image)
    return numpy.asarray(image)
    
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

def calculate_circle_vertices(diameter,  resolution = 1.0,  start_angle = 0,  end_angle = 360, pos = (0,0),  arc_slice = False):
    '''
    Resolution is in steps / degree
    radius is a list of x and y
    '''
    output_list = False
    if output_list:
        vertices = []
    else:
        n_vertices_arc = (end_angle - start_angle) * resolution + 1
        if abs(start_angle - end_angle) < 360 and arc_slice:
            n_vertices = n_vertices_arc + 1
        else:
            n_vertices = n_vertices_arc
        vertices = numpy.zeros(shape = (n_vertices,  2))
        
    if output_list:
        for i in range(int(start_angle * resolution),  int(end_angle * resolution)):
                    angle = (float(i)*math.pi / 180.0) / resolution
                    vertice = [0.5 * diameter[0] * math.cos(angle) + pos[0],  0.5 * diameter[1] * math.sin(angle) + pos[1]]
                    vertices.append(vertice)
    else:
        start_angle_rad = start_angle * math.pi / 180.0
        end_angle_rad = end_angle * math.pi / 180.0
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

def coordinate_system(type, SCREEN_RESOLUTION=None):
    '''looks up proper settings for commonly used coordinate system conventions'''
    if type=='ulcorner':
        if SCREEN_RESOLUTION == None: raise ValueError('Screen resolution is needed for converting to upper-left corner origo coordinate system.')
        ORIGO = cr((-0.5 * SCREEN_RESOLUTION['col'], 0.5 * SCREEN_RESOLUTION['row']))
        HORIZONTAL_AXIS_POSITIVE_DIRECTION = 'right'
        VERTICAL_AXIS_POSITIVE_DIRECTION = 'down'
    elif type=='center':
        ORIGO = cr((0, 0))
        HORIZONTAL_AXIS_POSITIVE_DIRECTION = 'right'
        VERTICAL_AXIS_POSITIVE_DIRECTION = 'up'
    else:
        raise ValueError('Coordinate system type '+type+' not recognized')
    return ORIGO, HORIZONTAL_AXIS_POSITIVE_DIRECTION, VERTICAL_AXIS_POSITIVE_DIRECTION
    
def centered_to_ulcorner_coordinate_system(coordinates, screen_size):
    cooridnates_ulcorner = coordinates
    cooridnates_ulcorner['row'] = - cooridnates_ulcorner['row'] + 0.5 * screen_size['row']
    cooridnates_ulcorner['col'] = cooridnates_ulcorner['col'] + 0.5 * screen_size['col']
    return cooridnates_ulcorner

def ulcorner_to_centered_coordinate_system(coordinates, screen_size):
    cooridnates_centered = coordinates
    cooridnates_centered['row'] = - cooridnates_centered['row'] - 0.5 * screen_size['row']
    cooridnates_centered['col'] = cooridnates_centered['col'] - 0.5 * screen_size['col']
    return cooridnates_centered

def arrays_equal(a1, a2):
    if isinstance(a1, list):
        a1_ = numpy.array(a1)
    else:
        a1_ = a1
    if isinstance(a2, list):
        a2_ = numpy.array(a2)
    else:
        a2_ = a2
    return (abs(a1_-a2_)).sum() == 0
    
def um2pixel(data, origin, scale):
    if scale['col'] == 0.0 or scale['row'] == 0.0:
        raise RuntimeError('Scaling is incorrect {0}'.format(scale))
    else:
        in_pixel = rc((numpy.cast['int']((data['row']-origin['row'])/scale['row']), numpy.cast['int']((data['col']-origin['col'])/scale['col'])))
    return in_pixel
    
def pixel2um(data, origin, scale):
    in_um = rc((data['row']*scale['row'] + origin['row'],data['col']*scale['col']+origin['col']))
    return in_um

def argsort(seq):
    '''same as numpy.argsort but works on sequences'''
    #http://stackoverflow.com/questions/3382352/equivalent-of-numpy-argsort-in-basic-python/3382369#3382369
    #by ubuntu
    return sorted(range(len(seq)), key=seq.__getitem__)
    
def nd(rcarray, squeeze=False, dim_order=None):
    '''Convenience function to convert a recarray to nd array'''
    if dim_order is None: dim_order = [0, 1, 2]
    dim_names4current_data = dim_names0[:len(rcarray.dtype.names)]
    names_in_order = [dim_names4current_data[dim_order[di]]  for di in range(len(rcarray.dtype.names))]
    if rcarray.dtype.names !=names_in_order: # fields are not ordered in the default order
        res = numpy.c_[[rcarray[f] for f in names_in_order]].T # take field by field in the default order
    else: # faster way
        res= rcarray.view((rcarray[rcarray.dtype.names[0]].dtype,len(rcarray.dtype.names)))
    if squeeze:
        res=numpy.squeeze(res)
    return res

def rcd(raw):
#    warning('todo:rcd should be merged with rc and detect automatically the number of dimensions')
    return rcd_pack(raw, dim_order = [0, 1, 2])
    
def rc(raw,**kwargs):
    return rcd_pack(raw, dim_order = [0, 1],**kwargs)

def cr(raw,  **kwargs):
    return rcd_pack(raw, dim_order = [1, 0],**kwargs)    
dim_names0 = ['row','col','depth']

def rcd_pack(raw, dim_order = [0, 1],**kwargs):
    '''If a tuple is given as raw, the output will be 0dimensional rc array'''
    order = argsort(dim_order)
    dim_order = sorted(dim_order)
    dim_names = [dim_names0[n] for n in dim_order] # sorted ensures that field ordering will always be as dim_names0, this way nd will always give [row,col] or [row,col,depth] ordered data
    if isinstance(raw, (tuple, list)) and len(raw)==0: #empty list or tuple
        return numpy.recarray((0,), dtype={'names':dim_names, 'formats':[object]*2}) #returned array should be iterable (though length 0)
    # handle case when input is a tuple having as many elements as dimensions (max 3)
    if (isinstance(raw,(list,tuple)) and ((len(raw) == len(dim_names)) and (type(raw[0])==int or type(raw[0])==float or type(raw[0]) == numpy.float64 or type(raw[0]) == numpy.float32 or type(raw[0]) == numpy.int32)) or (hasattr(raw,'ndim') and raw.ndim==1 and raw.size==len(dim_names))):
        nd = kwargs.get('nd',0)
        raw = numpy.array(raw)[order] #reorder elements if they are not in row,col,depth order
        dtype={'names':dim_names,'formats':[raw[0].dtype]*len(dim_names)}
        return numpy.array(tuple(raw), dtype,ndmin=nd) 
    #handle normal situation: input is a list (array) of tuples, each tuple contains 1 to 3 elements from the row,col,depth tuple
    raw = numpy.array(raw, ndmin=2)
    if numpy.squeeze(raw).ndim!=2 and raw.size!=len(dim_names): #1 dimensional with exactly 1 to 3 values is accepted as row,col pair
        raise RuntimeError('At least '+ str(len(dim_names)) +' values are needed')
    dtype={'names':dim_names,'formats':[raw.dtype]*len(dim_names)}
    if raw.ndim > len(dim_names):
        raise TypeError('Input data dimension must be '+str(len(dim_names))+' Call rc_flatten if you want data to be flattened before conversion')
    if raw.ndim==2 and raw.shape[1]==len(dim_names): # convenience feature: user must not care if input shape is (2,x) or (x,2)  we convert to the required format (2,x)
        raw=raw.T
    else:
        raw= numpy.take(raw, order, axis=0) #rearrange the input data so that the order along dim0 is [row,col,depth]
    return numpy.array(zip(*[raw[index] for index in range(len(dim_order))]),dtype=dtype)

def rc_add(operand1, operand2,  operation = '+'):
    '''
    supported inputs:
    - single rc + single rc
    - array of rc + array of rc
    - single rc + array of rc
    - array of rc + single rc
    (- constant + single rc
    - constant + array of rc)
    '''    
    if isinstance(operand1, numpy.ndarray) and (isinstance(operand2, numpy.ndarray)):        
        if operand1.shape == () and operand2.shape == ():
            if operation == '+':                
                return rc((operand1['row'] + operand2['row'], operand1['col'] + operand2['col']))
            elif operation == '-':
                return rc((operand1['row'] - operand2['row'], operand1['col'] - operand2['col']))
        elif operand1.shape != () and operand2.shape != ():
            if operation == '+':
                rows = operand1[:]['row'] + operand2[:]['row']
                cols = operand1[:]['col'] + operand2[:]['col']
            elif operation == '-':
                rows = operand1[:]['row'] - operand2[:]['row']
                cols = operand1[:]['col'] - operand2[:]['col']
            return rc(numpy.array([rows, cols]))
        elif operand1.shape == () and operand2.shape != ():
            if operation == '+':
                rows = operand1['row'] + operand2[:]['row']
                cols = operand1['col'] + operand2[:]['col']
            elif operation == '-':
                rows = operand1['row'] - operand2[:]['row']
                cols = operand1['col'] - operand2[:]['col']
            return rc(numpy.array([rows, cols]))
        elif operand1.shape != () and operand2.shape == ():
            if operation == '+':
                rows = operand1[:]['row'] + operand2['row']
                cols = operand1[:]['col'] + operand2['col']
            elif operation == '-':
                rows = operand1[:]['row'] - operand2['row']
                cols = operand1[:]['col'] - operand2['col']
            return rc(numpy.array([rows, cols]))
    
    
def rc_multiply(operand1, operand2):
    if isinstance(operand1, numpy.ndarray) and (isinstance(operand2, numpy.ndarray)):
        if operand1.shape == () and operand2.shape == ():
            return rc((operand1['row'] * operand2['row'], operand1['col'] * operand2['col']))
        elif operand1.shape != () and operand2.shape != ():
            rows = operand1[:]['row'] * operand2[:]['row']
            cols = operand1[:]['col'] * operand2[:]['col']
            return rc(numpy.array([rows, cols]))
        elif operand1.shape == () and operand2.shape != ():
            rows = operand1['row'] * operand2[:]['row']
            cols = operand1['col'] * operand2[:]['col']
            return rc(numpy.array([rows, cols]))
        elif operand1.shape != () and operand2.shape == ():
            rows = operand1[:]['row'] * operand2['row']
            cols = operand1[:]['col'] * operand2['col']
            return rc(numpy.array([rows, cols]))    
    else:
        raise TypeError('When multiplying two arrays of row_col type, make sure both operands have the row_col type') 
        
def rc_abs(value):
    return rc((abs(value['row']), abs(value['col'])))

def rc_multiply_with_constant(rc_value, constant):
    if rc_value.shape == ():
            return rc((rc_value['row'] * constant, rc_value['col'] * constant))
    else:
            rows = rc_value[:]['row'] * constant
            cols = rc_value[:]['col'] * constant
            return rc(numpy.array([rows, cols]))
            
def rc_angle(point1, point2, degree = False):
    '''
    Calculates the angle between two points
    '''
    angle = numpy.arctan2(point2['row']-point1['row'],point2['col']-point1['col'])
    if degree:
        angle *= 180/numpy.pi
    return angle
    
def coordinate_transform(coordinates, origo, horizontal_axis_positive_direction, vertical_axis_positive_direction):
    '''
    Transforms coordinates to the native coordinate system of visual stimulation software where the origo is in the center of the screen 
    and the positive directions of on the axis's are up and right
    -1 or 2 d numpy arrays where each item of the array is in row,column format
    '''    
    if horizontal_axis_positive_direction == 'right':
        horizontal_axis_positive_direction_ = 1
    elif horizontal_axis_positive_direction == 'left':
        horizontal_axis_positive_direction_ = -1
    if vertical_axis_positive_direction == 'up':
        vertical_axis_positive_direction_ = 1
    elif vertical_axis_positive_direction == 'down':
        vertical_axis_positive_direction_ = -1
    axis_direction = rc((vertical_axis_positive_direction_, horizontal_axis_positive_direction_))    
    return rc_add(rc_multiply(axis_direction, coordinates), origo)

def coordinate_transform_single_point(point, origo, axis_direction):
    '''
    axis_direction: row-column format, row - y axis, column - x axis
    '''
    x = float(origo['col']) + float(axis_direction['col']) * float(point['col'])
    y = float(origo['row']) + float(axis_direction['row']) * float(point['row'])
    if isinstance(point['row'], int):
        x = int(x)
        y = int(y)
    return rc((y, x))
    
def arc_perimeter(radius,  angle):
    '''
    angle is in degree
    '''
    slice_ratio = angle / 360.0
    return numpy.pi  * 2 *radius * slice_ratio
    
def rc_distance(point1,  point2, rc_distance_only = False):
    if 'depth' in point1.dtype.names and 'depth' in point2.dtype.names and not rc_distance:
        return numpy.sqrt((numpy.cast['float'](point1['col'])-numpy.cast['float'](point2['col']))**2 + (numpy.cast['float'](point1['row'])-numpy.cast['float'](point2['row']))**2 + (numpy.cast['float'](point1['depth'])-numpy.cast['float'](point2['depth']))**2)
    else:
        return numpy.sqrt((numpy.cast['float'](point1['col'])-numpy.cast['float'](point2['col']))**2 + (numpy.cast['float'](point1['row'])-numpy.cast['float'](point2['row']))**2)

def rc_point_curve_distance(point, curve):
    distance = numpy.zeros_like(curve['row'])
    for axis in point.dtype.names:
        distance += (curve[axis] - point[axis])**2
    return numpy.sqrt(distance)

def calculate_trajectory(start_point,  end_point,  spatial_resolution,  curve = 'linear'):
    '''
    Calculate trajectory coordinates between two points or a point pairs
    '''
    #TODO: multiple trajectories, trajectory of multiple predefined points    
    distance = rc_distance(start_point,  end_point)
    number_of_steps = int(round(distance / spatial_resolution, 0))
    step_size = distance / number_of_steps    
    number_of_steps += 1
    if curve == 'linear':
        direction = rc_add(end_point, start_point, operation = '-')
        angle = numpy.arctan2(float(direction['row']), float(direction['col']))
        trajectory = []
        step_vector = cr((numpy.cos(angle) * step_size, numpy.sin(angle) * step_size))
        trajectory_row = []
        trajectory_col = []
        for step in range(number_of_steps):
            p = rc_add(start_point, rc_multiply_with_constant(step_vector, step))
            trajectory_row.append(float(p['row']))
            trajectory_col.append(float(p['col']))
        trajectory = rc(numpy.array([trajectory_row,trajectory_col]))
        return trajectory
        
    
#== Application management ==    
def system_command(command):
    pid = subprocess.Popen(command,  shell = False, stdout = subprocess.PIPE)
    return pid.communicate()[0]
    
def is_file_open(path):
    if os.name == 'nt':
        raise RuntimeError('This function is not supported on Windows operating system')
    else:
        res = system_command('lsof')
        return path in res

def class_name(object):
    name = str(object.__class__)
    return name.split('\'')[1]
    
def fetch_classes(basemodule, classname=None,  exclude_classtypes=[],  required_ancestors=[], direct=True):
    '''Looks for the specified class, imports it and returns as class instance.
    Use cases:
    1. just specify user, others left as default: returns all classes
    2. specify user and classname: returns specific class without checking its type
    3. specify user, classname and list of classes that should not be in the ancestor tree of the class
      In this case you can specify if required ancestors and excluded classtypes applies to the whole 
      method resolution order tree (whole ancestor tree) or just the direct ancestors.
    '''
    import visexpman
    bm=__import__(basemodule, fromlist='dummy')
    class_list=[]
    if not isinstance(required_ancestors, (list, tuple)): required_ancestors=[required_ancestors]
    if not isinstance(exclude_classtypes, (list, tuple)): exclude_classtypes=[exclude_classtypes]
    
    for importer, modname, ispkg in pkgutil.iter_modules(bm.__path__,  bm.__name__+'.'):
        try:
            m= __import__(modname, fromlist='dummy')
            for attr in inspect.getmembers(m, inspect.isclass):
                if direct:
                    omro = attr[1].__bases__
                else:
                    omro = inspect.getmro(attr[1])
                any_wrong_in_class_tree = [cl in omro for cl in exclude_classtypes]
                all_good_ancestors = [True for a in required_ancestors if a in omro]
                if sum(all_good_ancestors) < len(required_ancestors):
                    continue
                if sum(any_wrong_in_class_tree) >0: continue # the class hierarchy contains ancestors that should not be in this class' ancestor list
                # required_ancestors or exlude_classtypes conditions handled, we need to check if name is correct:
                if (attr[0] == classname or classname==None):
                    class_list.append((m, attr[1]))
                    # here we also could execute some test on the experiment which lasts very short time but ensures stimulus will run  
        except ImportError:
            pass
    #Filter experiment config list. In test mode, experiment configs are loaded only from automated_test_data. In application run mode
    #this module is omitted
    filtered_class_list = []
    for class_item in class_list:
        if unit_test_runner.TEST_test:
            filtered_class_list.append(class_item)
        elif not 'automated_test_data' in class_item[0].__name__ and not unit_test_runner.TEST_test:
            filtered_class_list.append(class_item)
    return filtered_class_list
    
def class_list_in_string(class_list):
    class_list_string = []
    for item in class_list:
        class_list_string.append(item[1].__name__)
    return class_list_string

def keep_closest_ancestors(class_list,  required_ancestors):
    '''From the result of fetch_classes method, if class_list contains multiple items, this routine
    keeps the class with closest ancestors. The result might not be a single class, in such a case 
    an exception is raised.'''
    if len(class_list)==1:
        return class_list[0] #nothing to do
    elif len(class_list)==0:
        raise ValueError('Empty list of classes')
    levels = [] #level value in the class tree, i.e. how many steps from the child class
    for a in required_ancestors:
        levels.append([])
        for c in class_list:
            for b in c[1].__bases__:
                mro = b.mro()
                if a in mro:
                    levels[-1].append(mro.index(a))
                    break #a class can appear only once in the MRO, no need to look further
                else:
                    pass #this was an ancestor of the class that needs not to be inspected since it was not listed in required_ancestors    
    # if for a class in class_list the required_ancestor is closest to the child class, then a 1 is put in this table: 
    eligible = numpy.zeros(numpy.array(levels).shape, numpy.bool) 
    for l1 in range(len(levels)): # go through required_ancestors' positions
        d_i = min(levels[l1])# minimum distance from the child class
        m_i = [i for i in range(len(class_list)) if levels[l1][i]==d_i] # for which classes is the required_ancestor closest to the child class?
        eligible[[l1]*len(m_i), m_i] = 1
    all_ancestors_closest = numpy.where(eligible.sum(axis=0) == len(required_ancestors))[0]
    if len(all_ancestors_closest)!=1:
        raise ValueError('There is no class in the list for which all of the required ancestors are closest to the child')
    return class_list[all_ancestors_closest]
    
def prepare_dynamic_class_instantiation(modules,  class_name):        
    """
    Imports the necessary module and returns a reference to the class that could be sued for instantiation
    """
    #import experiment class
    module_name = find_class_in_module(modules, class_name,  module_name_with_hierarchy = True)
    __import__(module_name)
    #get referece to class and return with it
    return getattr(sys.modules[module_name], class_name)
    
def find_class_in_module(modules,  class_name, module_name_with_hierarchy = False):
    '''
    Finds the module where a certain class declaration resides
    '''
    module_found = None
    class_declaration_strings = ['class ' + class_name,  'class  ' + class_name]
    for module in modules:
         module_content = read_text_file(module)
         for class_declaration_string in class_declaration_strings:
            if module_content.find(class_declaration_string) != -1:
                if module_name_with_hierarchy:
                    items = module.split(os.sep)                    
                    module_found = ''
                    for item in items:
                        stripped_from_extension = item.replace('.py', '')                        
                        if stripped_from_extension.replace('_', '').isalnum():
                            module_found = module_found + '.' + stripped_from_extension
                    module_found = module_found[1:]
                else:
                    module_found = module.split(os.sep)[-1].split('.')[0]
    return module_found
    
version_paths = {
    'Queue' : 'standard', 
    'socket': 'standard', 
    'SocketServer': 'standard', 
    'math': 'standard', 
    'time': 'standard', 
    'datetime': 'standard', 
    'timeit': 'standard', 
    'sys': 'version',
    'threading':  'standard', 
    'pkgutil': 'standard', 
    'pickle': 'standard', 
    'cPickle': 'standard', 
    'zipfile': 'standard', 
    'unittest': 'standard', 
    'os': 'standard', 
    'uuid': 'standard', 
    'logging': 'standard', 
    're': 'standard', 
    'random': 'standard', 
    'inspect': 'standard', 
    'shutil': 'standard', 
    'ctypes':'standard',
    'StringIO':'standard',
    'cStringIO':'standard',
    'io':'standard',
    'select':'standard',
    'hashlib':'standard',
    'traceback':'standard',
    'tempfile':'standard', 
    'multiprocessing':'standard', 
    'gc': 'standard',
    'contextlib' : 'standard', 
    'weakref' : 'standard', 
    'sip': 'SIP_VERSION_STR',     
    'copy' : 'standard', 
    'getpass' : 'standard', 
    'subprocess' : 'standard', 
    'numpy': 'version.version', 
    'scipy': 'version.version', 
    'Image': 'VERSION', 
    'ImageDraw': 'Image.VERSION', 
    'tables': '__version__', 
    'serial': 'VERSION', 
    'parallel': 'VERSION', 
    'PyQt4.QtCore':' QtCore.PYQT_VERSION_STR', 
    'OpenGL': 'version.__version__', 
    'pygame': 'version.ver', 
    'PyDAQmx' : '__version__',
    'celery' : '__version__',
    'pp' : 'version',
    'mahotas': 'version.version',
    'Helpers' : 'version', 
    'visexpman': 'version', 
    'visexpA': 'version', 
    'sklearn':'__version__',
    'Polygon':'__version__'
    }    
    
def imported_modules():
    '''
    - List of imported visexpman module paths
    - List of imported module names
    '''        
    import visexpman.engine.generic.parameter
    visexpman_modules = []
    module_names = []
    #stdlib = list_stdlib() this takes long
    for k, v in sys.modules.items():
        if 'visexpman' in k or 'visexpA' in k:
            if v == None:
                new_module_name = k.split('.')[-1]
                if not is_in_list(module_names, new_module_name):
                    module_names.append(new_module_name)
            else:
                new_module_path = v.__file__.replace('.pyc', '.py')
                if not is_in_list(module_names, new_module_path):
                    visexpman_modules.append(new_module_path)
    module_names.sort()
    visexpman_modules.sort()
    return module_names, visexpman_modules
    
def system_memory():
    if os.name == 'nt':
        try:
            import wmi
            comp = wmi.WMI()
            physical_memory = 0
            for i in comp.Win32_ComputerSystem():
                physical_memory = i.TotalPhysicalMemory
            free_memory = 0
            for os_ in comp.Win32_OperatingSystem():
                free_memory = os_.FreePhysicalMemory
            return physical_memory, free_memory
        except:
            return 0, 0
    else:
        return 0, 0
       
def module_versions(modules):    
    module_version = ''
    module_version_dict = {}
    for module in modules:
        __import__(module)        
        try:
            if version_paths[module] != 'standard':
                try:
                    version_path = version_paths[module].split('.')
                    version = getattr(sys.modules[module], version_path[0])
                    if not isinstance(version, str):                        
                        version = getattr(version, version_path[1])                        
                except AttributeError:
                    version = ''                
                module_version += '%s %s\n'%(module, version.replace('\n', ' '))
                module_version_dict[module] = version
            else:
                module_version_dict[module] = 'standard'
                module_version += '%s\n'%(module)
        except KeyError:
            pass
            #raise RuntimeError('This module is not in the version list: %s. Update list in utils.module_versions() function' % str(module))
    return module_version, module_version_dict

def execute_program(command):
    '''Executes a program and captures its output'''
    import subprocess
    import sys
    child = subprocess.Popen(command, shell=True, stderr=subprocess.PIPE)
    complete = False
    sout = ''
    while True:
        out = child.stderr.read(1)
        sout+=out
        if out == '' and child.poll() != None:
            break
        if out != '':
            sys.stdout.write(out)
            sys.stdout.flush()
    return sout
        
def list_stdlib():
    import distutils.sysconfig as sysconfig
    import os
    std_lib = sysconfig.get_python_lib(standard_lib=True)
    lib_members = []
    for top, dirs, files in os.walk(std_lib):
        if 'site_packages' in top or 'dist_packages' in top: continue
        for nm in files:
            if nm != '__init__.py' and nm[-3:] == '.py':
                lib_members.append(os.path.join(top, nm)[len(std_lib)+1:-3].replace('\\','.'))
    return lib_members

#object <-> numpy array
def array2object(numpy_array):
    return pickle.loads(numpy_array.tostring())
    
def object2array(obj):
    return numpy.fromstring(pickle.dumps(obj), numpy.uint8)
    
def object2hdf5(h, vn):
    if hasattr(h, vn):
        setattr(h, vn, object2array(getattr(h, vn)))
        h.save(vn, overwrite=True)
    return copy.deepcopy(getattr(h, vn))
    
def hdf52object(h, vn, default_value = None):
    h.load(vn)
    if hasattr(h, vn) and hasattr(getattr(h, vn), 'dtype'):
        return copy.deepcopy(array2object(getattr(h, vn)))
    else:
        return default_value
    


#== Experiment specific ==
def um_to_normalized_display(value, config):
    '''
    Converts um dimension data to normalized screen size where the screen range is between -1...1 for both axes and the origo is the center of the screen
    '''
    if not isinstance(value,  list):
        value = [value,  value]
    normalized_x = 2.0 * config.SCREEN_PIXEL_TO_UM_SCALE * float(value[0]) / config.SCREEN_RESOLUTION['col']
    normalized_y = 2.0 * config.SCREEN_PIXEL_TO_UM_SCALE * float(value[1]) / config.SCREEN_RESOLUTION['row']
    return [normalized_x,  normalized_y]

def retina2screen(widths, speed=None, machine_config=None, option=None):
    '''converts microns on retina to cycles per pixel on screen
    '''
    if machine_config.IMAGE_PROJECTED_ON_RETINA == 0:
        visualangles = um2degrees(widths) # 300um is 10 degrees
        #widthsonmonitor = tan(2*pi/360*visualangles)*monitor.distancefrom_mouseeye/monitor.pixelwidth #in pixels
        widthsonmonitor = numpy.pi/180*visualangles*machine_config.SCREEN_DISTANCE_FROM_MOUSE_EYE/machine_config.SCREEN_PIXEL_WIDTH #in pixels
        if not option is None and option=='pixels':
            return widthsonmonitor

        no_periods_onscreen = machine_config.SCREEN_RESOLUTION['col']/(widthsonmonitor*2)
        cyclesperpixel = no_periods_onscreen/machine_config.SCREEN_RESOLUTION['col']
        if speed is None:
            return cyclesperpixel
        else: # calculates cycles per second from width on retina and um per second on the retina
            onecycle_pix = 1/cyclesperpixel
            for i in range(len(widths)):
            # from micrometers/s on the retina to cycles per pixel on screen
                speedonmonitor[i] = numpy.pi/180*um2degrees(speed)*machine_config.SCREEN_DISTANCE_FROM_MOUSE_EYE/machine_config.SCREEN_PIXEL_WIDTH
                cyclespersecond[i] = speedonmonitor[i]/(widthsonmonitor[i]*2) # divide by period, i.e. width*2
                time4onecycle_onscreen[i] = (machine_config.SCREEN_RESOLUTION['col']/onecycle_pix[i])/cyclespersecond[i]
            return cyclesperpixel, time4onecycle_onscreen
    elif machine_config.IMAGE_PROJECTED_ON_RETINA==1:
        widthsonmonitor = widths/machine_config.SCREEN_UM_TO_PIXEL_SCALE
        no_periods_onscreen = machine_config.SCREEN_RESOLUTION['col']/(widthsonmonitor*2)
        if speed is None:
            cyclesperpixel = no_periods_onscreen/machine_config.SCREEN_RESOLUTION['col']
            return cyclesperpixel
        else: # calculates cycles per second from width on retina and um per second on the retina
            cyclesperpixel = no_periods_onscreen/machine_config.SCREEN_RESOLUTION['col']
            onecycle_pix = 1/cyclesperpixel
            for i in range(len(widths)):
            # from micrometers/s on the retina to cycles per pixel on screen
                speedonmonitor[i]= speed/monitor.um2pixels
                cyclespersecond[i] = speedonmonitor[i]/(widthsonmonitor[i]*2) # divide by period, i.e. width*2
                time4onecycle_onscreen[i,:] = (widthsonmonitor[i]*2)/speedonmonitor[i]#cyclespersecond(i,:)
            return cyclespersecond, time4onecycle_onscreen

def um2degrees(umonretina):
# given umonretina estimates the visual angle, based on 300um on the retina
# is 10 degrees
    return 10.0*numpy.array(umonretina, numpy.float)/300
    
#== Time /Date ==
def datetime_string():
    now = time.localtime()
    return ('%4i-%2i-%2i_%2i-%2i-%2i'%(now.tm_year,  now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min, now.tm_sec)).replace(' ', '0')

def date_string():
    now = time.localtime()
    return ('%4i-%2i-%2i'%(now.tm_year,  now.tm_mon, now.tm_mday)).replace(' ', '0')

def truncate_timestamps(list_of_timestamps,  at_position):
    '''From a list of floats representing timestamps, we calculates timestamps 
    with least significant data truncated. E.g. to get timestamps that contain only
   year_month_date but no hour, second, millisecond: set at_position=3
   '''
    timetuples = numpy.array([time.localtime(ts) for ts in list_of_timestamps])
    truncated_timestamps= [time.mktime(tt[:at_position].tolist()+[0]*(9-at_position)) for tt in timetuples] #timestamps made from timetuples where only year month day differs, rest is 0
    return truncated_timestamps

def time_stamp_to_hms(timestamp):
    time_struct = time.localtime(timestamp)
    return ('%2i:%2i:%2.1f'%(time_struct.tm_hour, time_struct.tm_min, time_struct.tm_sec + numpy.modf(timestamp)[0])).replace(' ', '0')
    
def time_stamp_to_hm(timestamp):
    time_struct = time.localtime(timestamp)
    return ('%2i:%2i'%(time_struct.tm_hour, time_struct.tm_min)).replace(' ', '0')
    
def timestamp2ymdhms(timestamp):
    time_struct = time.localtime(timestamp)
    return '{0}-{1}-{2}+{3:2}:{4:2}:{5:2}'.format(time_struct.tm_year, time_struct.tm_mon, time_struct.tm_mday, time_struct.tm_hour, time_struct.tm_min, time_struct.tm_sec).replace(' ','0').replace('+',' ')

def timestamp2ymdhm(timestamp):
    time_struct = time.localtime(timestamp)
    return '{0}-{1}-{2}+{3:2}:{4:2}'.format(time_struct.tm_year, time_struct.tm_mon, time_struct.tm_mday, time_struct.tm_hour, time_struct.tm_min).replace(' ','0').replace('+',' ')
    
class Timeout(object):
    def __init__(self, timeout, sleep_period = 0.01):
        self.start_time = time.time()
        self.timeout = timeout
        self.sleep_period = sleep_period
        
    def is_timeout(self):
        now = time.time()
        if now - self.start_time > self.timeout and self.timeout != -1:
            return True
        else:
            return False
            
    def wait_timeout(self, break_wait_function = None, *args):
        '''
        break_wait_function: shall not block and shall return with a boolean fielld
        Returns True if expected condition is True
        '''        
        result = False
        while True:
            if self.is_timeout():
                result = False                
                break
            elif  break_wait_function != None:                
                if break_wait_function(*args): 
                    result = True                   
                    break            
            time.sleep(self.sleep_period)
        return result
        
def periodic_caller(period, call, args = None, idle_time = 0.1):
    last_run = time.time()
    while True:
        now = time.time()
        if now - last_run >= period:
            last_run = now
            if args == None:
                if call():
                    break
            else:
                if call(*args):
                    break
        time.sleep(idle_time)

##### Queue #########
def empty_queue(queue):
    results = []
    while not queue.empty():
        results.append(queue.get())
    return results
    
def wait_data_appear_in_queue(queue, timeout):
    '''
    Waits till the empty queue receives an item considering timeout
    '''
    t = Timeout(timeout)
    return t.wait_timeout(_is_queue_not_empty, queue)
       
def is_abort_experiment_in_queue(queue, keep_in_queue = True):
    return is_keyword_in_queue(queue, 'abort_experiment', keep_in_queue)

def is_graceful_stop_in_queue(queue, keep_in_queue = True):
    return is_keyword_in_queue(queue, 'graceful_stop_experiment', keep_in_queue)

def is_keyword_in_queue(queue, keyword, keep_in_queue = True):
    result = False
    if hasattr(queue, 'empty'):
        queue_content = []
        while not queue.empty():
            command = queue.get()
            if keyword in command:
                result = True
                if keep_in_queue:
                    queue_content.append(command)
            else:
                queue_content.append(command)
        for queue_content_item in queue_content:
            queue.put(queue_content_item)
    return result
    
def _is_queue_not_empty(queue):
    return not queue.empty()
    
#== Signals ==
def interpolate_waveform(waveform, ratio):    
    waveform_interpolated = []    
    for sample in waveform:
        if len(waveform.shape) != 1:
            shape = (ratio, waveform.shape[1])
        else:
            shape = ratio
        waveform_interpolated.append(sample * numpy.ones(shape))
    waveform_interpolated = numpy.array(waveform_interpolated)
    if len(waveform.shape) != 1:
        shape = (ratio * waveform.shape[0], waveform.shape[1])
    else:
        shape = ratio * waveform.shape[0]
    waveform_interpolated = waveform_interpolated.reshape(shape)
        
    return waveform_interpolated
    
def resample_waveform(waveform, ratio):
    resampled_waveform = []
    if len(waveform.shape) == 1:
        resampled_waveform = waveform[::ratio]
    else:
        for channel in range(waveform.shape[1]):
            resampled_waveform.append(waveform[:,channel][::ratio])
        resampled_waveform = numpy.array(resampled_waveform).transpose()
            
    return resampled_waveform
    
def generate_pulse_train(offsets, pulse_widths, amplitudes, duration, sample_rate = None):
    '''
    offsets: pulse offsets in samples, always must be a list of a numpy array
    pulse_widths: width of pulses in samples, if single number is provided, all the pulses will have the same size
    amplitudes: amplitude of each pulse. If a float or and int is provied, it is assumed that all the pulses must have the same amplitude
    duration: duration of the whole pulse train in samples
    
    If sample_rate is not none, the offsets, the pulse_widths and the duration parameters are handled in time units
    '''    
    if isinstance(offsets, list):
        number_of_pulses = len(offsets)
    elif isinstance(offsets, numpy.ndarray):
        number_of_pulses = offsets.shape[0]
    else:
        raise RuntimeError('Invalid data provided as offset parameters')
    if sample_rate == None:
        _duration = int(duration)
    else:
        _duration = int(duration * sample_rate)        
        
    if isinstance(pulse_widths, float) or isinstance(pulse_widths, int):
        _pulse_widths = numpy.ones(number_of_pulses) * pulse_widths
    elif isinstance(pulse_widths, list):
        _pulse_widths = numpy.array(pulse_widths)
    else:
        _pulse_widths = pulse_widths
        
    if sample_rate != None:
        _pulse_widths = _pulse_widths * sample_rate       

    if isinstance(amplitudes, float) or isinstance(amplitudes, int):
        _amplitudes = numpy.ones(number_of_pulses) * amplitudes
    else:
        _amplitudes = amplitudes
    waveform = numpy.zeros(_duration, dtype = numpy.float)
    for pulse_index in range(number_of_pulses):
        pulse = numpy.ones(_pulse_widths[pulse_index]) * _amplitudes[pulse_index]
        if sample_rate != None:
            offset = int(offsets[pulse_index] * sample_rate)
        else:
            offset = int(offsets[pulse_index])
        if offset + _pulse_widths[pulse_index] > _duration or offset + 1 > _duration:
            raise RuntimeError('Last pulse falls outside the waveform')        
        waveform[offset: offset + _pulse_widths[pulse_index]] = pulse
        
    return waveform

def generate_waveform(waveform_type,  n_sample,  period,  amplitude,  offset = 0,  phase = 0,  duty_cycle = 0.5):
    wave = []
    period = int(period)
    for i in range(int(n_sample)):
        if period == 0:
            value = 0
        elif waveform_type == 'sin':
            value = 0.5 * amplitude * math.sin(2 * math.pi * float(i) / period + phase * (math.pi/180.0)) + offset
        elif waveform_type == 'cos':
            value = 0.5 * amplitude * math.cos(2 * math.pi * float(i) / period + phase * (math.pi/180.0)) + offset            
        elif waveform_type == 'sqr':
            actual_phase = (i + int(period * (phase / 360.0))) % period
            if actual_phase < duty_cycle * period:
                value = 0.5 * amplitude
            else:
                value = -0.5 * amplitude
            value = value + offset
        elif waveform_type == 'saw':
            actual_phase = (i + int(period * (phase / 360.0))) % period
            value = amplitude * (float(actual_phase) / float(period-1.0)) - 0.5 * amplitude + offset
        elif waveform_type == 'tri':
            actual_phase = (i + int(period * (phase / 360.0))) % period
            if actual_phase < 0.5 * period:
                value = amplitude * (float(actual_phase) / float(0.5*period)) - 0.5 * amplitude + offset
            else:
                value = -amplitude * (float(actual_phase) / float(0.5 * period)) + 1.5 * amplitude + offset
        else:
            value = 0
        wave.append(value)    
    return wave    

def pack_position(stagexyz, objective_z = None):
    if isinstance(objective_z, numpy.ndarray):
        if objective_z.shape == ():
            objective_z_to_save = objective_z
        else:
            objective_z_to_save = objective_z[0]
    else:
        objective_z_to_save = objective_z
    return numpy.array([(0, stagexyz[0], stagexyz[1], stagexyz[2], objective_z_to_save)], [('um',numpy.float64), ('x',numpy.float64),('y',numpy.float64),('z_stage',numpy.float64), ('z',numpy.float64)])
    
#== Others ==
def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]
        
def file_to_binary_array(path):
    if os.path.exists(path):
        return numpy.fromfile(str(path), dtype = numpy.uint8)        
    else:
        return numpy.zeros(2)
    
def in_range(number,  range1,  range2, precision = None):
    if precision != None:
        number_rounded = round(number, precision)
        range1_rounded = round(range1, precision)
        range2_rounded = round(range2, precision)
    else:
        number_rounded = number
        range1_rounded = range1
        range2_rounded = range2
        
    if range1_rounded < range2_rounded:
        if number_rounded >= range1_rounded and number_rounded <= range2_rounded:
            return True        
    else:
        if number_rounded >= range2_rounded and number_rounded <= range1_rounded:
            return True
    return False

def is_vector_in_array(array,  vector):
    '''
        Find a vector in a list of vectors
    '''
    for item in array:
        if abs(item - vector).sum() < 1e-3:
            return True
    return False

def is_in_list(list, item_to_find):
    result = [item for item in list if item == item_to_find]
    if len(result) > 0:
        return True
    else:
        return False
        
def is_substring_in_list(list, substring):
    result = [item for item in list if substring in item]
    if len(result) > 0:
        return True
    else:
        return False
def string_to_array(string):
    array = []
    for byte in list(string):
        array.append(ord(byte))
    return numpy.array(array)
    
def nan2value(inarray, value=numpy.nanmin):
    '''removes NaNs from input array and replaces with the minimum value'''
    if hasattr(value, 'func_name'):
        value = value(inarray)
    inarray[numpy.isnan(inarray)]=value
    return inarray

def nan2mask(inarray):
    '''Converts a numpy array with posibble nan values to a masked array that is masked where inarray
    contained nan values'''
    return numpy.ma.array(inarray, mask=numpy.isnan(inarray))

def enter_hit():
    i,o,e = select.select([sys.stdin],[],[],0.0001)
    for s in i:
        if s == sys.stdin:
            input = sys.stdin.readline()
            return True
    return False
    
def safe_has_key(var, key):
    result = False
    if hasattr(var, 'has_key'):
        if var.has_key(key):
            result = True
    return result


class TestUtils(unittest.TestCase):
    def setUp(self):
        pass
            
    def tearDown(self):
        pass

    def test_01_pulse_train(self):
        waveform_reference = numpy.array([10.0, 0.0, 10.0, 10.0, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        waveform = generate_pulse_train([0,2,4], [1,2,1], [10, 10, 10], 10)
        self.assertEqual(waveform_reference.tolist(), waveform.tolist())
        
    def test_02_pulse_train(self):
        waveform_reference = numpy.array([10.0, 0.0, 10.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0])
        waveform = generate_pulse_train([0,2,5], 1, 10, 9)
        self.assertEqual(waveform_reference.tolist(), waveform.tolist())
        
    def test_03_pulse_train(self):
        waveform_reference = numpy.array([10.0, 0.0, 10.0, 0.0, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        waveform = generate_pulse_train(numpy.array([0,2,4]), numpy.array([1,1,1]), numpy.array([10.0, 10.0, 10.0]), 10)
        self.assertEqual(waveform_reference.tolist(), waveform.tolist())

    def test_04_pulse_train(self):
        waveform_reference = numpy.array([10.0, 0.0, 20.0, 0.0, 10.0, 10.0, 0.0, 0.0, 0.0, 0.0])
        waveform = generate_pulse_train(numpy.array([0,2,4]), [1,1,2], numpy.array([10.0, 20.0, 10.0]), 10)
        self.assertEqual(waveform_reference.tolist(), waveform.tolist())
        
    def test_05_pulse_train(self):
        sample_rate = 1000.0
        waveform_reference = numpy.array([10.0, 0.0, 10.0, 10.0, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        waveform = generate_pulse_train([0,2/sample_rate,4/sample_rate], [1/sample_rate,2/sample_rate,1/sample_rate], [10, 10, 10], 10/sample_rate, sample_rate = sample_rate)
        self.assertEqual(waveform_reference.tolist(), waveform.tolist())
        
    def test_06_pulse_train(self):
        sample_rate = 1000.0    
        waveform_reference = numpy.array([10.0, 0.0, 10.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0])
        waveform = generate_pulse_train([0,2/sample_rate,5/sample_rate], 1/sample_rate, 10, 9/sample_rate, sample_rate = sample_rate)
        self.assertEqual(waveform_reference.tolist(), waveform.tolist())
        
    def test_07_pulse_train(self):
        sample_rate = 1000.0    
        waveform_reference = numpy.array([10.0, 0.0, 10.0, 0.0, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        waveform = generate_pulse_train(numpy.array([0,2/sample_rate,4/sample_rate]), numpy.array([1/sample_rate,1/sample_rate,1/sample_rate]), numpy.array([10.0, 10.0, 10.0]), 10/sample_rate, sample_rate = sample_rate)
        self.assertEqual(waveform_reference.tolist(), waveform.tolist())

    def test_08_pulse_train(self):
        sample_rate = 1000.0    
        waveform_reference = numpy.array([10.0, 0.0, 20.0, 0.0, 10.0, 10.0, 0.0, 0.0, 0.0, 0.0])
        waveform = generate_pulse_train(numpy.array([0,2/sample_rate,4/sample_rate]), [1/sample_rate,1/sample_rate,2/sample_rate], numpy.array([10.0, 20.0, 10.0]), 10/sample_rate, sample_rate = sample_rate)
        self.assertEqual(waveform_reference.tolist(), waveform.tolist())

    def test_09_pulse_train(self):
        self.assertRaises(RuntimeError, generate_pulse_train, 1, 1, 1, 1)

    def test_10_pulse_train(self):
        self.assertRaises(RuntimeError, generate_pulse_train, numpy.array([0,2,4]), [1,1,1], numpy.array([10.0, 20.0, 10.0]), 4)
        
    def test_11_pulse_train(self):
        self.assertRaises(RuntimeError, generate_pulse_train, numpy.array([0,2,4]), [1,1,2], numpy.array([10.0, 20.0, 10.0]), 5)
    
    def test_12_rcd_pack(self):
        data = numpy.array(1)
        self.assertRaises(RuntimeError, rcd_pack, data, dim_order = [0, 1, 2])
    
    def test_13_rcd_pack(self):
        data = numpy.array([1, 2])
        self.assertRaises(RuntimeError, rcd_pack, data, dim_order = [0, 1, 2])
        
    def test_14_rcd_pack(self):
        results = []
        for d in range(2, 4):
            data =numpy.ones((4, d), numpy.uint16)
            if d>0:
                for d1 in range(1, 4):
                    data[0] = d1*data[0]
                if d>1:
                    for d2 in range(2, 4):
                        data[0, 0]=10*d2*data[0, 0]
            results.append([nd(rcd_pack(data, dim_order = range(d))), data])
        self.assertTrue(numpy.all((item[0]==item[1]).all() for item in results))
        pass
        
    def test_15_rcd_pack(self):
        data = (1, 2)
        rc_value = rc(data)
        self.assertEqual((rc_value['row'], rc_value['col']), data)
         
            
    def test_numpy_circles(self):
        pars = [ [[10, 25], (rc((1, 1)), rc((25, 25))), (64, 64), 255],  #
                        [[10, 25],  (rc((64-1, 64-1)), rc((64-25, 64-25))), (64, 64), 255],   # odd radius, single center
                        ]
        for p in pars:
            img = numpy_circles(p[0], p[1], p[2], p[3])
            pass
            
if __name__ == "__main__":
    #commented out by Daniel:
    #start_point = cr((0.0, 0.0))
    #end_point = cr((10.0, 10.0))
    #spatial_resolution =2.5
#    print rc_add(start_point, end_point)
    #print calculate_trajectory(start_point,  end_point,  spatial_resolution)
#    l = [1, 2, 3]
#    imported_modules()
# temp solution by Daniel:
    
#    class Test(unittest.TestCase):
#        def setUp(self):
#            pass
#            
#        def tearDown(self):
#            pass
#
#        def test_parsefilename(self):
#            filename = 'whatever/folder/Bl6(b 04.09.10 i 01.11.10)-(-372 -78 129)-r2-w1000-sp2400-3stat-3move-2.0x-20x(ND10 isoflCP 0.5 R).tif.frames'
#            commonpars = {'AnimalStrain':['^(\S+)\(', str], # Match M???(... at the beginning of the line
#                            'AnimalBirthDay_YMD':['\(b\S*\ (\d{2,2})\.(\d{2,2})\.(\d{2,2})\ ', int],
#                            'Injected_YMD':['i\S*\ (\d{2,2})\.(\d{2,2})\.(\d{2,2})\ *\)', int],
#                            'StagePos':['\((-*\d+\.*\d*)\ +(-*\d+\.*\d*)',float], # (x y # lookahead assertion needed?
#                            'Depth':['\ +(\d+\.*\d*)\)',float], # z)
#                            'Repetition':['-r(\d+)-',int], #-r??
#                            'StimulusName':['-r\d+-(\S+)-\d\.\d+mspl',str], #-r??-string
#                            'Objective':['-*(\d+)x\(',int],
#                            'Comments':['^M\d+(\S+)\(',str],
#                            'Anesthesia':['ND\d\d*\ (\S+\ *\S*)\ \S+\)$',str],
#                                          }
#            stimpar = file.parsefilename(filename, commonpars)
#            result = {'AnimalStrain':['Bl6'], # Match M???(... at the beginning of the line
#                            'AnimalBirthDay_YMD':[4, 9, 10],
#                            'Injected_YMD':[1, 11, 10],
#                            'StagePos':[-372, -78], # (x y # lookahead assertion needed?
#                            'Depth':[129.0], # z)
#                            'Repetition':[2], #-r??
#                            'StimulusName':['w1000-sp2400-3stat-3move'], #-r??-string
#                            'Objective':[20],
#                            'Comments':['isoflCP 0.5 R'],
#                            'Anesthesia':['isoflCP 0.5']
#                                          }
#            self.assertequal(stimpar, result)
#            
#        def test_getziphandler(self):
#            pass
#
#        def test_fetch_classes(self):
#            class GrandMother(object):
#                pass
#            class GrandFather(object):
#                pass
#            class Father(GrandMother, GrandFather):
#                pass
#            class Mother(GrandMother):
#                pass
#            class Boy(Mother):
#                pass
#            self.assertEqual(fetch_classes('visexpman.engine.generic', required_ancestors=[GrandMother, GrandFather], direct=False),1 )

            
    mytest = unittest.TestSuite()
    mytest.addTest(TestUtils('test_numpy_circles'))
    mytest.addTest(TestUtils('test_01_pulse_train'))
    mytest.addTest(TestUtils('test_02_pulse_train'))
    mytest.addTest(TestUtils('test_03_pulse_train'))
    mytest.addTest(TestUtils('test_04_pulse_train'))
    mytest.addTest(TestUtils('test_05_pulse_train'))
    mytest.addTest(TestUtils('test_06_pulse_train'))
    mytest.addTest(TestUtils('test_07_pulse_train'))
    mytest.addTest(TestUtils('test_12_rcd_pack'))
    mytest.addTest(TestUtils('test_13_rcd_pack'))
    mytest.addTest(TestUtils('test_14_rcd_pack'))
    mytest.addTest(TestUtils('test_15_rcd_pack'))
    alltests = unittest.TestSuite([mytest])
    #suite = unittest.TestLoader().loadTestsFromTestCase(Test)
    unittest.TextTestRunner(verbosity=2).run(alltests)
