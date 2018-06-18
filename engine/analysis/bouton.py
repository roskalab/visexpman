from skimage.feature import register_translation
from PIL import Image
import numpy
from visexpman.engine.generic import fileop
from pylab import plot,show,legend,ylim
for i in range(1,4):
    files=fileop.listdir('/tmp/00{0}'.format(i))
    files.sort()
    images=[numpy.asarray(Image.open(f))for f in files]
    shift=[]
    for i in range(len(images)):
        if i>0:
            res= register_translation(images[0], images[i])[0]
            shift.append(res)
            #print i, res
    shift=numpy.array(shift)
    plot(shift[:,0])
    plot(shift[:,1])
    pass
ylim([-10,10])
legend(['no smear x', 'no smear y', 'little smear x', 'little smear y', 'more smear x', 'more smear y'])
show()
pass
