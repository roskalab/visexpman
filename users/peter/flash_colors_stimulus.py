#this stimulus can be used for gamma calibration
import time
import numpy
on_time = 1.0   #how long shows a color
off_time1 = 0.5  #times before and after the color screen
off_time2 = 0.5
color_step = 0.2 #0=black, 1=the brightest of the actual color

intensities = numpy.linspace(color_step,  1.0,  1.0/color_step) #creates the intensity list, starts from color_step

colors = [] #makes the colors

for intensity in intensities: #gray
    colors.append([intensity,  intensity, intensity])

for intensity in intensities: #red
    colors.append([intensity,  0.0,  0.0])

for intensity in intensities: #green
    colors.append([0.0,  intensity,  0.0])

for intensity in intensities: #blue
    colors.append([0.0,  0.0,  intensity])

for color in colors:

    self.st.clear_screen(duration = off_time1,  color = self.config.BACKGROUND_COLOR)
    self.st.clear_screen(duration = on_time,  color = color)
    self.st.clear_screen(duration = off_time2,  color = self.config.BACKGROUND_COLOR)
    
#    self.st.set_parallel(7)
#    time.sleep(0.05)
#    self.st.set_parallel(0)

    if self.st.stimulation_control.abort_stimulus():
        break
        
