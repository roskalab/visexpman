import visexpA.engine.datahandlers.importers as importers
import visexpA.engine.datahandlers.hdf5io as hdf5io
import visexpA.engine.datahandlers.matlabfile as matlabfile
from visexpman.engine.hardware_interface import mes_interface
from visexpman.engine.generic import utils
import os
import os.path
import numpy
import Image
from visexpman.engine.generic import introspect
from visexpman.engine.visual_stimulation import configuration
from visexpman.engine.visual_stimulation import experiment
from visexpman.engine.visual_stimulation import experiment_data
from visexpman.users.daniel import moving_dot, configurations
import pp

######### Side folded frame ###############

matlabfile.read_vertical_scan('/home/zoltan/visexp/data/line_scan_parameters_00011.mat')
pass


#### celery ##########

#from celery.task import task
#
#@task
#def add(x, y):
#    res = 0
#    for i in range(1000000):
#        res += y
#    return res



#path = '/home/zoltan/visexp/debug/test1.hdf5'
#h = hdf5io.Hdf5io(path)
#machine_config = configurations.WinDev(None)
#experiment_config = moving_dot.MovingDotConfig(machine_config,  None)
#experiment_data.save_config(h, machine_config, experiment_config)
#h.close()

#path = '/home/zoltan/visexp/data/20120106/fragment_0.0_0.0_-154.0_MovingDot_1325865160_0.hdf5'
#h = hdf5io.Hdf5io(path)
#experiment_source = h.findvar('experiment_source').tostring()
#machine_config_dict = h.findvar('machine_config')
#conf = experiment.restore_experiment_config('MovingDotConfig', fragment_hdf5_handler = h, user = 'daniel')
#h.close()
#pass

#### Registration #####
#import pp
#from visexpA.engine.dataprocessors import itk_image_registration
#import Image
#from visexpA.engine.datadisplay.imaged import imshow
#folder = '/home/zoltan/visexp/debug/registration1/onescale'
#folder = '/mnt/rzws/debug/registration1/onescale'
#directories, all_files = utils.find_files_and_folders(folder)
#images = []
#for file in all_files:
#    if 'hdf5' in file:
#        h = hdf5io.Hdf5io(file)
#        two_photon_image = h.findvar('two_photon_image')
#        two_photon_image['stage_position'] = h.findvar('stage_position')
#        two_photon_image['filename'] = file
#        images.append(two_photon_image)
#        h.close()
#for image in images:
#    for image_to_compare in images:
#        if image_to_compare['filename'] != image['filename']:
#            f1 = numpy.cast['float32'](image['pmtUGraw'])
#            f2 = numpy.cast['float32'](image_to_compare['pmtUGraw'])
#            values,  outimage = itk_image_registration.register(f1, f2, metric='MeanSquares',  optimizertype='RegularStepGradientDescent', multiresolution=True, transform_type='CenteredRigid2D', debug=0)
#            translation = numpy.round(numpy.array(values[-2:]), 1)*numpy.array([-1, 1])
#            stage_offset = (image['stage_position'] - image_to_compare['stage_position'])[:-1]
#            error = numpy.round(translation*image['scale'].real - stage_offset, 1)
#            image_filename = os.path.join(folder, str(numpy.round(translation*image['scale'].real, 1)).replace('[', '').replace(']', '') + '_' + str(stage_offset[0]) + ' ' + str(stage_offset[1]) + '_' + str(error[0]) + '_' + str(error[1]) + '.png')
#            try:
#                Image.fromarray(numpy.cast['uint8'](255*(numpy.c_[f1, numpy.zeros_like(outimage), f2] / numpy.c_[f1, f2].max()))).save(image_filename)
#            except:
#                pass
#            print translation, numpy.round(translation*image['scale'].real, 1), stage_offset, round(values[0], 2), error, os.path.split(image_to_compare['filename'])[-1], os.path.split(image['filename'])[-1]
#    
#pass
### Parallel computing #####
#from celery.task import task
#
#@task
#def add(x, y):
#    return x + y
#    
#result = add.delay(4, 4)
#result.wait()



#import pp
#
#def func1(a, b):
#    res = 0
#    for i in range(1000000):
#        res +=a.sum()+b
#    return res
#
###job_server = pp.Server(ncpus = 0, ppservers = ('172.27.35.197:60000', '172.27.25.220:60000'), secret = 'retina')
###job_server = pp.Server(ppservers = ('172.27.35.197', '172.27.25.196', '172.27.25.220'))
#job_server = pp.Server(ncpus = 0, ppservers = ('rzws.fmi.ch', 'Fu238D-DDF19D.fmi.ch', 'f434l-fcc382.fmi.ch' ))
###job_server = pp.Server( ppservers = ('*', ))
###import logging
###path = '/home/zoltan/visexp/debug/txt.txt'
###handler = logging.FileHandler(path)
###formatter = logging.Formatter('%(message)s')
###handler.setFormatter(formatter)
###job_server.logger.addHandler(handler)
###job_server.logger.setLevel(logging.INFO)
#job_server.wait()
#f = []
#for i in range(100):
#    a = numpy.ones(i)
#    f.append(job_server.submit(func1, (a, i)))
#for ff in f:
#    print ff()
#job_server.print_stats()
