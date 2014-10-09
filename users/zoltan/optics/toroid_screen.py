from PIL import Image
from PIL import ImageDraw
import numpy
import visexpman.engine.generic.utils as utils

class ToroidScreen(object):
    def __init__(self, viewing_angle,  height,  inner_radius,  horizontal_radius):
        '''
        Parameters describing a toroid screen:
        -viewing angle: angle range covered by screen
        -height: heitht of screen, this is not equal to vertical radius
        -vertical radius (vertical diameter): the radius of the circle that describes the vertical profile of the screen.
        -inner radius (inner diameter): the distance between the toroid profile and the axis of rotation that makes the toroid. In other words: this is the radius of the circle inside the toroid screen
        --------------------------
        -horizontal radius: the biggest radius of toroid from top view
        -depth: horizontal depth of the screen
        
        The vertical profile of the toroid is a chord with determined by vertical radius and height parameters
        
                   /---------|              |
                 /           |  height  |
                /            |              |
               /             |              |
              /              |              |
             | <---->     |              |
              \   depth  |              |
               \             |              |
               |\            |              |
               | \           |              |
               |   \---------|   <-->    |
               |                inner radius
               |radius of this arc is the vertical radius
               
            <---------------------------->
            horizontal radius
            
        depth = vertical radius - sqrt(vertical radius ** 2 - height ** 2 / 4)
        horizontal radius = inner_radius + depth
        
        The most practical input parameters are:
        -viewing angle
        -height
        -inner radius
        -horizontal radius
        
        Then depth = horizontal radius - inner radius
        and vertical radius = (height ** 2 /4 + depth ** 2)/(2 * depth)
        
        horizontal radius = inner radius + vertical radius - sqrt(vertical radius ** 2 - height ** 2 /4)
        
        vertical angle range:
        The vertical profile of the toroid screen is an arc. If the two endpoints of the arc are connected to the center of the arc, then the angle of the two lines in respect to 
        a horizontal line makes the vertical angle range.
        '''
        self.viewing_angle = viewing_angle
        self.height = height
        self.inner_radius = inner_radius
        self.horizontal_radius = horizontal_radius
        self.depth = horizontal_radius - inner_radius
        self.vertical_radius = (height ** 2/4.0 + self.depth ** 2)/(2.0 * self.depth)
        
        vertical_angle_range = numpy.arccos(1.0 - self.height ** 2 / (2* self.vertical_radius**2)) * 180.0 / numpy.pi
        self.vertical_angle_range = [-0.5 * vertical_angle_range, 0.5 * vertical_angle_range]
        
        self.horizontal_perimeter_middle = utils.arc_perimeter(horizontal_radius, viewing_angle)
        self.horizontal_perimeter_endcap = utils.arc_perimeter(inner_radius, viewing_angle)
        self.vertical_perimeter = utils.arc_perimeter(self.vertical_radius, vertical_angle_range)
    
    def screen_stencil(self, number_of_goosenecks = 5, pixel_to_mm_scale = 0.25, path = None ):
        '''
        Generates a scaled pattern for screen canvas
        
        Pattern segment:
        
                    inner_circle_perimeter        
            **   ____     
                /       \                   | vertical_perimeter
       arc   /          \                 |
            *|            |                |
               \          /                 |
                 \____/                   |
                 
              <---------> horizontal_size
        
        * equator point
        ** pole
        '''
        size = (1024, 768)
        offset = [512, 384]
        
        #== calculate parameters ==
        chord_angle = numpy.arccos(1.0 - self.height ** 2 / (2.0 * self.vertical_radius ** 2))
        vertical_perimeter = self.vertical_radius * chord_angle
        horizontal_size = 2 * numpy.pi * self.horizontal_radius * (self.viewing_angle / 360.0) / number_of_goosenecks
        inner_circle_perimeter = 2 * numpy.pi * self.inner_radius * (self.viewing_angle / 360.0) / number_of_goosenecks
        
        
        #calculate radius of arc: Midpoint lies halfway between the segment of equator point and pole. The midpoint, equator point and the center of the arc make a 
        #right angle triangle where the angle at equator point is:
        equator_point_angle = numpy.arctan(vertical_perimeter / (horizontal_size - inner_circle_perimeter))
        #The distance between equator point and midpoint is:
        d = 0.5 * numpy.sqrt((0.5 * vertical_perimeter) ** 2 + (0.5 * (horizontal_size - inner_circle_perimeter)) ** 2 )
        #From this the radius of the arc is:
        arc_radius = d / numpy.cos(equator_point_angle)
        
        offset_pixel = offset
        horizontal_size_pixel = int(horizontal_size * pixel_to_mm_scale)
        vertical_perimeter_pixel = int(vertical_perimeter * pixel_to_mm_scale)
        inner_circle_perimeter_pixel = int(inner_circle_perimeter * pixel_to_mm_scale)
        arc_radius_pixel = int(arc_radius * pixel_to_mm_scale)
        
        #draw pattern segment
        screen_pattern = Image.new('L',  size, 255)
        draw = ImageDraw.Draw(screen_pattern)
        
        for i in range(number_of_goosenecks):
            segment_offset = (offset_pixel[0] + i * horizontal_size_pixel, offset_pixel[1])
            draw.line((segment_offset[0] - 0.5 * inner_circle_perimeter_pixel, segment_offset[1] - 0.5 * vertical_perimeter_pixel, segment_offset[0] + 0.5 * inner_circle_perimeter_pixel, segment_offset[1] - 0.5 * vertical_perimeter_pixel),  fill = 0)
            draw.line((segment_offset[0] - 0.5 * inner_circle_perimeter_pixel, segment_offset[1] + 0.5 * vertical_perimeter_pixel, segment_offset[0] + 0.5 * inner_circle_perimeter_pixel, segment_offset[1] + 0.5 * vertical_perimeter_pixel),  fill = 0)
            startxy = (segment_offset[0] - int(0.5 * horizontal_size_pixel), segment_offset[1] - arc_radius_pixel)
            xy = (startxy[0], startxy[1], startxy[0] + 2*arc_radius_pixel, startxy[1] + 2*arc_radius_pixel)
            draw.arc(xy,  150, 210,  fill = 0)
            circle_offset = (2 * arc_radius_pixel - horizontal_size_pixel)
            xy = (xy[0] - circle_offset, xy[1], xy[2] - circle_offset, xy[3])
            draw.arc(xy,  330, 30,  fill = 0)
            
        #draw grid of A4 papers
        rows = 10
        columns = 100
        for row in range(rows):
            for column in range(columns):
                x_offset = column * 297 * pixel_to_mm_scale + 90
                y_offset = row * 210 * pixel_to_mm_scale - 5
                draw.rectangle((x_offset, y_offset, x_offset + 297 * pixel_to_mm_scale, y_offset + 210 * pixel_to_mm_scale), outline = 128)
        
        #auxiliary lines
#        draw.line((offset_pixel[0] - 0.5 * horizontal_size_pixel, offset_pixel[1], offset_pixel[0] + 0.5 * horizontal_size_pixel, offset_pixel[1]),  fill = 0)
#        draw.line((offset_pixel[0], offset_pixel[1] - 0.5*vertical_perimeter_pixel, offset_pixel[0], offset_pixel[1] + 0.5*vertical_perimeter_pixel),  fill = 0)
        
        #draw 10 cm ruler
        draw.line((100, 10, 100+100 * pixel_to_mm_scale, 10),  fill = 0)
        if path != None:
            screen_pattern.save(path)
        screen_pattern.show()

    def gooseneck_bending(self, dot_per_mm, path = None):
        '''
        generates a printable image file that can be used as a stencil to bend the goosenecks to the right arc
        '''
        gooseneck_thickness = 19 #mm
        
        stencil_horizontal_size = dot_per_mm * self.height
        stencil_horizontal_size = 800 * int(numpy.ceil(stencil_horizontal_size / 800.0))
        
        stencil_vertical_size = dot_per_mm * self.depth
        stencil_vertical_size = 600 * int(numpy.ceil(stencil_vertical_size / 600.0))
        
        size = (stencil_horizontal_size, stencil_vertical_size)
        perimeter = numpy.pi * 2 * self.vertical_radius
        angle = 360
        toroid_vertical_radius_pixel = int(self.vertical_radius * dot_per_mm)
        gooseneck_half_thickness_pixel = int(gooseneck_thickness * 0.5 * dot_per_mm)
        angle = int(angle)
        stencil = Image.new('L',  size, 255)
        draw = ImageDraw.Draw(stencil)
        draw.arc((100, 100,2* toroid_vertical_radius_pixel + 100, 100+2*toroid_vertical_radius_pixel), 0, angle, fill=0)
        draw.arc((100 - gooseneck_half_thickness_pixel, 100 - gooseneck_half_thickness_pixel,2* toroid_vertical_radius_pixel + 100 + gooseneck_half_thickness_pixel, gooseneck_half_thickness_pixel + 100+2*toroid_vertical_radius_pixel), 0, angle, fill=0)
        draw.arc((100 + gooseneck_half_thickness_pixel, 100 + gooseneck_half_thickness_pixel,2* toroid_vertical_radius_pixel + 100 - gooseneck_half_thickness_pixel, -gooseneck_half_thickness_pixel + 100+2*toroid_vertical_radius_pixel), 0, angle, fill=0)        
        #draw a 100 mm squares as a references
        draw.rectangle((10, 10, 10+100*dot_per_mm, 10+100*dot_per_mm), outline = 0)
        draw.rectangle((stencil_horizontal_size - 400, 10, stencil_horizontal_size - 400+100*dot_per_mm, 10+100*dot_per_mm), outline = 0)
        if path != None:
            stencil.save(path)
        stencil.show()

    def goosneck_mapping(self, number_of_goosenecks = 5, optical_table = [25.4,  24, 48], pixel_to_mm_scale = 0.75,  hole_diameter = 6.0):
        '''
        Generates an image that shows how to place goosnecks on optical table with a given grid
        All the dimensions are in mm
        '''
        grid_size = optical_table[0]
        rows = optical_table[2]
        columns = optical_table[1]
        offset = [100, 100]
        gooseneck_diameter = 19.0
        size = (1024, 768)
        rotation = 90 #70
        screen_offset = [-440, 20] #mm [-300, 120]
        
        gooseneck_diameter = gooseneck_diameter * pixel_to_mm_scale
        screen_offset_pixel = [screen_offset[0] * pixel_to_mm_scale, screen_offset[1] * pixel_to_mm_scale]
        
        #calculate overall offset
        table_center = [rows * grid_size * 0.5, columns * grid_size * 0.5]
        overall_pixel_offset = [int(offset[0] + pixel_to_mm_scale * (table_center[0] + screen_offset[0])), int(offset[1] + pixel_to_mm_scale * (table_center[1] + screen_offset[1]))]
        
        gooseneck_mapping = Image.new('L',  size, 255)
        draw = ImageDraw.Draw(gooseneck_mapping)
        #draw m6 hole array
        for row in range(rows):
            for column in range(columns):
                center = [int(row * grid_size * pixel_to_mm_scale + offset[0]), int(column * grid_size * pixel_to_mm_scale + offset[1])]
                hole_pixel_radius = int(0.5 * hole_diameter * pixel_to_mm_scale)
                draw.ellipse((center[0] - hole_pixel_radius, center[1] - hole_pixel_radius, center[0] + hole_pixel_radius, center[1] + hole_pixel_radius), fill = 128)
        
        
        
        #draw where the goosenecks should be
        angles = numpy.linspace(rotation*numpy.pi/180.0, (self.viewing_angle+rotation)*numpy.pi/180.0, number_of_goosenecks)
        for angle in angles:
            x = int(self.inner_radius * numpy.cos(angle) * pixel_to_mm_scale)
            y = int(self.inner_radius * numpy.sin(angle) * pixel_to_mm_scale)
            draw.ellipse((x - gooseneck_diameter + overall_pixel_offset[0], y - gooseneck_diameter + overall_pixel_offset[1], x + gooseneck_diameter + overall_pixel_offset[0], y + gooseneck_diameter + overall_pixel_offset[1]), outline = 0)
        #draw the outer diameter of the canvas
        
        outer_radius_pixel = int(self.horizontal_radius * pixel_to_mm_scale)
        draw.arc((overall_pixel_offset[0] - outer_radius_pixel, overall_pixel_offset[1] - outer_radius_pixel, overall_pixel_offset[0] + outer_radius_pixel, overall_pixel_offset[1] + outer_radius_pixel), rotation, int(self.viewing_angle)+rotation, 0)
        
        #draw 10 cm ruler
        draw.line((100, 10, 100+100 * pixel_to_mm_scale, 10),  fill = 0)
        
        
        #show mapping
        gooseneck_mapping.show()
        
    def printer_scaling_test(self, dot_per_mm, path = None):
        size = (1600, 600)
        test_image = Image.new('L',  size, 255)
        draw = ImageDraw.Draw(test_image)
        draw.rectangle((0, 0, size[0]-1, size[1]-1), outline = 0)
        draw.rectangle((1, 1, size[0]-2, size[1]-2), outline = 128)
        #100 pixel square
        draw.rectangle((10, 10, 110, 110), outline = 0)
        #100 mm square
        side = 100 * dot_per_mm
        draw.rectangle((200, 200, 200+side, 200+side), outline = 0)
        
        if path != None:
            test_image.save(path)
        test_image.show()
    
if __name__ == "__main__":
    viewing_angle = 180.0
    height = 800.0
    inner_radius = 170.0
    horizontal_radius = 440.0
    ts = ToroidScreen(viewing_angle,  height,  inner_radius,  horizontal_radius)
    #ts.gooseneck_bending(3.50874, path = '/home/zoltan/gb.bmp')
    ts.goosneck_mapping()
#    ts.screen_stencil(path = '/home/zoltan/screen_stencil.bmp')
    #ts.printer_scaling_test(3.50874, path = '/home/zoltan/printer_test.bmp')
    print ts.depth
    print 2*ts.vertical_radius
