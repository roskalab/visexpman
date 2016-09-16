#examples for ring stimulus
#self.st.show_ring(n_rings, diameter,  inner_diameter = [],  duration = 0.0,  n_slices = 1,  colors = [],  pos = (0,  0))
#user_log_file_path = '/home/log.txt'

example = 5

for i in range(6):
    if not self.config.SHOW_ALL_EXAMPLES:
        example_i = example
    else:
        example_i = i
        
    if example_i == 0:
        n_rings = 3
        outer_diameter = [100,  200]
        inner_diameter = [50,  180]
        slices = 2
        col = utils.random_colors(n_rings * slices) 
        self.st.show_ring(n_rings, outer_diameter,  inner_diameter,  duration = 1.0,  n_slices = slices,  colors = col)
        
    elif example_i == 1:
        n_rings = 5
        outer_diameter = 100
        inner_diameter = 5
        slices = 1
        col = utils.random_colors(n_rings * slices) 
        self.st.show_ring(n_rings, outer_diameter,  inner_diameter,  duration = 1.0,  n_slices = slices,  colors = col)
        
    elif example_i == 2:
        n_rings = 4
        slices = 2
        outer_diameter = [100, 200, 300]
        inner_diameter = [90, 180, 250]
        colors = utils.random_colors(n_rings * slices) 
        self.st.show_ring(n_rings, outer_diameter,  inner_diameter, duration = 1.0,  n_slices = 2, colors = colors)
        
    elif example_i == 3:
        n_rings = 2
        outer_diameter = [[100, 200], [200, 300]]
        inner_diameter = [[90, 190], [190, 290]]
        colors = utils.random_colors(n_rings) 
        self.st.show_ring(n_rings, outer_diameter,  inner_diameter, duration = 1.0,  colors = colors) 
        
    elif example_i == 4:
        n_frames  = 60
        n_rings = 4
        slices = 2
        outer_d = 40
        inner_d = 20
       
        colors = utils.random_colors(n_rings * slices,  frames = n_frames)     
        
        for f in range(n_frames):
            self.st.show_ring(n_rings, outer_d,  inner_d,  duration = 0.0,  n_slices = slices,  colors = colors[f],  pos = (0,  0))
            #recommended code part, works when duration is zero
            if self.st.stimulation_control.abort_stimulus():
                break
        
    elif example_i == 5:
        n_rings = 3
        outer_diameter = [100,  200]
        inner_diameter = [50,  180]
        slices = 2
        col = utils.random_colors(n_rings * slices) 
        self.st.show_ring(n_rings, outer_diameter,  inner_diameter,  duration = 0.0,  n_slices = slices,  colors = col,  flip = False)
        self.st.show_ring(n_rings, outer_diameter,  inner_diameter,  duration = 0.0,  n_slices = slices,  colors = col, pos = (200, 0))
        
        
