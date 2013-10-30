#examples for handling stimulus hardware, like parallel port, filter wheel, etc
#self.st.set_parallel(bitmask)
#user_log_file_path = '/home/log.txt'

example = 0

if example == 0:
    switching_delay = 146e-6    
    period = 100e-3
    for i in range(int(1.0/period)):
        self.st.set_parallel(4)
        time.sleep(0.5 * period - switching_delay)
        self.st.set_parallel(0)
        time.sleep(0.5 * period - switching_delay)
