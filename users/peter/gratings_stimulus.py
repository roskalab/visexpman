# #gratings stimulus
# #user_log_file_path = '/home/log.txt'
# orientations = [0,  90,  180,  270]
# velocity = 40
# spatial_frequency = 300 #wavelength
# duration_per_orientation = 10.0 # time in seconds
# pause_between_gratings = 0.3
# duty=0.6 #if this is larger, more white in a wavelength
# 
# projector_resolution = (800,600) #resolution of the actual projector, usually 800x600
# display_area = (800,800) #just for this script, because it rotates the whole display area, what should remain the same
# 
# position = (float(-self.config.SCREEN_RESOLUTION[0])/2.0+float(projector_resolution[0])/2.0, float(self.config.SCREEN_RESOLUTION[1])/2.0-float(projector_resolution[1])/2.0)
# #self.config.XX is defined in Configurations.py/PetersConfig
# #hidden parameters are in the Stimulationlibrary.py, whet is not expliciteluy given in the scripts, is taken from here
# 
# for orientation in orientations:
#     self.st.show_gratings(duration = duration_per_orientation, orientation = orientation, velocity = velocity, display_area = display_area, pos=position,  duty_cycle=duty, spatial_frequency = spatial_frequency)
#     self.st.clear_screen(pause_between_gratings,  0.0)
