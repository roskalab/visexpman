import subprocess
import os
import os.path
from visexpman.engine.generic import fileop

def video2stimulus_frames(filename):
    '''
    1. convert video to 60 frame rate
    2. generate images
    '''
    fps = 60
    outfolder = filename.replace('.mp4', '_frames.mp4')
    fileop.mkdir_notexists(outfolder, remove_if_exists=True)
    command1 = 'avconv -y -i {0} -r {1} /tmp/test.mp4'.format(filename, fps)
    command2 = 'avconv -y -i /tmp/test.mp4 {0}'.format(os.path.join(outfolder, '{0}%10d.png'.format(os.path.split(filename)[1])))
    for c in [command1, command2]:
        subprocess.call(c, shell = True)
    
if __name__=='__main__':
    folder = '/home/rz/codes/data/Natural_Scene_Movies'
    for f in os.listdir(folder):
        if 'mp4' in f:
            video2stimulus_frames(os.path.join(folder,f))
#            break
            
