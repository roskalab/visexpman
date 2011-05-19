'''calculates positions of n dots moving in 8 directions through the screen'''
import utils
import numpy
import Helpers
from Helpers import normalize, l2s,  imshow
#from MultiLinePlot import WXPlot as WP
import Image

class MovingDot(Experiment):
    def run(self):
        self.diameter_um = [200]
        self.angles = [0,  90,  180,  270,  45,  135,  225,  315] # degrees
        self.speed = [1200] #[40deg/s] % deg/s should not be larger than screen size
        self.amplitude = 0.5
        self.repeats = 2
        self.pduration = 0
        self.gridstep = 1/3 # how much to step the dot's position between each sweep (gridstep*diameter)
        self.ndots = 1
        self.randomize = 1
        dot_sizes, dot_positions = movingdot_prepare(self)
        self.st.show_dots(dot_sizes, dot_positions, duration = fd,  color = colors)


    def prepare(pars)
    # we want at least 2 repetitions in the same recording, but the best is to
    # keep all repetitions in the same recording
    angleset = numpy.sort(numpy.unique(pars.angles))
    spatialfreq = utils.retina2screen(diameter_um,[],monitor)'; # from micometers on the retina to cycles per pixel
    moving_dot.diameter_pix = retina2screen(diameter_um,[],monitor,'pixels')'; 
    diameter_pix=moving_dot.diameter_pix
    moving_dot.tex = Screen('OpenOffScreenWindow', hw.win, [0,0,0,0], [0 0 diameter_pix diameter_pix])
    Screen('FillOval',moving_dot.tex,255,[0,0,diameter_pix,diameter_pix])
    moving_dot.speed_pix = retina2screen(speed,[],monitor,'pixels')'; 
    speed_pix=moving_dot.speed_pix
    [cyclepersec time4onecycleonscreen] = retina2screen(diameter_um, speed,monitor)
    allspatialfreq0 = repmat(spatialfreq,[1,length(speed)])
    allspeed0 = reshape(cyclepersec,size(allspatialfreq0))
    gridstep_pix = floor(gridstep*diameter_pix)
    movestep_pix = hw.ifi*speed_pix
    h=monitor.resolution.height
    w=monitor.resolution.width
    [hlines_r,hlines_c] = meshgrid(ceil(diameter_pix/2):gridstep_pix:w-ceil(diameter_pix/2),...
        -diameter_pix:movestep_pix:h+diameter_pix)
    [vlines_c,vlines_r] = meshgrid(ceil(diameter_pix/2):gridstep_pix:h-ceil(diameter_pix/2),...
        -diameter_pix:movestep_pix:w+diameter_pix)
    # we go along the diagonal from origin to bottom right and take perpicular diagonals' starting
    # and ing coords and lengths

    # perpiculars run from bottom left to top right
    [dlines,dlines_len]= diagonal_tr(45,diameter_pix,gridstep_pix,movestep_pix,w,h)

    diag_dur = 4*sum(dlines_len)/speed_pix/ndots
    len.ver0 = (w+(diameter_pix*2))*ones(1,size(vlines_r,2))
    len.hor0 = (h+(diameter_pix*2))*ones(1,size(hlines_r,2))
    ver_dur = 2*sum(len.ver0)/speed_pix/ndots
    hor_dur = 2*sum(len.hor0)/speed_pix/ndots
    total_dur = (pduration*8+diag_dur+ver_dur+hor_dur)*repeats
    nblocks = ceil(total_dur/hw.maxdur_perrec)
    block_dur = total_dur/nblocks
    moving_dot.block_dur = block_dur
    # we divide the grid into multiple recording blocks if necessary, all
    # angles and repetitions are played within a block
    allangles0 = repmat(angleset, [1,repeats])
    permlist = getpermlist(length(allangles0), randomize)
    allangles = allangles0(permlist)
    moving_dot.angles = allangles
    dot_tra = {}
    # coords are in matrix coordinates: origin is topleft corner. 0 degree runs
    # from left to right.
    #angles = 0:45:315
    dirs = [0,1;1,1;1,1;-1,1;-1,1;-1,-1;-1,-1;1,-1]
    #screen('closeall')
    for a = 1:length(angleset)
        for b = 1:nblocks
            # subsample the trajectories keeping only every nblocks'th line
            if any(angleset(a)==[0,90,180,270])
                if any(angleset(a)==[90,270])
                    vr = vlines_r(:,b:nblocks:); vc=vlines_c(:,b:nblocks:)
                    if angleset(a)==270
                        vr = vr(:-1:1,:); vc = vc(:-1:1,:)
                    
                elseif any(angleset(a)==[0,180]) # dots run horizontally
                    vr = hlines_r(:,b:nblocks:); vc=hlines_c(:,b:nblocks:)
                    if angleset(a)==180
                        vr = vr(:-1:1,:); vc = vc(:-1:1,:)
                    
                
                segm_length = size(vr,2)/ndots
                cl =1:size(vr,2)
                #partsep = [zeros(1,ndots),size(vr,2)]
                partsep = 0 : ceil(segm_length): size(vr,2)
                if length(partsep)<ndots+1 partsep(ndots+1)=size(vr,2);
                for d1 = 2:ndots+1
                    dots_line_i{d1-1} = partsep(d1-1)+1:partsep(d1)
                
                for s1 = 1 : ndots #each dot runs through a full line
                    dl = numel(vr(:,dots_line_i{s1}))
                    drc{s1} = [reshape(vr(:,dots_line_i{s1}),[1,dl]);...
                        reshape(vc(:,dots_line_i{s1}),[1,dl])]
                    if s1>1 && dl < length(drc{s1-1}) # a dot will run shorter than the others
                        drc{s1} = [drc{s1},-diameter_pix*ones(2,length(drc{s1-1})-dl)]; # complete with coordinate outside of the screen
                    
                
            else
                [row_col_f,linelengths_f]= diagonal_tr(angleset(a),diameter_pix,gridstep_pix,movestep_pix,w,h)
                row_col =row_col_f(b:nblocks:)
                linelengths = linelengths_f(b:nblocks:)
                segm_len = sum(linelengths)/ndots
                cl =cumsum(linelengths)
                partsep = [zeros(1,ndots),length(linelengths)]
                for d1 = 2:ndots+1
                    [remain(d1),partsep(d1)] = min(abs(cl-(d1-1)*segm_len))
                    dots_line_i{d1-1} = partsep(d1-1)+1:partsep(d1)
                
                while 1
                    for d1 = 2:ndots+1
                        drc{d1-1}=[row_col{dots_line_i{d1-1}}]
                        part_len(d1-1) = sum(linelengths(dots_line_i{d1-1}))
                    
                    [sv,si] = min(part_len); # shortest dot path
                    [lv,li] = max(part_len); # longest dot path
                    takeable_i = dots_line_i{li}
                    takeable_lengths=linelengths(takeable_i)
                    if any(takeable_lengths< (lv-sv)/2)
                        [mlv,mli] = min(abs(takeable_lengths-(lv-sv)/2)); # moved line
                        taken_line_i = dots_line_i{li}(mli)
                        dots_line_i{li} = dots_line_i{li}([1:mli-1,mli+1:])
                        dots_line_i{si} = [dots_line_i{si} taken_line_i]
                    else
                        break
                    
                
                for s1 = 1 : ndots #each dot runs through a full line
                    drc{s1}=[row_col{dots_line_i{s1}}]
                    ml(s1) = length(drc{s1})
                
                for s1 = 1:ndots
                    if length(drc{s1})<max(ml) # a dot will run shorter than the others
                        drc{s1} = [drc{s1},-diameter_pix*ones(2,max(ml)-length(drc{s1}))]; # complete with coordinate outside of the screen
                    
                
            
            arow_col{b,a} = drc
        

    moving_dot.row_col = {}
    moving_dot.angle_ = []
    moving_dot.block_ = []
    for b = 1 : nblocks
        for a1 = 1 : length(allangles)
            cai = find(angleset==allangles(a1))
            for f = 1 : length(arow_col{b,cai}{1})
                coords = []
                for n=1:ndots
                    coords(+1,:) = arow_col{b,cai}{n}(:,f); 
                
                moving_dot.row_col{+1} = coords
            
            moving_dot.angle_(+1) = length(moving_dot.row_col)
        
        moving_dot.block_(+1) = length(moving_dot.row_col)

def [row_col,dlines_len]= diagonal_tr(angle,diameter_pix,gridstep_pix,movestep_pix,w,h)
cornerskip = ceil(diameter_pix/2)+diameter_pix
pos_diag{1} = cornerskip:gridstep_pix:h/sqrt(2); # spacing of diagonals running from bottomleft 
diag_start_row{1} = sqrt(2)*pos_diag{1}
diag_start_col{1} = ones(size(diag_start_row{1}))
diag__row{1} = ones(size(diag_start_row{1}))
diag__col{1} = diag_start_row{1}
# we reached the bottom line, now keep row fixed and col moves till w
pos_diag{2} = pos_diag{1}()+gridstep_pix:gridstep_pix:w/sqrt(2)
#!!! small glitch in start coord's first value
diag_start_col{2} = sqrt(2)*pos_diag{2}-h
diag_start_row{2} = ones(size(diag_start_col{2}))*diag_start_row{1}()
diag__col{2} = sqrt(2)*pos_diag{2}
diag__row{2} = ones(size(diag__col{2}))
# we reached the right edge of the screen,
p = sqrt(2)*w-2*cornerskip
pos_diag{3} = pos_diag{2}()+gridstep_pix:gridstep_pix:p
diag_start_col{3} = sqrt(2)*pos_diag{3}-h
diag_start_row{3} = ones(size(diag_start_col{3}))*diag_start_row{1}()
diag__row{3} = w - sqrt(2)*(w*sqrt(2)-pos_diag{3})
diag__col{3} = ones(size(diag__row{3}))*w

dlines_len=[];dlines={}
offs= diameter_pix*1/sqrt(2)
swap=0;oppositedir=0; # 45 degrees
if any(angle == [45+180,135+180])
    oppositedir = 1

if any(angle==[135,135+180])
    swap = 1

dfl =0
if dfl, screen('closeall'); 
for d1 = 1 : length(pos_diag)
    for d2 = 1 : length(pos_diag{d1})
        dlines_len(+1) = sqrt((diag_start_row{d1}(d2)+offs-(diag__row{d1}(d2)-offs))^2+...
            (diag_start_col{d1}(d2)-offs-(diag__row{d1}(d2)+offs))^2)
        npix = ceil(dlines_len()/movestep_pix)
        if swap # 
            s_r = h-diag_start_row{d1}(d2)-offs
            e_r = h-diag__row{d1}(d2)+offs
        else
            s_r = diag_start_row{d1}(d2)+offs
            e_r = diag__row{d1}(d2)-offs
        
        s_c = diag_start_col{d1}(d2)-offs
        e_c = diag__col{d1}(d2)+offs
        if oppositedir
            aline_row = linspace(e_r,s_r,npix)
            aline_col = linspace(e_c,s_c,npix)
        else
            aline_row = linspace(s_r,e_r,npix)
            aline_col = linspace(s_c,e_c,npix)
        
        if dfl
            plot([1,w],[1,1]);hold on;plot([1,1],[1,h]);plot([w,w],[1,h]);plot([1,w],[h,h])
            plot(diag_start_col{d1}(d2),diag_start_row{d1}(d2),'gx')
            plot(diag__col{d1}(d2),diag__row{d1}(d2),'go')
            plot(s_c,s_r,'rx'); plot(e_c,e_r,'ro')
            plot(aline_col,aline_row,'.');axis equal;axis([1-diameter_pix,w+diameter_pix,1-diameter_pix,h+diameter_pix]);axis ij; #plot in PTB's coordinate system
        
        dlines{+1}= [aline_col;aline_row]
    

if dfl
    close gcf

row_col = dlines

def permlist = getpermlist(veclength,randomize)
if veclength > 256
    error('Predefined random order is only for vectors with max length 256')

fullpermlist = [200,212,180,52,115,84,122,123,2,113,119,168,112,202,153,80,126,78,59,154,131,118,251,167,141,105,51,181,254,15,135,189,173,188,159,45,158,245,10,124,156,190,11,221,208,54,106,71,102,91,66,151,148,225,175,152,48,146,172,98,47,145,57,28,201,55,13,9,82,32,114,163,93,64,228,162,29,27,187,134,164,253,127,218,35,109,237,211,17,4,72,116,230,165,233,207,96,198,234,81,213,191,62,238,8,183,65,89,161,99,133,38,197,142,111,132,196,169,195,75,58,139,250,244,193,21,90,6,242,63,43,69,30,14,37,226,206,140,240,255,76,34,223,110,67,61,125,166,20,239,79,107,121,120,219,40,209,231,104,108,128,224,70,155,92,24,176,204,235,229,26,56,252,178,136,74,3,12,117,101,186,130,203,39,16,232,137,246,36,249,7,143,241,129,95,31,138,220,210,185,50,97,214,68,85,243,73,88,215,77,41,149,248,194,25,182,23,256,5,236,1,33,103,157,217,19,192,18,147,170,179,174,83,49,44,184,144,53,22,199,222,150,216,227,100,171,42,94,177,86,46,247,205,60,87,160]
if randomize
    permlist = fullpermlist(fullpermlist<veclength+1); # pick only values that address the vector's values
else
    permlist = [1:veclength]


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
    This method has to be the exact port of the matlab def with the same name'''
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
    from Experiment import MovingDotTest
    MovingDotTest()
