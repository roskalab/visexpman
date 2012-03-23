import numpy
import Image
import ImageDraw
import ImageFont
import os
import utils
from visexpA.engine.dataprocessors import generic
import unittest

def rescale_numpy_array_image(image, scale):
    if not isinstance(scale,  numpy.ndarray) and not isinstance(scale,  numpy.void):
        scale = utils.cr((scale,  scale))
    im = Image.fromarray(generic.normalize(image,numpy.uint8))
    new_size = (int(im.size[0] * scale['col']), int(im.size[1] * scale['row']))
    im = im.resize(new_size)
    return numpy.asarray(im)

def draw_line_numpy_array(image, line, fill = (255, 0, 0)):
    im = Image.fromarray(generic.normalize(image,numpy.uint8))
    im = im.convert('RGB')
    draw = ImageDraw.Draw(im)
    draw.line(line, fill, width = 1)
    return numpy.asarray(im)
    
def draw_scalebar(image, origin, scale, division, frame_size = None, fill = (0, 0, 0),  mes = True):
    if frame_size == None:
        frame_size = 0.05 * min(image.shape)
    if not isinstance(scale,  numpy.ndarray) and not isinstance(scale,  numpy.void):
        scale = utils.rc((scale, scale))
    #Scale = unit (um) per pixel
    frame_color = 255
    fontsize = int(frame_size/3)
    if len(image.shape) == 3:
        image_with_frame_shape = (image.shape[0]+2*frame_size, image.shape[1]+2*frame_size, image.shape[2])
    else:
        image_with_frame_shape = (image.shape[0]+2*frame_size, image.shape[1]+2*frame_size)
    image_with_frame = frame_color*numpy.ones(image_with_frame_shape, dtype = numpy.uint8)
    if len(image.shape) == 3:
        image_with_frame[frame_size:frame_size+image.shape[0], frame_size:frame_size+image.shape[1], :] = generic.normalize(image,numpy.uint8)
    else:
        image_with_frame[frame_size:frame_size+image.shape[0], frame_size:frame_size+image.shape[1]] = generic.normalize(image,numpy.uint8)
    im = Image.fromarray(image_with_frame)
    im = im.convert('RGB')
    draw = ImageDraw.Draw(im)
    if os.name == 'nt':
        font = ImageFont.truetype("arial.ttf", fontsize)
    else:
        font = ImageFont.truetype("/usr/share/fonts/truetype/msttcorefonts/arial.ttf", fontsize)
    image_size = utils.cr((image.shape[0]*float(scale['row']), image.shape[1]*float(scale['col'])))
    if mes:
        number_of_divisions = int(image_size['row'] / division)
    else:
        number_of_divisions = int(image_size['col'] / division)
    col_labels = numpy.linspace(numpy.round(origin['col'], 1), numpy.round(origin['col'] + number_of_divisions * division, 1), number_of_divisions+1)
    if mes:
        number_of_divisions = int(image_size['col'] / division)
        row_labels = numpy.linspace(numpy.round(origin['row'], 1),  numpy.round(origin['row'] - number_of_divisions * division, 1), number_of_divisions+1)
    else:
        number_of_divisions = int(image_size['row'] / division)
        row_labels = numpy.linspace(origin['row'],  origin['row'] + number_of_divisions * division, number_of_divisions+1)
    #Overlay labels
    for label in col_labels:
        position = int((label-origin['col'])/scale['col']) + frame_size
        draw.text((position, 5),  str(int(label)), fill = fill, font = font)
        draw.line((position, int(0.75*frame_size), position, frame_size), fill = fill, width = 0)
        #Opposite side
        draw.text((position, image_with_frame.shape[0] - fontsize-5),  str(int(label)), fill = fill, font = font)
        draw.line((position,  image_with_frame.shape[0] - int(0.75*frame_size), position,  image_with_frame.shape[0] - frame_size), fill = fill, width = 0)
        
    for label in row_labels:
        if mes:
            position = int((-label+origin['row'])/scale['row']) + frame_size
        else:
            position = int((label-origin['row'])/scale) + frame_size
        draw.text((5, position), str(int(label)), fill = fill, font = font)
        draw.line((int(0.75*frame_size), position, frame_size, position), fill = fill, width = 0)
        #Opposite side
        draw.text((image_with_frame.shape[1] - int(2.0*fontsize), position),  str(int(label)), fill = fill, font = font)
        draw.line((image_with_frame.shape[1] - int(0.75*frame_size), position,  image_with_frame.shape[1] - frame_size, position), fill = fill, width = 0)
    im = numpy.asarray(im)
    return im
       
def generate_gui_image(images, size, config, lines  = [], sidebar_division = 0):
    '''
    Combine images with widgets like lines, sidebars. 
    
    Inputs:
    images: images to display. These will be overlaid using coloring, scaling and origin information.
    size: size of output image in pixels in row, col format
    lines: lines to draw on images, containing line endpoints in um
    sidebar_division: the size of divisions on the sidebar
    
    config: the following parameters are expected: 
                                LINE_WIDTH, LINE_COLOR
                                SIDEBAR_COLOR, SIDEBAR_SIZE

    Ouput: image_to_display
    '''
    out_image = 255*numpy.ones((size['row'], size['col'], 3), dtype = numpy.uint8)
    if not isinstance(images,  list):
        images = [images]
    if len(images) == 1:
        merged_image = images[0]
    else:
        #here the images are merged: 1. merge with coloring different layers, 2. merge without coloring
        pass
    image_area = utils.rc_add(size,  utils.cr((2*config.SIDEBAR_SIZE, 2*config.SIDEBAR_SIZE)), '-')
    #calculate scaling factor for rescaling image to required image size
    rescale = (numpy.cast['float64'](utils.nd(image_area)) / merged_image['image'].shape).min()
    rescaled_image = rescale_numpy_array_image(merged_image['image'], rescale)
    #Draw lines
    image_with_line = numpy.array([rescaled_image, rescaled_image, rescaled_image])
    image_with_line = numpy.rollaxis(image_with_line, 0, 3)
    for line in lines:
        #Line: x1,y1,x2, y2 - x - col, y = row
        #Considering MES/Image origin
        line_in_pixel  = [(line[0] - merged_image['origin']['col'])/merged_image['scale']['col'],
                            (-line[1] + merged_image['origin']['row'])/merged_image['scale']['row'],
                            (line[2] - merged_image['origin']['col'])/merged_image['scale']['col'],
                            (-line[3] + merged_image['origin']['row'])/merged_image['scale']['row']]
        line_in_pixel = (numpy.cast['int32'](numpy.array(line_in_pixel)*rescale)).tolist()
        image_with_line = draw_line_numpy_array(image_with_line, line_in_pixel)
    #create sidebar
    if sidebar_division != 0:
        image_with_sidebar = draw_scalebar(image_with_line, merged_image['origin'], utils.rc_multiply_with_constant(merged_image['scale'], 1.0/rescale), sidebar_division, frame_size = config.SIDEBAR_SIZE)
    else:
        image_with_sidebar = image_with_line
    out_image[0:image_with_sidebar.shape[0], 0:image_with_sidebar.shape[1], :] = image_with_sidebar
    return out_image
    
    
def expspace(start,  end,  number_of_points):
    exponent = numpy.log(end-start+1)
    return numpy.exp(numpy.linspace(0.0,  1.0,  number_of_points)*exponent)+start-1

class GuiImagesTestConfig():
    def __init__(self):
        self.SIDEBAR_SIZE = 40
        pass
        
class Test(unittest.TestCase):
    
#    def test_01(self):
#        file = '/home/zoltan/visexp/debug/mouse_regions.hdf5'
#        from visexpA.engine.datahandlers import hdf5io
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
