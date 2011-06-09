from visexpman.engine.generic import utils
import numpy
from scipy.ndimage.morphology import binary_erosion,  binary_dilation
import Helpers
from Helpers import normalize, l2s,  imshow
#from MultiLinePlot import WXPlot as WP
from numpy.random import shuffle as nshuffle
from numpy.random import random_integers
import Image
omap_b =[]

def calib(gridpoints,  cfg,  dot_area, dot_coord, dots_per_size, allowed_white_area_variation):
    # determine how many dots to fit into the multidot frames
        # calculate the area left for smallest dot size
    dots_per_size['mean'] = numpy.r_[[numpy.floor(float(dot_area[ds1+1])/dot_area[ds1])  for ds1 in range(len(dot_diameter_f)-1)], [1]] 
    multidot_frame_n = numpy.ceil(len(gridpoints[1])/dots_per_size['mean'][1])
    
    icd = numpy.setdiff1d(range(len(gridpoints)),cfg.enforce_complete_dots)
    part_dots={'center':[], 'ndots_extra':[], 'consumed_dots': numpy.array([0,0])}
    for e1 in numpy.sort(icd):
        part_dots['center'].append([numpy.array(cgp) for cgp in gridpoints[e1] if 
                            (cgp[0] < dot_diameter_f[e1]/2) + (cgp[0]>cfg.monitor['resolution']['height']-dot_diameter_f[e1]/2) +
                            (cgp[1] < dot_diameter_f[e1]/2) + (cgp[1]>cfg.monitor['resolution']['width']-dot_diameter_f[e1]/2)>0])
        
        part_dots['ndots_extra'].append(numpy.empty((len(part_dots['center'][-1]),e1 ), numpy.uint16))
        for g1 in range(len(part_dots['center'][-1])):
            inds = translate_dot(cfg.mres,part_dots['center'][-1][g1], dot_coord[e1])
            if e1 in self.onedot_perframe:
                missing_area = dot_area[e1]-len(inds)
                part_dots['ndots_extra'][-1][g1]=numpy.round(float(missing_area)/dot_area[0:e1])
                if numpy.abs(part_dots['ndots_extra'][-1][g1, e1-1]*dot_area[e1-1] - missing_area) <= allowed_white_area_variation:
                    part_dots['ndots_extra'][-1][g1, 0]=0
                else:
                    if part_dots['ndots_extra'][-1][g1, e1-1]*dot_area[e1-1] - missing_area > 0: #remove one bigger dot and fill up with smaller dots
                        part_dots['ndots_extra'][-1][g1, e1-1] -= 1
                    part_dots['ndots_extra'][-1][g1, 0] = round((missing_area - part_dots['ndots_extra'][-1][g1, 0]*dot_area[e1-1])/dot_area[0])
                part_dots['consumed_dots'] += part_dots['ndots_extra'][-1][g1]
            else:
                missing_area = abs(dot_area[-1]-(round(dots_per_size['mean'][e1])*dot_area[e1]-(dot_area[e1]-len(inds))))
                if missing_area > allowed_white_area_variation:
                    part_dots['ndots_extra'][-1][g1] = round(float(missing_area-allowed_white_area_variation)/dot_area[e1-1])
                else:
                    part_dots['ndots_extra'][-1][g1] =0
                part_dots['consumed_dots'] +=part_dots['ndots_extra'][-1][g1]
    return part_dots,  dots_per_size
    
 
def find_free_gridpoint(previous_frame_mask,current_frame_mask,dot_diameters,cdotsize,gridpoints,enforce_complete_dots,ONOFFratio):
    # Erodes previous_frame_mask with cdotsize. In previous_frame_mask allowed points are marked
    # with white. Dilates current_frame_mask with cdotsize*ONOFFratio
    # The eroded picture's white pixel coordinates are intersected
    # with the grid coordinates.
    # Returns gridpoint coordinates
    possible=[]
    cdotsize+=1
    if previous_frame_mask.dtype != numpy.bool:
        raise TypeError('Mask images must have boolean type')
    while len(possible) == 0:
        cdotsize -= 1
        if cdotsize in enforce_complete_dots:
            pmask = binary_erosion(previous_frame_mask,iterations=numpy.ceil(dot_diameters[cdotsize]/2)) # exclude borders so that valid area ensures complete dots
        else:
            pmask = -binary_dilation(-previous_frame_mask,iterations=numpy.ceil(dot_diameters[cdotsize]/2)) # do not exclude borders
        cmask = binary_dilation(current_frame_mask, iterations = numpy.ceil(dot_diameters[cdotsize]/2)) 
        comb_mask = pmask*(-cmask)
        possible= comb_mask.nonzero()
    free_gp = numpy.intersect1d(gridpoints[cdotsize],Helpers.rc(possible)) # which grid point lie in the valid range?
    if len(free_gp)==0: # pick a random location
        # find lowest disk sized area in omap where possible is true
        gpr = numpy.random.random_integers(0, len(possible[0])-1, 1)
        gp = Helpers.rc((possible[0][gpr], possible[1][gpr]))
        extra = True
    else:
        extra = False
        fi = random_integers(0, len(free_gp)-1,1)
        gp = free_gp[fi]
        gpi = numpy.where(gridpoints[cdotsize]==gp)[0] 
        # remove grid location from the list of available locations
        gridpoints[cdotsize]=numpy.delete(gridpoints[cdotsize], gpi)#.r{cdotsize}=gridpoints.r{cdotsize}...
    return gp, gridpoints,  cdotsize,  extra

def find_space(dot_radius):
    global omap_b
    level_map = numpy.zeros(omap_b.shape)
    lp = level_map.nonzero()
    level=omap_b.min()+1
    while len(lp[0])==0:
        level_map[omap_b<level]=1
        lp=binary_erosion(level_map,iterations=dot_radius).nonzero()
    
    
def  occupancy_map(mres,gridpoints,dot_coord, selection=None):
    omap = numpy.ma.zeros(mres)
    if selection is None: selection = len(gridpoints) 
    for od1 in range(selection):
        for p in range(len(gridpoints[od1])):
            omap = add_dot(omap,gridpoints[od1][p], dot_coord[od1],1)
    omap_b=omap
    omask = numpy.zeros(omap_b.shape, numpy.bool)
    omask[omap_b==0]=1
    omap_b.mask=omask
    return omap_b

def  add_dot(full_im,center, dot, color):
    # adds color value to the coordinates of full_im to which dot coordinates
    # point. The center of the dot given in dot_r, dot_c must be at 0,0
    inds = translate_dot(full_im.shape,center, dot)
    full_im[inds['row'], inds['col']] += color
    return full_im

def  translate_dot(heightwidth,center, dot_coord):
    r= dot_coord['row']+center['row']
    c= dot_coord['col']+center['col']
    vp = (r>0) * (r<heightwidth[0]) * (c>0) * (c<heightwidth[1])
    r= r[vp]
    c= c[vp]
    return Helpers.rc(numpy.c_[r, c])

def circle_coord(diameter,  resolution = 1.0,  image_size = None,  color = 1.0,  pos = (0, 0)):
    '''
    diameter: diameter of circle in pixels
    resolution: angle resolution of drawing circle
    image_size: x, y size of image/numpy array in pixels
    color: color of circle, greyscale, range 0...1
    pos : x, y position in pixels, center is 0, 0
    '''
    import Image,  ImageDraw,  numpy
    from bresenham import circle_arc
    vertices = utils.calculate_circle_vertices([diameter,  diameter],  resolution)
    if image_size is None:
        image_size = max(vertices)
    image = Image.new('L',  image_size,  0)
    draw = ImageDraw.Draw(image)
    
    vertices_int = []
    for i in vertices:
        vertices_int.append(int(i[0] + image_size[0] * 0.5) + pos[0])
        vertices_int.append(int(i[1] + image_size[1] * 0.5) - pos[1])
    
    
    draw.polygon(vertices_int,  fill = int(color * 255.0))    
    #just for debug
    image.show()
    print numpy.asarray(image)
    return numpy.asarray(image)

    
class Config:
    def __init__(self, debug_flag=0, seed=9):
        self.dot_diameter_um=[50, 200, 600]
        self.sec_per_block    = 270
        self.iniduration = 10 #seconds
        self.frames_per_sec = 1/0.5
        self.gridstep_factor = [1, 0.2, 0.2]
        self.monitor = {'resolution':{'width':[], 'height':[]}}
        self.monitor['resolution']['width'] =1024
        self.monitor['resolution']['height']= 768
        self.monitor['distancefrom_mouseeye'] = 36  #cm
        self.monitor['pixelwidth'] = 0.0425  #cm
        self.monitor['directlyonretina']=0 
        self.ONOFFratio = 1 # ratio of ON and OFF receptive field subregions, e.g. 1 means ON is a disk, OFF is an annulus with with=disk's diameter
        self.enforce_complete_dots = [0] # 'all' or the index of the dot_size(s) or 0 for 'none'
        self.bglevel = 0 # if 0: white is shown on black bg, if 128: black and white is shown on gray bg
        self.target_white_active_per_frame_ratio = 0.08 # ratio of the screen having white pixels
        self.white_area_variation_factor = 0.2 # times the middle dot area
        self.finalize(debug_flag, seed)
        
    def finalize(self, debug_flag, seed):
        '''Performs consistency checks and value transformations
        '''
        if debug_flag:
            self.subsample = self.monitor['resolution']['width']/800
        else:
            self.subsample=8
        if self.enforce_complete_dots=='all':
            self.enforce_complete_dots = range(len(self.dot_diameter_um))
        self.monitor['pixelwidth']=self.monitor['pixelwidth']
        self.monitor['resolution']['width']/=self.subsample
        self.monitor['resolution']['height']/=self.subsample
        self.monitor['npixels']=self.monitor['resolution']['width'] *self.monitor['resolution']['height'] 
        self.target_white_active_in_frame = self.target_white_active_per_frame_ratio*self.monitor['npixels']
        self.mres = numpy.array([self.monitor['resolution']['height'], self.monitor['resolution']['width']])
        dot_diameter_f = utils.retina2screen(self.dot_diameter_um,monitor=self.monitor,option='pixels')
        self.dot_diameter_pixels = dot_diameter_f/self.subsample
        self.seed=seed#2:6
        
class SparseDots():
    def __init__(self):
        ''' See wiki for explanations
        '''
        pass
    def prepare(self, cfg):
        from bresenham import bresenham_circle, disk
        self.cfg=cfg
        numpy.random.seed(cfg.seed)
         # measure number of pixels that dot types occupy on screen
        self.dot_coord = [Helpers.rc(list(disk((0, 0), di2/2))) for di2 in cfg.dot_diameter_pixels]
        dot_area = numpy.array([len(d) for d in self.dot_coord])
        # precompute dot coordinates that contain off pixels too
        self.dotmask_coord =  [Helpers.rc(list(disk((0, 0), di2/2*(1+cfg.ONOFFratio)))) for di2 in cfg.dot_diameter_pixels]
        n_dots_cover_screen = [numpy.ceil(cfg.mres/(di2*(1+2*cfg.ONOFFratio))).prod() for di2 in cfg.dot_diameter_pixels]
        self.onedot_perframe = numpy.nonzero(dot_area>cfg.target_white_active_in_frame)[0] # these types will be shown not in every frame
        multidot_perframe = numpy.nonzero(dot_area<=cfg.target_white_active_in_frame)[0]
        self.allowed_white_area_variation = cfg.white_area_variation_factor*dot_area[1]#middle dot size
        
        gridpoints = [];npos=[]
        for s1 in range(len(cfg.dot_diameter_pixels)):
            gridstep = cfg.dot_diameter_pixels[s1]*cfg.gridstep_factor[s1] # smallest receptive field on the retina is 200um
            if s1 in cfg.enforce_complete_dots: 
                bound = cfg.dot_diameter_pixels[s1]/2
            else: bound = 0
            gridpoints.append(Helpers.rc_flatten(numpy.meshgrid(numpy.arange(bound, cfg.monitor['resolution']['height']-bound, gridstep),
                numpy.arange(bound, cfg.monitor['resolution']['width']-bound, gridstep))))
        
        dots_per_size = numpy.r_[[numpy.floor(float(dot_area[ds1+1])/dot_area[ds1])  for ds1 in range(len(cfg.dot_diameter_pixels)-1)], [1]] 
        nframes_multidotperframe = numpy.ceil(len(gridpoints[1])/dots_per_size[1]) # this is an overestimation:when it is allowed to show incomplete biggest dots, the missing white pixels are filled with smaller dots
        nframes_onedotperframe = len(gridpoints[self.onedot_perframe])
        nframes_to_visit_grid_points =nframes_onedotperframe+nframes_multidotperframe
        nframes = int(nframes_to_visit_grid_points)
        self.nblocks = numpy.ceil(float(nframes)/(cfg.frames_per_sec*cfg.sec_per_block))# number of animation frames in loop
        self.frames_in_block=numpy.ceil(nframes/self.nblocks)
         
     #   RandStream.setDefaultStream(RandStream('mt19937ar','seed',1))
        self.debug_subsample = cfg.mres[1]/128
        previous_frame_mask = numpy.ones((2, cfg.monitor['resolution']['height'], cfg.monitor['resolution']['width']), numpy.bool)
        
        for b1 in range(self.nblocks): #each block must be a complete space so that blocks can also be analysed separately
            self.xy = {'center':[], 'color':[], 'diameter_pixels':[]}
            # subsample grid evenly across blocks
            gridpoints_b = [g[b1::self.nblocks] for g in gridpoints]
            n_pos_block = [len(g) for g in gridpoints_b]
            # compute occupancy map for the gridpoints visited in this block
            global omap_b
            omap_b = occupancy_map(cfg.mres,gridpoints_b,self.dot_coord)
            nframes_onedotperframe_b = n_pos_block[self.onedot_perframe]
            # allocate random time positions for big dots that are shown only once
            # in each grid node. Do not allow big dots at the  of the block
            # since number of frames in the block is not fully determined yet
            # (spatial constraints can make the block longer or shorter)
            biglim = 1#0.8
            timevec=numpy.zeros((self.frames_in_block,), numpy.uint16)
            self.debug_frames = cfg.bglevel*numpy.ones((cfg.mres/self.debug_subsample).tolist()+[self.frames_in_block],numpy.uint8)

            ti1 = 1
            for o1 in range(len(self.onedot_perframe)):
                timevec[ti1:ti1+len(gridpoints[self.onedot_perframe[o1]])]=self.onedot_perframe[o1]
                ti1 = ti1+len(gridpoints[self.onedot_perframe[o1]])+1
            
            nshuffle(timevec) # when to show large dots
            self.n_small_per_frame = len(gridpoints_b[0])/(timevec==0).sum()
            timevec[timevec==0]=self.onedot_perframe[0]-1 # in the rest of frames show the largest of the "small dots" at least once
            # compute occupancy map for all dot sizes visiting their
            # possible grid positions at least once
            previous_frame_maskflag = 0 # toggle this if the constraint of not allowing black and white pixels be at the same locations in consecutive frames but at least one grey time instance is required
            f=0
            missing_frames=numpy.inf
            while missing_frames>1:#missing_flashes_b > min(dot_area)
                #print('frame {0}'.format(f))
                # keep constant fill ratio and consume dot_types according to
                # dot_type_per_frame
                if sum(timevec[f:][numpy.where(timevec[f:]==2)[0]])/2 != len(gridpoints_b[2]):
                    pass
                if len(timevec) < f and len(gridpoints_b[2])>0: # in theory all gridpoints of biggest dots should have been assigned to original timevec
                    pass
                elif timevec[f]>multidot_perframe[-1]:
                    cdotsize = timevec[f] #single dot in frame
                else:
                    cdotsize = multidot_perframe[-1] # start with largest dot size assigned to the frame
                
                center, color, diameter_pixels, randflag = self.populate_frame(dot_area,cdotsize,gridpoints_b,\
                    previous_frame_mask, previous_frame_maskflag)
                randi = numpy.nonzero(randflag)[0]
                if 0 in randi and diameter_pixels[0]== self.cfg.dot_diameter_pixels[2]:
                    return len(gridpoints_b[2])
                    raise RuntimeError('Biggest dot was generated at random position. We try to avoid this. Change the seed of the random generator.')
                if diameter_pixels[0] != self.cfg.dot_diameter_pixels[cdotsize]: # could not fit planned dot size due to previous frame dot arrangement
                    #find next multidot time instance and replace it with the one just consumed
                    nmd = numpy.where(timevec[f:]==self.onedot_perframe[0]-1)[0]
                    timevec[f]=self.onedot_perframe[0]-1
                    if nmd.shape[0]==0:
                        timevec = numpy.append(timevec, cdotsize)
                    else:
                        timevec[f+nmd[0]]=cdotsize
                missing_frames = sum([len(gridpoints_b[g])/numpy.prod(dots_per_size[g:]) for g in range(len(gridpoints_b))])
                self.xy['center'].append(center)
                self.xy['color'].append(color)
                self.xy['diameter_pixels'].append(diameter_pixels)
                self.debug_frames[:,:,f] = numpy.array(Image.fromarray(normalize(previous_frame_mask[1-previous_frame_maskflag], numpy.uint8)).resize((self.debug_frames.shape[:2]))).T
                previous_frame_mask[previous_frame_maskflag] = numpy.ones(cfg.mres, numpy.bool) # reset previous_frame_mask not used in next round
                f=f+1
                previous_frame_maskflag=1-previous_frame_maskflag
            
            xyi, debug_i = self.populate_iniframes([g[b1::self.nblocks] for g in gridpoints], dot_area)
            for k in self.xy.keys():
                xyi[k].extend(self.xy[k])
                self.xy[k] = xyi[k]
            self.debug_frames = numpy.dstack((debug_i, self.debug_frames[:, :, 0:f]))
            self.export_to_matlab(b1)
     
    def populate_iniframes(self, gridpoints, dot_area):
        ''' populates frames to show before the real stimulus to accomodate the visual system. 
        Generates frames backwards using the first real frame as previous_frame_mask'''
        previous_frame_mask = numpy.ones((2, cfg.monitor['resolution']['height'], cfg.monitor['resolution']['width']), numpy.bool)
        previous_frame_maskflag = 0
        previous_frame_mask[previous_frame_maskflag] = normalize(numpy.array(Image.fromarray(self.debug_frames[:, :, 0]).resize(self.cfg.mres)), numpy.bool).T
        n_iniframes = self.cfg.iniduration*self.cfg.frames_per_sec
        timevec=numpy.zeros((n_iniframes,), numpy.uint16)
        debug_frames = cfg.bglevel*numpy.ones((cfg.mres/self.debug_subsample).tolist()+[n_iniframes],numpy.uint8)
        ti1 = 0
        for o1 in range(len(self.onedot_perframe)):
            timevec[ti1:ti1+round(n_iniframes/4)]=self.onedot_perframe[o1]
            ti1 += round(n_iniframes/4)
        nshuffle(timevec) # when to show large dots
        timevec[timevec==0]=self.onedot_perframe[0]-1 # in the rest of frames show the largest of the "small dots" at least once
        xy= {'center':[], 'color':[], 'diameter_pixels':[]}
        for i1 in range(n_iniframes):
            center, color, diameter_pixels, randflag = self.populate_frame(dot_area,timevec[i1],gridpoints,\
                    previous_frame_mask, previous_frame_maskflag)
            xy['center'].append(center)
            xy['color'].append(color)
            xy['diameter_pixels'].append(diameter_pixels)
            debug_frames[:,:,i1] = numpy.array(Image.fromarray(normalize(previous_frame_mask[1-previous_frame_maskflag], numpy.uint8)).resize((self.debug_frames.shape[:2]))).T
            previous_frame_mask[previous_frame_maskflag] = numpy.ones(self.cfg.mres, numpy.bool) # reset previous_frame_mask not used in next round
            previous_frame_maskflag=1-previous_frame_maskflag
        [item.reverse() for k, item in xy.items()]
        return xy,  debug_frames[:, :, ::-1]
        
    def populate_frame(self, dot_area,dotsizes,gridpoints, previous_frame_mask, pfmf):
        current_frame_mask = numpy.zeros(self.cfg.mres, numpy.bool)
        carea=0
        cdotsizes = dotsizes
        cdotsi = cdotsizes  
        missing_area = dot_area[-1] # target is that each frame has as many pixels as the largest dot. 
        center =[];color=[];diameter_pixels=[];  extra=[]
        while missing_area>self.allowed_white_area_variation:
            gp,gridpoints, cdotsi, randflag = find_free_gridpoint(previous_frame_mask[pfmf],current_frame_mask,
                    self.cfg.dot_diameter_pixels,cdotsi,gridpoints,self.cfg.enforce_complete_dots,self.cfg.ONOFFratio)
            inds = translate_dot(self.cfg.mres,gp, self.dot_coord[cdotsi])
            previous_frame_mask[1-pfmf, inds['row'], inds['col']]=0 # next round cannot put objects that were active in this round
            minds = translate_dot(self.cfg.mres, gp, self.dotmask_coord[cdotsi])
            current_frame_mask[minds['row'], minds['col']]=1
            missing_area -= len(inds)
            center.append(gp)
            color.append(255)
            extra.append(randflag)
            diameter_pixels.append(self.cfg.dot_diameter_pixels[cdotsi])
            if len(inds)==dot_area[2]: # dot type of "self.onedot_perframe" and fully on screen
                break
            if missing_area < dot_area[cdotsi]:
                cdotsi-=1
        return center,  color, diameter_pixels, extra
    
    def export_to_matlab(self, bi):
        from scipy.io import savemat
        import zipfile
        import StringIO, os
        from CaData import rawdata2avi_menc
        xy=self.xy
        filename=generate_filename(['fixed_compl_random', self.cfg.dot_diameter_um,self.cfg.mres*self.cfg.subsample,self.cfg.ONOFFratio,
                self.cfg.enforce_complete_dots,self.cfg.bglevel,self.cfg.gridstep_factor,self.nblocks,
                self.cfg.white_area_variation_factor, self.cfg.sec_per_block,self.cfg.iniduration, self.cfg.frames_per_sec, bi])
        while os.path.exists(filename+'.mat'):
            bi+=1
            filename=generate_filename(['fixed_compl_random', self.cfg.dot_diameter_um,self.cfg.mres*self.cfg.subsample,self.cfg.ONOFFratio,
                self.cfg.enforce_complete_dots,self.cfg.bglevel,self.cfg.gridstep_factor,self.nblocks,
                self.cfg.white_area_variation_factor, self.cfg.sec_per_block,self.cfg.iniduration, self.cfg.frames_per_sec, bi])
        xyv = numpy.concatenate([numpy.c_[[(fi,p['row']*self.cfg.subsample, p['col']*self.cfg.subsample, color, dia*self.cfg.subsample)  for p, color, dia in zip(
                xy['center'][fi], xy['color'][fi], xy['diameter_pixels'][fi])]] for fi in range(len(xy['center']))])
        s = StringIO.StringIO()
        zf = zipfile.ZipFile(s, 'w')
        zf.write(__file__)
        savemat(filename, {'xy':xyv, 'debug_frames':self.debug_frames,'creating_code':s.getvalue(), 'seed':self.cfg.seed})
        rawdata2avi_menc(self.debug_frames, '/data/temp/test.avi')
        
def generate_filename(args):
    '''creates a string that is used as mat file name to store random dot
    positions
    This method has to be the exact port of the matlab function with the same name'''
    type = args[0]
    if hasattr(type, 'tostring'): type=type.tostring()
    radii = l2s(args[1])
    if len(type)==0 or type=='random':
        n_dots,nframes,interleave,interleave_step = args[2:]
        fn = radii+'{0:.0f}-{1:.0f}-{2:.0f}-{3:.0f}.mat'.format(n_dots[0], nframes[0], interleave[0], interleave_step[0])
    elif type=='fixed':
        n_dots,gridstep_factor,nblocks,sec_per_block,frames_per_sec=args[1:]
        fn = radii+'{0}-{1:1.2f}-{2}-{3}-{4}.mat'.format(n_dots, gridstep_factor,
                                        nblocks, sec_per_block, frames_per_sec)
    elif type=='fixed_compl_random':
        res,ONOFFratio,enforce_complete_dots,bglevel, gridstep_factor,\
            nblocks, white_area_variation_factor,sec_per_block, iniduration, frames_per_sec, bi = args[2:]
        fn = radii+'_{0}_{1}_{2}_{3}_{4}_{5}_{6}_{7}_{8}_{9}'.format(l2s(res, '-','1.0f'),  l2s(gridstep_factor,'-',  '1.2f'),
                            l2s(enforce_complete_dots,'-',  '1.0f'), l2s(sec_per_block), l2s(iniduration), l2s(frames_per_sec, '', '1.2f'), l2s(ONOFFratio, '-', '1.2f'),  
                            l2s(white_area_variation_factor, '', '1.2f'), l2s(bglevel),l2s(bi))
    return fn
    

if __name__ == '__main__':
    sd=[] #9:1, 45:0, 123:0
    #srange = range(194, 390)
    srange=[45, 123,272,275]
    for seed in srange:
    #seed=45
        cfg = Config(seed=seed)
        sdo = SparseDots()
        sd.append(sdo.prepare(cfg))
        print(sd[-1])
    print(repr(zip(srange, sd)))
