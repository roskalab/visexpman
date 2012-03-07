import numpy
import Image
import ImageDraw
import ImageFont
import os
import utils
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
    
def draw_scalebar(image, origin, scale, division, fill = (0, 0, 0),  mes = True):
    #Scale = unit (um) per pixel
    frame_color = 255
    fontsize = int(min(image.shape)*0.07) +2
    frame_size = 3.5*fontsize
    image_with_frame = frame_color*numpy.ones((image.shape[0]+2*frame_size, image.shape[1]+2*frame_size), dtype = numpy.uint8)
    image_with_frame[frame_size:frame_size+image.shape[0], frame_size:frame_size+image.shape[1]] = generic.normalize(image,numpy.uint8)
    im = Image.fromarray(image_with_frame)
    im = im.convert('RGB')
    draw = ImageDraw.Draw(im)
    if os.name == 'nt':
        font = ImageFont.truetype("arial.ttf", fontsize)
    else:
        font = ImageFont.truetype("/usr/share/fonts/truetype/msttcorefonts/arial.ttf", fontsize)

    image_size = utils.cr((image.shape[0]*float(scale), image.shape[1]*float(scale)))
    if mes:
        number_of_divisions = int(image_size['row'] / division)
    else:
        number_of_divisions = int(image_size['col'] / division)
    col_labels = numpy.linspace(origin['col'],  origin['col'] + number_of_divisions * division, number_of_divisions+1)
    if mes:
        number_of_divisions = int(image_size['col'] / division)
        row_labels = numpy.linspace(origin['row'],  origin['row'] - number_of_divisions * division, number_of_divisions+1)
    else:
        number_of_divisions = int(image_size['row'] / division)
        row_labels = numpy.linspace(origin['row'],  origin['row'] + number_of_divisions * division, number_of_divisions+1)
    
    #Overlay labels
    for label in col_labels:
        position = int((label-origin['col'])/scale) + frame_size
        draw.text((position, 5),  str(int(label)), fill = fill, font = font)
        draw.line((position, int(0.75*frame_size), position, frame_size), fill = fill, width = 2)
        #Opposite side
        draw.text((position, image_with_frame.shape[0] - fontsize-5),  str(int(label)), fill = fill, font = font)
        draw.line((position,  image_with_frame.shape[0] - int(0.75*frame_size), position,  image_with_frame.shape[0] - frame_size), fill = fill, width = 2)
        
    for label in row_labels:
        if mes:
            position = int((-label+origin['row'])/scale) + frame_size
        else:
            position = int((label-origin['row'])/scale) + frame_size
        draw.text((5, position), str(int(label)), fill = fill, font = font)
        draw.line((int(0.75*frame_size), position, frame_size, position), fill = fill, width = 2)
        #Opposite side
        draw.text((image_with_frame.shape[1] - int(2.0*fontsize), position),  str(int(label)), fill = fill, font = font)
        draw.line((image_with_frame.shape[1] - int(0.75*frame_size), position,  image_with_frame.shape[1] - frame_size, position), fill = fill, width = 2)
    return numpy.asarray(im)

if __name__ == '__main__':
    im = 128*numpy.ones((436, 576))
    im = Image.fromarray(draw_scalebar(im, utils.rc((-40.4, -192.6)), 0.367878 , 30.0,  fill = 0))
    if os.name == 'nt':
        im.save('v:\\debug\\scalebar.png')
    else:
        im.save('/home/zoltan/visexp/debug/scalebar.png')
