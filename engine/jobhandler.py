'''Processes/sends commands via network, imports and processes incoming data'''
#at the moment we use threading but later might extend the code to multiprocessing/cluster processing
import numpy
import sys
import os
import time
import Queue
import unittest
import os.path
import traceback
import hashlib
from PyQt4 import QtCore
import PyQt4.Qt as Qt
import unittest
import shutil
import multiprocessing

if QtCore.QCoreApplication.instance() is None:
    qt_app = Qt.QApplication([])
from visexpA.engine import analysis
import visexpman
from visexpman.engine.hardware_interface import network_interface
from visexpman.engine.generic import command_parser
from visexpman.engine.generic import log
from visexpman.engine.generic import utils
from visexpman.engine.generic import file
from visexpman.engine.vision_experiment import configuration
from visexpA.engine.dataprocessors import itk_image_registration
from visexpA.engine.datahandlers import hdf5io
from visexpA.engine.datahandlers import matlabfile
from visexpA.users.zoltan import fragment_process
from visexpA.engine.datahandlers import importers
from visexpman.engine.generic import introspect
from visexpA.engine.component_guesser import rawname2cachedname
#from multiprocessing import Manager, Process 
introspect.celery_available()
if len(sys.argv) >= 4:
    STATIC = (sys.argv[3] == 'static')
else:
    STATIC = False
    
BACKGROUND_COPIER = True

class Jobhandler(object):
    def __init__(self, user, config_class, **kwargs):
        '''
        Jobhandler application runs all the computational intensive and analysis related tasks during running experiment.
        '''
        self.config = utils.fetch_classes('visexpman.users.'+user, classname = config_class, required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig,direct=False)[0][1]()
        self.queues = {}
        self.queues['gui'] = {}
        self.queues['gui']['out'] = Queue.Queue()
        self.queues['gui']['in'] = Queue.Queue()
        self.connections = {}
        self.connections['gui'] = network_interface.start_client(self.config, 'ANALYSIS', 'GUI_ANALYSIS', self.queues['gui']['in'], self.queues['gui']['out'])
        self.log = log.Log('analysis interface log', file.generate_filename(os.path.join(self.config.LOG_PATH, 'jobhandler_log.txt'))) 
        self.queues['low_priority_processor'] = {}
        self.queues['low_priority_processor']['in'] = Queue.Queue()#Fragment check and mesextractor has higher priority
        self.queues['low_priority_processor']['in'] = Queue.PriorityQueue()#Fragment check and mesextractor has higher priority
        self.queues['low_priority_processor']['out'] = Queue.PriorityQueue()
        self.command_handler = CommandInterface(self.config, self.queues, log = self.log)
        self.command_handler.kwargs = kwargs
        if False:
            self.lowpridp= LowPriorityProcessor(self.config, self.queues, self.log, printl = self.command_handler.printl)
            self.lowpridp.background_copier_command_queue = self.command_handler.background_copier_command_queue
            self.lowpridp.start()
            
    def run(self):
        last_run_time = time.time()
        last_mouse_file_check = time.time()
        while True:
            result = self.command_handler.parse(True)
            if result[0] == 'exit' or utils.enter_hit():
                break
            now = time.time()
#            if now - last_run_time > self.config.PARSE_PERIOD:
#                last_run_time = now
#                result = self.command_handler.parse(True)
#                if result[0] == 'exit' or utils.enter_hit():
#                    break
            if now - last_mouse_file_check > self.config.MOUSE_FILE_CHECK_PERIOD:
                last_mouse_file_check = now
                if hasattr(self.command_handler, 'periodic'):
                    self.command_handler.periodic()
            time.sleep(0.01)
        self.close()

    def close(self):
        self.command_handler._save_files()
        if BACKGROUND_COPIER:
            self.command_handler.background_copier_command_queue.put('TERMINATE')
            print 'Wait for background copier to finish'
            self.command_handler.background_copier.join()
        self.queues['gui']['out'].put('Jobhandler quits')
        time.sleep(0.1)
        self.log.queue(self.connections['gui'].log_queue, 'gui connection')
        self.queues['gui']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.queues['low_priority_processor']['in'].put('SOCcloseEOCEOP')
        time.sleep(1.0)
        print 'Jobhandler quit'

class CommandInterface(command_parser.CommandParser):
    '''
    This is the command processor class of the jobhandler application. Receives commands from network interface (GUI) and processes them.
    Processing measurement data is done automatically by asking a copy of the mouse file. Then it is checked for unprocessed measurements.
    '''
    def __init__(self, config, queues, log = None):
        self.config = config
        self.queues = queues
        command_parser.CommandParser.__init__(self, [self.queues['gui']['in'], self.queues['low_priority_processor']['out']], self.queues['gui']['out'], log = log)
        user = 'daniel'
        import visexpA.engine.configuration
        if len(sys.argv)==3:
            aconfigname = sys.argv[3]
        else:
            aconfigname = 'Config'
        self.analysis_config = utils.fetch_classes('visexpA.users.'+user, classname=aconfigname, required_ancestors=visexpA.engine.configuration.Config,direct=False)[0][1]()
        self.copy_request_pending = False
        self.copy_request_time = 0
        self.sent_to_mesextractor = []
        self.sent_to_find_cells = []
        self.zeromq_pusher = network_interface.ZeroMQPusher(5500, type='PUSH')
        self._check_freespace()
        self.not_copied_to_tape = []
        if BACKGROUND_COPIER:
            import multiprocessing
            self.background_copier_command_queue = multiprocessing.Queue()
            self.background_copier = file.BackgroundCopier(self.background_copier_command_queue,postpone_seconds=5,debug=0,thread=0)
            self.background_copier.start()
        self.printl('Jobhandler started')

            
    def _check_freespace(self):
        #Check free space on databig and tape
        free_space_on_databig = file.free_space(self.config.DATABIG_PATH)/(1024**3)
        try:
            free_space_on_tape = file.free_space(self.config.TAPE_PATH)/(1024**3)
        except:
            free_space_on_tape = 'Not available'
        if free_space_on_databig < 8:
            raise RuntimeError('Critically low free space on databig: {0} GB'.format(free_space_on_databig))
            sys.exit(0)
        self.printl('Free space on databig {0} GB and tape {1} GB'.format(free_space_on_databig, free_space_on_tape))
            
    def periodic(self):
        dt = time.time() - self.copy_request_time
        self.log.info((self.copy_request_pending, dt))
        if not self.copy_request_pending or dt > 20:
            self.log.info(dt)
            self._ask_mouse_file_copy()

    ################## Fragment processing #######################
    def _jobs_from_database(self):
        '''
        Checks for unprocessed measurements in scan_regions database.
        '''
        self.log.info('_jobs_from_database started: {0},{1}'.format(self.mouse_file, self.queues['low_priority_processor']['out'].empty()))
        if hasattr(self, 'mouse_file') and os.path.exists(self.mouse_file) and self.queues['low_priority_processor']['out'].empty():
            time.sleep(2.0)
#             while utils.is_file_open(self.mouse_file):
#                 print 'Wait file'
#                 time.sleep(0.2)
            scan_regions = hdf5io.read_item(self.mouse_file, 'scan_regions',filelocking=False)#sometimes this read fails with tables.isPyTablesFile(self.filename), None is returned
            time.sleep(1.0)
            os.remove(self.mouse_file)
            self.log.info('scan regions read')
            if hasattr(scan_regions, 'values'):
                for scan_region in scan_regions.values():
                    if scan_region.has_key('process_status'):
                        for id, measurment_unit in scan_region['process_status'].items():
                            if not measurment_unit['fragment_check_ready'] and not measurment_unit['mesextractor_ready'] and id not in self.sent_to_mesextractor:
                                self.queues['low_priority_processor']['out'].put('SOCcheck_and_preprocess_fragmentEOCid={0}EOP'.format(id))
                                self.sent_to_mesextractor.append(id)#TODO: this mechanism might not be necessary
                                self.log.info('sent to mesextractor: {0}'.format(id))
#                                 break
                            elif not measurment_unit['find_cells_ready'] and measurment_unit['mesextractor_ready'] and id not in self.sent_to_find_cells:
                                time.sleep(1.0)#Make sure that measurement data file is closed by GUI
                                self.queues['low_priority_processor']['out'].put('SOCfind_cellsEOCid={0}EOP'.format(id))
                                self.sent_to_find_cells.append(id)
                                self.log.info('sent to finding cell: {0}'.format(id))
#                                 break

    def _ask_mouse_file_copy(self):
        self.log.info('_ask_mouse_file_copy')
        self.queue_out.put('SOCmouse_file_copyEOCjobhandlerEOP')
        self.copy_request_pending = True
        self.copy_request_time = time.time()
        
    def mouse_file_copied(self, filename = None):
        self.log.info('mouse_file_copied')
        #If mouse file changed, save previous one to tape
        new_mouse_filename = os.path.join(self.config.EXPERIMENT_DATA_PATH, filename)
        if hasattr(self,'mouse_file') and self.mouse_file != new_mouse_filename:
            self._save_files()
            self.printl('Mouse file backed up')
        self.mouse_file = new_mouse_filename
        self._jobs_from_database()
        self.copy_request_pending = False
        
    def mouse_file_not_copied(self, filename = None):
        self.copy_request_pending = False
        self.log.info('mouse_file_not_copied')
        
    def reset_jobhandler(self):
        self.printl('Jobhandler reset')
        self.copy_request_pending = False
        self.clear_joblist()
        self._check_freespace()
        
    def clear_joblist(self):
        self.sent_to_find_cells = []
        self.sent_to_mesextractor = []

    ######## Ready events #############################
    def _fragment_check_ready(self, check_result = False, id=None):
        check_result = (check_result=='True')
        if not check_result:
            self.printl('Fragment check failed: {0}' .format(fragment_name_to_short_string(file.get_measurement_file_path_from_id(id, self.config, filename_only = True))))
        else:
            self.printl('Fragment check ready: {0}'.format(fragment_name_to_short_string(file.get_measurement_file_path_from_id(id, self.config, filename_only = True))))
            self.queues['gui']['out'].put('SOCfragment_check_readyEOC{0}EOP'.format(id))

    def _mesextractor_ready(self, id=None):
        time.sleep(0.3)#Make sure that file is closed after MESExtractor
        self.printl('Mesextractor ready: {0}'.format(fragment_name_to_short_string(file.get_measurement_file_path_from_id(id, self.config, filename_only = True))))
        time.sleep(0.3)
        self.queues['gui']['out'].put('SOCmesextractor_readyEOC{0}EOP'.format(id))

    def _find_cells_ready(self, id =None, runtime=None):
        time.sleep(0.3)#Make sure that file is closed
        filename = file.get_measurement_file_path_from_id(id, self.config, filename_only = True)
        fullpath = fragment_name_to_short_string(filename)
        self.printl('Copying files to databig and tape')
        databig_path, tape_path = self._generate_copypath(filename)
        exit = False
        try:
            shutil.copy(os.path.join(self.config.EXPERIMENT_DATA_PATH, filename), databig_path)
            if len(sys.argv) > 3 and sys.argv[3] == 'EXPORT_DATA_TO_MAT':
                p1=os.path.join(self.config.EXPERIMENT_DATA_PATH, filename)
                shutil.copy(p1.replace('.hdf5', '_mat.mat'), databig_path.replace('.hdf5', '_mat.mat'))
            if os.path.exists(os.path.join(os.path.split(databig_path)[0], 'output', filename)):
                shutil.rmtree(os.path.join(os.path.split(databig_path)[0], 'output', filename))
            else:
                plot_folder = os.path.join(self.config.EXPERIMENT_DATA_PATH, 'output', filename)
                if os.path.exists(plot_folder):
                    shutil.copytree(plot_folder, os.path.join(os.path.split(databig_path)[0], 'output', filename))
                else:
                    self.printl('No soma rois found, no plots to copy')
        except:
            self.printl(traceback.format_exc())
            self.printl('Problem with copying to comparer folder {0},{1}, Jobhandler terminates.'.format(os.path.join(os.path.split(databig_path)[0], 'output', filename),
                                os.path.exists(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'output', filename))))
            exit = True
        if BACKGROUND_COPIER:
            if not os.path.ismount('/mnt/tape'):
                print '!!! Tape not mounted, measurement data is not backed up !!!'
            else:
                self.background_copier_command_queue.put((os.path.join(self.config.EXPERIMENT_DATA_PATH, filename), tape_path))
                self.background_copier_command_queue.put((os.path.join(self.config.EXPERIMENT_DATA_PATH, filename).replace('.hdf5','.mat'), tape_path.replace('.hdf5','.mat')))
        else:
            try:
                if not os.path.ismount('/mnt/tape'):
                    self.printl('Tape not mounted')
                    import subprocess#Mount tape if not mounted
                    try:
                        subprocess.call(u'mount /mnt/tape',shell=True)
                        subprocess.call(u'fusermount -u /mnt/tape',shell=True)
                    except:
                        pass
                if 1 and os.path.ismount('/mnt/tape'):#Copy data if tape is mounted
                    shutil.copy(os.path.join(self.config.EXPERIMENT_DATA_PATH, filename), tape_path)
                    shutil.copy(os.path.join(self.config.EXPERIMENT_DATA_PATH, filename).replace('.hdf5','.mat'), tape_path.replace('.hdf5','.mat'))
                else:
                    #self.printl('Tape cannot be mounted. Try to mount it manually')
                    #self.printl('Number of files not copied to the tape: {0}.'.format(len(self.not_copied_to_tape)))
                    self.not_copied_to_tape.append([os.path.join(self.config.EXPERIMENT_DATA_PATH, filename), tape_path])
                    self.not_copied_to_tape.append([os.path.join(self.config.EXPERIMENT_DATA_PATH, filename).replace('.hdf5','.mat'), tape_path.replace('.hdf5','.mat')])
            except:
                self.printl(traceback.format_exc())
                self.printl('Problem with copying to tape')
                #tries to copy mat file to databig
                try:
                    shutil.copy(os.path.join(self.config.EXPERIMENT_DATA_PATH, filename).replace('.hdf5','.mat'), databig_path.replace('.hdf5','.mat'))
                except:
                    self.printl(traceback.format_exc())
                    self.printl('Mat file cannot be copyied to databig. Check if mat files are backed up')
                    exit = True
#        if exit:            
#            sys.exit(0)
        self.printl('Cell detection ready: ({1} s) {0}' .format(fullpath, runtime))
        time.sleep(0.3)
        self.queues['gui']['out'].put('SOCfind_cells_readyEOC{0}EOP'.format(id))
        print 'sending msg:'+databig_path
        self.zeromq_pusher.send((('add_and_sync', databig_path, ), ), False) #also opens the file
        
    def _generate_copypath(self, filename):
        try:
            paths = []
            for dir in [self.config.DATABIG_PATH,self.config.TAPE_PATH]:
                d = os.path.join(dir, utils.date_string().replace('-',''), os.path.split(self.mouse_file)[1].split('_')[1])
                if not os.path.exists(d):
                    try:
                        os.makedirs(d)
                    except:
                        pass
                paths.append(os.path.join(d, os.path.split(filename)[1]))
            return paths
        except:
            self.printl(traceback.format_exc())
            
    def _save_files(self):
        print 'Saving mouse file to databig and tape'
        if hasattr(self, 'mouse_file'):
            mouse_file = self.mouse_file.replace('_jobhandler','')
            databig_path, tape_path = self._generate_copypath(mouse_file)
            if os.path.exists(databig_path):
                os.remove(databig_path)
            try:
                shutil.copy(mouse_file, databig_path)
            except:
                self.printl(traceback.format_exc())
                self.printl('Problem with copying mousefile. Copy it manually to databig/u drive.')
            if BACKGROUND_COPIER:
                self.printl('Command sent to background copier: {0}'.format((mouse_file, tape_path)))
                self.background_copier_command_queue.put((mouse_file, tape_path))
            else:
                try:
                    shutil.copy(mouse_file, tape_path)
                except:
                    self.printl(traceback.format_exc())
                    self.printl('Problem with copying to tape')
#                 print 'Saving plots to databig'
#                 try:
#                     shutil.copytree(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'output'), os.path.join(os.path.split(databig_path)[0],'output'))
#                 except:
#                     self.printl(traceback.format_exc())
#                     self.printl('Problem with copying plots to databig')
                #Retry unsuccessful copies to tape
                if not os.path.ismount('/mnt/tape'):
                    import subprocess#Mount tape if not mounted
                    try:
                        subprocess.call(u'mount /mnt/tape',shell=True)
                        subprocess.call(u'fusermount -u /mnt/tape',shell=True)
                    except:
                        pass
                if os.path.ismount('/mnt/tape'):#Copy data if tape is mounted
                    [shutil.copy(source, target) for source, target in self.not_copied_to_tape[1:]]
                    [shutil.copy(source, target) for source, target in self.not_copied_to_tape[1:]]
                     #[subprocess.call('cp {0} {1}'.format(source,target) for source, target in self.not_copied_to_tape]
                else:
                    self.printl('Tape cannot be mounted. Try to mount it manually and perform the following copies manually:')
                    for source, target in self.not_copied_to_tape:
                        print '{0} to {1}' .format(source, target)

    def check_and_preprocess_fragment(self, id = None, force_recreate = False):
        '''
        '''
        try:
            full_fragment_path = file.get_measurement_file_path_from_id(id, self.config)
            #Make a copy
            if BACKGROUND_COPIER:
                if not os.path.ismount('/mnt/tape'):
                    print '!!! Tape not mounted, measurement data is not backed up !!!'
                else:
                    filename = full_fragment_path
#                    self.background_copier_command_queue.put((os.path.join(self.config.EXPERIMENT_DATA_PATH, filename), tape_path))
#                    self.background_copier_command_queue.put((os.path.join(self.config.EXPERIMENT_DATA_PATH, filename).replace('.hdf5','.mat'), tape_path.replace('.hdf5','.mat')))
            #Run mesextractor with fragment check
            if self.config.ENABLE_MESEXTRACTOR and not full_fragment_path is None:
                self.printl('MESExtractor started: {0}'.format(fragment_name_to_short_string(os.path.split(full_fragment_path)[1])))
                file_info = os.stat(full_fragment_path)
                # tell file_pool to close the file and freeze it until jobhandler is done with it:
               #self.zeromq_pusher.send((('close', full_fragment_path)))
                #self.zeromq_pusher.send((('suspend', full_fragment_path)))
                mes_extractor = importers.MESExtractor(full_fragment_path, config = self.config, queue_out = self.queues['low_priority_processor']['out'])                
                data_class, stimulus_class,anal_class_name, mes_name = mes_extractor.parse(fragment_check = True, force_recreate = force_recreate)
                file.set_file_dates(full_fragment_path, file_info)
                self.queues['low_priority_processor']['out'].put('SOC_mesextractor_readyEOCid={0}EOP' .format(id))
            else:
                self.printl('MESExtractor skipped')
        except:
            self.printl(traceback.format_exc())

    def find_cells(self, id = None):
        try:
            if self.config.ENABLE_CELL_DETECTION:
                full_fragment_path = file.get_measurement_file_path_from_id(id, self.config)
                if full_fragment_path is not None:
                    fragment_path = os.path.split(full_fragment_path)[1]
                    self.printl('Start finding cells: {0}'.format(fragment_name_to_short_string(fragment_path)))
                    file_info = os.stat(full_fragment_path)
                    if hasattr(self.config, 'GAMMA_CORRECTION'):
                        import copy
                        config = copy.deepcopy(self.config)
                        config.GAMMA_CORRECTION = 0
                    else:
                        config=self.config
                    if False:
                        result = analysis.cell_centers_from_fragment.delay(full_fragment_path, config, STATIC)
                        runtime = result.get()
                    elif not False:
                        runtime = 0
                        excluded_experiments = ['natural','receptive']
                        if len([True for excluded_experiment in excluded_experiments if excluded_experiment.lower() in full_fragment_path.lower()]) == 0:
                            create = ['roi_curves','soma_rois_manual_info']#'rawdata_mask',
                            export = ['roi_curves'] 
                            h = hdf5io.iopen(full_fragment_path,self.analysis_config)
                            if h is not None:
                                for c in create:
                                    self.printl('create_'+c)
                                    h.perform_create_and_save(c,overwrite=True,force=True,path=h.h5fpath)
                                for e in export:
                                    self.printl('export_'+e)
                                    getattr(h,'export_'+e)()
                                h.close()
                        else:
                            self.printl('No online analysis for this type of experiment')
                    else:
                        runtime=0
                    file.set_file_dates(full_fragment_path, file_info)
                    
                    if len(sys.argv) > 3:
                        self.kwargs['export'] = sys.argv[3]
                    if self.kwargs['export'] == 'EXPORT_SYNC_DATA_TO_MAT':
                        self.printl('Saving sync data to mat file')
                        from visexpA.users.zoltan import converters
                        converters.hdf52mat(full_fragment_path, rootnode_names = ['sync_signal', 'idnode'],  outtag = 'sync', outdir = os.path.split(full_fragment_path)[0], retain_idnode_name=False)
                    elif self.kwargs['export'] == 'EXPORT_DATA_TO_MAT':
                        self.printl('Saving data to mat file')
                        from visexpA.users.zoltan import converters
                        converters.hdf52mat(full_fragment_path, rootnode_names = ['idnode','rawdata', 'sync_signal'],  outtag = '_mat', outdir = os.path.split(full_fragment_path)[0])
                    self.queues['low_priority_processor']['out'].put('SOC_find_cells_readyEOCid={0},runtime={1}EOP'.format(id, runtime))
                else:
                    self.printl('Not existing ID: {0}'.format(id))
            else:
                self.printl('Cell detection skipped')
        except:
            self.printl(traceback.format_exc())

                     
   ############## Realignment/image registration ##########################
   # This is run here to avoid that because of data processing this function gets blocked
    def register(self, metric='MeanSquares', multiresolution=True, optimizertype='RegularStepGradientDescent', transform_type='Rigid2D'):
        '''
        f1 and f2 are stored in image.hdf5
        '''
        f1, f2 = self._load_images()
        self.queue_out.put('SOCregisterEOCstartedEOP')
        self.printl(('images loaded',  f1.shape,  f2.shape), to_queue = False)
        try:
#            result = itk_image_registration.register.delay(f1, f2, metric=metric,  optimizertype=optimizertype, multiresolution=bool(multiresolution), transform_type=transform_type, iterations = 400, debug=0)
#            values,  outimage, parameters = result.get()
            values,  outimage, parameters = itk_image_registration.register(f1, f2, metric=metric,  optimizertype=optimizertype, multiresolution=bool(multiresolution), transform_type=transform_type, iterations = 400, debug=0)
            values = str(values).replace(' ', '').replace('[', '').replace(']', '')
            self.printl(values, to_queue = False)
            self.queue_out.put('SOCregisterEOC{0}EOP' .format(values))
        except:
            self.printl(traceback.format_exc())
            self.queue_out.put('SOCregisterEOCerrorEOP')
        time.sleep(0.1)
        self.copy_request_pending = False
        
    def _load_images(self):
        image_hdf5_handler = hdf5io.Hdf5io(os.path.join(self.config.CONTEXT_PATH, 'image.hdf5'),filelocking=False)
        f1 = image_hdf5_handler.findvar('f1')
        f2 = image_hdf5_handler.findvar('f2')
        image_hdf5_handler.close()
        return f1, f2
        
    #####################Helpers############################    
    def echo(self, par):
        self.queue_out.put(self.message)
        
    def printl(self, message, to_queue = True):
        if to_queue:
            self.queue_out.put(message)
        message = str(message).replace('SOC', '').replace('EOC', '').replace('EOP', '')
        self.log.info(message)
        print utils.datetime_string() + ' ' + message
        
    def exit(self):
        self.queue_out.put('SOCclose_connectionEOCstop_clientEOP')
        return 'exit'

def fragment_name_to_short_string(filename):
    parts = file.parse_fragment_filename(filename)
    return '{0}, {1}, {2}, {3}'.format(parts['scan_mode'], parts['depth'], parts['stimulus_name'], parts['id'])
    
class TestJobhandler(unittest.TestCase):
   
    @unittest.skip('')
    def test_01_task_finished(self):
        import zmq
        from visexpman.users.zoltan.test import unit_test_runner
        import psutil
        for proc in psutil.process_iter():
            if 'comparer.py' in proc.name: # comparer is running
                pports = proc.get_connections()
        unit_test_runner.prepare_test_data('jobhandler_short')
        monitor = network_interface.ZeroMQPuller(5501,type='SUB', serializer= '')
        monitor.start()
        queue = network_interface.zmq_device(5500, 5502, 5501)
        jh = Jobhandler('daniel', 'RcMicroscopeSetup')
        jh.config.EXPERIMENT_DATA_PATH = unit_test_runner.TEST_working_folder
        jh.command_handler.mouse_file = 'mouse_000_xxx'
        jh.command_handler.find_cells_ready(id ='1355574962', runtime=0) #if comparer is not listening, message will be lost jobhandler should not care
        listener = network_interface.ZeroMQPuller(5502, type='PULL', serializer='json')
        listener.start()
        jh.command_handler.find_cells_ready(id ='1355574962', runtime=0) #should see the message in the monitor process
        print list(monitor.queue)
        print list(listener.queue)
        monitor.close()
        listener.close()
        queue.launcher.terminate()
        jh.close()
        del jh
        del queue
        
        pass
    
    def test_02_process_folder(self):
        datafolder = '/mnt/datafast/debug/new'
        
        mouse_file = os.path.join(datafolder, [fn for fn in os.listdir(datafolder) if 'mouse_' in fn][0])
        scan_regions = hdf5io.read_item(mouse_file, 'scan_regions',filelocking=False)
        jh = Jobhandler('daniel', 'RcMicroscopeSetup', export = 'EXPORT_SYNC_DATA_TO_MAT')
#        jh = Jobhandler('daniel', 'JobhandllerConfig', export = 'EXPORT_SYNC_DATA_TO_MAT')
        for k, v in scan_regions.items():
            if 'mast' in k: continue
            for id in [id for id in v['process_status'].keys() if 'Natural' in v['process_status'][id]['info']['stimulus'] ]:
                jh.command_handler.check_and_preprocess_fragment(id,force_recreate = True)
                jh.command_handler.find_cells(id)
        jh.close()
        

if __name__=='__main__':
    if len(sys.argv)==1:
        unittest.main()
    elif len(sys.argv)<3:
        print 'Command line parameters: username machine_config_name,  for example: daniel RcMicroscopeConfig'
    else:
        print sys.argv[1:]
        Jobhandler(sys.argv[1], sys.argv[2]).run()
    print 'jobhandler all done'
        
