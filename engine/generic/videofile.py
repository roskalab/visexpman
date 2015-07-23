'''
Contains video file related functions
'''
import fileop
import subprocess
import platform
import tempfile
import os
import os.path
import unittest


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
    command = 'avconv -y -r {0} -i {1} -map 0 -c:v libx264 -b 5M {2}'.format(fps, os.path.join(folder, 'f%5d.png'), video_path)
    subprocess.call(command, shell=True)
    
class TestVideoFile(unittest.TestCase):
    def test_01_frame_rate(self):
        folder = '/home/rz/codes/data//181214_Lema_offcell'
        results = map(get_fps, [f for f in fileop.listdir_fullpath(folder) if '.avi' in f])
        map(self.assertLess, results, [100] * len(results))
        map(self.assertGreater, results, [10] * len(results))
    
if __name__=='__main__':
    unittest.main()