# #moving rectangles spot
# #user_log_file_path = '/home/log.txt'
# 
# size = 100
# step_size = 100 #distance between spots
# n_steps = 6 # number of flashes in a direction
# on_time = 1.0 #s
# off_time = 1.0 #s
# 
# color = 1.0 #0...1
# background_color = 0
# 
# projector_resolution = (800,600) #actual projector resolution
# origo = (float(-self.config.SCREEN_RESOLUTION[0])/2.0+float(projector_resolution[0])/2.0, float(self.config.SCREEN_RESOLUTION[1])/2.0-float(projector_resolution[1])/2.0)
# #self.config.XX is defined in Configurations.py/PetersConfig
# #hidden parameters are in the Stimulationlibrary.py, whet is not expliciteluy given in the scripts, is taken from here
# 
# pos = []
# 
# for j in range (n_steps):
#     for i in range(n_steps):
#         offset = -(n_steps - 1) * 0.5 * step_size
#         x = int(offset + i * step_size) + origo[0]
#         y=int(offset + j*step_size)+origo[1]
#         p = (x,  y)
#         pos.append(p)
# 
# 
# for position in pos:
#     self.st.show_shape(shape = 'rect',  duration = on_time,  size = size,  pos = position,  color = color)    
#     if self.st.stimulation_control.abort_stimulus():
#         break
#     self.st.clear_screen(off_time,  background_color)    
#     if self.st.stimulation_control.abort_stimulus():
#         break
