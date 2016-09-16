import numpy
import visexpman.engine.generic.utils as utils
import angular_amplification_mirror
import visexpman.users.zoltan.configurations

def mesh_point(mesh_size, angle_range, radius):
    angle = abs(angle_range[0] - angle_range[1])
    length_of_arc = numpy.pi * 2.0 * radius * (angle / 360.0)
    return length_of_arc / mesh_size

def toroid_mesh(horizontal_radius, horizontal_angle_range, vertical_radius, vertical_angle_range, mesh_size):
    '''
    First calculate radiuses for horizontally aligned circles that make the toroid
    
    mesh_size = horizontal mesh, vertical mesh
    '''
    precision = visexpman.users.zoltan.configurations.GEOMETRY_PRECISION
    vertical_n_mesh_points = mesh_point(mesh_size[1], vertical_angle_range, vertical_radius)
    horizontal_n_mesh_points = mesh_point(mesh_size[0], horizontal_angle_range, horizontal_radius)
    vertical_angles = numpy.linspace(vertical_angle_range[0], vertical_angle_range[1], vertical_n_mesh_points) * numpy.pi / 180.0
    horizontal_angles = numpy.linspace(horizontal_angle_range[0], horizontal_angle_range[1], horizontal_n_mesh_points) * numpy.pi / 180.0
    
    mesh_points = []
    for horizontal_angle in horizontal_angles:
        mesh_points_vertical = []
        for vertical_angle in vertical_angles:
            radius_correction = vertical_radius * (numpy.cos(vertical_angle) - 1.0)
            y = vertical_radius * (1.0 - numpy.sin(vertical_angle) - 1.0)  #subtracting 1 is to center vertically the toroid
            corrected_radius = horizontal_radius + radius_correction
            x = corrected_radius * numpy.sin(horizontal_angle)
            z = corrected_radius * numpy.cos(horizontal_angle)
            mesh_points_vertical.append([x, y, z])
        mesh_points.append(mesh_points_vertical)
    mesh_points = numpy.array(mesh_points)
    number_of_shapes = (mesh_points.shape[0] - 1, mesh_points.shape[1] - 1)
#    print mesh_points.shape, number_of_shapes 
    polygons = []
    for horizontal_index in range(number_of_shapes[0]):
        for vertical_index in range(number_of_shapes[1]):
                polygons.append(mesh_points[horizontal_index, vertical_index])
                polygons.append(mesh_points[horizontal_index + 1, vertical_index])
                polygons.append(mesh_points[horizontal_index, vertical_index + 1])
                
                polygons.append(mesh_points[horizontal_index + 1, vertical_index])
                polygons.append(mesh_points[horizontal_index + 1, vertical_index + 1])
                polygons.append(mesh_points[horizontal_index, vertical_index + 1])

    polygons = numpy.array(polygons).round(precision)
#    print mesh_points.shape, number_of_shapes
#    print mesh_points
#    print polygons.shape
    return polygons,  2 * number_of_shapes[0] * number_of_shapes[1]

def aam_mesh(focal_distance, amplification, mesh_size, mirror_profile, angle_range = [0, 2*numpy.pi]):
    '''
    
    '''
    precision = visexpman.users.zoltan.configurations.GEOMETRY_PRECISION
    
#    #== Generate mirror profile ==
#    mirror_profile, invalid_angles = angular_amplification_mirror.calculate_angular_amplification_mirror_profile(amplification, focal_distance, angle_range = [0.0, 1.5], angular_resolution = 50)
    mirror_profile = numpy.array(mirror_profile)
    
    #== Generate angle range for rotation using mesh_size ==
    maximal_radius = mirror_profile[:,1].max()
    number_of_slices = round(abs(angle_range[1]-angle_range[0]) * maximal_radius/mesh_size)
    angles = numpy.linspace(angle_range[0], angle_range[1], number_of_slices)
    mesh_points = []
    
    #== Calculate coordinates of mesh points ==
    for horizontal_level in range(mirror_profile.shape[0]):
        radius = mirror_profile[horizontal_level][1]
        vertical_position = mirror_profile[horizontal_level][0] - focal_distance
#        print radius, vertical_position
        mesh_points_one_level = []
        for angle in angles:
            x = radius * numpy.cos(angle)
            z = radius * numpy.sin(angle)
            mesh_points_one_level.append((x, vertical_position, z))
        mesh_points.append(mesh_points_one_level)
            
    mesh_points = numpy.array(mesh_points)
    
    #== Combine triangles from mesh points ==
    number_of_shapes = (mesh_points.shape[0]-1, mesh_points.shape[1]-1)
    polygons = []
    for horizontal_index in range(number_of_shapes[0]):
        for vertical_index in range(number_of_shapes[1]):
            polygons.append(mesh_points[horizontal_index, vertical_index])
            polygons.append(mesh_points[horizontal_index+1, vertical_index])
            polygons.append(mesh_points[horizontal_index+1, vertical_index+1])
            if horizontal_index > 0:
                polygons.append(mesh_points[horizontal_index, vertical_index])
                polygons.append(mesh_points[horizontal_index, vertical_index+1])
                polygons.append(mesh_points[horizontal_index+1, vertical_index+1])
                
    #round to precision and flip it hirzontally so that the mirror looks "down"
    polygons = -numpy.array(polygons).round(precision)
            
#    print mesh_points.shape, mirror_profile.shape, number_of_shapes
#    print mirror_profile
#    print mesh_points
#    print angles
#    print polygons.shape
    
    return polygons,  2 * number_of_shapes[0] * number_of_shapes[1] - number_of_shapes[1]
            

if __name__ == "__main__":
#    horizontal_radius = 120.0
#    horizontal_angle_range = (-90.0, 90.0)
#    vertical_radius = 60.0
#    vertical_angle_range = (-90.0, 90.0)
#    mesh_resolution = 12.0
#    toroid_mesh(horizontal_radius, horizontal_angle_range, vertical_radius, vertical_angle_range, mesh_resolution)
    print aam_mesh(100.0, 1.0, 70.0)
    
    
