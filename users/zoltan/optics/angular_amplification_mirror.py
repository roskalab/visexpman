import numpy
try:
    import Image, ImageDraw
except ImportError:
    from PIL import Image, ImageDraw
#class AngularAmplificationMirrror(object):
#    """
#    Performs calculations related to angular amplification mirror design
#    """
#    def __init__(self,  angular_amplification,  focal_distance):
#        self.angular_amplification = angular_amplification
#        self.focal_distance = focal_distance
#        self.angle_range = numpy.linspace(0.0, 23.0, 1500)
#        self.angle_range = self.angle_range * numpy.pi / 180.0
#        self.kappa = (1.0 + angular_amplification) * 0.5
#        self.mirror_profile = []

def calculate_angular_amplification_mirror_profile(angular_amplification, focal_distance, angle_range = [0.0, 23.0], angular_resolution = 1500):
    angles = numpy.linspace(angle_range[0], angle_range[1], angular_resolution)    
    angles = angles * numpy.pi / 180.0
    kappa = (1.0 + angular_amplification) * 0.5
    mirror_profile = []

    invalid_angles = []
    for angle in angles:
        r = focal_distance * (numpy.cos(kappa * angle) ** kappa)            
        if numpy.isnan(r):
            invalid_angles.append(angle * 180.0 / numpy.pi)                
        else:
            x = r * numpy.cos(angle)
            y = r * numpy.sin(angle)
            if len(mirror_profile)>0:
                #append if while profile does not curve back
                if x < mirror_profile[-1][0] and y > mirror_profile[-1][1]:
                    mirror_profile.append((x, y))
            else:
                mirror_profile.append((x, y))
#    print mirror_profile
    return mirror_profile, invalid_angles

def show_mirror_profile(mirror_profile, focal_distance, path):
    size = (800, 600)
    profile_image = Image.new('L', size, 255)
    for i in range(len(mirror_profile)):
        intensity = int(float(i) / float(len(mirror_profile)) * 192.0) + 64.0
        intensity = 0
        xy = (int(mirror_profile[i][0] + 0.0 * size[0]), int(mirror_profile[i][1] + 0.5 * size[1]))
        try:
            profile_image .putpixel(xy, intensity)
        except:
            pass
        #mirror the profile
        xy = (int(mirror_profile[i][0] + 0.0 * size[0]), int(-mirror_profile[i][1] + 0.5 * size[1]))
        try:
            profile_image .putpixel(xy, intensity)
        except:
            pass
        
    xy = (int(mirror_profile[0][0] + 0.0 * size[0] + focal_distance), int(mirror_profile[0][1] + 0.5 * size[1]))
    try:
        profile_image .putpixel(xy, 0)            
    except:
        pass
#    draw = ImageDraw.Draw(profile_image)
#    draw.line((0, xy[1], size[0] * 0.5, xy[1]), fill = 0)
    profile_image = profile_image.rotate(270)
    profile_image.save(path)
    profile_image.show()

if __name__ == "__main__":
    focal_distance = 27000.0
    amplification = 5.0
    amplifications = numpy.linspace(1.0,  13.0, 13)
    amplifications = [12]
    path ='/home/zoltan/aam/profile.png'
    for amplification in amplifications:
        mirror_profile, invalid_angles = calculate_angular_amplification_mirror_profile(amplification, focal_distance, angle_range = [0.0, 0.3], angular_resolution = 3000)
        mirror_profile = numpy.array(mirror_profile)
        offset = mirror_profile.min(axis = 0)[0]
        mirror_profile = mirror_profile - numpy.array([offset, 0])
        print mirror_profile[:, 1].max()
#        print mirror_profile
        
        show_mirror_profile(mirror_profile, focal_distance, path.replace('.png', str(amplification) + '.png'))
    #print min(invalid_angles), max(invalid_angles)

    print min(invalid_angles), max(invalid_angles)
