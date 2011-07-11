#checkerboard stimulus
#user_log_file_path = '/home/log.txt'

if self.config.SCREEN_RESOLUTION[0] == 1680 and self.config.SCREEN_RESOLUTION[1] == 1050:
    box_side = 210.0
elif self.config.SCREEN_RESOLUTION[0] == 800 and self.config.SCREEN_RESOLUTION[1] == 600:
    box_side = 100.0
elif self.config.SCREEN_RESOLUTION[0] == 1024 and self.config.SCREEN_RESOLUTION[1] == 768:
    box_side = 128.0

n_checkers = (int(self.config.SCREEN_RESOLUTION[0]/box_side), int(self.config.SCREEN_RESOLUTION[1]/box_side))
box_size = [box_side, box_side]

#checkerboard:
w = [1.0,1.0,1.0]
b = [1.0,0.0,0.0]

cols = []
phase = 0
for i in range(n_checkers[0] * n_checkers[1]):
    if i % n_checkers[0] == 0:
         if phase == 1:
             phase = 0
         elif phase == 0:
            phase = 1
    if i%2 == phase:
        cols.append(b)
    else:
        cols.append(w)

while True:
    self.st.show_checkerboard(n_checkers, duration = 0, pos = (0, 0), color = cols, box_size = box_size)
    if self.st.stimulation_control.abort_stimulus():
        break
