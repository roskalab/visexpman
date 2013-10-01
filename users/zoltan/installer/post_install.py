import os
import os.path
import subprocess

def install_modules():
    module_names = ['eric4', 'PyDAQmx', 'zc.lockfile']
    if os.name == 'nt':
        tmp_folder = 'c:\\temp\\visexp_installers'
        for fn in os.listdir(tmp_folder):
            module_name = [mn for mn in module_names if mn in fn]
            if len(module_name) == 1:
                try:
                    __import__(module_name[0])
                    print module_name[0], 'already installed'
                except:
                    folder = os.path.join(tmp_folder, fn)
                    if 'eric' in fn :
                        install_command = 'python {0}'.format(os.path.join(folder, 'install.py'))
                    else:
                        install_command = 'python {0} install'.format(os.path.join(folder, 'setup.py'))
                    os.chdir(folder)
                    try:
                        subprocess.call(install_command, shell=True)
                    except:
                        print 'Reboot computer and run install again'
    else:
        tmp_folder = '/tmp'

def create_pth():
    if os.name == 'nt':
        package_path = 'c:\\visexp'
        ppath = 'c:\\python27\\Lib\\site-packages'
    else:
        ppath = '/usr/lib/python2.7/dist-packages/'
    if not os.path.exists(os.path.join(ppath, 'visexp.pth')):
        f = open(os.path.join(ppath, 'visexp.pth'), 'wt')
        f.write(package_path)
        f.close()

if __name__ == '__main__':
    create_pth()
    install_modules()
