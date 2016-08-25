#moving rectangles spot
#user_log_file_path = '/home/log.txt'

size = 100
step_size = 300
n_steps = 5
on_time = 1.0 #s
off_time = 1.0 #s

color = 1.0 #0...1
background_color = 0

pos = []
for i in range(n_steps):
    offset = -(n_steps - 1) * 0.5 * step_size
    x = int(offset + i * step_size)
    p = (x,  0)
    pos.append(p)

for position in pos:
    self.st.show_shape(shape = 'rect',  duration = on_time,  size = size,  pos = position,  color = color)    
    if self.st.stimulation_control.abort_stimulus():
        break
    self.st.clear_screen(off_time,  background_color)    
    if self.st.stimulation_control.abort_stimulus():
        break
