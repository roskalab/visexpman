import multiprocessing

from visexpman.engine import visexp_gui
from visexpman.engine import visexp_runner
from visexpA.engine.datahandlers import hdf5io
    

if __name__ == '__main__':
    v = visexp_runner.VisionExperimentRunner(*visexp_runner.find_out_config())
    p = multiprocessing.Process(target = v.run_loop)
    p.start()
    visexp_gui.run_gui()
    p.join()
    hdf5io.lockman.__del__()
