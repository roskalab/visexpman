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
        y = 0.5 * diameter[0] * numpy.sin(angle) + pos[1]
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

def generate_waveform(waveform_type,  n_sample,  period,  amplitude,  offset = 0,  phase = 0,  duty_cycle = 0.5):
    wave = []
    period = int(period) 
    for i in range(n_sample):
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
    
def fetch_classes(basemodule, classname=None,  exclude_classtypes=[],  required_ancestors=[], direct=True):
    '''Looks for the specified class, imports it and returns as class instance.
    Use cases:
    1. just specify user, others left as default: returns all classes
    2. specify user and classname: returns specific class without checking its type
    3. specify user, classname,and list of classes that should not be in the ancestor tree of the class
      In this case you can specify if required ancestors and excluded classtypes applies to the whole 
      method resolution order tree (whole ancestor tree) or just the direct ancestors. You can specify 
      'direct' for all required ancestors as a single True value as argument or as a list of booleans. In
      the latter case, the booleans in the list apply to the class in the same position in the 
      required_ancestors list.
    '''
    import visexpman
    bm=__import__(basemodule, fromlist='dummy')
    class_list=[]
    if not isinstance(required_ancestors, (list, tuple)): required_ancestors=[required_ancestors]
    if not isinstance(exclude_classtypes, (list, tuple)): exclude_classtypes=[exclude_classtypes]
    if not isinstance(direct, (list, tuple)): direct=[direct]*len(required_ancestors)
    
    for importer, modname, ispkg in pkgutil.iter_modules(bm.__path__,  bm.__name__+'.'):
        m= __import__(modname, fromlist='dummy')
        for attr in inspect.getmembers(m, inspect.isclass):
            for ai1 in range(len(required_ancestors)):
                if direct[ai1]==True:
                    ancestors = attr[1].__bases__
                else:
                    ancestors = inspect.getmro(attr[1])
                any_wrong_in_class_tree = [cl in ancestors for cl in exclude_classtypes]
                if sum(any_wrong_in_class_tree) >0: 
                    # the class hyerarchy contains ancestors that should not be in this class' ancestor list
                    break
                if not required_ancestors[ai1] in ancestors:
                    break
                # required_ancestors or exlude_classtypes conditions handled, we need to check if name is correct:
                if (attr[0] == classname or classname==None):
                    class_list.append((m, attr[1]))
                    # here we also could execute some test on the experiment which lasts very short time but ensures stimulus will run    
    return class_list
    
def um_to_normalized_display(value, config):
    '''
    Converts um dimension data to normalized screen size where the screen range is between -1...1 for both axes and the origo is the center of the screen
    '''
    if not isinstance(value,  list):
        value = [value,  value]
    normalized_x = 2.0 * config.SCREEN_PIXEL_TO_UM_SCALE * float(value[0]) / config.SCREEN_RESOLUTION['col']
    normalized_y = 2.0 * config.SCREEN_PIXEL_TO_UM_SCALE * float(value[1]) / config.SCREEN_RESOLUTION['row']
    return [normalized_x,  normalized_y]

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
    
def read_text_file(path):
    f = open(path,  'rt')
    txt =  f.read(os.path.getsize(path))
    f.close()            
    return txt
    
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

def find_files_and_folders(start_path,  extension = None):
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
                else:
                    all_files.append(root + os.sep + file)    
        return directories, all_files
        
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
 
def prepare_dynamic_class_instantiation(modules,  class_name):        
    """
    Imports the necessary module and returns a reference to the class that could be sued for instantiation
    """
    #import experiment class
    module_name = find_class_in_module(modules, class_name,  module_name_with_hierarchy = True)
    __import__(module_name)
    #get referece to class and return with it
    return getattr(sys.modules[module_name], class_name)

def rc(raw):
    return rc_pack(raw, order = 'rc')

def cr(raw):
    return rc_pack(raw, order = 'cr')    
            
def rc_pack(raw, order = 'rc'):
    if order == 'rc':
        index_first = 1
        index_second = 0
    elif order == 'cr':
        index_first = 0
        index_second = 1    
    if isinstance(raw, numpy.ndarray) and raw.ndim==2:
        #input is a numpy array
        if raw.ndim==2 and raw.shape[1]==2:
            raw=raw.T
        if raw.dtype == numpy.float:
            return numpy.array(zip(raw[index_first], raw[index_second]),dtype={'names':['col','row'],'formats':[numpy.float32,numpy.float32]})
        else:
            return numpy.array(zip(raw[index_first], raw[index_second]),dtype={'names':['col','row'],'formats':[numpy.int16,numpy.int16]})
    elif isinstance(raw, numpy.ndarray) and raw.ndim > 2:
        raise TypeError('Input data dimension must be 2. Call rc_flatten if you want data to be flattened before conversion')
    else:
        #input is a tuple or 1D numpy array: this case has to be handled separately so that indexing mydata['row'] returns a value and not an array.
        if isinstance(raw[0], float):
            return numpy.array((raw[index_first], raw[index_second]),dtype={'names':['col','row'],'formats':[numpy.float32,numpy.float32]})
        else:
            return numpy.array((raw[index_first], raw[index_second]),dtype={'names':['col','row'],'formats':[numpy.int16,numpy.int16]})

def rc_add(operand1, operand2):
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
            return rc((operand1['row'] + operand2['row'], operand1['col'] + operand2['col']))
        elif operand1.shape != () and operand2.shape != ():
            rows = operand1[:]['row'] + operand2[:]['row']
            cols = operand1[:]['col'] + operand2[:]['col']
            return rc(numpy.array([rows, cols]))
        elif operand1.shape == () and operand2.shape != ():
            rows = operand1['row'] + operand2[:]['row']
            cols = operand1['col'] + operand2[:]['col']
            return rc(numpy.array([rows, cols]))
        elif operand1.shape != () and operand2.shape == ():
            rows = operand1[:]['row'] + operand2['row']
            cols = operand1[:]['col'] + operand2['col']
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
    
def listdir_fullpath(folder):
    files = os.listdir(folder)
    full_paths = []
    for file in files:
        full_paths.append(os.path.join(folder,  file))
    return full_paths
    
def generate_filename(path):
    '''
    Inserts index into filename resulting unique name.
    '''    
    index = 0
    while True:
        testable_path = path.replace('.',  '_%3i.'%index).replace(' ', '0')
        if not os.path.isfile(testable_path):
            break
        index = index + 1        
    return testable_path
    
def generate_foldername(path):
    '''
    Inserts index into filename resulting unique name.
    '''    
    index = 0
    while True:
        testable_path = (path + '_%3i'%index).replace(' ', '0')
        if not os.path.isdir(testable_path):
            break
        index = index + 1        
    return testable_path


class testCoordinateTransformation(unittest.TestCase):
    pass

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

if __name__ == "__main__":
    l = [1, 2, 3]
    print is_in_list(l, 'a')
#    print is_vector_in_array(numpy.array([[1.0, 2.0, 3.0], [2.0, 3.0, 4.0], [3.0, 4.0, 5.0]]),  numpy.array([1.0, 2.0, 3.0]))
#    unittest.main()
#    a = [1.0, 2.0, 3.0]
#    b = [10.0, 20.0, 30.0]
#    c = rc(numpy.array([a, b]))    
#    p = coordinate_transform_single_point(rc((0.0, 1.0)), rc((100.0, -100.0)), rc((-1, 1)) )
#    print p['row']
#    print p['col']

#    print rc_multiply(rc((2, 0)), rc((1, 1)))
#    print rc_multiply(rc(numpy.array([a, b])), rc((0, -10)))
#    print rc_multiply(rc(numpy.array([a, b])), rc(numpy.array([a, b])))
#    print a[:]['row']

#    res = coordinate_transform(cr((100, 100)), cr((-100, 100)), 'right', 'down')
#    print res['col'], res['row']
    
#    cols = [0,  100, -100]
#    rows = [0,  100, 100]
#    coords = cr(numpy.array([cols, rows]))    
#    print coords.shape
#    res = coordinate_transform(coords, cr((-100, 100)), 'right', 'down')    
##    print res
#    print rc_multiply_with_constant(c, 10)
#    a = numpy.zeros((3, coords.shape[0]))
#    a[0][0] = coords[1]['row']
#    
#    print a    
#    print generate_filename('/media/Common/visexpman_data/log.txt')

def test_parsefilename():
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
    
def test_getziphandler():
    pass

def test_fetch_classes():
    class GrandMother(object):
        pass
    class GrandFather(object):
        pass
    class Father(GrandMother, GrandFather):
        pass
    class Mother(GrandMother, Father):
        pass
    self.assertequal(fetch_classes(visexpman.engine.generic.utils, required_ancestors=[GrandMother, GrandFather], direct=False),1 )
