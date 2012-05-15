parameters = locals()
if not parameters.has_key('wavelength_range'):
    wavelength_range = 'uv'
import time
#parameters
on_time=2.0
off_time=4.0
init_delay = 2.0
if wavelength_range == 'uv':
    wavelengths= [330,350,370,390, 410]
elif wavelength_range == 'm':
    wavelengths = [480, 500, 520, 540, 560]

repeats = 1
def toggle_shutter():
    import serial
    shutter_serial_port = serial.Serial(port ='COM6', baudrate = 9600, timeout = 0.1)
    shutter_serial_port.open()
    shutter_serial_port.write('ens\r')
    shutter_serial_port.close()
def init_polychrome(config):
    import ctypes
    import os.path
    dllref = ctypes.WinDLL(os.path.join(config.BASE_PATH,'till','TILLPolychrome.dll'))
    handle = ctypes.c_void_p()
    dllref.TILLPolychrome_Open(ctypes.pointer(handle),ctypes.c_int(0))
    return (handle,dllref)
def set_wavelength(handle, wavelength):
    import ctypes
    handle[1].TILLPolychrome_SetRestingWavelength(handle[0],ctypes.c_double(float(wavelength)))
def close_polychrome(handle):
    handle[1].TILLPolychrome_Close(handle[0])
start_time = time.time()
self.st.clear_screen(0, 0)
h=init_polychrome(self.config)
time.sleep(init_delay - (time.time()-start_time))
for i in range(repeats):
    for wavelength in wavelengths:
        set_wavelength(h,wavelength)
        if self.config.ENABLE_PARALLEL_PORT:
            self.parallel.setData(self.config.FRAME_TRIGGER_ON)
        toggle_shutter()
        time.sleep(on_time)
        if self.config.ENABLE_PARALLEL_PORT:
            self.parallel.setData(self.config.FRAME_TRIGGER_OFF)
        toggle_shutter()
        time.sleep(off_time)
        

close_polychrome(h)
