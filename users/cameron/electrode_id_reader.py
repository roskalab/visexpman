#electrode_helper.py



import os.path

import numpy



#--------------------------------------------------------------------------------------------------

#reading the electrodes of interest

def f_electrode_list_reader(path = '/home/retina2/Optics/elek'):


    f = open(path, 'rt')

    data = f.read(os.path.getsize(path))

    f.close()



#Transforming the datafile to a list 

    el_interest_list = []  

    for item in data.split('\n'):        
        el_interest_list.append(int(item))



    return el_interest_list

#--------------------------------------------------------------------------------------------------

#digging out one NeuroDishRouter electrode coordinate pair from a given index



def f_one_elcoord_digger(one_elidx):

#one_elidx: from 1 to >11000

    import visexpman
    import os.path
    path = os.path.join(os.path.join(os.path.split(visexpman.__file__)[0], 'users', 'antonia'), 'eltab1.txt')

    f = open(path, 'rt')

    data = f.read(os.path.getsize(path))

    f.close()



    #Transforming the datafile to a list 

    el_list = []    

    for line in data.split('\n')[1:]:        

        el_info = []        

        for item in line.split('\t'):

            el_info.append(float(item)) 

        el_list.append(el_info)

     

    el_array = numpy.array(el_list)

   

    #print el_array

    #the electrode index is at the position zero, array made previously



    ex = el_array[one_elidx][1]

    #IMPORTANT! here I introduced the transformation induced by the lens (x reverted, y remains)

    ey = el_array[one_elidx][2]



    vec_one_ex_ey=[ex,ey]    



    return vec_one_ex_ey

    #one electrode's x and y coordinates, can be referred as a 2-vector

     

#-------------------------------------------------------------------------------------------------

#digging out NeuroDishRouter electrode coordinates from a list of electrode indices   



def f_listof_elcoord_digger(list_elidx):

    NDR_coordvec_list = []

    leng=len(list_elidx)

    for i in range(leng):

        NDR_coordvec_list.append(f_one_elcoord_digger(list_elidx[i]))

    return NDR_coordvec_list

    #list of 2-vectors, list of xy coordinates of the listed electrodes



#--------------------------------------------------------------------------------------------------



#Calculating the Python screen xy-coordinate from one NeuroDishRouter electrode xy-coordinate

def f_one_point_calcul(NDR_xy):



    TRANS=numpy.matrix([[0,0.6144,-672.968],[0.6144,0,-640.819],[0.0,0.0,1.0]])

    #print TRANS



    one_el_coords=numpy.matrix([NDR_xy[0],NDR_xy[1],1.0]).transpose()

   

    result=TRANS*one_el_coords



    sx=numpy.array(result)[0][0]

    sy=numpy.array(result)[1][0]

    

    vec_one_screencoords=[sx,-sy]



    return vec_one_screencoords

    #pixel coordinates corresponding to an electrode's coordinates, a 2-vector

#--------------------------------------------------------------------------------------------------



def f_list_calcul(NDR_coordvec_list):

   

    #print NDR_coordvec_list



    screencoord_list = []



    leng=len(NDR_coordvec_list)

    for i in range(leng):

        screencoord_list.append(f_one_point_calcul(NDR_coordvec_list[i]))

   

    return screencoord_list

    #list of 2-vectors, list of SCREENcoordinates of the listed electrodes

#--------------------------------------------------------------------------------------------------

def read_electrode_coordinates():
    import visexpman
    from visexpman.engine.generic import file,utils
    import os.path
    path = os.path.join(os.path.join(os.path.split(visexpman.__file__)[0], 'users', 'antonia'), 'selected_electrode_configuration.txt')
    try:
        filename = file.read_text_file(path)
        data = file.read_text_file(os.path.join(os.path.join(os.path.split(visexpman.__file__)[0], 'users', 'antonia', 'electrode_configuration_coordinates'), filename))
        data = map(float, data.split(','))
        center = utils.cr((data[0],data[1]))
        size = utils.cr((data[2],data[3]))
        return center, size
    except:
        import visexpman.engine.vision_experiment.configuration
        config = utils.fetch_classes('visexpman.users.antonia', classname = 'MEASetup', required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig,direct = False)[0][1]()
        center = config.SCREEN_CENTER
        size = config.SCREEN_SIZE_UM
        return center, size
    
def nrk2elek():
    import visexpman
    from visexpman.engine.generic import utils
    import visexpman.engine.vision_experiment.configuration
    config = utils.fetch_classes('visexpman.users.antonia', classname = 'MEASetup', required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig,direct = False)[0][1]()
    um2pixel_scale = config.SCREEN_UM_TO_PIXEL_SCALE
    import os.path
    path = os.path.join(os.path.join(os.path.split(visexpman.__file__)[0], 'users', 'antonia'), 'electrode_configuration_coordinates')
    for nrk2 in [nrk2 for nrk2 in os.listdir(path) if 'el2fi.nrk2' in nrk2]:
        print nrk2
        #Parse electrode ids
        f = open(os.path.join(path,nrk2), 'rt')
        content = f.read(-1)
        f.close()
        lines = content.split(', filter) ')
        electrode_ids = []
        for line in lines:
            tags = line.split('(')
            if len(tags)>2:
                electrode_ids.append(int(tags[2].split(')')[0]))
        print 'ids calculated'
        #assign screen coordinates to electrode ids
        coordinates = numpy.array(f_list_calcul(f_listof_elcoord_digger(electrode_ids)))
        bounding_box = [coordinates[:,0].min(), coordinates[:,0].max(), coordinates[:,1].min(), coordinates[:,1].max()]
        center = [(bounding_box[0]+bounding_box[1])*0.5/um2pixel_scale, (bounding_box[2]+bounding_box[3])*0.5/um2pixel_scale]
        size = [(bounding_box[1]-bounding_box[0])/um2pixel_scale, (bounding_box[3]-bounding_box[2])/um2pixel_scale]
        print 'center and size calculated'
        f=open(os.path.join(path,nrk2).replace('.nrk2', '.txt'), 'wt')
        f.write('{0},{1},{2},{3}'.format(center[0], center[1], size[0],size[1]))
        f.close()
       
        
def read_single_electrode_coordinate():
    from visexpman.engine.generic import utils,file
    import visexpman.engine.vision_experiment.configuration
    config = utils.fetch_classes('visexpman.users.antonia', classname = 'MEASetup', required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig,direct = False)[0][1]()
    um2pixel_scale = config.SCREEN_UM_TO_PIXEL_SCALE
    import os.path
    path = os.path.join(os.path.join(os.path.split(visexpman.__file__)[0], 'users', 'antonia'), 'elek.txt')
    try:
        ids = map(int,file.read_text_file(path).split(','))
    except:
        return numpy.array([[0,0]])
    return numpy.array(f_list_calcul(f_listof_elcoord_digger(ids)))/um2pixel_scale
    
def read_receptive_field_centers():
    import visexpman
    import visexpman.engine.vision_experiment.configuration
    from visexpman.engine.generic import utils,file
    from scipy.io import loadmat
    config = utils.fetch_classes('visexpman.users.antonia', classname = 'MEASetup', required_ancestors = visexpman.engine.vision_experiment.configuration.VisionExperimentConfig,direct = False)[0][1]()
    path = file.read_text_file(os.path.join(os.path.join(os.path.split(visexpman.__file__)[0], 'users', 'antonia'), 'selected_receptive_field_list.txt'))
    um_coordinates = loadmat(path)['RFcenters']
    contrasts = um_coordinates[:,2]
    um_coordinates = um_coordinates[:,:2]
#    #Convert centered origin coordinate system
#    um_coordinates_centered = um_coordinates - numpy.array([config.SCREEN_RESOLUTION['col']*0.5, config.SCREEN_RESOLUTION['row']*0.5])
#    um_coordinates_centered[:,1] *=-1
    return um_coordinates,contrasts
    
if __name__ == "__main__":  
#    nrk2elek() 
    read_receptive_field_centers()

#     ##== Here you can run your test code

#     ##in a terminal: python name_of_module

#     lista=(1340,1413,9675,9602,5457)

#     f_listof_elcoord_digger(lista)

#     f_list_calcul(f_listof_elcoord_digger(lista))



    

   









