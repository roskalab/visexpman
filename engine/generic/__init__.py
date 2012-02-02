import numpy
import Image
from visexpA.engine.dataprocessors import generic

def rescale_numpy_array_image(image, scale):
    im = Image.fromarray(generic.normalize(image,numpy.uint8))
    new_size = (int(im.size[0] * scale), int(im.size[1] * scale))
    im = im.resize(new_size)
    return numpy.asarray(im)
