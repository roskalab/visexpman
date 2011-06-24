'''calculates positions of n dots moving in 8 directions through the screen'''
import visexpman
import Helpers
from Helpers import normalize,  imshow
#from MultiLinePlot import WXPlot as WP
import Image
import numpy
from visexpman.engine.visual_stimulation import experiment
from visexpman.engine.generic import utils
from visexpman.engine.visual_stimulation import stimulation_library as stl
#import visexpman.engine.generic.configuration
#import visexpman.engine.generic.utils
import time

class MovingDotConfig(experiment.ExperimentConfig):
    def _create_application_parameters(self):
        #place for experiment parameters
        #parameter with range: list[0] - value, list[0] - range
        #path parameter: parameter name contains '_PATH'
        #string list: list[0] - empty        
        self.DIAMETER_UM = [200]
        self.ANGLES = [0,  90,  180,  270,  45,  135,  225,  315] # degrees
        self.SPEED = [1200] #[40deg/s] % deg/s should not be larger than screen size
        self.AMPLITUDE = 0.5
        self.REPEATS = 2
        self.PDURATION = 0
        self.GRIDSTEP = 1/3 # how much to step the dot's position between each sweep (GRIDSTEP*diameter)
        self.NDOTS = 1
        self.RANDOMIZE = 1
        self.runnable = 'MovingDot'
        self.pre_runnable = 'MovingDotPre'
        self.USER_ADJUSTABLE_PARAMETERS = ['DIAMETER_UM', 'SPEED', 'NDOTS', 'RANDOMIZE']
        self._create_parameters_from_locals(locals())
        experiment.ExperimentConfig.__init__(self) # needs to be called so that runnable is instantiated and other checks are done

class MovingDotPre(experiment.PreExperiment):    
    def run(self):
        #calls to stimulation library
        print 'pre running'
        time.sleep(0.2)
        pass

class MovingDot(experiment.Experiment):
    def __init__(self, experiment_config):
        experiment.Experiment.__init__(self, experiment_config)
        self.prepare()
        
    def run(self, stl):
        for dot_row_col in self.row_col:
            stl.show_dots(self.diameter_pix, dot_row_col, self.experiment_config.NDOTS,  color = [1.0, 1.0, 1.0])
        pass

    def prepare(self):
        # we want at least 2 repetitions in the same recording, but the best is to
        # keep all repetitions in the same recording
        angleset = numpy.sort(numpy.unique(self.experiment_config.ANGLES))
        diameter_pix = utils.retina2screen(self.experiment_config.DIAMETER_UM,machine_config=self.experiment_config.machine_config,option='pixels')
        self.diameter_pix = diameter_pix
        speed_pix = utils.retina2screen(self.experiment_config.SPEED,machine_config=self.experiment_config.machine_config,option='pixels')
        gridstep_pix = numpy.floor(self.experiment_config.GRIDSTEP*diameter_pix)
        movestep_pix = speed_pix/self.experiment_config.machine_config.SCREEN_EXPECTED_FRAME_RATE
        h=self.experiment_config.machine_config.SCREEN_RESOLUTION['row']#monitor.resolution.height
        w=self.experiment_config.machine_config.SCREEN_RESOLUTION['col']#monitor.resolution.width
        hlines_r,hlines_c = numpy.meshgrid(numpy.arange(numpy.ceil(diameter_pix/2), w-numpy.ceil(diameter_pix/2),gridstep_pix),  
            numpy.arange(-diameter_pix, h+diameter_pix+0.1, movestep_pix))
        vlines_c,vlines_r = numpy.meshgrid(numpy.arange(numpy.ceil(diameter_pix/2), h-numpy.ceil(diameter_pix/2),gridstep_pix), 
            numpy.arange(-diameter_pix, w+diameter_pix, movestep_pix))
        # we go along the diagonal from origin to bottom right and take perpicular diagonals' starting
        # and ing coords and lengths

        # diagonals run from bottom left to top right
        dlines,dlines_len = diagonal_tr(45,diameter_pix,gridstep_pix,movestep_pix,w,h)

        diag_dur = 4*sum(dlines_len)/speed_pix/self.experiment_config.NDOTS
        line_len={'ver0': (w+(diameter_pix*2))*numpy.ones((1,vlines_r.shape[1])), 
                        'hor0' : (h+(diameter_pix*2))*numpy.ones((1,hlines_r.shape[1]))}
        ver_dur = 2*line_len['ver0'].sum()/speed_pix/self.experiment_config.NDOTS
        hor_dur = 2*line_len['hor0'].sum()/speed_pix/self.experiment_config.NDOTS
        total_dur = (self.experiment_config.PDURATION*8+diag_dur+ver_dur+hor_dur)*self.experiment_config.REPEATS
        nblocks = numpy.ceil(total_dur/self.experiment_config.machine_config.MAXIMUM_RECORDING_DURATION)[0]
        block_dur = total_dur/nblocks
        block_dur = block_dur
        # we divide the grid into multiple recording blocks if necessary, all
        # ANGLES and repetitions are played within a block
        allangles0 = numpy.tile(angleset, [self.experiment_config.REPEATS])
        permlist = getpermlist(allangles0.shape[0], self.experiment_config.RANDOMIZE)
        allangles = allangles0[permlist]
        ANGLES = allangles
        # coords are in matrix coordinates: origin is topleft corner. 0 degree runs
        # from left to right.
        #ANGLES = 0:45:315
        #screen('closeall')
        arow_col = []
        for a in range(len(angleset)):
            arow_col.append([])
            for b in range(nblocks):
                arow_col[a].append([])
                # subsample the trajectories keeping only every nblocks'th line
                if numpy.any(angleset[a]==[0,90,180,270]):
                    if numpy.any(angleset[a]==[90,270]):
                        vr = vlines_r[:,b::nblocks] 
                        vc=vlines_c[:,b::nblocks]
                        if angleset[a]==270: # swap coordinates
                            vr = vr[-1::-1] 
                            vc = vc[-1::-1]
                    elif numpy.any(angleset[a]==[0,180]): # dots run horizontally
                        vr = hlines_r[:,b::nblocks]
                        vc= hlines_c[:,b::nblocks]
                        if angleset[a]==180:
                            vr = vr[-1::-1]
                            vc = vc[-1::-1]
                    # try to balance the dot run lengths (in case of multiple dots) so that most of the time the number of dots on screen is constant        
                    
                    segm_length = vr.shape[0]/self.experiment_config.NDOTS #length of the trajectory 1 dot has to run in the stimulation segment
                    cl =range(vr.shape[0])
                    #partsep = [zeros(1,self.experiment_config.NDOTS),size(vr,2)]
                    partsep = range(0 , vr.shape[0], numpy.ceil(segm_length))
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
                else:
                    row_col_f,linelengths_f = diagonal_tr(angleset[a],diameter_pix,gridstep_pix,movestep_pix,w,h)
                    row_col =row_col_f[b::nblocks]
                    linelengths = linelengths_f[b:: nblocks]
                    segm_len = linelengths.sum()/self.experiment_config.NDOTS
                    cl =numpy.cumsum(linelengths)
                    partsep = numpy.c_[numpy.zeros((1,self.experiment_config.NDOTS)),len(linelengths)].T
                    for d1 in range(1, self.experiment_config.NDOTS+1):
                        partsep[d1] = numpy.argmin(numpy.abs(cl-(d1)*segm_len))
                        dots_line_i[d1-1] = range(partsep[d1-1],partsep[d1]+1)
                    while 1:
                        part_len = []
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
        self.row_col = []
        self.angle_end = []
        self.block_end = []
        # create a list of coordinates where dots have to be shown, note when a direction subblock ends, and when a block ends (in case the stimulus has to be split into blocks due to recording duration limit)
        for b in range(nblocks):
            for a1 in range(len(allangles)):
                cai = numpy.where(angleset==allangles[a1])[0]
                for f in range(arow_col[cai][b][0].shape[1]):
                    coords = []
                    for n in range(self.experiment_config.NDOTS):
                        coords.append(arow_col[cai][b][n][:,f])
                    self.row_col.append(utils.rc(numpy.array(coords)))
                self.angle_end.append(len(self.row_col))
            self.block_end.append(len(self.row_col))
    
def  diagonal_tr(angle,diameter_pix,gridstep_pix,movestep_pix,w,h):
    ''' Calculates positions of the dot(s) for each movie frame along the lines dissecting the screen at 45 degrees'''
    cornerskip = numpy.ceil(diameter_pix/2)+diameter_pix
    pos_diag = [0 for i in range(3)] #preallocate list. Using this prealloc we can assign elements explicitly (not with append) that makes the code clearer for this algorithm
    diag_start_row = [0 for i in range(3)] ; diag_end_col = [0 for i in range(3)] 
    diag_start_col = [0 for i in range(3)] ; diag_end_row = [0 for i in range(3)] 
    pos_diag[0] = numpy.arange(cornerskip, h/numpy.sqrt(2), gridstep_pix) # spacing of diagonals running from bottomleft 
    diag_start_row[0] = numpy.sqrt(2)*pos_diag[0]
    diag_start_col[0] = numpy.ones(diag_start_row[0].shape)
    diag_end_row[0] = numpy.ones(diag_start_row[0].shape)
    diag_end_col[0] = diag_start_row[0].copy()
    # we reached the bottom line, now keep row fixed and col moves till w
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
            dlines.append(numpy.c_[aline_col, aline_row])
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
        #place for experiment parameters
        #parameter with range: list[0] - value, list[0] - range
        #path parameter: parameter name contains '_PATH'
        #string list: list[0] - empty        
        self.DIAMETER_UM = [200]
        self.ANGLES = [0,  90,  180,  270,  45,  135,  225,  315] # degrees
        self.SPEED = [1200] #[40deg/s] % deg/s should not be larger than screen size
        self.AMPLITUDE = 0.5
        self.REPEATS = 2
        self.PDURATION = 0
        self.GRIDSTEP = 1.0/3 # how much to step the dot's position between each sweep (GRIDSTEP*diameter)
        self.NDOTS = 1
        self.RANDOMIZE = 1
        self.runnable = 'MovingDot'
        self.pre_runnable = 'MovingDotPre'
        self.USER_ADJUSTABLE_PARAMETERS = ['DIAMETER_UM', 'SPEED', 'NDOTS', 'RANDOMIZE']
        self._create_parameters_from_locals(locals())

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
        
    return

def run_stimulation(vs):
    vs.run()
    
if __name__ == '__main__':
    import visexpman
    import threading
    from visexpman.engine.run_visual_stimulation import VisualStimulation
    vs_runner = VisualStimulation('ZoliTester', 'daniel')
    messages = ['start_stimulation']
    parameters = ['']
    pause_before = [1, 2]
    sender = threading.Thread(target=send_tcpip_sequence, args=(vs_runner, messages, parameters, pause_before))
    sender.setDaemon(True)
    sender.start()
    vs_runner.run()
#    runner = threading.Thread(target=run_stimulation, args=(vs_runner, ))
#    runner.setDaemon(True)
#    runner.start()
    pass
