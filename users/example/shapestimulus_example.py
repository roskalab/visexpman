#shape stimulus examples
#self.st.show_shape(shape = '',  duration = 0.0,  position = (0,  0),  color = [1.0,  1.0,  1.0],  orientation = 0.0,  size = [0,  0],  formula = [],  ring_size = 1.0)
#user_log_file_path = '/home/log.txt'

example = 7
for i in range(8):
    if not self.config.SHOW_ALL_EXAMPLES:
        example_i = example
    else:
        example_i = i
        
    if example_i == 0:
        self.st.show_shape(shape = 'rect',  duration = 0.0,  size = [10,  100])
        
    elif example_i == 1:    
        self.st.show_shape(shape = 'circle',  duration = 0.0,  size = 100)    
        
    elif example_i == 2:
        self.st.show_shape(shape = 'annuli',  duration = 1.0,  color = [1.0, 0.0, 0.0], size = [210,  100],  ring_size = [50,  10])
        
    elif example_i == 3:
        parameters = []
        posx = ['100*sin(t)',  parameters]
        posy = ['100*cos(t)',  parameters]
        ori = ['',  []]  #unconfigured parametric control
        color_r = ['sin(t)',  parameters]
        color_g = ['cos(t)',  parameters]
        color_b = ['cos(t+pi*0.25)',  parameters]
        #the order of parametric control configurations matter
        formula = [posx,  posy,  ori, color_r,  color_g,  color_b]
        self.st.show_shape(shape = 'rect',  duration = 5.0,  size = [100,  200],  formula = formula)
        
    elif example_i == 4:
        self.st.show_shape(shape = 'rect',  duration = 1.0,  size = [10,  100])
        self.st.show_shape(shape = 'annuli',  duration = 1.0,  color = [1.0, 0.0, 0.0], size = [210,  100],  ring_size = [50,  10])

    elif example_i == 5:
        #show circles with random color, size and position
        duration = 3.0
        n_frames = int(duration * self.config.EXPECTED_FRAME_RATE)
        col = utils.random_colors(n_frames)
        from numpy import random
        pos = random.rand(n_frames,  2)
        size = random.rand(n_frames)
        pos = (pos  * 500 - 250).tolist()
        size = (size * 500).tolist()
        for i in range(n_frames):
            self.st.show_shape(shape = 'circle',  duration = 0.0,  size = size[i],  pos =pos[i],  color = col[i])
            if self.st.stimulation_control.abort_stimulus():
                break
                
    elif example_i == 6:
        parameters = []
        posx = ['100*sin(t)',  parameters]
        posy = ['',  []]
        ori = ['10*t',  []]  #unconfigured parametric control
        color_r = ['',  []]
        color_g = ['cos(t)',  parameters]
        color_b = ['cos(t+pi*0.25)',  parameters]
        #the order of parametric control configurations matter
        formula = [posx,  posy,  ori, color_r,  color_g,  color_b]
        self.st.show_shape(shape = 'rect',  duration = 5.0,  size = [100,  200],  formula = formula)
        
    elif example_i == 7:
        self.st.show_shape(shape = 'rect',  duration = 0.0,  size = [10,  100],  flip = False)
        self.st.show_shape(shape = 'rect',  duration = 0.0,  size = [10,  100],  pos = (100, 0))
        from time import sleep
        sleep(1.0)
