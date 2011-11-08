#direction selective stimulus
#user_log_file_path = '/home/log.txt'

size = [100, 20] #size of the moving object
color = 1.0 #white
background_color = 0 #black
oris = [0, 10,  30, 45,  90, 100,  150,  180, 200,  250,  270,  300,  330] #orientations of the moving rectangle
#oris = [10, 45] #you may overwrite the previous values
speed = 50 #pixel/s
off_time = 0.5 #time of the black screen while changing direction
projector_resolution = (800,600) #actual projector resolution

display_area = (600,600)



position = (float(-self.config.SCREEN_RESOLUTION[0])/2.0+float(projector_resolution[0])/2.0, float(self.config.SCREEN_RESOLUTION[1])/2.0-float(projector_resolution[1])/2.0)
#self.config.XX is defined in Configurations.py/PetersConfig
#hidden parameters are in the Stimulationlibrary.py, whet is not expliciteluy given in the scripts, is taken from here


from math import pi,  sqrt,  cos,  sin

for ori in oris:    
    ori_rad = ori * pi / 180
    path_length = sqrt((cos(ori_rad) * display_area[0]) ** 2 + (sin(ori_rad) * display_area[1] )**2)
    if type(size) is list:
        path_length = path_length - sqrt(size[0] ** 2 + size[1] ** 2)
    else:
        path_length = path_length - size        
        
    start_pos = (position[0] + int(-0.5 * path_length * cos(ori_rad)), position[1] + int(-0.5 * path_length * sin(ori_rad)))  
    
    posx = ['prev + ' + str(float(speed) / self.config.EXPECTED_FRAME_RATE) + '* cos(' + str(ori_rad) + ')',  []]
    posy = ['prev + ' + str(float(speed) / self.config.EXPECTED_FRAME_RATE) + '* sin(' + str(ori_rad) + ')',  []]
    ori_ = ['',  []]  #unconfigured parametric control
    color_r = ['', []]
    color_g = ['', []]
    color_b = ['', []]
    #the order of parametric control configurations matter
    formula = [posx,  posy,  ori_, color_r,  color_g,  color_b]
    duration = path_length / speed
    self.st.show_shape(shape = 'rect',  duration = duration,  pos = start_pos, color = color,   orientation = -ori,  size = size,  formula = formula)
    self.st.clear_screen(off_time,  background_color)
