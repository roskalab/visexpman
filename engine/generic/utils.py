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
import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner
import tempfile
import copy

#== Computer graphics colors ==
def convert_color(color):
    '''
    Any color format (rgb, greyscale, 8 bit grayscale) is converted to visexpman rgb format
    '''    
    if isinstance(color, float):
        converted_color = [color, color, color]
    elif isinstance(color, int):
        converted_color = [color/255.0, color/255.0, color/255.0]
    else:
        converted_color = color
    return converted_color

def convert_color_from_pp(color_pp):
    '''
    convert color from psychopy format to Presentinator default format (0...1 range)
    '''
    color = []
    for color_pp_channel in color_pp:
        color.append(0.5 * (color_pp_channel + 1.0))
    return color
    
def convert_int_color(color):
    '''
    Rgb color is converted to 8 bit rgb
    '''    
    if isinstance(color,  list):
        return (int(color[0] * 255.0),  int(color[1] * 255.0),  int(color[2] * 255.0))
    else:
        return (int(color * 255.0),  int(color * 255.0),  int(color * 255.0))
        
def random_colors(n,  frames = 1,  greyscale = False,  inital_seed = 0):
    '''
    Renerates random colors
    '''    
    random.seed(inital_seed)
    col = []
    if frames == 1:
        for i in range(n):
            r = random.random()
            g = random.random()
            b = random.random()
            if greyscale:
                g = r
                b = r
            col.append([r,g,b])
    else:
        for f in range(frames):
            c = []
            for i in range(n):
                r = random.random()
                g = random.random()
                b = random.random()
                if greyscale:
                    g = r
                    b = r
                c.append([r,g,b])
            col.append(c)
    return col

#== Coordinate geometry ==
#TODO: check for redundant functions in this section

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

def nd(rcarray):
    '''Convenience function to convert a recarray to nd array'''
    return rcarray.view((rcarray[rcarray.dtype.names[0]].dtype,len(rcarray.dtype.names)))

def rcd(raw):
    return rcd_pack(raw, dim_order = [0, 1, 2])
    
def rc(raw):
    return rcd_pack(raw, dim_order = [0, 1])

def cr(raw):
    return rcd_pack(raw, dim_order = [1, 0])    
            
def rcd_pack(raw, dim_order = [0, 1]):
    dim_names0 = ['row','col','depth']
    dim_names = [dim_names0[n] for n in dim_order]
    raw = numpy.array(raw, ndmin=2)
    if numpy.squeeze(raw).ndim!=2 and raw.size!=len(dim_names): #1 dimensional with exactly 2 values is accepted as row,col pair
        raise RuntimeError('At least '+ str(len(dim_names)) +' values are needed')
    dtype={'names':dim_names,'formats':[raw.dtype]*len(dim_names)}
    if raw.ndim > len(dim_names):
        raise TypeError('Input data dimension must be '+str(len(dim_names))+' Call rc_flatten if you want data to be flattened before conversion')
    if raw.ndim==2 and raw.shape[1]==len(dim_names): # convenience feature: user must not care if input shape is (2,x) or (x,2)  we convert to the required format (2,x)
        raw=raw.T    
    if raw.size == len(dim_names):
        return numpy.array(tuple(raw), dtype)
    else:
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

def rc_multiply_with_constant(rc_value, constant):
    if rc_value.shape == ():
            return rc((rc_value['row'] * constant, rc_value['col'] * constant))
    else:
            rows = rc_value[:]['row'] * constant
            cols = rc_value[:]['col'] * constant
            return rc(numpy.array([rows, cols]))
    
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
    
def rc_distance(point1,  point2):
    return numpy.sqrt((point1['col']-point2['col'])**2 + (point1['row']-point2['row'])**2)
    
def calculate_trajectory(start_point,  end_point,  spatial_resolution,  curve = 'linear'):
    '''
    Calculate trajectory coordinates between two points or a point pairs
    '''
    #TODO: multiple trajectories, trajectory of multiple predefined points    
    distance = rc_distance(start_point,  end_point)
    number_of_steps = int(round(distance / spatial_resolution, 0))
    step_size = distance / number_of_steps    
    if curve == 'linear':
        direction = rc_add(end_point, start_point, operation = '-')
        angle = numpy.arctan(float(direction['row'])/float(direction['col']))
        trajectory = []
        step_vector = cr((numpy.cos(angle) * step_size, numpy.sin(angle) * step_size))
        for step in range(number_of_steps):
            trajectory.append(rc_add(start_point, rc_multiply_with_constant(step_vector, step)))
        trajectory = numpy.array(trajectory)
        return trajectory
        
    
#== Application management ==    
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
                
    #Filter experiment config list. In test mode, experiment configs are loaded only from automated_test_data. In application run mode
    #this module is omitted
    filtered_class_list = []
    for class_item in class_list:
        if (class_item[0].__name__.find('automated_test_data') != -1 or \
        class_item[0].__name__.find('presentinator_experiment') != -1 or\
        class_item[0].__name__.find('default_configs') != -1) and unit_test_runner.TEST_test:
            filtered_class_list.append(class_item)
        elif not class_item[0].__name__.find('automated_test_data') != -1 and not unit_test_runner.TEST_test:
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
    'visexpman': 'version', 
    'visexpA': 'version', 
    'math': 'standard', 
    'time': 'standard', 
    'sys': 'version',     
    'ImageDraw': 'Image.VERSION', 
    'threading':  'standard', 
    'numpy': 'version.version', 
    'Image': 'VERSION', 
    'pkgutil': 'standard', 
    'zipfile': 'standard', 
    'unittest': 'standard', 
    'os': 'standard', 
    'pygame': 'version.ver', 
    'logging': 'standard', 
    're': 'standard', 
    'OpenGL': 'version.__version__', 
    'parallel': 'VERSION', 
    'random': 'standard', 
    'inspect': 'standard', 
    'serial': 'VERSION', 
    'PyQt4':' QtCore.QT_VERSION_STR', 
    'scipy': 'version.version', 
    'shutil': 'standard', 
    'tempfile':'standard', 
    'multiprocessing':'standard', 
    'gc': 'standard',
    'PyDAQmx' : '__version__',
    'contextlib' : 'standard', 
    'weakref' : 'standard', 
    'sip': 'SIP_VERSION_STR', 
    'Helpers' : 'version', 
    'copy' : 'standard'
    
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
        if k.find('visexpman') != -1 or k.find('visexpA') != -1:
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
    return [module_names, visexpman_modules]
    
def module_versions(modules):    
    module_version = ''
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
            else:
                module_version += '%s\n'%(module)
        except KeyError:
            pass
            #raise RuntimeError('This module is not in the version list: %s. Update list in utils.module_versions() function' % str(module))
    return module_version


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
    
#== File(name) operations ==

def find_files_and_folders(start_path,  extension = None, filter = None):
        '''
        Finds all folders and files. With extension the files can be filtered
        '''
        directories = []
        all_files  = []
        directories = []
        for root, dirs, files in os.walk(start_path):            
            for dir in dirs:
                directories.append(root + os.sep + dir)
            for file in files:
                if extension != None:
                    if file.split('.')[1] == extension:
                        all_files.append(root + os.sep + file)
                elif filter != None:
                    if filter in file:
                        all_files.append(root + os.sep + file)
                else:                        
                    all_files.append(root + os.sep + file)    
        return directories, all_files

def getziphandler(zipstream):
    '''convenience wrapper that returns the zipreader object for both a byte array and a string containing 
    the filename of the zip file'''
    import StringIO,  zipfile
    if hasattr(zipstream, 'data'):
        sstream = StringIO.StringIO(zipstream.data) # zipfile as byte stream
    else:
        sstream = zipstream #filename
    return zipfile.ZipFile(sstream)

def parsefilename(filename, regexdict):
    '''From a string filename extracts fields as defined in a dictionary regexdict. 
    Data will be put into a directory with the same keys as found in regextdict.
    The value of each regextdict key must be a list. The first element of the list
    is a regular expression that tells what to extract from the string. The second element
    is a python class that is used to convert the extracted string into a number (if applicable)
    '''
    import re
    for k,v in regexdict.items():
        for expr in v[:-1]: #iterate through possible patterns (compatibility patters for filename structured used earlier)
            p = re.findall(expr,filename)
        if p:
            if isinstance(p[0], tuple): #stagepos extracts a tuple
                p = p[0]
            try:
                regexdict[k] = [v[-1](elem) for elem in p] # replace the regex pattern with the value
            except TypeError:
                raise
        else:
            regexdict[k] = None # this pattern was not found
    return regexdict

def filtered_file_list(folder_name,  filter, fullpath = False):
    files = os.listdir(folder_name)
    filtered_files = []
    for file in files:
        if isinstance(filter,  list) or isinstance(filter,  tuple):
            found  = False
            for filter_item in filter:                
                if file.find(filter_item) != -1:
                    found = True
            if found:
                if fullpath:
                    filtered_files.append(os.path.join(folder_name, file))
                else:
                    filtered_files.append(file)
        elif isinstance(filter,  str):
            if file.find(filter) != -1:
                if fullpath:
                    filtered_files.append(os.path.join(folder_name, file))
                else:
                    filtered_files.append(file)
    return filtered_files

def read_text_file(path):
    f = open(path,  'rt')
    txt =  f.read(os.path.getsize(path))
    f.close()            
    return txt

def listdir_fullpath(folder):
    files = os.listdir(folder)
    full_paths = []
    for file in files:
        full_paths.append(os.path.join(folder,  file))
    return full_paths
    
def find_latest(path):
    number_of_digits = 5
    latest_date = 0
    latest_file = ''
    for file in listdir_fullpath(os.path.split(path)[0]):
        if file.find(os.path.split(path)[-1].split('.')[0][:-number_of_digits]) != -1:
            file_date = os.path.getmtime(file)
            if latest_date < file_date:
                latest_date = file_date
                latest_file = file
    return latest_file
    
    
def generate_filename(path, insert_timestamp = False):
    '''
    Inserts index into filename resulting unique name.
    '''    
    index = 0
    number_of_digits = 5
    while True:
        testable_path = path.replace('.',  '_%5i.'%index).replace(' ', '0')
        if not os.path.isfile(testable_path):
            break
        index = index + 1
        if index >= 10 ** number_of_digits:
            raise RuntimeError('Filename cannot be generated')
    if insert_timestamp:
        testable_path = path.replace('.',  '_%i_%5i.'%(int(time.time()), index)).replace(' ', '0')
    return testable_path
    
def generate_foldername(path):
    '''
    Inserts index into foldername resulting unique name.
    '''
    number_of_digits = 5
    index = 0
    while True:
        testable_path = (path + '_%5i'%index).replace(' ', '0')
        if not os.path.isdir(testable_path):
            break
        index = index + 1
        if index >= 10 ** number_of_digits:
            raise RuntimeError('Foldername cannot be generated')
    return testable_path

def convert_path_to_remote_machine_path(local_file_path, remote_machine_folder, remote_win_path = True):
    filename = os.path.split(local_file_path)[-1]
    remote_file_path = os.path.join(remote_machine_folder, filename)
    if remote_win_path:
        remote_file_path = remote_file_path.replace('/',  '\\')
    return remote_file_path

#== Time /Date ==
def datetime_string():
    now = time.localtime()
    return ('%4i-%2i-%2i_%2i-%2i-%2i'%(now.tm_year,  now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min, now.tm_sec)).replace(' ', '0')

def date_string():
    now = time.localtime()
    return ('%4i-%2i-%2i'%(now.tm_year,  now.tm_mon, now.tm_mday)).replace(' ', '0')
    
def time_stamp_to_hms(timestamp):
    time_struct = time.localtime(timestamp)
    return ('%2i:%2i:%2.3f'%(time_struct.tm_hour, time_struct.tm_min, time_struct.tm_sec + numpy.modf(timestamp)[0])).replace(' ', '0')
    
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
        
def wait_data_appear_in_queue(queue, timeout):
    '''
    Waits till the empty queue receives an item considering timeout
    '''
    t = Timeout(timeout)
    return t.wait_timeout(_is_queue_not_empty, queue)

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
    amplitudes: amplitude of each pulse. If a float or and int is provied, it is aasumed that all the pulses must have the same amplitude
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
    
#== Saving data to hdf5 ==
def save_config(hdf5, machine_config, experiment_config = None):
    hdf5.machine_config = copy.deepcopy(machine_config.get_all_parameters()) #The deepcopy is necessary to avoid conflict between daqmx and hdf5io
    hdf5.save('machine_config')
    hdf5.experiment_config = experiment_config.get_all_parameters()
    hdf5.save('experiment_config')
    
def save_position(hdf5, stagexyz, objective_z = None):
    '''
    z is the objective's position, since this is more frequently used than z_stage.
    '''
    if isinstance(objective_z, numpy.ndarray):
        objective_z_to_save = objective_z[0]
    else:
        objective_z_to_save = objective_z
    hdf5.position = numpy.array([(0, stagexyz[0], stagexyz[1], stagexyz[2], objective_z_to_save)], [('um',numpy.float64), ('x',numpy.float64),('y',numpy.float64),('z',numpy.float64), ('z_stage',numpy.float64)])
    hdf5.save('position')

#== Others ==
def empty_queue(queue):
    results = []
    while not queue.empty():
        results.append(queue.get())
    return results
def file_to_binary_array(path):
    if os.path.exists(path):
        return numpy.fromfile(path, dtype = numpy.uint8)        
    else:
        return numpy.zeros(2)
        
def string_to_binary_array(s):
    binary_in_bytes = []
    for byte in list(s):
        binary_in_bytes.append(ord(byte))
    return numpy.array(binary_in_bytes, dtype = numpy.uint8)
    
        
    
def in_range(number,  range1,  range2, preceision = None):
    if preceision != None:
        number_rounded = round(number, preceision)
        range1_rounded = round(range1, preceision)
        range2_rounded = round(range2, preceision)
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
            data = numpy.ones((4, d, ), numpy.uint16)
            if d>0:
                for d1 in range(1, 4):
                    data[0] = d1*data[0]
                if d>1:
                    for d2 in range(2, 4):
                        data[0, 0]=10*d2*data[0, 0]
            results.append(nd(rcd_pack(data, dim_order = range(d))))
        self.assertTrue(numpy.all(item) for item in results)    
        pass
        
    def test_15_rcd_pack(self):
        data = (1, 2)
        rc_value = rc(data)
        self.assertEqual((rc_value['row'], rc_value['col']), data)
                
if __name__ == "__main__":
    start_point = cr((0.0, 0.0))
    end_point = cr((10.0, 10.0))
    spatial_resolution =2.5
#    print rc_add(start_point, end_point)
    print calculate_trajectory(start_point,  end_point,  spatial_resolution)
#    l = [1, 2, 3]
#    imported_modules()
# temp solution by Daniel:
    
    class Test(unittest.TestCase):
        def setUp(self):
            pass
            
        def tearDown(self):
            pass

        def test_parsefilename(self):
            filename = 'whatever/folder/Bl6(b 04.09.10 i 01.11.10)-(-372 -78 129)-r2-w1000-sp2400-3stat-3move-2.0x-20x(ND10 isoflCP 0.5 R).tif.frames'
            commonpars = {'AnimalStrain':['^(\S+)\(', str], # Match M???(... at the beginning of the line
                            'AnimalBirthDay_YMD':['\(b\S*\ (\d{2,2})\.(\d{2,2})\.(\d{2,2})\ ', int],
                            'Injected_YMD':['i\S*\ (\d{2,2})\.(\d{2,2})\.(\d{2,2})\ *\)', int],
                            'StagePos':['\((-*\d+\.*\d*)\ +(-*\d+\.*\d*)',float], # (x y # lookahead assertion needed?
                            'Depth':['\ +(\d+\.*\d*)\)',float], # z)
                            'Repetition':['-r(\d+)-',int], #-r??
                            'StimulusName':['-r\d+-(\S+)-\d\.\d+mspl',str], #-r??-string
                            'Objective':['-*(\d+)x\(',int],
                            'Comments':['^M\d+(\S+)\(',str],
                            'Anesthesia':['ND\d\d*\ (\S+\ *\S*)\ \S+\)$',str],
                                          }
            stimpar = parsefilename(filename, commonpars)
            result = {'AnimalStrain':['Bl6'], # Match M???(... at the beginning of the line
                            'AnimalBirthDay_YMD':[4, 9, 10],
                            'Injected_YMD':[1, 11, 10],
                            'StagePos':[-372, -78], # (x y # lookahead assertion needed?
                            'Depth':[129.0], # z)
                            'Repetition':[2], #-r??
                            'StimulusName':['w1000-sp2400-3stat-3move'], #-r??-string
                            'Objective':[20],
                            'Comments':['isoflCP 0.5 R'],
                            'Anesthesia':['isoflCP 0.5']
                                          }
            self.assertequal(stimpar, result)
            
        def test_getziphandler(self):
            pass

        def test_fetch_classes(self):
            class GrandMother(object):
                pass
            class GrandFather(object):
                pass
            class Father(GrandMother, GrandFather):
                pass
            class Mother(GrandMother):
                pass
            class Boy(Mother):
                pass
            self.assertEqual(fetch_classes('visexpman.engine.generic', required_ancestors=[GrandMother, GrandFather], direct=False),1 )

            
    mytest = unittest.TestSuite()
    mytest.addTest(Test('test_fetch_classes'))
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
