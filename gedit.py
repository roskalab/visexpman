import subprocess
import getpass,os
root='/data/software/rc-setup/visexpman/users'
if getpass.getuser()=='rz':
     folder='/data/software/rc-setup/visexpman/users/zoltan'
elif getpass.getuser()=='fm':
     folder=os.path.join(root,'fiona')
elif getpass.getuser()=='st':
     folder=os.path.join(root,'stuart')
elif getpass.getuser()=='gk':
     folder=os.path.join(root,'georg')
else:
     folder='/data/software/rc-setup/visexpman/users'
os.chdir(folder)
subprocess.call('gedit'.format(folder)) 
