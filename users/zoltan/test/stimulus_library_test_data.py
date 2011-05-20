import os.path
import generic.utils

class StimulusLibraryTestData():
    
    def __init__(self,  config):
        self.config = config

        if self.config.OS_TYPE == 'win':
            vid_test = False
        else:
            vid_test = True
            
        self.run_test = {'show_image() tests': True,  
                            'show_movie() tests': vid_test, 
                            'show_shape() test': True, 
                            'show_checkerboard() test': True, 
                            'show_ring() test': True, 
                            'show_gratings() test': True,
                            }

        screen_size = [self.config.SCREEN_RESOLUTION[0] / self.config.PIXEL_TO_UM_SCALE,  self.config.SCREEN_RESOLUTION[1] / self.config.PIXEL_TO_UM_SCALE]  

        parameters = [1.0/60.0 * screen_size[0],  1.0/60.0 * screen_size[1]]

        test_datas_show_image = [
                                            {
                                            'test name': 'Show single image',
                                            'expected result': 'The default image is shown for 1 sec in the middle of the screen',
                                            'duration' : 1.0,
                                            'position' : (0,  0), 
                                            'path' : self.config.DEFAULT_IMAGE_PATH,
                                            'formula' : [] ,
                                            'size' : None
                                            }, 
                                            {
                                            'test name': 'Show images in a path', 
                                            'expected result': 'The temporary, the bullseye and the default image is shown for 1-1 second in the middle of the screen', 
                                            'duration' : 1.0, 
                                            'position' : (0,  0), 
                                            'path' : os.path.dirname(self.config.DEFAULT_IMAGE_PATH),
                                            'formula' : [] ,
                                            'size' : None
                                            }, 
                                            {
                                            'test name': 'Show images in a path each for 1-1 frame time ', 
                                            'expected result': 'The temporary, the bullseye and the default image is shown for 1-1 frame time  in the middle of the screen', 
                                            'duration' : 0.0, 
                                            'position' : (0,  0), 
                                            'path' : os.path.dirname(self.config.DEFAULT_IMAGE_PATH),
                                            'formula' : [] ,
                                            'size' : None
                                            }, 
                                            {
                                            'test name': 'Um to pixel conversion', 
                                            'expected result': 'The default image is shown in the top left corner of the screen and fits to the screen edges', 
                                            'duration' : 1.0, 
                                            'position' : (-0.4 * screen_size[0],  0.4 * screen_size[1]), 
                                            'path' : self.config.DEFAULT_IMAGE_PATH,
                                            'formula' : [] ,
                                            'size' : (0.2 * screen_size[0],  0.2 * screen_size[1])
                                            },
                                            {
                                            'test name': 'Parametric control of image position', 
                                            'expected result': 'Image moves from bottom left corner to top right corner in 1 s', 
                                            'duration' : 1.0, 
                                            'position' : (-0.5 * screen_size[0], -0.5 * screen_size[1]), 
                                            'path' : self.config.DEFAULT_IMAGE_PATH,
                                            'formula' : [['prev + p[0]',  parameters],  ['prev + p[1]',  parameters]] ,
                                            'size' : (0.2 * screen_size[0],  0.2 * screen_size[1])
                                            },
                                            {
                                            'test name': 'Parametric control of images in a folder, each frame is shown for 1 sec', 
                                            'expected result': 'The three images are shown in three different positions: right, middle and left side of the screen', 
                                            'duration' : 1.0, 
                                            'position' : (0.8 * screen_size[0], 0), 
                                            'path' : os.path.dirname(self.config.DEFAULT_IMAGE_PATH),
                                            'formula' : [['prev - ' + str(0.4 * screen_size[0]),  []],  ['',  []]] ,
                                            'size' : None
                                            },
                                            {
                                            'test name': 'Parametric control of images in a folder, each frame is shown for 1 frame time', 
                                            'expected result': 'The three images are shown in three different positions: right, middle and left side of the screen', 
                                            'duration' : 0.0, 
                                            'position' : (0.8 * screen_size[0], 0), 
                                            'path' : os.path.dirname(self.config.DEFAULT_IMAGE_PATH),
                                            'formula' : [['prev - ' + str(0.4 * screen_size[0]),  []],  ['',  []]] ,
                                            'size' : None
                                            },
                                            ]           
        test_datas_show_movie = [
                                            {  
                                            'test name': 'play video',
                                            'expected result': 'Video is played positioned to the top right side of the screen',
                                            'position' : (0,  0.35 * screen_size[1]), 
                                            'video_file_path' : 'video/natural_scene',                                    
                                            }, 
                                            ]
                                            
        parameters = [1.0/60.0 * screen_size[0] ,  1.0/60.0 * screen_size[1] ]
        test_datas_show_shape = [
                                            {  
                                            'test name': 'check stimulus timing, size and positioning',
                                            'expected result': 'Rectangle is on the top left corner of the screen, its size is 1/4 of the screen and is shown for 1 s ',
                                            'shape': 'rect', 
                                            'duration' : 1.0, 
                                            'position' : (-screen_size[0] * 0.25,  screen_size[1] * 0.25), 
                                            'color': 1.0, 
                                            'orientation': 0, 
                                            'size': [screen_size[0] * 0.5,  screen_size[1] * 0.5], 
                                            'formula': [], 
                                            'ring_size': 0 
                                            }, 
                                            {  
                                            'test name': 'check stimulus timing, size and positioning 2',
                                            'expected result': 'Rectangle is on the top left corner of the screen, its size is 1/4 of the screen and is shown for 1 frame time ',
                                            'shape': 'rect', 
                                            'duration' : 0.0, 
                                            'position' : (-screen_size[0] * 0.25,  screen_size[1] * 0.25), 
                                            'color': 0.5, 
                                            'orientation': 0, 
                                            'size': [screen_size[0] * 0.5,  screen_size[1] * 0.5], 
                                            'formula': [], 
                                            'ring_size': 0 
                                            }, 
                                            {  
                                            'test name': 'check rectangle stimulus size configurations',
                                            'expected result': 'A square is shown for 1 s, on the middle of the screen in white color. The square\'s rotation is 45 degree',
                                            'shape': 'rect', 
                                            'duration' : 1.0, 
                                            'position' : (0,  0), 
                                            'color': 255, 
                                            'orientation': 45, 
                                            'size': screen_size[0] * 0.25, 
                                            'formula': [], 
                                            'ring_size': 0 
                                            }, 
                                            {  
                                            'test name': 'check circle stimulus size configurations',
                                            'expected result': 'A circle is shown for 1 s, on the middle of the screen in red color',
                                            'shape': 'circle', 
                                            'duration' : 1.0, 
                                            'position' : (0,  0), 
                                            'color': (255,  0,  0), 
                                            'orientation': 0, 
                                            'size': screen_size[0] * 0.5, 
                                            'formula': [], 
                                            'ring_size': 0 
                                            }, 
                                            {
                                            'test name': 'check circle stimulus size configurations 2',
                                            'expected result': 'An ellipse is shown for 1 s, on the middle of the screen in green color',
                                            'shape': 'circle', 
                                            'duration' : 1.0, 
                                            'position' : (0,  0), 
                                            'color': (0,  1.0,  0), 
                                            'orientation': 0, 
                                            'size': [screen_size[0] * 0.5,  screen_size[1] * 0.5], 
                                            'formula': [], 
                                            'ring_size': 0 
                                            }, 
                                            {
                                            'test name': 'check annulus stimulus size',
                                            'expected result': 'An ellipse ring is shown for 1 s, on the middle of the screen in green color. The thickness of the ring is 1/4 of the sreen size',
                                            'shape': 'annuli', 
                                            'duration' : 1.0, 
                                            'position' : (0,  0), 
                                            'color': (0,  1.0,  0), 
                                            'orientation': 0, 
                                            'size': [screen_size[0] * 0.5,  screen_size[1] * 0.5], 
                                            'formula': [], 
                                            'ring_size': [screen_size[0] * 0.25,  screen_size[1] * 0.25]
                                            }, 
                                            {
                                            'test name': 'check annulus stimulus size 2',
                                            'expected result': 'An ellipse ring is shown for 1 s, on the middle of the screen in green color. The thickness of the ring is even',
                                            'shape': 'annuli', 
                                            'duration' : 1.0, 
                                            'position' : (0,  0), 
                                            'color': (0.0,  1.0,  0), 
                                            'orientation': 0, 
                                            'size': [screen_size[0] * 0.5,  screen_size[1] * 0.5], 
                                            'formula': [], 
                                            'ring_size': screen_size[0] * 0.25
                                            },                                     
                                            {
                                            'test name': 'check parametric control of the position of shape stimulus',
                                            'expected result': 'A circle shall move across the screen from the bottom left to the top right in 1 s',
                                            'shape': 'circle', 
                                            'duration' : 1.0, 
                                            'position' : (-screen_size[0] * 0.5,  -screen_size[1] * 0.5), 
                                            'color': 0.75, 
                                            'orientation': 0, 
                                            'size': screen_size[0] * 0.25, 
                                            'formula': [['prev + p[0]',  parameters],  ['prev + p[1]',  parameters],  ['',  []],  ['',  []],  ['',  []],  ['',  []]], 
                                            'ring_size': 0
                                            }, 
                                            {
                                            'test name': 'check parametric control of the position and orientation of shape stimulus',
                                            'expected result': 'A rectangle shall move across the screen from the bottom left to the top right in 1 s while the rectangle shall make a 1/4 turn rotation',
                                            'shape': 'rect', 
                                            'duration' : 1.0, 
                                            'position' : (-screen_size[0] * 0.5,  -screen_size[1] * 0.5), 
                                            'color': 0.75, 
                                            'orientation': 0, 
                                            'size': screen_size[0] * 0.25, 
                                            'formula': [['prev + p[0]',  parameters],  ['prev + p[1]',  parameters],  ['prev + ' + str(0.25 * 6.0),  []],  ['',  []],  ['',  []],  ['',  []]], 
                                            'ring_size': 0
                                            }, 
                                            {
                                            'test name': 'check parametric control of the position and orientation and color of shape stimulus',
                                            'expected result': 'A rectangle shall move across the screen from the bottom left to the top right in 1 s while the rectangle shall make a 1/4 turn rotation and turns gradually from red to green',
                                            'shape': 'rect', 
                                            'duration' : 1.0, 
                                            'position' : (-screen_size[0] * 0.5,  -screen_size[1] * 0.5), 
                                            'color': (1.0,  0.0,  0.0), 
                                            'orientation': 0, 
                                            'size': screen_size[0] * 0.25, 
                                            'formula': [['prev + p[0]',  parameters],  ['prev + p[1]',  parameters],  ['prev + ' + str(0.25 * 6.0),  []],  ['prev - ' + str(1.0/60.0),  []],  ['prev + ' + str(1.0/60.0),  []],  ['prev + 0',  []]],                                     
                                            'ring_size': 0
                                            },
                                            ]
                                            

        colors0 = [0.0,  0.25,  0.5,  1.0]
        nx = 25
        ny = 25
        colors1 = utils.random_colors(nx * ny)
        n = 100
        colors2 = utils.random_colors(n)
        test_datas_show_checkerboard = [
                                            {  
                                            'test name': 'Check checker size',
                                            'expected result': 'Four checkers shall cover the whole screen',
                                            'duration' : 1.0, 
                                            'n_checkers': (2, 2), 
                                            'position' : (0,  0), 
                                            'color' : colors0, 
                                            'box_size' : (screen_size[0] * 0.5, screen_size[1] * 0.5)
                                            }, 
                                            {  
                                            'test name': 'Check checker position',
                                            'expected result': 'Four checkers shall cover the upper left quarter of the screen for 1 frame time',
                                            'duration' : 0.0, 
                                            'n_checkers': (2, 2), 
                                            'position' : (-0.25 * screen_size[0],  0.25 * screen_size[1]), 
                                            'color' : colors0,
                                            'box_size' : (screen_size[0] * 0.25, screen_size[1] * 0.25)
                                            }, 
                                            {  
                                            'test name': 'Check checkerboard maximum checker number',
                                            'expected result': 'The checkers shall have random colors and shall cover the middle half of the screen. No frame drop can take place',
                                            'duration' : 1.0, 
                                            'n_checkers': (nx, ny), 
                                            'position' : (0,  0), 
                                            'color' : colors1,
                                            'box_size' : (1.0/float(nx) * screen_size[0] * 0.5, 1.0/float(ny) * screen_size[1] * 0.5)
                                            }, 
                                            {  
                                            'test name': 'Check showing stripes',
                                            'expected result': 'Horizontally packed boxes shall appear on the screen ',
                                            'duration' : 1.0, 
                                            'n_checkers': (n, 1), 
                                            'position' : (0,  0), 
                                            'color' : colors2,
                                            'box_size' : (1.0/float(n) * screen_size[0] * 0.5, 0.25 * screen_size[1])
                                            }, 
                                            ]                                  
                                            
        test_datas_show_ring = [
                                            {  
                                            'test name': 'Check ring sizes',
                                            'expected result': 'Two concentric ellipses shall appear where the thickness of the rings are equal and the outer one fits to the edge of the screen',
                                            'n_rings' : 2,
                                            'diameter' : [[screen_size[0],  screen_size[1]],  [screen_size[0] * 0.5,  screen_size[1] * 0.5]],
                                            'inner_diameter' : [], 
                                            'duration' : 1.0, 
                                            'n_slices': 1, 
                                            'pos' : (0,  0), 
                                            'color' : utils.random_colors(2), 
                                            }, 
                                            {  
                                            'test name': 'Check ring position',
                                            'expected result': 'Two concentric ellipses shall appear where the thickness of the rings are equal and the outer one fits to the top right quarter of the screen',
                                            'n_rings' : 2,
                                            'diameter' : [[screen_size[0] * 0.25,  screen_size[1] * 0.25],  [screen_size[0] * 0.5,  screen_size[1] * 0.5]],
                                            'inner_diameter' : [], 
                                            'duration' : 1.0, 
                                            'n_slices': 1, 
                                            'pos' : (screen_size[0] * 0.25,  screen_size[1] * 0.25), 
                                            'color' : utils.random_colors(2), 
                                            },
                                            {  
                                            'test name': 'Check outer radius configuration whith incorrect number of rings',
                                            'expected result': 'Three concentric circles shall appear fitting to the right half of the screen',
                                            'n_rings' : 2,
                                            'diameter' : [screen_size[1] ,  screen_size[1] * 0.66,  screen_size[1] * 0.33],
                                            'inner_diameter' : [], 
                                            'duration' : 1.0, 
                                            'n_slices': 1, 
                                            'pos' : (screen_size[0] * 0.25,  0), 
                                            'color' : utils.random_colors(3), 
                                            },
                                            {  
                                            'test name': 'Check outer radius and inner radius configuration',
                                            'expected result': 'Three concentric rings shall appear fitting to the right half of the screen',
                                            'n_rings' : 2,
                                            'diameter' : [screen_size[1] ,  screen_size[1] * 0.66,  screen_size[1] * 0.33],
                                            'inner_diameter' : [screen_size[1] * 0.9 ,  screen_size[1] * 0.66 * 0.9,  screen_size[1] * 0.33 * 0.9], 
                                            'duration' : 1.0, 
                                            'n_slices': 1, 
                                            'pos' : (screen_size[0] * 0.25,  0), 
                                            'color' : utils.random_colors(3), 
                                            },
                                            {  
                                            'test name': 'Ellipse rings',
                                            'expected result': 'Two concentric ellipse shaped ring shall appear fitting to the right half of the screen',
                                            'n_rings' : 2,
                                            'diameter' : [[screen_size[0] * 0.25,  screen_size[1] * 0.5],  [screen_size[0] * 0.5,  screen_size[1]]],
                                            'inner_diameter' : [[screen_size[0] * 0.25 * 0.9,  screen_size[1] * 0.5 * 0.9],  [screen_size[0] * 0.5 * 0.9,  screen_size[1]* 0.9]], 
                                            'duration' : 1.0, 
                                            'n_slices': 1, 
                                            'pos' : (screen_size[0] * 0.25,  0), 
                                            'color' : utils.random_colors(3), 
                                            },
                                            {  
                                            'test name': 'Rings with fixed thickness',
                                            'expected result': 'Three concentric ellipse shaped ring shall appear fitting to the left half of the screen',
                                            'n_rings' : 3,
                                            'diameter' : [[screen_size[0] * 0.125,  screen_size[1] * 0.25], [screen_size[0] * 0.25,  screen_size[1] * 0.5], [screen_size[0] * 0.5,  screen_size[1]]],
                                            'inner_diameter' : screen_size[0] * 0.05, 
                                            'duration' : 0.0, 
                                            'n_slices': 3, 
                                            'pos' : (-screen_size[0] * 0.25,  0), 
                                            'color' : utils.random_colors(9), 
                                            },
                                            {  
                                            'test name': 'Rings with fixed thickness',
                                            'expected result': 'Three concentric ring shall appear with the same thickness',
                                            'n_rings' : 3,
                                            'diameter' : [screen_size[1] * 0.125,  screen_size[1] * 0.25,  screen_size[1] * 0.5],
                                            'inner_diameter' : screen_size[1] * 0.1, 
                                            'duration' : 0.5, 
                                            'n_slices': 2, 
                                            'pos' : (0,  0), 
                                            'color' : utils.random_colors(6), 
                                            },
                                            {  
                                            'test name': 'Rings with fixed thickness and spacing',
                                            'expected result': 'Five concentric ring shall appear with the same thickness and with 3 slices',
                                            'n_rings' : 5,
                                            'diameter' : screen_size[1] * 0.2,
                                            'inner_diameter' : screen_size[1] * 0.1, 
                                            'duration' : 1.5, 
                                            'n_slices': 3, 
                                            'pos' : (0,  0), 
                                            'color' : utils.random_colors(15), 
                                            },
                                            ]
                                            
        test_datas_show_gratings = [
                                            {  
                                            'test name': 'Check stimulus size orientation and position',
                                            'expected result': 'Balck and white bars shall go upside, covering the top right quarter of the screen',
                                            'duration' : 5.0, 
                                            'profile' : 'sqr', 
                                            'spatial_frequency' : 0.2 * screen_size[0], 
                                            'display_area' : (0.5 * screen_size[1],  0.5 * screen_size[0]), 
                                            'orientation' : -90, 
                                            'starting_phase' : 0, 
                                            'velocity' : 0.2 * screen_size[0], 
                                            'color_contrast' : 1.0, 
                                            'color_offset' : 0, 
                                            'pos' : (0.25 * screen_size[0],  0.25 * screen_size[1]), 
                                            'duty_cycle' : 0.5, 
                                            'noise_intensity' : 0
                                            }, 
                                            {  
                                            'test name': 'Check stimulus spatial frequency and velocity',
                                            'expected result': 'Each point shall go across the screen in 5 s, All the time 4 black and 4 white bars shall be seen ',
                                            'duration' : 5.0, 
                                            'profile' : 'sqr', 
                                            'spatial_frequency' : 0.25 * screen_size[0], 
                                            'display_area' : (0,  0), 
                                            'orientation' : 0, 
                                            'starting_phase' : 0, 
                                            'velocity' : 0.2 * screen_size[0], 
                                            'color_contrast' : 1.0, 
                                            'color_offset' : 0, 
                                            'pos' : (0,  0), 
                                            'duty_cycle' : 0.5, 
                                            'noise_intensity' : 0
                                            }, 
                                            {  
                                            'test name': 'Check orientation at fullscreen config and duty cycle',
                                            'expected result': 'Bars where the sizes are 25% white, 75% black. At the edges and corners no ungrated are shall appear ',
                                            'duration' : 3.0, 
                                            'profile' : 'sqr', 
                                            'spatial_frequency' : 0.1 * screen_size[0], 
                                            'display_area' : (0,  0), 
                                            'orientation' : 150, 
                                            'starting_phase' : 0, 
                                            'velocity' : 0.05 * screen_size[0], 
                                            'color_contrast' : 1.0, 
                                            'color_offset' : 0, 
                                            'pos' : (0,  0), 
                                            'duty_cycle' : 0.25, 
                                            'noise_intensity' : 0
                                            }, 
                                            {  
                                            'test name': 'Check starting phase and random noise',
                                            'expected result': 'The sawtooth profile shall be shifted with 45 degree and random noise shall be seen over the stimulus',
                                            'duration' : 3.0, 
                                            'profile' : 'saw', 
                                            'spatial_frequency' : 0.5 * screen_size[0], 
                                            'display_area' : (0,  0), 
                                            'orientation' : 0, 
                                            'starting_phase' : 45, 
                                            'velocity' : 0, 
                                            'color_contrast' : 0.8, 
                                            'color_offset' : 0.1, 
                                            'pos' : (0,  0), 
                                            'duty_cycle' : 0.5, 
                                            'noise_intensity' : 0.1
                                            }, 
                                            {  
                                            'test name': 'Check color contrast and offset',
                                            'expected result': 'Red waves shall turn to purple',
                                            'duration' : 5.0, 
                                            'profile' : 'sin', 
                                            'spatial_frequency' : 0.25 * screen_size[0], 
                                            'display_area' : (0.25 * screen_size[0],  0.25 * screen_size[1]), 
                                            'orientation' :150, 
                                            'starting_phase' : 0, 
                                            'velocity' : 0.1 * screen_size[0], 
                                            'color_contrast' : [0.0,  0.0,  1.0], 
                                            'color_offset' : [1.0,  0.0,  0.0],
                                            'pos' : (0,  0),
                                            'duty_cycle' : 0.5, 
                                            'noise_intensity' : 0
                                            },
                                            ] 
                                            
        self.test_data_set = [test_datas_show_image,  test_datas_show_movie,  test_datas_show_shape,  test_datas_show_checkerboard,  test_datas_show_ring,  test_datas_show_gratings]
