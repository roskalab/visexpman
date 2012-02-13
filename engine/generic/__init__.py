import numpy
import Image
import ImageDraw
from visexpA.engine.dataprocessors import generic
import unittest

def rescale_numpy_array_image(image, scale):
    im = Image.fromarray(generic.normalize(image,numpy.uint8))
    new_size = (int(im.size[0] * scale['col']), int(im.size[1] * scale['row']))
    im = im.resize(new_size)
    return numpy.asarray(im)

def draw_line_numpy_array(image, line, fill = (255, 0, 0)):
    im = Image.fromarray(generic.normalize(image,numpy.uint8))
    im = im.convert('RGB')
    draw = ImageDraw.Draw(im)
    draw.line(line, fill, width = 2)
    return numpy.asarray(im)
    
########## Look-up table ###############

def lut(value,  lookup_table):
    '''
    Finds the lookup table value for value
    If value is an array, then the LUT is applied to each value
    Lookup table is a 2D array with two columns and arbitrary number of rows
    
    '''
    if hasattr(value, 'dtype'):
        pass
    else:
        pass
    
class TestLUT(unittest.TestCase):
    def setUp(self):
        self.lut_linear= numpy.array([[1.0, 2.0], 
                                                    [0.4, 0.8], 
                                                    [0.0, 0.0]])
        self.lut_projector = numpy.array([[255, 19260], 
                                            [240, 19250], 
                                            [230, 19250], 
                                            [220, 19160], 
                                            [210, 18790], 
                                            [200, 17680], 
                                            [190, 16400], 
                                            [180, 14170], 
                                            [170, 11530], 
                                            [160, 8390], 
                                            [150, 6528], 
                                            [140, 4590], 
                                            [130, 1340], 
                                            [120, 1245], 
                                            [110, 1088], 
                                            [100, 950], 
                                            [90, 826], 
                                            [80, 646], 
                                            [70, 490], 
                                            [60, 351], 
                                            [50, 256], 
                                            [40, 109], 
                                            [30, 83], 
                                            [20, 55], 
                                            [10, 27], 
                                            [0, 12.5]])

    def test_01_single(self):
        self.assertEqual(lut(0.5, self.lut_linear), 1.0)
    
if __name__ == '__main__':
    unittest.main()
