# #checkerboard stimulus
# #user_log_file_path = '/home/log.txt'
# n_checkers = (40,  30) #number of small ubits
# box_size = [20, 20] #size of one small unit
# duration = 200.0 #s
# color = 'BW' #BW = balck and white, GS = greyscale, COL = color
# pattern_time = 0.5 #how long one pattern is showed
# projector_resolution = (800,600) #actual projector resolution
# 
# position = (float(-self.config.SCREEN_RESOLUTION[0])/2.0+float(projector_resolution[0])/2.0, float(self.config.SCREEN_RESOLUTION[1])/2.0-float(projector_resolution[1])/2.0)
# #self.config.XX is defined in Configurations.py/PetersConfig
# #hidden parameters are in the Stimulationlibrary.py, whet is not expliciteluy given in the scripts, is taken from here
# 
# n_frames = int(duration / pattern_time)
# print n_frames
# if color == 'COL':
#    greyscale_switch = False
# else:
#    greyscale_switch = True
# cols = utils.random_colors(n_checkers[0] * n_checkers[1],  frames = n_frames,  greyscale = greyscale_switch,  inital_seed = 2)
# #cols: here 4 parameters are used, byu it has 2 dimensions - one goes like a snake through the checkerboard, the other one is the time
# #here are stored the colors used during the stimulation
# 
# if color == 'BW':
#     from numpy import *
#     cols = array(cols)
#     cols = where(cols < 0.5,  0.0,  1.0)
#     cols = cols.tolist()
# for i in range(n_frames):
#     self.st.show_checkerboard(n_checkers, duration = pattern_time, pos = position, color = cols[i], box_size = box_size)
#     if self.st.stimulation_control.abort_stimulus(): #aborting: 2 lines
#         break
