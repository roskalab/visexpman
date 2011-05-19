#this stimulus can be used for gamma calibration
import time
import numpy
on_time = 1.0
off_time1 = 0.5
off_time2 = 1.5
color_step = 0.1
intensities = numpy.linspace(color_step,  1.0,  1.0/color_step)

colors = []

for intensity in intensities:
    colors.append([intensity,  intensity, intensity])

for intensity in intensities:
    colors.append([intensity,  0.0,  0.0])

for intensity in intensities:
    colors.append([0.0,  intensity,  0.0])

for intensity in intensities:
    colors.append([0.0,  0.0,  intensity])

self.st.set_parallel(1)
time.sleep(0.05)
self.st.set_parallel(0)

for color in colors:
    
    
#    self.st.set_parallel(7)
#    time.sleep(0.05)
#    self.st.set_parallel(0)

    self.st.clear_screen(duration = off_time1,  color = self.config.BACKGROUND_COLOR)
    self.st.clear_screen(duration = on_time,  color = color)
    self.st.clear_screen(duration = off_time2,  color = self.config.BACKGROUND_COLOR)
    
#    self.st.set_parallel(7)
#    time.sleep(0.05)
#    self.st.set_parallel(0)

    if self.st.stimulation_control.abort_stimulus():
        break
        

self.st.set_parallel(2)
time.sleep(0.05)
self.st.set_parallel(0)
