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

if __name__ == '__main__':
    unittest.main()
