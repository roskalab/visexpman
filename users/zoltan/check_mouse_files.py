import scipy.io,hdf5io,os
from visexpman.engine.generic import fileop

if __name__ == "__main__":
    folder='/home/rz/mysoftware/data/mousefiles'
    result=[]
    for f in fileop.listdir(folder):
        s=hdf5io.read_item(f, 'scan_regions',filelocking=False)
        for name, scan_region in s.items():
            if 'xz' in scan_region:
                tmpfn='/tmp/tmp.mat'
                if os.path.exists(tmpfn):
                    os.remove(tmpfn)
                scan_region['xz']['mes_parameters'].tofile(tmpfn)
                m=scipy.io.loadmat(tmpfn)
                ok=False
                try:
                    if m['DATA'][0]['info_Protocol'][0]['protocol'][0][0]['inputcurves'][0][0][0][0][0]=='DI0':
                        ok=True
                except:
                    ok=False
                result.append((ok,os.path.basename(f),name))
                pass
    for r in result:
        print(r)
        
