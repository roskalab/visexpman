# #increasing spot
# #user_log_file_path = '/home/log.txt'
# 
# projector_resolution = (800,600) #actual projector resolution
# 
# pos = (float(-self.config.SCREEN_RESOLUTION[0])/2.0+float(projector_resolution[0])/2.0, float(self.config.SCREEN_RESOLUTION[1])/2.0-float(projector_resolution[1])/2.0)
# #self.config.XX is defined in Configurations.py/PetersConfig
# #hidden parameters are in the Stimulationlibrary.py, whet is not expliciteluy given in the scripts, is taken from here
# 
# color = 1.0 #0...1
# background_color = 0
# 
# sizes = [50,  100,  200, 300, 400, 500, 600] #flashes disks with different sizes (diamater), these are the sizes of the disks
# on_time = 1.0 #s
# off_time = 1.0 #s
# 
# #self.filterwheels[0].set(1) #[0] if there is only one wheel, (x) the number of the filter, 1..6
# 
# for size in sizes: # for cycle for sizes
#     self.st.show_shape(shape = 'circle',  duration = on_time,  size = size,  pos = pos,  color = color) #parameters of a shown disk
#     if self.st.stimulation_control.abort_stimulus(): #aborting: 2 lines
#         break
#     if off_time != 0.0:
#         self.st.clear_screen(off_time,  background_color) #clearing
#     if self.st.stimulation_control.abort_stimulus(): #aborting: 2 lines
#         break
#             
# 
#     
