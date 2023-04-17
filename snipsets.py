import os
import psutil
import time

def LoadEstimator():
    time1 = time.time()
    #psutil.cpu_percent()
    UPDATE_DELAY = 5
    ram_avg_load = psutil.virtual_memory()[2]
    network_load_1 = psutil.net_io_counters()
    cpu_avg_load = psutil.cpu_percent(interval=UPDATE_DELAY) #monitor.cpu_averages()['cpu.average.5s']
    network_load_2 = psutil.net_io_counters()
    network_sent_avg_load = (network_load_2.bytes_sent - network_load_1.bytes_sent)/1024/UPDATE_DELAY   #Avarage upload speeed in the last 2 second in kbyte/sec
    network_recv_avg_load = (network_load_2.bytes_recv - network_load_1.bytes_recv)/1024/UPDATE_DELAY   #Avarage download speeed in the last 2 second in kbyte/sec
    avg_load = {"cpu" : cpu_avg_load, "ram" : ram_avg_load, "net_sent" : network_sent_avg_load , "net_recv" : network_recv_avg_load }
    print(f"Ellapsed: {time.time()-time1}" )
    return avg_load

print(LoadEstimator())
