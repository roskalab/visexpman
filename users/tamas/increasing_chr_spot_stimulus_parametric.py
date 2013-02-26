#Changes
# 2011 07 19: moving and stepping dots
#if parameters are not provided, create them with default values
#template for setting parameters
# chr_annulus = 0 #0,1
# post_stim_time = 0.0
# on_pulse_width = 100.0 
# off_pulse_width = 100.0 
# on_color = 'blue'
# off_color = 'green'
# on_time = 2.0
# off_time = 2.0
    
parameters = locals()
if not parameters.has_key('chr_stimulation_enable'):
    chr_stimulation_enable = True #True/False
if not parameters.has_key('stimulus_length'):
    stimulus_length = 'short' #'long'/'short'/'no'/'stepping_circle'/'moving_circle'
if not parameters.has_key('pulse_width'):
    pulse_width = 100 #ms
if not parameters.has_key('on_light_level'):
    on_light_level = 'ND40' #'ND0' ... 'ND40'
if not parameters.has_key('off_light_level'):
    off_light_level = 'ND40' #... 'ND40'
if not parameters.has_key('nd_level'):
    nd_level = 'ND100' #...'ND100'
if not parameters.has_key('chr_annulus'):
    chr_annulus = 0 #0,1
if not parameters.has_key('post_stim_time'):
    post_stim_time = 0.0
if not parameters.has_key('on_pulse_width'):
    on_pulse_width = 100.0 #ms
if not parameters.has_key('off_pulse_width'):
    off_pulse_width = 100.0 #ms
if not parameters.has_key('on_color'):
    on_color = 'blue'  #blue/green/orange
if not parameters.has_key('off_color'):
    off_color = 'green'
if not parameters.has_key('on_time'):    
    on_time = 2.0 #s
if not parameters.has_key('off_time'):    
    off_time = 4.0 #s


if on_color == 'blue':
    on_color = self.config.FILTER_470
elif on_color == 'green':
    on_color = self.config.FILTER_530
elif on_color == 'orange':
    on_color = self.config.FILTER_590
    
if off_color == 'blue':
    off_color = self.config.FILTER_470
elif off_color == 'green':
    off_color = self.config.FILTER_530
elif off_color == 'orange':
    off_color = self.config.FILTER_590
    
#increasing spot
import time

pos = (0,  0)
background_color = 0
#With this parameter you can control the time between showing fullscreen white and opening the shutter
flash_preset_time = 1.0
#With this parameter you can control the time between closing the shutter and turning off the fullscreen white
flash_post_time = 1.0

#===INPUT PARAMETERS===
#required configurations:
#first light stimulus shall come at 5s

#== Visual stimulus parameters ==
annulus_size = 400
if stimulus_length == 'short':
    sizes = [800]
elif stimulus_length == 'long':
    sizes = [25,  50, 100,  200, 400, 800, 1600] # 800
elif stimulus_length == 'no':
    sizes = [0]
color = 1.0 #0...1, this corresponds to the 0...255 range
#== Stepping circles parameters ==
stepping_circles_disc_size = 800.0
stepping_circles_step_size = 100.0 #um
stepping_circles_on_time = 2.0
stepping_circles_off_time = 5.0
stepping_circles_horizontal_range = [-800.0, 800.0]

#calculations
stepping_circles_number_of_steps = int((stepping_circles_horizontal_range[1] - stepping_circles_horizontal_range[0]) / stepping_circles_step_size)+1
stepping_circles_horizontal_positions = numpy.linspace(stepping_circles_horizontal_range[0],stepping_circles_horizontal_range[1], stepping_circles_number_of_steps)

#== Moving circles parameters ==
moving_circles_disc_size = 800.0
moving_circles_speed = 600.0 #600.0 #um/s
moving_circles_horizontal_range = [-1600, 1600.0]
moving_circles_duration = (moving_circles_horizontal_range[1] - moving_circles_horizontal_range[0]) / moving_circles_speed
#chr_stimulation_enable = True
chr_on_pulse_width = float(on_pulse_width) * 1e-3 #10, 50, 100, 500 ms
chr_off_pulse_width = float(off_pulse_width) * 1e-3
no_chr_preset_wait_time = 4.0
chr_switch_off_delay = 0.0
chr_on_nd_filter = self.config.CHR_LIGHT_LEVELS[on_light_level] #filterwheel2_ND10# same nd level for on and off, additionally off is stronger 10 than on
chr_off_nd_filter = self.config.CHR_LIGHT_LEVELS[off_light_level] #filterwheel2_ND10
experiment_filterwheel_combination = self.config.EXPERIMENT_ND_LEVELS[nd_level]#(filterwheel1_ND0, filterwheel2_ND20) #all combinations except for  nd0 nd 50 combination to avoid redunancy
#===END OF INPUT PARAMETERS===
# post_experiment_filterwheel_combination = (self.config.FILTERWHEEL1_IR, self.config.FILTERWHEEL2_ND50)
chr_on_filterwheel_combination = (on_color, chr_on_nd_filter)
chr_off_filterwheel_combination = (off_color, chr_off_nd_filter)

if self.config.SERIAL_PORT_SHUTTER:
    #Serial port controlled shutter initialization
    import generic.Instrument
    shutter = generic.Instrument.Shutter(self.config,id = 0)

if chr_stimulation_enable:
    #move filterwheel to chr on filter
    if self.config.FILTERWHEEL_ENABLE:
        self.filterwheels[chr_on_filterwheel_combination[0][0]].set(chr_on_filterwheel_combination[0][1])
        self.filterwheels[chr_on_filterwheel_combination[1][0]].set(chr_on_filterwheel_combination[1][1])
    time.sleep(1.0)
    #show white screen then open shutter
    if chr_annulus == 0:
        self.st.clear_screen(duration = flash_preset_time,  color = 1.0)
    elif chr_annulus == 1:
        self.st.clear_screen(duration = 0.0,  color = 1.0)
        self.st.show_shape(shape = 'circle',  duration = flash_preset_time,  size = annulus_size,  pos = pos,  color = 0.0)

    if self.config.SERIAL_PORT_SHUTTER:
        shutter.toggle()
        time.sleep(chr_on_pulse_width)
        shutter.toggle()
    else:
        self.st.set_parallel(0)
        self.st.set_parallel(self.config.SHUTTER_CONTROL_VALUE)
        time.sleep(chr_on_pulse_width)
        self.st.set_parallel(0)
    time.sleep(flash_post_time)
    self.st.clear_screen(duration = 0.1,  color = 0.0)
    
    #move filterwheel to required nd level
    if self.config.FILTERWHEEL_ENABLE:
        self.filterwheels[experiment_filterwheel_combination[0][0]].set(experiment_filterwheel_combination[0][1])
        self.filterwheels[experiment_filterwheel_combination[1][0]].set(experiment_filterwheel_combination[1][1])
    time.sleep(1.0)
else:
    time.sleep(no_chr_preset_wait_time)

#open shutter
if stimulus_length == 'stepping_circle' or stimulus_length == 'moving_circle':
    if self.config.SERIAL_PORT_SHUTTER:
        shutter.toggle()
    else:
        self.st.set_parallel(self.config.SHUTTER_CONTROL_VALUE)
    
if stimulus_length == 'stepping_circle':
    for stepping_circles_horizontal_position in stepping_circles_horizontal_positions:
        self.st.show_shape(shape = 'circle',  duration = stepping_circles_on_time,  size = stepping_circles_disc_size,  pos = (stepping_circles_horizontal_position, 0),  color = color)    
        self.st.clear_screen(stepping_circles_off_time,  background_color)    
        if self.st.stimulation_control.abort_stimulus():
            break
elif stimulus_length == 'moving_circle':
    parameters = [moving_circles_horizontal_range[0]]
    posx = ['prev + ' + str(float(moving_circles_speed) / self.config.EXPECTED_FRAME_RATE),  parameters]
    posy = ['',  []]
    ori = ['',  []]  #unconfigured parametric control
    color_r = ['',  []]
    color_g = ['',  []]
    color_b = ['',  []]
    formula = [posx,  posy,  ori, color_r,  color_g,  color_b]
    self.st.show_shape(shape = 'circle',  duration = moving_circles_duration,  size = moving_circles_disc_size,  pos = (moving_circles_horizontal_range[0],0), color = color, formula = formula)
    self.st.clear_screen(0.0,  background_color)    
else:
    for size in sizes:
        self.st.show_shape(shape = 'circle',  duration = 0.0,  size = size,  pos = pos,  color = color) 
        time.sleep(0.5)   
        self.st.set_parallel(0)
        self.st.set_parallel(self.config.SHUTTER_CONTROL_VALUE)
        psychopy.log.data('shutter on')
        time.sleep(on_time)
        self.st.set_parallel(0)
        psychopy.log.data('shutter off')
        if self.st.stimulation_control.abort_stimulus():
            break
        if off_time > 0.5:
            time.sleep(off_time-0.5)
        else:
            time.sleep(off_time)
        if self.st.stimulation_control.abort_stimulus():
            break
            
self.st.clear_screen(0.0,  background_color) 
#close shutter
if self.config.SERIAL_PORT_SHUTTER:
    shutter.toggle()
else:
    self.st.set_parallel(0)

if chr_stimulation_enable:
    #set filterhweel to chr off filter
    if self.config.FILTERWHEEL_ENABLE:
        self.filterwheels[chr_off_filterwheel_combination[0][0]].set(chr_off_filterwheel_combination[0][1])
        self.filterwheels[chr_off_filterwheel_combination[1][0]].set(chr_off_filterwheel_combination[1][1])
    #show white screen then open shutter
    if chr_annulus == 0:
        self.st.clear_screen(duration = flash_preset_time,  color = 1.0)
    elif chr_annulus == 1:
        self.st.clear_screen(duration = 0.0,  color = 1.0)
        self.st.show_shape(shape = 'circle',  duration = flash_preset_time,  size = annulus_size,  pos = pos,  color = 0.0)
    if self.config.SERIAL_PORT_SHUTTER:
        shutter.toggle()
        time.sleep(chr_off_pulse_width)
        shutter.toggle()
    else:
        self.st.set_parallel(0)
        self.st.set_parallel(self.config.SHUTTER_CONTROL_VALUE)
        time.sleep(chr_off_pulse_width)
        self.st.set_parallel(0)
    time.sleep(flash_post_time)
    self.st.clear_screen(duration = 0.1, color = 0.0)

    #select ir and nd20 filters
    if self.config.FILTERWHEEL_ENABLE:
        self.filterwheels[self.config.POST_EXPERIMENT_FILTERWHEEL_COMBINATION[0][0]].set(self.config.POST_EXPERIMENT_FILTERWHEEL_COMBINATION[0][1])
        self.filterwheels[self.config.POST_EXPERIMENT_FILTERWHEEL_COMBINATION[1][0]].set(self.config.POST_EXPERIMENT_FILTERWHEEL_COMBINATION[1][1])
    time.sleep(chr_switch_off_delay)
else:
    time.sleep(no_chr_preset_wait_time)
    
if self.config.SERIAL_PORT_SHUTTER:
    shutter.close_communication_interface()
    
time.sleep(post_stim_time)