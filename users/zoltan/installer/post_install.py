import os
import os.path
import subprocess
import shutil
import tempfile

def install_modules():
    module_names = ['eric4', 'zc.lockfile']
    if os.name == 'nt':
        module_names.append('PyDAQmx')
        #check what is installed
        modules2install = []
        print 'Check which module is not yet installed'
        for mn in module_names:
            try:
                __import__(mn)
            except ImportError:
                modules2install.append(mn)
        remote_folder = 'm:\\Zoltan\\visexpman_installer\\common'
        tmp_folder = os.path.join(tempfile.gettempdir(), 'visexp_installers')
        installer_folders = [os.path.join(remote_folder, fn) for fn in os.listdir(remote_folder) if os.path.isdir(os.path.join(remote_folder,fn))]
        selected_installer_folders = []
        for m in modules2install:
            f = [f for f in installer_folders if m in f]
            if len(f)>0:
                selected_installer_folders.extend(f)
        print 'copy files to tmp and install modules'
        if os.path.exists(tmp_folder):
            shutil.rmtree(tmp_folder)
        for folder in selected_installer_folders:
            shutil.copytree(folder, tmp_folder)
            if 'eric' in folder:
                    install_command = 'python {0}'.format(os.path.join(tmp_folder, 'install.py'))
            else:
                install_command = 'python {0} install'.format(os.path.join(tmp_folder, 'setup.py'))
            os.chdir(tmp_folder)
            try:
#                print install_command
                subprocess.call(install_command, shell=True)
            except:
                print 'Reboot computer and run install again'
            os.chdir(tempfile.gettempdir())
            shutil.rmtree(tmp_folder)
        
        
    else:
        raise NotImplementedError('')

if __name__ == '__main__':
    install_modules()
