#gratings stimulus
#user_log_file_path = '/home/log.txt'
orientations = [0,  90,  180,  270]
velocity = 300
spatial_frequency = 100
duration_per_orientation = 3.0
pause_between_gratings = 0.3

for orientation in orientations:
    self.st.show_gratings(duration = duration_per_orientation, orientation = orientation, velocity = velocity, spatial_frequency = spatial_frequency)
    self.st.clear_screen(pause_between_gratings,  0.0)
