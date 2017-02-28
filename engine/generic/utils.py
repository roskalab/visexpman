import sys
import math
import random
import numpy
import os.path
import os
import time
import datetime
import unittest
import pkgutil
import inspect
import unittest
import tempfile
import copy
import select
import subprocess
import cPickle as pickle
import zlib
import urllib2
try:
    import blosc as compressor
except ImportError:
    import zlib as compressor
if os.name == 'nt':
    try:
        import win32process
        import win32api
    except ImportError:
        pass
ENABLE_COMPRESSION=False
import fileop
import introspect
import platform

def is_network_available():
    if platform.system() == 'Windows':
        try:
            proxy = urllib2.ProxyHandler({'http': 'iproxy.fmi.ch:8080'})
            opener = urllib2.build_opener(proxy)
            urllib2.install_opener(opener)
            urllib2.urlopen('http://www.google.com')
            return True
        except:
            return False
    elif platform.system() == 'Linux' or platform.system()=='Darwin':
        try:
            response=urllib2.urlopen('http://gnu.org',timeout=1)
            return True
        except :
            return False
    else:
        raise NotImplementedError('')
        
def get_ip():
    '''
    Assuming that internet connection is available
    '''
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    addresses =['rzws.fmi.ch', 'google.com', '127.0.0.1']#Assuming to be in FMI, otherwise assuming connected to internet, finally trying localhost
    for address in addresses:
        try:
            s.connect((address, 0))
            break
        except:
            continue
    return s.getsockname()[0]
        
def resample_array(array, factor):
    '''
    Increases sampling rate of array with factor
    '''
    if factor == 1:
        return arrayutils.py
    else:
        return numpy.array([array]*int(factor)).flatten('F')
    
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

def get_window_title(config):
    from visexpman.engine import MachineConfigError
    if not hasattr(config, 'user_interface_name'):
        raise MachineConfigError('user_interface_name is missing from config')
    if not config.USER_INTERFACE_NAMES.has_key(config.user_interface_name):
        raise MachineConfigError('Unknown application name: {0}' .format(config.user_interface_name))
    return '{0} - {1} - {2}' .format(config.USER_INTERFACE_NAMES[config.user_interface_name], config.user, config.__class__.__name__)

#== Coordinate geometry ==
#TODO: check for redundant functions in this section
def roi_center(roi):
    return rc((roi['row'].mean(), roi['col'].mean()))
    
def toRGBarray(array):
    rgb_array = numpy.array([array, array, array])
    rgb_array = numpy.rollaxis(rgb_array, 0, len(array.shape))
    return rgb_array

def coordinate_system(type, SCREEN_RESOLUTION=None):
    '''looks up proper settings for commonly used coordinate system conventions'''
    if type=='ulcorner':
        if SCREEN_RESOLUTION == None: raise ValueError('Screen resolution is needed for converting to upper-left corner origo coordinate system.')
        ORIGO = cr((-0.5 * SCREEN_RESOLUTION['col'], 0.5 * SCREEN_RESOLUTION['row']))
        HORIZONTAL_AXIS_POSITIVE_DIRECTION = 'right'
        VERTICAL_AXIS_POSITIVE_DIRECTION = 'down'
        UPPER_LEFT_CORNER = rc((0,0))
    elif type=='center':
        ORIGO = cr((0, 0))
        HORIZONTAL_AXIS_POSITIVE_DIRECTION = 'right'
        VERTICAL_AXIS_POSITIVE_DIRECTION = 'up'
        UPPER_LEFT_CORNER = cr((-0.5 * SCREEN_RESOLUTION['col'], 0.5 * SCREEN_RESOLUTION['row']))
    else:
        raise ValueError('Coordinate system type '+type+' not recognized')
    return ORIGO, HORIZONTAL_AXIS_POSITIVE_DIRECTION, VERTICAL_AXIS_POSITIVE_DIRECTION, UPPER_LEFT_CORNER
    
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
        in_pixel = rc(((data['row']-origin['row'])/scale['row'], (data['col']-origin['col'])/scale['col']))
    return in_pixel
    
def pixel2um(data, origin, scale):
    in_um = rc((data['row']*scale['row'] + origin['row'],data['col']*scale['col']+origin['col']))
    return in_um

def argsort(seq):
    '''same as numpy.argsort but works on sequences'''
    #http://stackoverflow.com/questions/3382352/equivalent-of-numpy-argsort-in-basic-python/3382369#3382369
    #by ubuntu
    return sorted(range(len(seq)), key=seq.__getitem__)
    
def inrange(val, min, max):
    if hasattr(val, 'dtype') and ((val >= min).all() and (val <= max).all()):
        return True
    elif val >= min and val <= max:
       return True
    return False
        
    
def nd(rcarray, squeeze=False, dim_order=None,tuples=0):
    '''Convenience function to convert a recarray to nd array'''
    if dim_order is None: dim_order = [0, 1, 2]
    dim_names4current_data = dim_names0[:len(rcarray.dtype.names)]
    names_in_order = [dim_names4current_data[dim_order[di]]  for di in range(len(rcarray.dtype.names))]
    if rcarray.dtype.names !=names_in_order: # fields are not ordered in the default order
        res = numpy.c_[[rcarray[f] for f in names_in_order]].T # take field by field in the default order
    else: # faster way
        res= rcarray.view((rcarray[rcarray.dtype.names[0]].dtype,len(rcarray.dtype.names)))
    if squeeze or rcarray.ndim==0:
        res=numpy.squeeze(res)
    if tuples: #gives back list of tuples on which set operations can be performed
        res = [tuple(item) for item in res]
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

def rc_x_const(rc_value, constant):
    if rc_value.shape == ():
            return rc((rc_value['row'] * constant, rc_value['col'] * constant))
    else:
            rows = rc_value[:]['row'] * constant
            cols = rc_value[:]['col'] * constant
            return rc(numpy.array([rows, cols]))
            
def rc_multiply_with_constant(rc_value, constant):#Obsolete
    return rc_x_const(rc_value, constant)
            
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
            p = rc_add(start_point, rc_x_const(step_vector, step))
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
            print modname
            import traceback
            print traceback.format_exc()
    #Filter experiment config list. In test mode, experiment configs are loaded only from automated_test_data. In application run mode
    #this module is omitted
    filtered_class_list = []
    test_running = introspect.is_test_running()
    for class_item in class_list:
        #If unit test or batch of unit tests (unittest_aggregator) is run, add fetch all machine configs, otherwise omit automated_test_data module.
        if test_running:
            filtered_class_list.append(class_item)
        elif not 'automated_test_data' in class_item[0].__name__:
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
    'PIL': 'VERSION', 
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
    'visexpman': 'version', 
    'visexpA': 'version', 
    'sklearn':'__version__',
    'Polygon':'__version__',
    'blosc': '__version__',
    'zmq': '__version__',
    'psutil': '__version__',
    'PIL': 'VERSION',
    'argparse': '__version__',
    'optparse': '__version__',
    'matplotlib': '__version__',
    'zlib': '__version__',
    'json': '__version__',
    'simplejson': '__version__',
    'struct': 'standard',
    'warnings': 'standard',
    'glob': 'standard',
    'pdb': 'standard',
    'itertools': 'standard',
    'functools': 'standard',
    'platform': 'standard',
    'getpass': 'standard',
    'blosc': 'TBD',
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
                    if not isinstance(version, str) and not isinstance(version, unicode):
                        if callable(getattr(version, version_path[1])):
                            version = getattr(version, version_path[1])()
                        else:
                            version = getattr(version, version_path[1])
                except AttributeError:
                    version = 'unknown'
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
def object2str(obj):
    if ENABLE_COMPRESSION:
        return compressor.compress(pickle.dumps(obj, 2),6)
    else:
        return pickle.dumps(obj, 2)

def str2object(string):
    if ENABLE_COMPRESSION:
        return pickle.loads(compressor.decompress(string))
    else:
        return pickle.loads(string)

def array2object(numpy_array):
    if ENABLE_COMPRESSION:
        return pickle.loads(compressor.decompress(numpy_array.tostring()))
    else:
        try:
            return pickle.loads(numpy_array.tostring())
        except:
            return pickle.loads(compressor.decompress(numpy_array.tostring()))
    
def object2array(obj):
    return numpy.fromstring(object2str(obj), numpy.uint8)
        
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
    if machine_config.IMAGE_DIRECTLY_PROJECTED_ON_RETINA == 0:
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
    elif machine_config.IMAGE_DIRECTLY_PROJECTED_ON_RETINA==1:
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
def datetime_string(separator = '-', datetime_separator='_'):
    now = time.localtime()
    return ('{1:0=4}{0}{2:0=2}{0}{3:0=2}{7}{4:0=2}{0}{5:0=2}{0}{6:0=2}'.format(separator, now.tm_year,  now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min, now.tm_sec, datetime_separator))

def date_string():
    now = time.localtime()
    return ('{0:0=4}-{1:0=2}-{2:0=2}'.format(now.tm_year,  now.tm_mon, now.tm_mday))

def truncate_timestamps(list_of_timestamps,  at_position):
    '''From a list of floats representing timestamps, we calculates timestamps 
    with least significant data truncated. E.g. to get timestamps that contain only
   year_month_date but no hour, second, millisecond: set at_position=3
   '''
    timetuples = numpy.array([time.localtime(ts) for ts in list_of_timestamps])
    truncated_timestamps= [time.mktime(tt[:at_position].tolist()+[0]*(9-at_position)) for tt in timetuples] #timestamps made from timetuples where only year month day differs, rest is 0
    return truncated_timestamps

def timestamp2hms(timestamp):
    time_struct = time.localtime(timestamp)
    return ('{0:0=2}:{1:0=2}:{2:0=2.1f}'.format(time_struct.tm_hour, time_struct.tm_min, time_struct.tm_sec + numpy.modf(timestamp)[0]))
    
def timestamp2hm(timestamp):
    time_struct = time.localtime(timestamp)
    return ('{0:0=2}:{1:0=2}'.format(time_struct.tm_hour, time_struct.tm_min))
    
def timestamp2ymdhms(timestamp,filename=False):
    time_struct = time.localtime(timestamp)
    if filename:
        dt='_'
        t='-'
    else:
        dt=' '
        t=':'
    return '{0:0=4}-{1:0=2}-{2:0=2}{6}{3:0=2}{7}{4:0=2}{7}{5:0=2}'.format(time_struct.tm_year, time_struct.tm_mon, time_struct.tm_mday, time_struct.tm_hour, time_struct.tm_min, time_struct.tm_sec,dt,t)

def timestamp2ymdhm(timestamp):
    time_struct = time.localtime(timestamp)
    return '{0:0=4}-{1:0=2}-{2:0=2}+{3:0=2}:{4:0=2}'.format(time_struct.tm_year, time_struct.tm_mon, time_struct.tm_mday, time_struct.tm_hour, time_struct.tm_min).replace('+',' ')

def timestamp2ymd(timestamp,separator='-'):
    time_struct = time.localtime(timestamp)
    return '{0:0=4}{3}{1:0=2}{3}{2:0=2}'.format(time_struct.tm_year, time_struct.tm_mon, time_struct.tm_mday,separator).replace('+',' ')
    
def datestring2timestamp(ds,format="%d/%m/%Y"):
    return time.mktime(datetime.datetime.strptime(ds, format).timetuple())
    
def timestamp2secondsofday(timestamp):
    time_struct = time.localtime(timestamp)
    return time_struct.tm_hour*3600+time_struct.tm_min*60+time_struct.tm_sec
    
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
        break_wait_function: shall not block and shall return with boolean
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
        
def periodic_caller(period, call, args = None, idle_time = 0.1):#OBSOLETE, not used by anyone
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

def generate_waveform(waveform_type,  n_sample, period, amplitude,  offset = 0,  phase = 0,  duty_cycle = 0.5):
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
    
def safe_istrue(obj, var):
    return (hasattr(obj, var) and getattr(obj, var))
    
def get_key(var, key):
    '''
    Returns None when var does not have specified key or var is not a dict at all
    '''
    if safe_has_key(var, key):
        return var[key]
    else:
        return None
        
def sort_dict(list_of_dict, key):
    '''
    Sorts a list of dictionaries by values in key. Values in key shall be unique
    '''
    sortable_values = [item[key] for item in list_of_dict]
    sortable_values.sort()
    sorted_list = []
    for val in sortable_values:
        for item in list_of_dict:
            if item[key] == val:
                if item in sorted_list:
                    continue
                sorted_list.append(item)
                break
    return sorted_list
    
    
def item2list(item):
    '''
    Checks if item is a list or not. If not, makes a 1 item list of it
    '''
    if hasattr(item, '__iter__'):
        item_list = item
    else:
        item_list = [item]
    return item_list
    
def check_expected_parameter(config, parameter_name):
    for pn in item2list(parameter_name):
        if not hasattr(config, pn):
            raise RuntimeError('{0} parameter must be defined'.format(pn))
    
def printl(self, message, loglevel='info', stdio = True):
    '''
    Message to logfile, queued socket and standard output
    '''
    message_string = str(message)
    self.send(message_string)
    if stdio:
        sys.stdout.write(message_string+'\n')
    if hasattr(self.log, loglevel):
        getattr(self.log, loglevel)(message_string, self.machine_config.user_interface_name)
        
def list_swap(l, i1, i2):
    l[i1], l[i2] = l[i2], l[i1]
    return l
    
def sendmail(to, subject, txt):
    import subprocess,fileop
    message = 'Subject:{0}\n\n{1}\n'.format(subject, txt)
    fn='/tmp/email.txt'
    fileop.write_text_file(fn,message)
    # Send the mail
    cmd='/usr/sbin/sendmail {0} < {1}'.format(to,fn)
    res=subprocess.call(cmd,shell=True)
    os.remove(fn)
    return res==0
    
def push2git(server, user, password, repository_path, message,branchname):
    '''
    automatically pushes changes in repository
    '''
    import subprocess
    subprocess.call('cd {0};git add .;git commit -m "{1}";git push origin {2}'.format(repository_path, message, branchname), shell=True)
    

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
            
    def test_17_object2array(self):
        objects = [
                   [1,2,3,'a'],
                   {'d':range(10000000)},
                   ]
        res = []
        for o in objects:
            res.append(array2object(object2array(o)))
        self.assertEqual(objects, res)
        
    def test_18_shuffle_positions(self):
        from visexpman.users.test import unittest_aggregator
        positions=array2object(numpy.load(os.path.join(unittest_aggregator.prepare_test_data('shuffle_positions'),'positions.npy')))
        col=[1.0,0.0]
        import itertools
        pc=[[c,p] for p,c in itertools.product(positions,col)]
        shuffle_positions_avoid_adjacent(pc,rc((150,150)))

    def test_19_sendmail(self):
        self.assertTrue(sendmail('zoltan.raics@fmi.ch','test','c'))
        
    def test_20_push(self):
        import fileop
        push2git('rlvivo1.fmi.ch', 'rz', 'ATxmega16A4', '/tmp/visexpman', 'commit msg', 'test')
        
def shuffle_positions_avoid_adjacent(positions,shape_distance):
    remaining=copy.deepcopy(positions)
    success=True
    shuffled=[]
    while True:
        selected_i = random.choice(range(len(remaining)))
        if len(shuffled)>0:
            while True:
                coords=rc(numpy.array([nd(shuffled[-1][1]),nd(remaining[selected_i][1])]))
                if abs(numpy.diff(coords['row'])[0])<=shape_distance['row'] and abs(numpy.diff(coords['col'])[0])<=shape_distance['col']:
                    if len(remaining)>1:
                        selected_i = random.choice(range(len(remaining)))
                    else:
                        success=False
                        break
                else:
                    break
        shuffled.append(remaining[selected_i])
        del remaining[selected_i]
        if len(remaining)==0:
            break
    return shuffled,success
    
def send_udp(ip,port,msg):
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(msg, (ip, port))
            
if __name__ == "__main__":
    module_names, visexpman_module_paths = imported_modules()
    module_versions, module_version = module_versions(module_names)
    pass
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
#            stimpar = fileop.parsefilename(filename, commonpars)
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
    mytest.addTest(TestUtils('test_18_shuffle_positions'))
    mytest.addTest(TestUtils('test_19_sendmail'))
    mytest.addTest(TestUtils('test_20_push'))
    alltests = unittest.TestSuite([mytest])
    #suite = unittest.TestLoader().loadTestsFromTestCase(Test)
    unittest.TextTestRunner(verbosity=2).run(alltests)
