'''
smr_aligner.py <input folder> <output folder> <ncpu>
'''
import sys
from visexpman.engine.generic import fileop
from visexpman.engine.vision_experiment import experiment_data
import multiprocessing
if __name__=='__main__':
    fns =  [fn for fn in fileop.listdir_fullpath(sys.argv[1]) if '.smr' in fn]
    fns.sort()
    fileop.mkdir_notexists(sys.argv[2])
    cpus = int(sys.argv[3])
    if cpus == 1:
        for fn in fns:
            experiment_data.SmrVideoAligner((fn, sys.argv[2]))
    else:
        pool = multiprocessing.Pool(processes = cpus)
        pars = [(fn, sys.argv[2]) for fn in fns]
        pool.map(experiment_data.SmrVideoAligner, pars)
        pool.close()
        pool.join()
    print 'Done'
