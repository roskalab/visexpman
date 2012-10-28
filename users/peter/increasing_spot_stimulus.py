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
# relative_positions = [(0, 0), (-100, 0), (100, 0)]
# 
# #eagle_stimulus parameters
# start_size = 0 #just for true, continuous growth, begin size
# end_size = 400 #just for true, continuous growth, end size
# duration = 6.0 
# 
# #self.filterwheels[0].set(1) #[0] if there is only one wheel, (x) the number of the filter, 1..6
# 
# import numpy
# sizes = numpy.linspace(start_size,  end_size,  duration * self.config.EXPECTED_FRAME_RATE)
# 
# while True: #until you dont stop
#     if self.st.stimulation_control.abort_stimulus():
#         break
#     for rel_pos in relative_positions: #python style for cycle, fetching elements from a list
#         actual_position = (pos[0] + rel_pos[0], pos[1] + rel_pos[1])
#         for i in range(2): #switching btw background and foreground colors // for cycle within a numerical range
#             if i == 1:
#                 self.st.clear_screen(0.0, color) 
#             elif i == 0:
#                 self.st.clear_screen(0.0, background_color)     
#             for size in sizes:
#                 if i == 1:
#                     self.st.show_shape(shape = 'circle',  duration = 0.0,  size = size,  pos = actual_position,  color = background_color)
#                 elif i ==0:
#                     self.st.show_shape(shape = 'circle',  duration = 0.0,  size = size,  pos = actual_position,  color = color)
#             
#             
# 
#     
