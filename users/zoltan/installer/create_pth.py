import os
import os.path
package_path = os.getcwd()
print package_path
if os.name == 'nt':
    ppath = 'c:\\python27\\Lib\\site-packages'
else:
    path = '/usr/lib/python2.7/dist-packages/'
f = open(os.path.join('visexp.pth','wt'))
f.write(package_path)
f.close()

