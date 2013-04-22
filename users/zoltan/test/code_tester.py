from visexpA.engine.datahandlers.hdf5io import read_item
from visexpman.engine.generic.file import get_measurement_file_path_from_id,  find_files_and_folders
ids = [1352299907,1352467589, 1352801989, 1353320566, 1352321104, 1352476797, 1352810088, 1353331721]
ids = map(str, ids)
d,  files = find_files_and_folders('/mnt/databig/tmp/files')
for f in files:
    print read_item(f,  'image_scale',  filelocking=False)
