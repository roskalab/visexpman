from visexpman.engine import jobhandler
import sys
import unittest,os



class TestRestore(unittest.TestCase):
    def test_01(self):
        import shutil
        wf='/mnt/databig/debug/6'
        if os.path.exists(wf):
            shutil.rmtree('/mnt/databig/debug/6')
        shutil.copytree('/mnt/tape/hillier/invivocortex/TwoPhoton/default_user/2016111/151', wf)
        jobhandler.offline(wf)


if __name__=='__main__':
    if len(sys.argv)==1:
        unittest.main()
    else:
        input_folder=sys.argv[1]
        jobhandler.offline(input_folder)

        
