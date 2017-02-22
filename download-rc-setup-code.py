import sys,os,shutil,platform,psutil,time,getpass,subprocess
if getpass.getuser()!='hd':
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'engine','generic')
    sys.path.insert(0,path)
    import fileop
    pw=fileop.read_text_file(os.path.join(path,'..','..','..', '..','jobhandler','pw.txt')).title()
    host=platform.uname()[1]
    if host in ['microscopy-3d', 'Fu238D-DDF19D']:
        try:
            import visexpman
            dst=os.path.dirname(os.path.dirname(visexpman.__file__))
        except ImportError:
            dst='c:\\visexp'
    elif host=='rlvivo1':
        dst='/tmp/jobhandler'
        #subprocess.call('rm -rf {0}'.format(dst), shell=True)
    if os.path.exists(dst):
        try:
            shutil.rmtree(dst)
            os.mkdir(dst)
        except:
            pass
    for package in ['visexpman', 'visexpA']:
        print 'downloading', package
        fileop.download_folder('rldata.fmi.ch', 'mouse', '/data/software/rc-setup/{0}'.format(package), dst, password=pw)
    sys.path.remove(path)
#     if host=='rlvivo1':#Make sure that any user can delete this folder later
#         subprocess.call('chmod -R 777 {0}'.format(dst), shell=True)

