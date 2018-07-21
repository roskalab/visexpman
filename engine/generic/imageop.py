'''
Image related operations
'''
import unittest,os
from PIL import Image
from visexpman.engine.generic import fileop

def rotate_folder(src, dst, rot):
    print src
    files=fileop.find_files_and_folders(src)[1]
    for f in files:
        img=Image.open(f)
        rotated=img.rotate(rot)
        fout=os.path.join(dst, os.path.relpath(f,src))
        if not os.path.exists(os.path.dirname(fout)):
            os.makedirs(os.path.dirname(fout))
        rotated.save(fout)
    
class ImageOpTest(unittest.TestCase):
    def test_01_rotate_folder(self):
        import numpy,tempfile,shutil
        nfiles=10
        wf=os.path.join(tempfile.gettempdir(),'img','imgsub')
        dst=os.path.join(tempfile.gettempdir(),'imgrot')
        for d in [wf, dst]:
            if os.path.exists(d):
                shutil.rmtree(d)
            os.makedirs(d)
        img1=numpy.zeros((100,100,3),dtype=numpy.uint8)
        img1[:,10:20,0]=255
        img2=numpy.zeros((100,100),dtype=numpy.uint8)
        img2[:,20:40]=200
        for i in range(nfiles):
            img=numpy.roll(numpy.copy(img1),i,axis=1)
            Image.fromarray(img).save(os.path.join(wf, 'rgb_{0}.png'.format(i)))
            img=numpy.roll(numpy.copy(img2),i,axis=1)
            Image.fromarray(img).save(os.path.join(wf, 'gray_{0}.jpeg'.format(i)))
        for rot in range(45,180, 45):
            rotate_folder(os.path.dirname(wf), dst+str(rot), rot)
        
if __name__=='__main__':
        unittest.main()
