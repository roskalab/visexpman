# #test stimulus
# #user_log_file_path = '/home/log.txt'
# 
# totalduration=200 #sec
# ontime=10 
# offtime=10
# #the ontime-offtime cycle is repeated until totalduration ios over
# 
# for i in range(totalduration/(ontime+offtime)): #so many cycles
#     self.st.clear_screen(duration = ontime,  color = 1.0)
#     if self.st.stimulation_control.abort_stimulus(): #aborting: 2 lines
#         break
#     self.st.clear_screen(duration = offtime,  color = 0.0)
#     if self.st.stimulation_control.abort_stimulus(): #aborting: 2 lines
#         break
