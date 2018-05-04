import scipy.io,hdf5io,os,shutil
from visexpman.engine.generic import fileop,utils
from visexpA.engine.datahandlers import matlabfile

def copy_image2mouse_file(filename,scan_region):
    img_src=os.path.join(os.path.split(filename)[0], 'image_'+os.path.split(filename)[1])
    if not os.path.exists(img_src):
        return
    s=hdf5io.read_item(img_src, 'scan_regions',filelocking=False)
    tmpfn='/tmp/tmp.mat'
    if os.path.exists(tmpfn):
        os.remove(tmpfn)
    s[scan_region]['xz']['mes_parameters'].tofile(tmpfn)
    m=scipy.io.loadmat(tmpfn)
    img_src=m['DATA'][0]['IMAGE'][0]
    #Open copy of original file
    fn=filename.replace('.hdf5', '_fixed.hdf5')
    shutil.copy(filename, fn)
    h=hdf5io.Hdf5io(fn)
    h.load('scan_regions')
    os.remove(tmpfn)
    h.scan_regions[scan_region]['xz']['mes_parameters'].tofile(tmpfn)
    m=scipy.io.loadmat(tmpfn)
    m['DATA'][0]['IMAGE'][0]=img_src
    scipy.io.savemat(tmpfn, m)
    h.scan_regions[scan_region]['xz']['mes_parameters']=utils.file_to_binary_array(tmpfn)
    ss=matlabfile.read_vertical_scan(tmpfn)[0]
    for k in ['scaled_image', 'averaging', 'image', 'scaled_scale', 'scale']:
        h.scan_regions[scan_region]['xz'][k]=ss[k]
    h.save('scan_regions')
    h.close()

if __name__ == "__main__":
    copy_image2mouse_file('/home/rz/mysoftware/data/mousefiles/mouse_RD1007_scnn1aXai94Xc3h(homo)_28-12-2018_14-2-2018_0_2.hdf5', 'W_190418_0_0')
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
        
