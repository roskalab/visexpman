import sys
import os
import struct
import os.path
import numpy

def phys2clampfit(filename):
    '''
    Converts phys file with trigger information to be readable by clampfit software
   ''' 
    f =open(filename)
    offset = f.read(4)
    offset = struct.unpack('>i',offset)[0]
    f.seek(4+offset)
    dim1 = f.read(4)
    dim2 = f.read(4)
    dim1 = struct.unpack('>i',dim1)[0]
    dim2 = struct.unpack('>i',dim2)[0]
    data = f.read(2*dim1*dim2)
    data = numpy.array(struct.unpack('>'+''.join(dim1*dim2*['h']),data), dtype = numpy.int16).reshape((dim1, dim2))
    data = data.flatten('F').reshape(dim1, dim2)
    data.tofile(filename.replace('.phys', '_converted.phys'))
    f.close()
    
if __name__=='__main__':
    folder = str(sys.argv[1])
    [phys2clampfit(os.path.join(folder, f)) for f in os.listdir(folder) if '.phys' in f]
    print 'DONE'
