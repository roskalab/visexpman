#This modules contains all the (stimulus) color related conversion, manipulation function
#From utils all the color related functions shall be moved to here
import numpy

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
