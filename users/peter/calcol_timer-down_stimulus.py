#this stimulus can be used for photon count calibration
import time
import numpy
on_time = 20.0   #how long shows a color
#off_time1 = 2  #times before and after the color screen
#off_time2 = 2
color_step = 0.05 #0=black, 1=the brightest of the actual color, that is 255

intensities = numpy.linspace(1.0, color_step,  1.0/color_step) #creates the intensity list, starts from color_step

colors = [] #makes the colors

#for intensity in intensities: #gray
#    colors.append([intensity,  intensity, intensity])

#for intensity in intensities: #red
#    colors.append([intensity,  0.0,  0.0])

#for intensity in intensities: #green
#    colors.append([0.0,  intensity,  0.0])

#for intensity in intensities: #blue
#   colors.append([0.0,  0.0,  intensity])

for intensity in intensities: #blue-green
    colors.append([0.0,  intensity,  intensity])

for color in colors:

    #self.st.clear_screen(duration = off_time1,  color = self.config.BACKGROUND_COLOR)
    print color
    self.st.clear_screen(duration = on_time,  color = color)
    #time.sleep(4.0)
    if self.st.stimulation_control.abort_stimulus():
        break

    #self.st.clear_screen(duration = off_time2,  color = self.config.BACKGROUND_COLOR)
    
#    self.st.set_parallel(7)
#    time.sleep(0.05)
#    self.st.set_parallel(0)

        
