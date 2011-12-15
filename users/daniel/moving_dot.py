'''calculates positions of n dots moving in 8 directions through the screen'''
import visexpman
import os.path
try:
    import Helpers
    from Helpers import normalize,  imshow
except:
    pass
#from MultiLinePlot import WXPlot as WP
import Image
import numpy
from visexpman.engine.visual_stimulation import experiment
from visexpman.engine.generic import utils
#from visexpman.engine.visual_stimulation import stimulation_library as stl
#import visexpman.engine.generic.configuration
import visexpman.engine.visual_stimulation.command_handler as command_handler
import visexpman.engine.hardware_interface.daq_instrument as daq_instrument
import visexpman.engine.hardware_interface.mes_interface as mes_interface
import time
import visexpA.engine.datahandlers.hdf5io as hdf5io
import pickle
import copy
import visexpA.engine.datahandlers.matlabfile as matlab_mat
import shutil

class MovingDotConfig(experiment.ExperimentConfig):
    def _create_application_parameters(self):
        #place for experiment parameters
        #parameter with range: list[0] - value, list[0] - range
        #path parameter: parameter name contains '_PATH'
        #string list: list[0] - empty        
        self.DIAMETER_UM = [200]
        self.ANGLES = [0,  90,  180,  270, 45,  135,  225,  315] # degrees
#        self.ANGLES = [0] # degrees
        self.SPEED = [1800] #[40deg/s] % deg/s should not be larger than screen size
        self.AMPLITUDE = 0.5
        self.REPEATS = 1
        self.PDURATION = 0
        self.GRIDSTEP = 1.0/3 # how much to step the dot's position between each sweep (GRIDSTEP*diameter)
        self.NDOTS = 1
        self.RANDOMIZE = 1
        self.runnable = 'MovingDot'
#         self.pre_runnable = 'MovingDotPre'
        self.USER_ADJUSTABLE_PARAMETERS = ['DIAMETER_UM', 'SPEED', 'NDOTS', 'RANDOMIZE']
        MES_PARAMETER_PATH = os.path.join(self.machine_config.EXPERIMENT_DATA_PATH, 'parameter', 'line_scan_parameters.mat')
        self._create_parameters_from_locals(locals())
#         experiment.ExperimentConfig.__init__(self) # needs to be called so that runnable is instantiated and other checks are done

class MovingDotPre(experiment.PreExperiment):    
    def run(self):
        #calls to stimulation library
        print 'pre running'
        time.sleep(0.2)
        pass

class MovingDot(experiment.Experiment):
    def __init__(self, machine_config, caller, experiment_config):
        experiment.Experiment.__init__(self, machine_config, caller, experiment_config)
        self.prepare()
        
    def run(self):
        self.show_fullscreen(color = 0.0)
        experiment_start_time = int(time.time())
        number_of_fragments = len(self.row_col)
        ######################## Prepare line scan parameter file ###############################
        self.printl('create parameter file')
        parameter_file_prepare_success, parameter_file = self.mes_interface.prepare_line_scan(scan_time = 1.0)
        if parameter_file_prepare_success:
            for di in range(len(self.row_col)):
                ######################## Prepare fragment ###############################                
                #Generate file name
                mes_fragment_name = '{0}_{1}_{2}'.format(self.experiment_name, experiment_start_time, di)
                self.printl('Fragment {0}/{1}, name: {2}'.format(di + 1, len(self.row_col), mes_fragment_name))
                fragment_mat_path = os.path.join(self.machine_config.EXPERIMENT_DATA_PATH, ('fragment_{0}.mat'.format(mes_fragment_name)))
                fragment_hdf5_path = fragment_mat_path.replace('.mat', '.hdf5')
                #Create mes parameter file
                stimulus_duration = float(len(self.row_col[di]) / self.experiment_config.NDOTS)/self.machine_config.SCREEN_EXPECTED_FRAME_RATE
                mes_interface.set_line_scan_time(stimulus_duration + 3.0, parameter_file, fragment_mat_path)
                ######################## Start mesurement ###############################
               #Start recording analog signals
                ai = daq_instrument.AnalogIO(self.machine_config, self.caller)
                ai.start_daq_activity()
                self.log.info('ai recording started')
               #empty queue
                while not self.mes_response.empty():
                    self.mes_response.get()
               #start two photon recording
                line_scan_start_success, line_scan_path = self.mes_interface.start_line_scan(parameter_file = fragment_mat_path)
                if line_scan_start_success:
                    time.sleep(1.0)
                    self.printl('visual stimulation started')
                   ######################## Start visual stimulation ###############################
                    self.show_dots([self.diameter_pix]*len(self.row_col[di]), self.row_col[di], self.experiment_config.NDOTS,  color = [1.0, 1.0, 1.0])
                    self.show_fullscreen(color = 0.0)                    
                    line_scan_complete_success =  self.mes_interface.wait_for_line_scan_complete(0.5 * stimulus_duration)
                    ######################## Finish fragment ###############################
                    if line_scan_complete_success:
                       #Stop acquiring analog signals
                        ai.finish_daq_activity()
                        ai.release_instrument()
                        self.printl('ai recording finished, waiting for data save complete')
                        line_scan_data_save_success = self.mes_interface.wait_for_line_scan_save_complete(stimulus_duration)
                        ######################## Save data ###############################
                        if line_scan_data_save_success:
                            self.printl('Saving measurement data to hdf5')
                           #Save
                            fragment_hdf5 = hdf5io.Hdf5io(fragment_hdf5_path , config = self.machine_config, caller = self.caller)
                            if not hasattr(ai, 'ai_data'):
                                ai.ai_data = numpy.zeros(2)                            
                            data_to_hdf5 = {
                                            'sync_data' : ai.ai_data,
                                            'mes_data': utils.file_to_binary_array(fragment_mat_path),
                                            'number_of_fragments' : number_of_fragments,
                                            'actual_fragment' : di,
                                            }
                            helper_data ={}
                            if hasattr(self, 'show_line_order'):
                                helper_data['shown_line_order'] = self.shown_line_order[di]
                            if hasattr(self,'shown_directions'):
                                helper_data['shown_directions']= self.shown_directions[di]
                            data_to_hdf5['generated_data'] = helper_data
                           #Saving source code of experiment
                            for path in self.caller.visexpman_module_paths:
                                if 'moving_dot.py' in path:
                                    data_to_hdf5['experiment_source'] = utils.file_to_binary_array(path)
                                    break
                            utils.save_config(fragment_hdf5, self.machine_config, self.experiment_config)
                            time.sleep(5.0) #Wait for file ready            
                            utils.save_position(fragment_hdf5, self.stage.read_position(),mes_interface.get_objective_position(fragment_mat_path))
                            fragment_hdf5.machine_config = copy.deepcopy(self.machine_config.get_all_parameters())
                            fragment_hdf5.experiment_config = self.experiment_config.get_all_parameters()
                            setattr(fragment_hdf5, mes_fragment_name, data_to_hdf5)
                            fragment_hdf5.save(mes_fragment_name)
                            fragment_hdf5.close()
                           #move/delete mat file
                            self.printl('measurement data saved to hdf5: {0}'.format(fragment_hdf5_path))                            
                           #Notify VisexpA, data files are ready
                            if self.command_buffer.find('stop') != -1:
                                self.command_buffer.replace('stop', '')
                                self.printl('user stopped experiment')
                        else:
                            reason = 'line scan data save error'
                            self.printl(reason)                            
                    else:
                        reason = 'line scan complete error'
                        self.printl(reason)                        
                else:
                    reason = 'line scan start error'
                    self.printl(reason)                    
            experiment_identifier = '{0}_{1}'.format(self.experiment_name, experiment_start_time)        
            self.experiment_hdf5_path = os.path.join(self.machine_config.EXPERIMENT_DATA_PATH, experiment_identifier + '.hdf5')
            setattr(self.hdf5, experiment_identifier, {'id': None})
            self.hdf5.save(experiment_identifier)            
            #Try to set back line scan time to initial 2 sec
            self.printl('set back line scan time to 2s')
            mes_interface.set_line_scan_time(2.0, parameter_file, parameter_file)
            line_scan_start_success, line_scan_path = self.mes_interface.start_line_scan(timeout = 5.0, parameter_file = parameter_file)
            if not line_scan_start_success:
                self.printl('setting line scan time to 2 s was not successful')
            else:
                line_scan_complete_success =  self.mes_interface.wait_for_line_scan_complete(2.0)
                if line_scan_complete_success:
                    line_scan_save_complete_success =  self.mes_interface.wait_for_line_scan_save_complete(2.0)
        else:
            self.printl( 'Parameter file not created')
        self.printl('moving dot complete')
    
    def post_experiment(self):
        if hasattr(self, 'experiment_hdf5_path'):
            try:
                shutil.move(self.hdf5.filename, self.experiment_hdf5_path)
            except:
                print self.hdf5.filename, self.experiment_hdf5_path
                self.printl('not copied for some reason')
        
    def prepare(self):
        # we want at least 2 repetitions in the same recording, but the best is to
        # keep all repetitions in the same recording
        angleset = numpy.sort(numpy.unique(self.experiment_config.ANGLES))
        allangles0 = numpy.tile(angleset, [self.experiment_config.REPEATS])
        permlist = getpermlist(allangles0.shape[0], self.experiment_config.RANDOMIZE)
        allangles = allangles0[permlist]

        diameter_pix = utils.retina2screen(self.experiment_config.DIAMETER_UM,machine_config=self.experiment_config.machine_config,option='pixels')
        self.diameter_pix = diameter_pix
        speed_pix = utils.retina2screen(self.experiment_config.SPEED,machine_config=self.experiment_config.machine_config,option='pixels')
        gridstep_pix = numpy.floor(self.experiment_config.GRIDSTEP*diameter_pix)
        movestep_pix = speed_pix/self.experiment_config.machine_config.SCREEN_EXPECTED_FRAME_RATE
        h=self.experiment_config.machine_config.SCREEN_RESOLUTION['row']#monitor.resolution.height
        w=self.experiment_config.machine_config.SCREEN_RESOLUTION['col']#monitor.resolution.width
        hlines_c,hlines_r = numpy.meshgrid(numpy.arange(-diameter_pix, w+diameter_pix,movestep_pix),  
            numpy.arange(numpy.ceil(diameter_pix/2), h-numpy.ceil(diameter_pix/2), gridstep_pix))
        vlines_r,vlines_c = numpy.meshgrid(numpy.arange(-diameter_pix, h+diameter_pix,movestep_pix), 
            numpy.arange(numpy.ceil(diameter_pix/2), w-numpy.ceil(diameter_pix/2), gridstep_pix))
        # we go along the diagonal from origin to bottom right and take perpicular diagonals' starting
        # and ing coords and lengths
        # diagonals run from bottom left to top right
        dlines,dlines_len = diagonal_tr(45,diameter_pix,gridstep_pix,movestep_pix,w,h)

        diag_dur = 4*sum(dlines_len)/speed_pix/self.experiment_config.NDOTS #each diagonal is shown 4 times, this is not optimal, we should look into angles and check the number of diagonal directions
        diag_line_maxlength = max(dlines_len)
        longest_line_dur = max([diag_line_maxlength, (w+diameter_pix*2)])/speed_pix/self.experiment_config.NDOTS # vertical direction has no chance to be longer than diagonal
        if longest_line_dur > self.experiment_config.machine_config.MAXIMUM_RECORDING_DURATION: #check if allowed block duration can accomodate the longest line
            raise ValueError('The longest trajectory cannot be shown within the time interval set as MAXIMUM RECORDING DURATION')
        line_len={'ver0': (w+(diameter_pix*2))*numpy.ones((1,vlines_c.shape[0])),  # add 2*line_lenght to trajectory length, because the dot has to completely run in/out to/of the screen in both directions
                        'hor0' : (h+(diameter_pix*2))*numpy.ones((1,hlines_c.shape[0]))}
        ver_dur = 2*line_len['ver0'].sum()/speed_pix/self.experiment_config.NDOTS #2 vertical directions are to be shown
        hor_dur = 2*line_len['hor0'].sum()/speed_pix/self.experiment_config.NDOTS
        total_dur = (self.experiment_config.PDURATION*8+diag_dur+ver_dur+hor_dur)*self.experiment_config.REPEATS
        nblocks = numpy.ceil(total_dur/self.experiment_config.machine_config.MAXIMUM_RECORDING_DURATION)[0]
        # hard limit: a block in which all directions are shown the grid must not be sparser than 3*dot size. Reason: we assume dotsize
        # corresponds to excitatory receptive field size. We assume excitatiory receptive field is surrounded by inhibitory fields with same width.
         # here we divide the grid into multiple recording blocks if necessary
        if nblocks*gridstep_pix > diameter_pix*3:
            self.caller.log.info('Stimulation has to be split into blocks. The number of blocks is too high meaning that the visual field would be covered too sparsely in a block \
                if we wanted to present all angles in every block. We shall multiple lines in a block but not all angles.')
            self.angles_broken_to_multi_block( w, h, diameter_pix, speed_pix,gridstep_pix, movestep_pix,  hlines_r, hlines_c, vlines_r, vlines_c,   angleset, allangles)
        else:
            vr_all= dict();vc_all=dict()
            vr_all[(90, 270,)] = [vlines_r[b::nblocks, :] for b in range(int(nblocks))]
            vc_all[(90, 270,)] = [vlines_c[b::nblocks, :] for b in range(int(nblocks))]
            vr_all[(0, 180,)] = [hlines_r[b::nblocks, :] for b in range(int(nblocks))]
            vc_all[(0, 180,)]= [hlines_c[b::nblocks, :] for b in range(int(nblocks))]
            self.allangles_in_a_block(diameter_pix,gridstep_pix,movestep_pix,w, h, nblocks,  vr_all, vc_all, angleset, allangles, total_dur)
            
    def angles_broken_to_multi_block(self, w, h, diameter_pix, speed_pix,gridstep_pix, movestep_pix,  hlines_r, hlines_c, vlines_r, vlines_c,   angleset, allangles):
        '''In a block the maximum possible lines from the same direction is put. Direction is shuffled till all lines to be shown are put into blocks.
        Repetitions are not put into the same block'''
        from copy import deepcopy
        if self.experiment_config.NDOTS > 1:
            raise NotImplementedError('This algorithm is not yet working when multiple dots are to be shown on the screen')
        nlines_in_block_hor = int(numpy.floor(self.experiment_config.machine_config.MAXIMUM_RECORDING_DURATION / ((w+diameter_pix*2)/speed_pix/self.experiment_config.NDOTS))) #how many horizontal trajectories fit into a block? 
        nlines_in_block_ver = int(numpy.floor(self.experiment_config.machine_config.MAXIMUM_RECORDING_DURATION / ((h+diameter_pix*2)/speed_pix/self.experiment_config.NDOTS))) #how many horizontal trajectories fit into a block? 
        nblocks_hor = int(numpy.ceil(float(hlines_r.shape[0])/nlines_in_block_hor))
        nblocks_ver = int(numpy.ceil(float(vlines_r.shape[0])/nlines_in_block_ver))
        #nlines_in_block_diag=
        line_order = dict()
        lines_rowcol = dict()
        if 90 in angleset:
            line_order[90] = [numpy.arange(b, vlines_r.shape[0], nblocks_ver) for b in range(nblocks_ver)]
            lines_rowcol[90] = [numpy.vstack(numpy.dstack([vlines_r[b::nblocks_ver, :],  vlines_c[b::nblocks_ver, :]])) for b in range(nblocks_ver)]
        if 270 in angleset:
            line_order[270] = [numpy.arange(b, vlines_r.shape[0], nblocks_ver) for b in range(nblocks_ver)]
            lines_rowcol[270] = [numpy.vstack(numpy.dstack([vlines_r[b::nblocks_ver, :][-1::-1, :],  vlines_c[b::nblocks_ver, :][-1::-1, :]])) for b in range(nblocks_ver)]
        if 0 in angleset:
            line_order[0] = [numpy.arange(b, hlines_r.shape[0], nblocks_hor) for b in range(nblocks_hor)]
            lines_rowcol[0] = [numpy.vstack(numpy.dstack([hlines_r[b::nblocks_hor, :],  hlines_c[b::nblocks_hor, :]])) for b in range(nblocks_hor)]
        if 180 in angleset:
            line_order[180] = [numpy.arange(b, hlines_r.shape[0], nblocks_hor) for b in range(nblocks_hor)]
            lines_rowcol[180] = [numpy.vstack(numpy.dstack([hlines_r[b::nblocks_hor, :][-1::-1, :],  hlines_c[b::nblocks_hor, :][-1::-1, :]])) for b in range(nblocks_hor)]
        diag_angles = [a1 for a1 in angleset if a1 in [45, 135, 225, 315]] #this implementation does not require doing the loop for all angles but we do it anyway, eventually another implementation might give different results for different angles
        for a1 in diag_angles:
            line_order[a1]=[]
            lines_rowcol[a1] = []
            row_col_f,linelengths_f = diagonal_tr(a1,diameter_pix,gridstep_pix,movestep_pix,w, h)
            linelengths_f = numpy.squeeze(linelengths_f) # .shape[1] = NDOTS
            # for diagonal lines we need to find a good combination of lines that fill the available recording time
            while linelengths_f.sum()>0:
                line_order[a1].append([])
                # in a new block, first take the longest line
                cblockdur=0
                while linelengths_f.sum()>0 and cblockdur < self.experiment_config.machine_config.MAXIMUM_RECORDING_DURATION:                    
                    li = int(numpy.where(linelengths_f==max(linelengths_f))[0][0])
                    if cblockdur+linelengths_f[li]/speed_pix/self.experiment_config.NDOTS > self.experiment_config.machine_config.MAXIMUM_RECORDING_DURATION:
                        break # we found a line that fits into max recording duration
                    line_order[a1][-1].append(int(numpy.where(linelengths_f==linelengths_f[li])[0][0])) #if needed, this converts negative index to normal index
                    cblockdur += max(linelengths_f)/speed_pix/self.experiment_config.NDOTS
                    linelengths_f[li] = 0
                    if linelengths_f.sum()==0: break
                    # then find the line at half-screen distance and take it as next line
                    li = li - int(row_col_f.shape[0]/2) #negative direction automatically wrapped in numpy
                    step=1
                    all_sides = 0
                    while linelengths_f[li]==0: # look at both sides of the line which was already used
                        li += -1*step
                        if cblockdur+linelengths_f[li]/speed_pix/self.experiment_config.NDOTS <  self.experiment_config.machine_config.MAXIMUM_RECORDING_DURATION:
                            break # we found a line that fits into max recording duration
                        allsides+=1
                        if allsides == 2: #both negative and positive offsets from the original lines have been tried
                            step+=1 # step to next two neighbors
                            allsides=0
                        if li + step > len(linelengths_f):
                            li = None
                            break
                    if li== None: # no more lines for this block
                        break
                    else: # append the line to the list of lines in the current block
                        line_order[a1][-1] .append(int(numpy.where(linelengths_f==linelengths_f[li])[0][0]))
                        cblockdur += linelengths_f[li]/speed_pix/self.experiment_config.NDOTS
                        linelengths_f[li]=0
                lines_rowcol[a1].append(numpy.vstack(row_col_f[line_order[a1][-1]]))

        self.row_col = [] # list of coordinates to show on the screen
        self.block_end = [] # index in the coordinate list where stimulation has to stop and microscope needs to save data
        self.shown_directions = [] # list of direction of each block presented on the screen
        self.shown_line_order  = []
        for r in range(self.experiment_config.REPEATS):
            lines_rc = deepcopy(lines_rowcol) # keep original data in case of multiple repetitions. 
            lineo = deepcopy(line_order)
            while sum([len(value) for key, value in lines_rc.items()])>0: # are there lines that have not yet been shown?
                for direction in angleset: # display blocks obeying angle pseudorandom order
                    if len(lines_rc[direction])>0:
                        lrc = lines_rc[direction].pop();# take the last element (containing n lines) and remove from list of lines to be shown
                        self.row_col.append(utils.rc(numpy.array(lrc)))
                        self.block_end.append(len(self.row_col))
                        self.shown_directions.append(direction)
                        self.shown_line_order.append(lineo[direction].pop())
        return 
        
    def allangles_in_a_block(self, diameter_pix,gridstep_pix,movestep_pix,w, h, nblocks,  vr_all, vc_all, angleset, allangles, total_dur):
        '''algortithm that splits the trajectories to be shown into blocks so that each block shows all angles and repetitions'''
        block_dur = total_dur/nblocks
        
        # ANGLES and repetitions are played within a block
        # coords are in matrix coordinates: origin is topleft corner. 0 degree runs
        # from left to right.
        arow_col = []
        for a in range(len(angleset)):
            arow_col.append([])
            for b in range(int(nblocks)):
                arow_col[a].append([])
                # in order to fit into the time available for one recording (microscope limitation) we keep only every nblocks'th line in one block. This way all blocks have all directions. 
                #For very short block times this would keep only 1 or 2 trajectory from a given direction in a block which is not good because we are supposed to wait between changing directions
               # so that calcium transients can settle and we can clearly distinguish responses belonging to different directions. 
                if numpy.any(angleset[a]==[0,90,180,270]):
                    direction = [k for k in vr_all.keys() if angleset[a] in k][0]
                    vr = vr_all[direction][b]; vc = vc_all[direction][b]
                    if angleset[a] in [270, 180]: # swap coordinates
                        vr = vr[-1::-1] 
                        vc = vc[-1::-1]
                    
                    # try to balance the dot run lengths (in case of multiple dots) so that most of the time the number of dots on screen is constant        
                    segm_length = vr.shape[1]/self.experiment_config.NDOTS #length of the trajectory 1 dot has to run in the stimulation segment
                    cl =range(vr.shape[0])
                    #partsep = [zeros(1,self.experiment_config.NDOTS),size(vr,2)]
                    partsep = range(0 , vr.shape[0], int(numpy.ceil(segm_length)))
                    if len(partsep)<self.experiment_config.NDOTS+1:
                        partsep.append(vr.shape[1])
                    dots_line_i = [range(partsep[d1-1], partsep[d1]) for d1 in range(1, self.experiment_config.NDOTS+1)]
                    drc=[]
                    for s1 in range(self.experiment_config.NDOTS): #each dot runs through a full line
                        dl = numpy.prod(vr[:,dots_line_i[s1]].shape)
                        drc.append(numpy.r_[numpy.reshape(vr[:,dots_line_i[s1]],[1,dl]), 
                            numpy.reshape(vc[:,dots_line_i[s1]],[1,dl])])
                        if s1>1 and dl < len(drc[s1-1]): # a dot will run shorter than the others
                        # the following line was not tested in python (works in matlab)
                            drc[s1] = numpy.c_[drc[s1],-diameter_pix*numpy.ones(2,len(drc[s1-1])-dl)] # complete with coordinate outside of the screen
                else: # diagonal line
                    row_col_f,linelengths_f = diagonal_tr(angleset[a],diameter_pix,gridstep_pix,movestep_pix,w, h)
                    row_col =row_col_f[b::nblocks]
                    linelengths = linelengths_f[b:: nblocks]
                    segm_len = linelengths.sum()/self.experiment_config.NDOTS
                    cl =numpy.cumsum(linelengths)
                    partsep = numpy.c_[numpy.zeros((1,self.experiment_config.NDOTS)),len(linelengths)].T
                    dots_line_i = [[] for i2 in range(self.experiment_config.NDOTS)]
                    for d1 in range(1, self.experiment_config.NDOTS+1):
                        partsep[d1] = numpy.argmin(numpy.abs(cl-(d1)*segm_len))
                        dots_line_i[d1-1] = range(partsep[d1-1],partsep[d1]+1)
                    while 1:
                        part_len = []
                        drc = [[] for i2 in range(self.experiment_config.NDOTS)]
                        for d1 in range(1, self.experiment_config.NDOTS+1):
                            drc[d1-1]=numpy.vstack(row_col[dots_line_i[d1-1]]).T
                            part_len.append(sum(linelengths[dots_line_i[d1-1]]))
                        si = numpy.argmin(part_len) # shortest dot path
                        li = numpy.argmax(part_len) # longest dot path
                        takeable_i = dots_line_i[li]
                        takeable_lengths=linelengths[takeable_i]
                        midpoint = part_len[li]-part_len[si]
                        if numpy.any(takeable_lengths<midpoint):
                            mli = numpy.argmin(numpy.abs(takeable_lengths-midpoint)) # moved line
                            taken_line_i = dots_line_i[li][mli]
                            dll = len(dots_line_i[li])
                            dots_line_i[li] = dots_line_i[li][numpy.c_[range(mli-1),range(mli+1, dll)]]
                            dots_line_i[si] = numpy.c_[dots_line_i[si],  taken_line_i]
                        else:
                            break
                    ml=[]
                    for s1 in range(self.experiment_config.NDOTS): #each dot runs through a full line
                        drc[s1]= numpy.vstack(row_col[dots_line_i[s1]]).T#row_col[dots_line_i[s1]]
                        ml.append(len(drc[s1]))
                    for s1 in range(self.experiment_config.NDOTS):
                        if len(drc[s1])<max(ml): # a dot will run shorter than the others
                            drc[s1] = numpy.c_[drc[s1],-diameter_pix*numpy.ones(2,max(ml)-len(drc[s1]))] # complete with coordinate outside of the screen
                arow_col[a][b] = drc
        self.row_col = [] # list of coordinates to show on the screen
        self.line_end = [] # index in coordinate list where a line ends and another starts (the other line can be of the same or a different direction
        self.shown_directions = [] # list of direction of each block presented on the screen
        # create a list of coordinates where dots have to be shown, note when a direction subblock ends, and when a block ends (in case the stimulus has to be split into blocks due to recording duration limit)
        for b in range(int(nblocks)):
            self.row_col.append([])
            self.shown_directions.append([])
            self.line_end.append([])
            for a1 in range(len(allangles)):
                cai = numpy.where(angleset==allangles[a1])[0]
                for f in range(arow_col[cai][b][0].shape[1]):
                    coords = []
                    for n in range(self.experiment_config.NDOTS):
                        coords.append(arow_col[cai][b][n][:,f])
                    self.row_col[-1].extend(coords)
                self.shown_directions[-1].append((allangles[a1], sum(len(s1) for s1 in self.row_col[-1]))) # at each coordinate we store the direction, thus we won't need to analyze dot coordinates 
                self.line_end[-1].append(arow_col[cai][b][0].shape[1])
            self.row_col[-1]=utils.rc(numpy.array(self.row_col[-1]))
        pass
    
def  diagonal_tr(angle,diameter_pix,gridstep_pix,movestep_pix,w,h):
    ''' Calculates positions of the dot(s) for each movie frame along the lines dissecting the screen at 45 degrees'''
    cornerskip = numpy.ceil(diameter_pix/2)+diameter_pix # do not show dot where it would not be a full dot, i.e. in the screen corners
    pos_diag = [0 for i in range(3)] #preallocate list. Using this prealloc we can assign elements explicitly (not with append) that makes the code clearer for this algorithm
    diag_start_row = [0 for i in range(3)] ; diag_end_col = [0 for i in range(3)] 
    diag_start_col = [0 for i in range(3)] ; diag_end_row = [0 for i in range(3)] 
    # pos_diag is a diagonal running at 45 degree from the vertical (?):
    # we space perpendicularly running dots on this diagonal, trajectories are spaced at regular intervals
    pos_diag[0] = numpy.arange(cornerskip, h/numpy.sqrt(2), gridstep_pix) 
    diag_start_row[0] = numpy.sqrt(2)*pos_diag[0]
    diag_start_col[0] = numpy.ones(diag_start_row[0].shape)
    diag_end_row[0] = numpy.ones(diag_start_row[0].shape)
    diag_end_col[0] = diag_start_row[0].copy()
    # we reached the bottom of the screen along the 45 degree diagonal. To continue this diagonal,we now keep row fixed and col moves till w
    pos_diag[1] = numpy.arange(pos_diag[0][-1]+gridstep_pix, w/numpy.sqrt(2), gridstep_pix)
    #!!! small glitch in start coord's first value
    diag_start_col[1] = numpy.sqrt(2)*pos_diag[1]-h
    diag_start_row[1] = numpy.ones(diag_start_col[1].shape)*diag_start_row[0][-1]
    diag_end_col[1] = numpy.sqrt(2)*pos_diag[1]
    diag_end_row[1] = numpy.ones(diag_end_col[1].shape)
    # we reached the right edge of the screen,
    endp = numpy.sqrt(2)*w-2*cornerskip
    pos_diag[2] = numpy.arange(pos_diag[1][-1]+gridstep_pix, endp, gridstep_pix)
    diag_start_col[2] = numpy.sqrt(2)*pos_diag[2]-h
    diag_start_row[2] = numpy.ones(diag_start_col[2].shape)*diag_start_row[0][-1]
    diag_end_row[2] = w - numpy.sqrt(2)*(w*numpy.sqrt(2)-pos_diag[2])
    diag_end_col[2] = numpy.ones(diag_end_row[2].shape)*w

    dlines_len=[]
    dlines=[]
    offs= diameter_pix*1/numpy.sqrt(2)
    swap=0
    oppositedir=0 # 45 degrees
    if numpy.any(angle == [45+180,135+180]):
        oppositedir = 1
    if numpy.any(angle==[135,135+180]):
        swap = 1
    dfl =0
    if dfl:
        full = QPlotWindow(None, visible=False)
    for d1 in range(len(pos_diag)):
        for d2 in range(len(pos_diag[d1])):
            dlines_len.append(numpy.sqrt((diag_start_row[d1][d2]+offs-(diag_end_row[d1][d2]-offs))**2+
                (diag_start_col[d1][d2]-offs-(diag_end_col[d1][d2]+offs))**2))
            npix = numpy.ceil(dlines_len[-1]/movestep_pix)
            if swap: # 
                s_r = h-diag_start_row[d1][d2]-offs
                e_r = h-diag_end_row[d1][d2]+offs
            else:
                s_r = diag_start_row[d1][d2]+offs
                e_r = diag_end_row[d1][d2]-offs
            
            s_c = diag_start_col[d1][d2]-offs
            e_c = diag_end_col[d1][d2]+offs
            if oppositedir:
                aline_row = numpy.linspace(e_r,s_r,npix)
                aline_col = numpy.linspace(e_c,s_c,npix)
            else:
                aline_row = numpy.linspace(s_r,e_r,npix)
                aline_col = numpy.linspace(s_c,e_c,npix)
            
            if dfl:
                full.p.setdata([w, 0, 0, h, w, h, w, h],n=[0, 0, 0, 0, w, 0, 0, h],  penwidth=w,  color=Qt.Qt.black)#, vlines =self.rawfullblockstartinds)
                full.p.adddata(diag_start_row[d1][d2],diag_start_col[d1][d2], color=Qt.Qt.green, type='x')
                full.p.adddata(diag_end_row[d1][d2],diag_end_col[d1][d2], color=Qt.Qt.blue, type='x')
                full.p.adddata(s_r,s_c, color=Qt.Qt.red, type='x')
                full.p.adddata(e_r,e_c, color=Qt.Qt.darkRed, type='x')
                full.p.addata(aline_row,aline_col)
                #axis equal
                #axis([1-diameter_pix,w+diameter_pix,1-diameter_pix,h+diameter_pix])axis ij #plot in PTB's coordinate system
            dlines.append(numpy.c_[aline_row, aline_col])
    row_col = dlines
    return numpy.array(row_col),numpy.array(dlines_len) #using array instead of list enables fancy indexing of elements when splitting lines into blocks
        


def getpermlist(veclength,RANDOMIZE):
    if veclength > 256:
        raise ValueError('Predefined random order is only for vectors with max len 256')
    fullpermlist = numpy.array([200,212,180,52,115,84,122,123,2,113,119,168,112,202,153,80,126,78,59,154,131,118,251,167,141,105,51,181,254,
                15,135,189,173,188,159,45,158,245,10,124,156,190,11,221,208,54,106,71,102,91,66,151,148,225,175,152,48,146,172,98,47,145,57,
                28,201,55,13,9,82,32,114,163,93,64,228,162,29,27,187,134,164,253,127,218,35,109,237,211,17,4,72,116,230,165,233,207,96,198,234,
                81,213,191,62,238,8,183,65,89,161,99,133,38,197,142,111,132,196,169,195,75,58,139,250,244,193,21,90,6,242,63,43,69,30,14,37,226,206,
                140,240,255,76,34,223,110,67,61,125,166,20,239,79,107,121,120,219,40,209,231,104,108,128,224,70,155,92,24,176,204,235,229,26,56,252,
                178,136,74,3,12,117,101,186,130,203,39,16,232,137,246,36,249,7,143,241,129,95,31,138,220,210,185,50,97,214,68,85,243,73,88,215,77,41,
                149,248,194,25,182,23,256,5,236,1,33,103,157,217,19,192,18,147,170,179,174,83,49,44,184,144,53,22,199,222,150,216,227,100,171,42,94,177,86,46,247,205,60,87,160])-1 # was defined in matlab so we transform to 0 based indexing
    if RANDOMIZE:
        permlist = fullpermlist[fullpermlist<veclength] # pick only values that address the vector's values
    else:
        permlist = numpy.arange(veclength)
    return permlist

   
def generate_filename(args):
    '''creates a string that is used as mat file name to store random dot
    positions
    This method has to be the exact port of the matlab def with the same name'''
    type = args[0]
    if hasattr(type, 'tostring'): type=type.tostring()
    radii = l2s(args[0])
    if len(type)==0 or type=='random':
        n_dots,nframes,interleave,interleave_step = args[2:]
        fn = radii+'[0:.0f]-[1:.0f]-[2:.0f]-[3:.0f].mat'.format(n_dots[0], nframes[0], interleave[0], interleave_step[0])
    elif type=='fixed':
        n_dots,gridstep_factor,nblocks,sec_per_block,frames_per_sec=args[1:]
        fn = radii+'[0]-[1:1.2f]-[1]-[2]-[4].mat'.format(n_dots, gridstep_factor,
                                        nblocks, sec_per_block, frames_per_sec)
    elif type=='fixed_compl_random':
        res,ONOFFratio,enforce_complete_dots,bglevel, gridstep_factor,\
            nblocks, white_area_variation_factor,sec_per_block, iniduration, frames_per_sec, bi = args[2:]
        fn = radii+'_[0]_[0]_[1]_[2]_[4]_[5]_[6]_[7]_[8]_[9]'.format(l2s(res, '-','1.0f'),  l2s(gridstep_factor,'-',  '1.2f'),
                            l2s(enforce_complete_dots,'-',  '1.0f'), l2s(sec_per_block), l2s(iniduration), l2s(frames_per_sec, '', '1.2f'), l2s(ONOFFratio, '-', '1.2f'),  
                            l2s(white_area_variation_factor, '', '1.2f'), l2s(bglevel),l2s(bi))
        return fn
        
class MovingDotTestConfig(experiment.ExperimentConfig):
    def _create_application_parameters(self):  
    	self.MAX_FRAGMENT_TIME = 120.0
        self.DIAMETER_UM = [200]
        self.ANGLES = [0, 90, 180, 270] # degrees
        self.SPEED = [1200] #[40deg/s] % deg/s should not be larger than screen size
        self.AMPLITUDE = 0.5
        self.REPEATS = 2
        self.PDURATION = 0
        self.GRIDSTEP = 1.0/1 # how much to step the dot's position between each sweep (GRIDSTEP*diameter)
        self.NDOTS = 1
        self.RANDOMIZE = 1
        self.runnable = 'MovingDot'
        self.USER_ADJUSTABLE_PARAMETERS = ['DIAMETER_UM', 'SPEED', 'NDOTS', 'RANDOMIZE']
        self._create_parameters_from_locals(locals())
        
#RZ: send_tcpip_sequence and run_stimulation methods are probably obsolete:
def send_tcpip_sequence(vs_runner, messages, parameters,  pause_before):    
    '''This method is intended to be run as a thread and sends multiple message-parameter pairs. 
    Between sending individual message-parameter pairs, we wait pause_before amount of time. This can be used to allow remote side do its processing.'''
    import socket
    import struct
#    l_onoff = 1                                                                                                                                                           
  #  l_linger = 0                                                                                                                                                          
    #sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,                                                                                                                     
      #           struct.pack('ii', l_onoff, l_linger))
    # Send data
    for i in range(len(messages)):
        while vs_runner.state !='idle':
            time.sleep(0.2)
        time.sleep(pause_before[i])
        print 'slept ' + str(pause_before[i])
        try:
            sock = socket.create_connection(('localhost', 10000))
            sock.sendall('SOC'+messages[i]+'EOC'+parameters[i]+'EOP')
        except Exception as e:
            print e
        finally:  
            sock.close()
    print 'everything sent,  returning'
    return

def run_stimulation(vs):
    vs.run()
    
if __name__ == '__main__':
    import visexpman    
    import sys
    from visexpman.engine.visexp_runner import VisExpRunner
    vs_runner = VisExpRunner('daniel', sys.argv[1]) #first argument should be a class name
#     commands = [
#                     [0.0,'SOCexecute_experimentEOC'],                    
#                     [0.0,'SOCquitEOC'],
#                     ]
#     cs = command_handler.CommandSender(vs_runner.config, vs_runner, commands)
#     cs.start()
    vs_runner.run_loop()
#     cs.close()

