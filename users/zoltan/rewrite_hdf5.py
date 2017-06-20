from visexpA.engine.datahandlers import hdf5io
import os,sys

def rewrite(filename, outfile):
    h=hdf5io.Hdf5io(filename,filelocking=False)
    hout=hdf5io.Hdf5io(outfile,filelocking=False)
    ignore_nodes=['hashes']
    rootnodes=[v for v in dir(h.h5f.root) if v[0]!='_' and v not in ignore_nodes]
    for rn in rootnodes: 
        rnd=h.findvar(rn)
        setattr(hout,rn, rnd)
        hout.save(rn)
    h.close()
    hout.close()
    
if __name__=='__main__':
    src=sys.argv[1]
    dst=sys.argv[2]
    for f in os.listdir(src):
        print f
        rewrite(os.path.join(src,f), os.path.join(dst, f))
