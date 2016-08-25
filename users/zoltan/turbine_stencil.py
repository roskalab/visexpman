from PIL import Image,ImageDraw
import numpy
dpi=300
mm2pixel=dpi/25.4


if __name__ == "__main__":
    page_size=300
    center_square_size=50
    prop_height=60
    prop_radius=75-25
    prop_width=10
    center_square_size=int(center_square_size*mm2pixel)
    prop_width=int(prop_width*mm2pixel)
    prop_height=int(prop_height*mm2pixel)
    prop_radius=int(prop_radius*mm2pixel)
    img=Image.new('L',(int(page_size*mm2pixel), int(page_size*mm2pixel)),255)
    d=ImageDraw.Draw(img)
    pgsp=int(page_size*mm2pixel)
    center=numpy.array([pgsp/2,pgsp/2])
    d.rectangle((center[0]-center_square_size/2,center[1]-center_square_size/2,center[0]+center_square_size/2,center[1]+center_square_size/2), fill=100)
    
    d.rectangle((center[0]-(prop_radius+center_square_size/2), center[1],center[0]-center_square_size/2,center[1]-(prop_height+prop_width)), fill=100)
    d.rectangle((center[0]+center_square_size/2,center[1], center[0]+prop_radius+center_square_size/2, center[1]+(prop_height+prop_width)), fill=100)
    
    
    d.rectangle((center[0]-(prop_height+prop_width),center[1]+prop_radius+center_square_size/2,center[0],center[1]+center_square_size/2), fill=100)
    d.rectangle((center[0],center[1]-center_square_size/2, center[0]+(prop_height+prop_width), center[1]-prop_radius-center_square_size/2), fill=100)
    img.save('/tmp/prop.png',dpi=(dpi,dpi))
