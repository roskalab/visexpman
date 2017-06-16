import sys,os,shutil,platform,psutil,time,getpass,subprocess
setup_name=sys.argv[1]
if getpass.getuser()!='hd':
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'engine','generic')
    sys.path.insert(0,path)#This is needed for importing fileop
    import fileop
    pw=fileop.read_text_file(os.path.join(path,'..','..','..', '..','jobhandler','pw.txt')).title()
    host=platform.uname()[1]
    print host
    if host in ['microscopy-3d', 'Fu238D-DDF19D', 'FEMTO-0195', 'FEMTO-0193', 'F446i-95FDDE']:
        try:
            import visexpman
            dst=os.path.dirname(os.path.dirname(visexpman.__file__))
        except ImportError:
            dst='c:\\visexp'
        if setup_name=='ao':
            dst='c:\\visexp'
    elif host=='rlvivo1.fmi.ch':
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
        if setup_name=='ao':
            folder='/data/software/ao-setup/visexpman'
            if package=='visexpA':                 
                folder='/data/software/ao-setup/hdf5io.py'
        elif setup_name=='rc':
            folder='/data/software/rc-setup/{0}'.format(package)
        else:
            raise NotImplementedError('')
        fileop.download_folder('rldata.fmi.ch', 'mouse', '{0}'.format(folder), dst, password=pw)
    sys.path.remove(path)
#     if host=='rlvivo1':#Make sure that any user can delete this folder later
#         subprocess.call('chmod -R 777 {0}'.format(dst), shell=True)

