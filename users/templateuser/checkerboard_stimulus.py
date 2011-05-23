#checkerboard stimulus
#user_log_file_path = '/home/log.txt'
n_checkers = (25,  25)
box_size = [20, 20]
duration = 2.0 #s
color = 'BW' #BW = balck and white, GS = greyscale

n_frames = int(duration * self.config.SCREEN_EXPECTED_FRAME_RATE)
cols = utils.random_colors(n_checkers[0] * n_checkers[1],  frames = n_frames,  greyscale = True,  inital_seed = 2) 
if color == 'BW':
    from numpy import *
    cols = array(cols)
    cols = where(cols < 0.5,  0.0,  1.0)
    cols = cols.tolist()
for i in range(n_frames):
    self.st.show_checkerboard(n_checkers, duration = 0, pos = (0, 0), color = cols[i], box_size = box_size)
    if self.st.stimulation_control.abort_stimulus():
        break