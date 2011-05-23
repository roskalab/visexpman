#examples for grating stimulus
#self.st.show_gratings(duration = 0.0,  profile = 'sqr',  spatial_frequency = SCREEN_RESOLUTION['col'],  display_area = (0,  0),  orientation = 0,  starting_phase = 0.0,  velocity = 0.0,  color_contrast = 1,  color_offset = 0,  pos = (0,  0), duty_cycle = 0.5)
#user_log_file_path = '/home/log.txt'

example = 0

for i in range(7):
    if not self.config.SHOW_ALL_EXAMPLES:
        example_i = example
    else:
        example_i = i       
    
    if example_i == 0:
        self.st.show_gratings(duration = 3.0, orientation = 45, velocity = 100, spatial_frequency = 300,  duty_cycle = 0.5)          
        
    elif example_i == 1:
        self.st.show_gratings(duration = 3.0, profile = 'sin', display_area = (500, 500), starting_phase = 10, velocity = 100, spatial_frequency = 200)
        
    elif example_i == 2:
        self.st.show_gratings(duration = 1.0, profile = 'saw', velocity = 100, spatial_frequency = 200, color_contrast = [1.0,0.0,0.0], color_offset = [0.0,0.0,1.0])         
        
    elif example_i == 3:
        #random noise
        self.st.show_gratings(duration = 10.0,  profile = 'sqr',  spatial_frequency = 500,  display_area = (700,  700),  velocity = 50.0,  color_contrast = 0.5,  color_offset = 0.25,  noise_intensity = 0.15)
        
    elif example_i == 4:
        #different profiles for different color channels
        self.st.show_gratings(duration = 3.0,  profile = ['sin',  'cos',  'tri'],  spatial_frequency = 500,  display_area = (0,  700),  velocity = 50.0,  color_contrast = [0.5,  0.5,  0.0],  color_offset = 0.1,  noise_intensity = 0.05)
    elif example_i == 5:    
        #sequence of different spatial frequencies and orientations
        spatial_frequencies = [300,  1000]
        orientations = [0,  45,  170,  -90]
        orientations = [0]
        duration = 2.0
        velocity = 50
        display = (0, 0)
        profile = ['sin',  'cos',  'tri']
    #    profile = 'sqr'
        cc = [0.5,  0.5,  0.0]
        co = 0.1
        n = 0.0
        
        for spatial_frequency in spatial_frequencies:
            for orientation in orientations:
                self.st.show_gratings(duration = duration,  orientation = orientation,  profile = profile,  spatial_frequency = spatial_frequency,  display_area = display,  velocity = velocity,  color_contrast = cc,  color_offset = co,  noise_intensity = n)

    elif example_i == 6:
        self.st.show_gratings(duration = 3.0, profile = 'sin', display_area = (500, 500), starting_phase = 0, velocity = 100, spatial_frequency = 200)
