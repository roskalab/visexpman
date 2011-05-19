import time
on_time = 1.0
off_time1 = 0.5
off_time2 = 1.5
color = [1.0,  0.0,  0.0]


self.st.set_parallel(1)
time.sleep(0.05)
self.st.set_parallel(0)

self.st.clear_screen(duration = off_time1,  color = self.config.BACKGROUND_COLOR)
self.st.clear_screen(duration = on_time,  color = color)
self.st.clear_screen(duration = off_time2,  color = self.config.BACKGROUND_COLOR)

self.st.set_parallel(2)
time.sleep(0.05)
self.st.set_parallel(0)
