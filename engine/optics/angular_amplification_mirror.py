import numpy
import Image
import ImageDraw

class AngularAmplificationMirrror(object):
    """
    Performs calculations related to angular amplification mirror design
    """
    def __init__(self,  angular_amplification,  focal_distance):
        self.angular_amplification = angular_amplification
        self.focal_distance = focal_distance
        self.angle_range = numpy.linspace(0.0, 23.0, 1500)
        self.angle_range = self.angle_range * numpy.pi / 180.0
        self.kappa = (1.0 + angular_amplification) * 0.5
        self.mirror_profile = []

    def calculate_mirror_profile(self):
        self.invalid_angles = []
        for angle in self.angle_range:
            r = self.focal_distance * (numpy.cos(self.kappa * angle) ** self.kappa)            
            
            if numpy.isnan(r):
                self.invalid_angles.append(angle * 180.0 / numpy.pi)                
            else:
                x = r * numpy.cos(angle)
                y = r * numpy.sin(angle)
                self.mirror_profile.append((x, y))
    
    def show_mirror_profile(self):
        size = (800, 600)
        profile_image = Image.new('L', size, 255)        
        for i in range(len(self.mirror_profile)):
            intensity = int(float(i) / float(len(self.mirror_profile)) * 192.0) + 64.0
            intensity = 0
#            print self.mirror_profile[i][0], self.mirror_profile[i][1], size[0], size[1]
            xy = (int(self.mirror_profile[i][0] + 0.0 * size[0]), int(self.mirror_profile[i][1] + 0.5 * size[1]))
            profile_image .putpixel(xy, intensity)
            
        xy = (int(self.mirror_profile[0][0] + 0.0 * size[0] + self.focal_distance), int(self.mirror_profile[0][1] + 0.5 * size[1]))
        profile_image .putpixel(xy, 0)            
        draw = ImageDraw.Draw(profile_image)
        draw.line((0, xy[1], size[0] * 0.5, xy[1]), fill = 0)
        profile_image.save('/home/zoltan/profile.png')    
        profile_image.show()

a = AngularAmplificationMirrror(1.0, 100.0) #12, 39
a.calculate_mirror_profile()
a.show_mirror_profile()
print min(a.invalid_angles), max(a.invalid_angles)
