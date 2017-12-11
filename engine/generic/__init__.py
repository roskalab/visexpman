#TODO: Functions obsolete or has to be reworked
import numpy
try:
    import Image
    import ImageDraw
    import ImageFont
except ImportError:
    from PIL import Image
    from PIL import ImageDraw
    from PIL import ImageFont

import os
if 0:
    from visexpA.engine.dataprocessors import generic
import unittest
import itertools
    
#TODO: these functions may go to visexpA/generic
def pack_to_rgb(array_r, array_g=None, array_b = None):
    if array_g==None and array_b == None:
        return numpy.rollaxis(numpy.array([array_r, array_r, array_r]),  0,  3)
    else:
        return numpy.rollaxis(numpy.array([array_r, array_g, array_b]),  0,  3)

def rescale_numpy_array_image(image, scale,  filter = None,  normalize = True):
    if not isinstance(scale,  numpy.ndarray) and not isinstance(scale,  numpy.void):
        scale = utils.cr((scale,  scale))
    if filter is None:
        filter = Image.ANTIALIAS
    if normalize:
        im = Image.fromarray(generic.normalize(image,numpy.uint8))
    else:
        im = Image.fromarray(image)
        
    new_size = (int(im.size[0] * scale['col']), int(im.size[1] * scale['row']))
    im = im.resize(new_size, filter)
    return numpy.asarray(im)
    
def vertical_flip_array_image(image,  normalize = True):
    if normalize:
        im = Image.fromarray(generic.normalize(image,numpy.uint8))
    else:
        im = Image.fromarray(image)
    im = im.transpose(Image.FLIP_TOP_BOTTOM)
    return numpy.asarray(im)
    
def horizontal_flip_array_image(image,  normalize = True):
    if normalize:
        im = Image.fromarray(generic.normalize(image,numpy.uint8))
    else:
        im = Image.fromarray(image)
    im = im.transpose(Image.FLIP_LEFT_RIGHT)
    return numpy.asarray(im)

def draw_line_numpy_array(image, line, fill = (255, 0, 0)):
    im = Image.fromarray(generic.normalize(image,numpy.uint8))
    im = im.convert('RGB')
    draw = ImageDraw.Draw(im)
    draw.line(line, fill, width = 1)
    return numpy.asarray(im)
    
def box_to_lines(box):
    lines = []
    lines.append([box[0], box[1], box[0], box[3]])
    lines.append([box[0], box[1], box[2], box[1]])
    lines.append([box[0], box[3], box[2], box[3]])
    lines.append([box[2], box[1], box[2], box[3]])
    return lines

def expspace(start,  end,  number_of_points):
    exponent = numpy.log(end-start+1)
    return numpy.exp(numpy.linspace(0.0,  1.0,  number_of_points)*exponent)+start-1
    
def iterate_parameter_space(parameters):
    iterable_parameters = []
    for parameter_name in parameters.keys():
        iterable_parameters.append(parameters[parameter_name])
    iterable = []
    for item in itertools.product(*iterable_parameters):
        iterable.append(item)
    iterable_parameters = []    
    for item in iterable:
        parameter_set = {}        
        for i in range(len(parameters.keys())):
            parameter_set[parameters.keys()[i]] = item[i]
        iterable_parameters.append(parameter_set)
    return iterable_parameters

class GuiImagesTestConfig():
    def __init__(self):
        self.SIDEBAR_SIZE = 40
        pass
        
class Test(unittest.TestCase):
    
#    def test_01(self):
#        file = '/home/zoltan/visexp/debug/mouse_regions.hdf5'
#        import hdf5io
#        sr = hdf5io.read_item(file,  'scan_regions')
#        image = [sr[sr.keys()[1]]['brain_surface']]
#    #    image = {'image': 100*numpy.ones((100, 200),  numpy.uint16), 'origin':utils.rc((0, 0)), 'scale': utils.rc((1, 1))}
#        im = generate_gui_image(image, utils.cr((600, 600)), GuiImagesTestConfig(), lines = [[0, 0, 100, 0]], sidebar_division = 100)
#        Image.fromarray(im).save('/home/zoltan/visexp/debug/debug.png')
    
#    def test_02(self):
#        im = 128*numpy.ones((436, 576))
#        im = Image.fromarray(draw_scalebar(im, utils.rc((-40.4, -192.6)), 0.367878 , 30.0,  fill = 0))
#        if os.name == 'nt':
#            im.save('v:\\debug\\scalebar.png')
#        else:
#            im.save('/home/zoltan/visexp/debug/scalebar.png')
#    
    def test_03(self):
        print expspace(0,  10,  4)
    
if __name__ == '__main__':
    unittest.main()
