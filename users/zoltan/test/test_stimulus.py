#test stimulus
#user_log_file_path = '/home/log.txt'

test = 0


#test  == 0: toggle between black and white screens
#test == 1: show white screen


test_time = 3.0
preset_time  = 0.0
posttest_delay = 0.0

self.st.clear_screen(duration = preset_time,  color = 0.0)

if test == 0:
    for i in range(int(self.config.SCREEN_EXPECTED_FRAME_RATE * test_time * 0.5)):
        self.st.clear_screen(duration = 0.0,  color = 1.0)
        self.st.clear_screen(duration = 0.0,  color = 0.0)
elif test == 1:
    self.st.clear_screen(duration = test_time,  color = 1.0)
    
self.st.clear_screen(duration = posttest_delay,  color = 0.0)