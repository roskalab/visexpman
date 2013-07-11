#This modules contains all the (stimulus) color related conversion, manipulation function
#From utils all the color related functions shall be moved to here
import numpy
import Image

def imshow(ima, show=True):
    im = Image.fromarray(numpy.cast['uint8'](255*(ima - ima.min())/(ima.max()-ima.min())))
    if show:
        im.show()
    return im
    
def imsave(imarray, filename):
    imshow(imarray, False).save(filename)

#== Computer graphics colors ==
def convert_color(color, config = None):
    '''
    Any color format (rgb, greyscale, 8 bit grayscale) is converted to visexpman rgb format
    '''
    if (isinstance(color, list) and len(color) == 1) or (isinstance(color, numpy.ndarray) and color.shape[0] == 1):
        converted_color = [color[0], color[0], color[0]]
    elif isinstance(color, float):
        converted_color = [color, color, color]
    elif isinstance(color, int):
        converted_color = [color/255.0, color/255.0, color/255.0]
    else:
        converted_color = color
    if hasattr(config, 'COLOR_MASK'):
        converted_color = config.COLOR_MASK * nupy.array(converted_color)
    if hasattr(config, 'GAMMA_CORRECTION'):
        converted_color =config.GAMMA_CORRECTION(converted_color).tolist()
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

def wavlength2rgb(wavelength):
    """
    convert wavelength in nm to rgb values
    """
    w = wavelength
   
    # colour
    if w >= 380 and w < 440:
            R = -(w - 440.) / (440. - 350.)
            G = 0.0
            B = 1.0
    elif w >= 440 and w < 490:
            R = 0.0
            G = (w - 440.) / (490. - 440.)
            B = 1.0
    elif w >= 490 and w < 510:
            R = 0.0
            G = 1.0
            B = -(w - 510.) / (510. - 490.)
    elif w >= 510 and w < 580:
            R = (w - 510.) / (580. - 510.)
            G = 1.0
            B = 0.0
    elif w >= 580 and w < 645:
            R = 1.0
            G = -(w - 645.) / (645. - 580.)
            B = 0.0
    elif w >= 645 and w <= 780:
            R = 1.0
            G = 0.0
            B = 0.0
    else:
            R = 0.0
            G = 0.0
            B = 0.0

    # intensity correction
    if w >= 380 and w < 420:
            SSS = 0.3 + 0.7*(w - 350) / (420 - 350)
    elif w >= 420 and w <= 700:
            SSS = 1.0
    elif w > 700 and w <= 780:
            SSS = 0.3 + 0.7*(780 - w) / (780 - 700)
    else:
            SSS = 0.0

    val = (float(SSS*R), float(SSS*G), float(SSS*B))
    return val
