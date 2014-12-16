'''
Stimulus for Santiago's experiment,2014 dec
'''
from PIL import Image
import shutil
import os
import os.path
import subprocess
import numpy
folder = '/home/rz/rzws/dataslow/roskalab/santiago_stim_videos/capture'
repetitions = 3
add_flash=True
ontime=4
offtime=4
frame_rate=60

if __name__=='__main__':
    if os.path.exists('/tmp/frames'):
        shutil.rmtree('/tmp/frames')
    os.mkdir('/tmp/frames')
    files = map(os.path.join, len(os.listdir(folder))*[folder],os.listdir(folder))
    files.sort()
    files = repetitions*files
    res=[shutil.copy2(files[i],os.path.join('/tmp/frames', 'f_{0:0=5}.png'.format(i))) for i in range(len(files))]
    onframe=numpy.ones_like(numpy.asarray(Image.open(files[0])),dtype=numpy.uint8)
    pattern=[1,0]*repetitions
    frame_colors = numpy.repeat(numpy.array(pattern),frame_rate*ontime)
    for i in range(frame_colors.shape[0]):
        Image.fromarray(frame_colors[i]*255*onframe).save('/tmp/frames/f_{0:0=5}.png'.format(i+len(res)))
    subprocess.call('avconv -y -r 60 -i /tmp/frames/f_%05d.png -map 0 -c:v libx264 -b 5M /tmp/moving_bar_natural_bar_rep_{0}.mp4'.format(repetitions),shell=True)
