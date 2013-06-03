import os
import os.path
def analyze_logs():
    path = '/home/rz/Downloads/log'
    if False:
        database = []
        selected = []
        for fn in os.listdir(path):
            print fn
            with open(os.path.join(path, fn)) as f:
                while True:
                    content = f.readline()
                    if content == '':
                        break
                    elif 'Scan start ERROR' in content:
                        database.append(content)
                        selected.append(database[-2].split(': ')[-1].split('\\')[-1])
                    elif 'SOCacquire_line_scanEOCV' in content:
                        database.append(content)
    else:
        from visexpA.engine.datahandlers import hdf5io
        selected = hdf5io.read_item('/home/rz/Downloads/t.hdf5', 'selected',  filelocking=False)
    names = ['_'.join(s.split('_')[2:-4]) for s in selected]
    unames = {}
    for name in names:
        if not unames.has_key(name):
            unames[name] = 1
        else:
            unames[name] += 1
    print [['_'.join(uname.split('_')[:-2]), len('_'.join(uname.split('_')[:-2])),  unames[uname]] for uname in unames.keys() if unames[uname] > 1]
    
if __name__=='__main__':
    pass
