'''
This modules contains all the (stimulus) color related conversion, manipulation function
'''
import numpy,random

#== Computer graphics colors ==
def convert_color(color, config = None):
    '''
    Any color format (rgb, greyscale, 8 bit grayscale) is converted to visexpman rgb format:
    When integer value provided, it is assumed that max intensity is 255
    Gamma correction is applied if config.GAMMA_CORRECTION exists
    If config.COLOR_MASK exists, rgb values are multiplied with this parameters
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
        converted_color = config.COLOR_MASK * numpy.array(converted_color)
    if hasattr(config, 'GAMMA_CORRECTION'):
        converted_color =config.GAMMA_CORRECTION(converted_color).tolist()
    return converted_color

#OBSOLETE
def convert_color_from_pp(color_pp):
    '''
    convert color from psychopy format to Presentinator default format (0...1 range)
    '''
    color = []
    for color_pp_channel in color_pp:
        color.append(0.5 * (color_pp_channel + 1.0))
    return color

#NOT USED, OBSOLETE
def convert_int_color(color):
    '''
    Rgb color is converted to 8 bit rgb
    '''    
    if isinstance(color,  list):
        return (int(color[0] * 255.0),  int(color[1] * 255.0),  int(color[2] * 255.0))
    else:
        return (int(color * 255.0),  int(color * 255.0),  int(color * 255.0))
        
def get_color(index):
    '''
    Generate a color:
    index   color
    0           red
    1           green
    2           blue
    3           yellow
    4           magenta
    5           cyna
    '''
    c=numpy.array([1,0,0,
          0,1,0,
          0,0,1,
          1,1,0,
          1,0,1,
          0,1,1,
          ],dtype=numpy.float)
    c=numpy.concatenate((c,0.5*c, numpy.array([1,0.5,0,])))
    if index>=c.shape[0]/3:
        raise RuntimeError('No more colors')
    return list(c[index*3:(index+1)*3])
        
def random_colors(n,  frames = 1,  greyscale = False,  inital_seed = 0):
    '''
    Renerates random colors.
    An array of rgb values are generated if frames>1
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

def colorstr2channel(color_str):
    '''
    Converts color string to channel index, like 'blue' to 2
    '''
    color_strings = ['red','green','blue']
    return color_strings.index(color_str.lower())
    
def addframe(im, frame_color, width=1):
    '''
    Add frame to image represented by im in numpy.array format. The width of the frame is one pixel by default
    '''
    im[:width,:,:]=frame_color
    im[-width,:,:]=frame_color
    im[:,:width,:]=frame_color
    im[:,-width,:]=frame_color
    return im
    
import unittest
class TestColorUtils(unittest.TestCase):
    def test_01_add_frame(self):
        im=addframe(numpy.ones((100,100,3)), numpy.array([0.3,0,0]), width=1)
        numpy.testing.assert_equal(im[0,0,:],numpy.array([0.3,0,0]))
        im=addframe(numpy.ones((100,100,3)), 0.4, width=1)
        numpy.testing.assert_equal(im[0,0,:],numpy.array([0.4,0.4,0.4]))
        im=addframe(numpy.ones((100,100,3)), 0.4, width=10)
        numpy.testing.assert_equal(im[9,-9,:],numpy.array([0.4,0.4,0.4]))
        
    def test_02_colorstr2channel(self):
        self.assertEqual(colorstr2channel('red'),0)
        
    def test_get_colors(self):
        for i in range(13):
            self.assertLessEqual(max(get_color(i)),1)
            self.assertGreaterEqual(min(get_color(i)),0)
        self.assertRaises(RuntimeError,get_color,13)
        
if __name__ == "__main__":
    unittest.main()
