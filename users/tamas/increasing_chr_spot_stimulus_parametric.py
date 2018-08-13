
#if parameters are not provided, create them with default values
parameters = locals()
if 'chr_stimulation_enable' not in parameters:
    chr_stimulation_enable = True #True/False
if 'stimulus_length' not in parameters:
    stimulus_length = 'short' #'long'/'short'
if 'pulse_width' not in parameters:
    pulse_width = 100 #ms
if 'on_light_level' not in parameters:
    on_light_level = 'ND40' #'ND0' ... 'ND40'
if 'off_light_level' not in parameters:
    off_light_level = 'ND40' #... 'ND40'
if 'nd_level' not in parameters:
   nd_level = 'ND100' #...'ND100'

#increasing spot
import time

serial_port_shutter = True
pos = (0,  0)
background_color = 0
flash_preset_time = 1.0
flash_post_time = 1.0

filterwheel1_IR = (0, 1)
filterwheel1_ND0 = (0, 2)
filterwheel1_ND50 = (0, 3)
filter_590 = (0, 4)
filter_530 = (0, 5)
filter_470 = (0, 6)

filterwheel2_ND20 = (1, 1)
filterwheel2_ND30 = (1, 2)
filterwheel2_ND40 = (1, 3)
filterwheel2_ND50 = (1, 4)
filterwheel2_ND0 = (1, 5)
filterwheel2_ND10 = (1, 6)

chr_light_levels = {
			'ND0' : filterwheel2_ND0,
			'ND10' : filterwheel2_ND10,
			'ND20' : filterwheel2_ND20,
			'ND30' : filterwheel2_ND30,
			'ND40' : filterwheel2_ND40,
}

experiment_nd_levels = {
			'ND0' : (filterwheel1_ND0, filterwheel2_ND0),
			'ND10' : (filterwheel1_ND0, filterwheel2_ND10),
			'ND20' : (filterwheel1_ND0, filterwheel2_ND20),
			'ND30' : (filterwheel1_ND0, filterwheel2_ND30),
			'ND40' : (filterwheel1_ND0, filterwheel2_ND40),
			'ND50' : (filterwheel1_ND0, filterwheel2_ND50),
			'ND60' : (filterwheel1_ND50, filterwheel2_ND10),
			'ND70' : (filterwheel1_ND50, filterwheel2_ND20),
			'ND80' : (filterwheel1_ND50, filterwheel2_ND30),
			'ND90' : (filterwheel1_ND50, filterwheel2_ND40),
			'ND100' : (filterwheel1_ND50, filterwheel2_ND50),
}

#===INPUT PARAMETERS===
#required configurations:
#first light stimulus shall come at 5s
if stimulus_length == 'short':
    sizes = [800]
elif stimulus_length == 'long':
    sizes = [25,  50, 100,  200, 400, 800, 1600] # 800
color = 1.0 #0...1, this corresponds to the 0...255 range
on_time = 2.0 #s
off_time = 4.0 #s
#chr_stimulation_enable = True
chr_on_pulse_width = float(pulse_width) * 1e-3 #10, 50, 100, 500 ms
chr_off_pulse_width = float(pulse_width) * 1e-3
no_chr_preset_wait_time = 4.0
chr_switch_off_delay = 0.0
chr_off_color = filter_530 # filter_590 too
chr_on_nd_filter = chr_light_levels[on_light_level] #filterwheel2_ND10# same nd level for on and off, additionally off is stronger 10 than on
chr_off_nd_filter = chr_light_levels[off_light_level] #filterwheel2_ND10
experiment_filterwheel_combination = experiment_nd_levels[nd_level]#(filterwheel1_ND0, filterwheel2_ND20) #all combinations except for  nd0 nd 50 combination to avoid redunancy
#===END OF INPUT PARAMETERS===

post_experiment_filterwheel_combination = (filterwheel1_IR, filterwheel2_ND50)
chr_on_filterwheel_combination = (filter_470, chr_on_nd_filter)
chr_off_filterwheel_combination = (chr_off_color, chr_off_nd_filter)

if serial_port_shutter:
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
    self.st.clear_screen(duration = flash_preset_time,  color = 1.0)
    if serial_port_shutter:
        shutter.toggle()
        time.sleep(chr_on_pulse_width)
        shutter.toggle()
    else:
        self.st.set_parallel(0)
        self.st.set_parallel(2)
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
if serial_port_shutter:
    shutter.toggle()
else:
    self.st.set_parallel(2)
    
for size in sizes:
    self.st.show_shape(shape = 'circle',  duration = on_time,  size = size,  pos = pos,  color = color)    
    if self.st.stimulation_control.abort_stimulus():
        break
    self.st.clear_screen(off_time,  background_color)    
    if self.st.stimulation_control.abort_stimulus():
        break
        
#close shutter
if serial_port_shutter:
    shutter.toggle()
else:
    self.st.set_parallel(0)

if chr_stimulation_enable:
    #set filterhweel to chr off filter
    if self.config.FILTERWHEEL_ENABLE:
        self.filterwheels[chr_off_filterwheel_combination[0][0]].set(chr_off_filterwheel_combination[0][1])
        self.filterwheels[chr_off_filterwheel_combination[1][0]].set(chr_off_filterwheel_combination[1][1])
    #show white screen then open shutter
    self.st.clear_screen(duration = flash_preset_time,  color = 1.0)
    if serial_port_shutter:
        shutter.toggle()
        time.sleep(chr_off_pulse_width)
        shutter.toggle()
    else:
        self.st.set_parallel(0)
        self.st.set_parallel(2)
        time.sleep(chr_off_pulse_width)
        self.st.set_parallel(0)
    time.sleep(flash_post_time)
    self.st.clear_screen(duration = 0.1, color = 0.0)

    #select ir and nd20 filters
    if self.config.FILTERWHEEL_ENABLE:
        self.filterwheels[post_experiment_filterwheel_combination[0][0]].set(post_experiment_filterwheel_combination[0][1])
        self.filterwheels[post_experiment_filterwheel_combination[1][0]].set(post_experiment_filterwheel_combination[1][1])
    time.sleep(chr_switch_off_delay)
else:
    time.sleep(no_chr_preset_wait_time)
    
if serial_port_shutter:
    shutter.close_communication_interface()