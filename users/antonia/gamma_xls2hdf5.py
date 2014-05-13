from visexpA.engine.datahandlers import hdf5io
import xlrd
import sys
import numpy
import os.path
def xls2hdf5(filename, sheet_name, date, outfolder):
    wb = xlrd.open_workbook(filename)
    sh = wb.sheet_by_name(sheet_name)
    for row in range(sh.nrows):
        if str(sh.row_values(row)[0]) == date:
            contrast = sh.row_values(row+2)[1:]
            intensity = sh.row_values(row+3)[1:]
            gamma_correction = numpy.array([contrast, intensity]).T
            h = hdf5io.Hdf5io(os.path.join(outfolder,'gamma.hdf5'), filelocking=False)
            h.gamma_correction = gamma_correction
            h.save('gamma_correction')
            h.close()
            pass


if __name__=='__main__':
    xls2hdf5(*sys.argv[1:])
