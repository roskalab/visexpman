'''
Contains video file related functions
'''
import fileop
import subprocess
import platform
import tempfile
import os,shutil
import unittest
from PIL import Image

def get_fps(filename):
    logfile = os.path.join(tempfile.gettempdir(), 'fps.txt')
    command = '{0}probe "{1}" 2>{2}'.format('av' if platform.system() == 'Linux' else 'ff', filename, logfile)
    subprocess.call(command, shell=True)
    with open(logfile, 'r') as f:
        l = f.read()
    os.remove(logfile)
    return [float(item.replace('tbr','')) for item in l.split('\n')[l.split('\n').index([line for line in l.split('\n') if 'Duration: ' in line][0])+1].split(', ') if 'tbr' in item][0]
    
def images2mpeg4(folder, video_path,  fps):
    if os.path.exists(video_path):
        os.remove(video_path)
    filenames=os.listdir(folder)
    filenames.sort()
    os.remove(os.path.join(folder,filenames[-1]))
    tag=filenames[0].split('0000')[0]
    cmd = 'ffmpeg' if os.name=='nt' else 'avconv'
    command = '{3} -y -r {0} -i {1} -map 0 -c:v libx264 -b 5M {2}'.format(fps, os.path.join(folder, '{0}%5d.png'.format(tag)), video_path,cmd)
    subprocess.call(command, shell=True)
    
def array2mp4(array, videofile, fps):
    folder=os.path.join(tempfile.gettempdir(), 'vf')
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.mkdir(folder)
    for i in range(array.shape[0]):
        Image.fromarray(array[i]).save(os.path.join(folder, 'f{0:0=5}.png'.format(i)))
    images2mpeg4(folder, videofile, fps)
    
class TestVideoFile(unittest.TestCase):
    def test_01_frame_rate(self):
        folder = '/home/rz/codes/data//181214_Lema_offcell'
        results = map(get_fps, [f for f in fileop.listdir_fullpath(folder) if '.avi' in f])
        map(self.assertLess, results, [100] * len(results))
        map(self.assertGreater, results, [10] * len(results))
    
    def test_02_array2mp4(self):
        import numpy
        array=numpy.cast['uint8'](numpy.random.random((240, 640, 480, 3))*255)
        array2mp4(array, '/tmp/t.mp4', 24) 
    
if __name__=='__main__':
    unittest.main()
