#examples for checkerboard stimulus
#self.st.show_checkerboard(n_checkers,  duration = 0.0,  pos = (0,  0),  color = [],  box_size = (0, 0))
#user_log_file_path = '/home/log.txt'

example = 0    

for i in range(2):
    
    if not self.config.SHOW_ALL_EXAMPLES:
        example_i = example
    else:
        example_i = i
        
    if example_i == 0:
        #fullscreen config
        n_checkers = (21, 21)
        box_size = [80, 50]    
        n_frames = 60    
        cols = utils.random_colors(n_checkers[0] * n_checkers[1],  frames = n_frames) 
        for i in range(n_frames):
            self.st.show_checkerboard(n_checkers, duration = 0, pos = (0, 0), color = cols[i], box_size = box_size)
            if self.st.stimulation_control.abort_stimulus():
                break
            
    elif example_i == 1:   
        n_checkers = (8, 8)
        box_size = [100, 100]    
        n_frames = 100
        cols = utils.random_colors(n_checkers[0] * n_checkers[1],  frames = n_frames,  greyscale = True) 
        for i in range(n_frames):
            self.st.show_checkerboard(n_checkers, duration = 0, pos = (0, 0), color = cols[i], box_size = box_size)
            if self.st.stimulation_control.abort_stimulus():
                break
                
    if not self.config.SHOW_ALL_EXAMPLES:
        break
