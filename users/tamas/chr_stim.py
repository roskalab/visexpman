   
parameters = locals()

if not parameters.has_key('off_time'):
    off_time = 4.0
if not parameters.has_key('on_time'):    
    on_time = 2.0 #s    
if not parameters.has_key('on_color'):
    on_color = 'blue'  #blue/green/orange/white
if not parameters.has_key('on_light_level'):
    on_light_level = 'ND0' #...'ND40'


#after stim: nd20, ir filter
if on_color == 'blue':
    on_color = self.config.FILTER_470
elif on_color == 'green':
    on_color = self.config.FILTER_530
elif on_color == 'orange':
    on_color = self.config.FILTER_590
elif on_color == 'white':
    on_color = self.config.FILTERWHEEL1_ND0
    
chr_on_nd_filter = self.config.CHR_LIGHT_LEVELS[on_light_level]
chr_on_filterwheel_combination = (on_color, chr_on_nd_filter)
post_stim_filterwheel_combination = (self.config.FILTERWHEEL1_IR, self.config.FILTERWHEEL2_ND20)
import time

pos = (0,  0)
background_color = 0

if self.config.SERIAL_PORT_SHUTTER:
    #Serial port controlled shutter initialization
    import generic.Instrument
    shutter = generic.Instrument.Shutter(self.config,id = 0)

if self.config.FILTERWHEEL_ENABLE:
    self.filterwheels[chr_on_filterwheel_combination[0][0]].set(chr_on_filterwheel_combination[0][1])
    self.filterwheels[chr_on_filterwheel_combination[1][0]].set(chr_on_filterwheel_combination[1][1])
self.st.clear_screen(duration = 0.0,  color = 1.0)
time.sleep(off_time)
if self.config.SERIAL_PORT_SHUTTER:
    shutter.toggle()
else:
    self.st.set_parallel(0)
    self.st.set_parallel(self.config.SHUTTER_CONTROL_VALUE)
time.sleep(on_time)
if self.config.SERIAL_PORT_SHUTTER:
    shutter.toggle()
else:
    self.st.set_parallel(0)
time.sleep(off_time)
self.st.clear_screen(duration = 0.0,  color = 0.0)
if self.config.FILTERWHEEL_ENABLE:
    self.filterwheels[post_stim_filterwheel_combination[0][0]].set(post_stim_filterwheel_combination[0][1])
    self.filterwheels[post_stim_filterwheel_combination[1][0]].set(post_stim_filterwheel_combination[1][1])
    print post_stim_filterwheel_combination

if self.config.SERIAL_PORT_SHUTTER:
    shutter.close_communication_interface()