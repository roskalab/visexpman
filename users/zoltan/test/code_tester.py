from visexpA.engine.datahandlers import hdf5io
import sys
import unittest
if __name__ == "__main__":
    unittest.main(exit=False)
    hdf5io.lockman.__del__()
    print sys._current_frames()


