import sys,os,shutil,platform
path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'engine','generic')
sys.path.insert(0,path)
import fileop
pw=fileop.read_text_file(os.path.join(path,'..','..','..', '..','jobhandler','pw.txt')).title()
host=platform.uname()[1]
if host=='microscopy-3d':
    try:
        import visexpman
        dst=os.path.dirname(os.path.dirname(visexpman.__file__))
    except ImportError:
        dst='c:\\visexp'
elif host=='rlvivo1':
    dst='/tmp/jobhandler'
if os.path.exists(dst):
    shutil.rmtree(dst)
os.mkdir(dst)
for package in ['visexpman', 'visexpA']:
    print 'downloading', package
    fileop.download_folder('rldata.fmi.ch', 'mouse', '/data/software/rc-setup/{0}'.format(package), dst, password=pw)

