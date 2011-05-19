#increasing spot
#user_log_file_path = '/home/log.txt'


sizes = [50,  100,  200, 300,  1000]
pos = (0,  0)
color = 1.0 #0...1
background_color = 0
on_time = 1.0 #s
off_time = 1.0 #s
n = 1

#eagle_stimulus parameters
eagle_stimulus = False
start_size = 0
end_size = 1000
duration = 2.0

if eagle_stimulus:
    off_time = 0.0
    on_time = 0.0
    import numpy
    sizes = numpy.linspace(start_size,  end_size,  duration * self.config.EXPECTED_FRAME_RATE)
    n = 2

for i in range(n):
    #in case of eagle stimulus swap colors after first run
    if i == 1 and eagle_stimulus:        
        self.st.clear_screen(0.0, color) 
        color = background_color
    
    for size in sizes:
        self.st.show_shape(shape = 'circle',  duration = on_time,  size = size,  pos = pos,  color = color)    
        if self.st.stimulation_control.abort_stimulus():
            break
            
        if off_time != 0.0:
            self.st.clear_screen(off_time,  background_color) 
            if self.st.stimulation_control.abort_stimulus():
                break

    
