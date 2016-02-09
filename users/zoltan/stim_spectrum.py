import numpy,os
from PIL import Image
from pylab import *
folder='/tmp/capture'
framerate=60
speed=800
s=numpy.asarray(Image.open(os.path.join(folder,os.listdir(folder)[0])))[:,:,0].shape
frames=numpy.zeros((len(os.listdir(folder)),s[0],s[1]), dtype=numpy.uint8)
files=os.listdir(folder)
files.sort()
for i in range(len(files)):
    fn=files[i]
    frames[i]=numpy.asarray(Image.open(os.path.join(folder,fn)))[:,:,0]
profile=frames[:,10,10]
#profile=3*numpy.sin(0.2*numpy.arange(profile.shape[0]))+2
t=numpy.linspace(0,profile.shape[0]/float(framerate),profile.shape[0])
s=speed*t#Space domain
spectrum=abs(numpy.fft.rfft(profile,profile.shape[0]))/profile.shape[0]
frq=numpy.fft.fftfreq(profile.shape[0], 1.0/framerate)[:spectrum.shape[0]]
figure(1);plot(frq,spectrum)
figure(2);plot(t,profile);show()
