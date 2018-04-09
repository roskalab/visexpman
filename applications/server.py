'''
This module holds functions that run periodically by servers
'''
import unittest,os
from visexpman.engine.generic import fileop,utils

def mdrive_checker(folders, signature_file, emailto):
    files=[]
    for folder in folders:
        files.extend(fileop.find_files_and_folders(folder)[1])
    signatures=[fileop.file_signature(f) for f in files if ',' not in f]
    signatures=dict([(s[0], (s[1], s[2])) for s in signatures])
    if os.path.exists(signature_file):
        txt=fileop.read_text_file(signature_file)
        signature_p=[line.split(',') for line in txt.split('\r\n')]
        signature_p=dict([(s[0], (int(s[1]), int(s[2]))) for s in signature_p])
        #Compare current signature with previous one
        #print len(signature_p.keys()), len(signatures.keys())
        #Check for deleted files:
        missing_files=[fn for fn in signature_p.keys() if not signatures.has_key(fn)]
#        import pdb;pdb.set_trace()
        error_msg=''
        if len(missing_files)>0:
            error_msg+='Missing files {0}\r\n'.format('\r\n'.join(missing_files))
        else:
            #Compare signatures
            for fn in signature_p.keys():
                if signature_p[fn]!=signatures[fn]:
                    error_msg+='{0} changed: {1}, {2}\r\n'.format(fn, signature_p[fn], signatures[fn])
        if len(error_msg)==0:
            error_msg='Files did not change'
        print error_msg
        if not isinstance(emailto,list):
             emailto=[emailto]
        for e in emailto:
            utils.sendmail(e,'m drive check', error_msg)
    #Save current signature
    txt='\r\n'.join([','.join(map(str,[fn, s[0], s[1]])) for fn, s in signatures.items()])
    fileop.write_text_file(signature_file,txt)
    
        
    pass
    
class Test(unittest.TestCase):
    def test_01_mdrive(self):
        mdrive_checker(['/home/rz/mysoftware'], '/tmp/sig.txt','')
    
if __name__=='__main__':
    unittest.main()
