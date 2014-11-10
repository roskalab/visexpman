import time
import pygame
import sys
import serial
import numpy
################ Grating parameters ################
BAR_WIDTHS =  [20,40] #4,6,10,20#deg
SPEEDS = [2]#deg/s, 10, 5, 1,0.4
MEAN_INTENSITIES = [0.5]
CONTRASTS = [1.0, 0.5]
ORIENTATION = [0,180]#0,-180
DURATION = 1.0#s, -1: unlimited, duration per orientation
REPEATS = 2
BACKGROUND = 0.5
TIME1 = 2.0
TIME2 = 4.0
TIME3 = 3.0
MOUSE_EYE_SCREEN_DISTANCE = 8.0#cm
DUTY_CYCLE = 0.5
################ End of parameters ################
PORT = 'COM3'
SCREEN_SIZE = [47.6,26.9]
SCREEN_RESOLUTION = (800,600)
SCREEN_RESOLUTION = (1067,600)
SCREEN_RESOLUTION = (1920,1080)
#SCREEN_RESOLUTION = (1024,768)
SCREEN_FRQ = 450#1750#60
FULLSCREEN = False

BAR_WIDTHS = numpy.tan(numpy.radians(numpy.array(BAR_WIDTHS)))*MOUSE_EYE_SCREEN_DISTANCE
SPEEDS = numpy.tan(numpy.radians(numpy.array(SPEEDS)))*MOUSE_EYE_SCREEN_DISTANCE
if __name__=='__main__':
    try:
        s=serial.Serial(PORT)
        s.setRTS(True)#Clearing acq pin
        serial_port=True
    except:
        print 'no camera triggering'
        serial_port=False
    pygame.init()
    if FULLSCREEN:
        screen = pygame.display.set_mode(SCREEN_RESOLUTION,pygame.FULLSCREEN|pygame.HWSURFACE|pygame.DOUBLEBUF)
    else:
        screen = pygame.display.set_mode(SCREEN_RESOLUTION)
    pygame.mouse.set_visible(not FULLSCREEN)
    background = tuple([int(255*BACKGROUND)]*3)
    exit=False
    while True:
        screen.fill(background)
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and pygame.key.name(event.key) == 'escape'):
                exit=True
            elif (event.type == pygame.KEYDOWN and pygame.key.name(event.key) == 'e'):
                stim_abort =False
                import itertools
                time.sleep(TIME1)
                for rep, mean_intensity, contrast, bar_width,spd,ori in itertools.product(range(REPEATS), MEAN_INTENSITIES,CONTRASTS,BAR_WIDTHS,SPEEDS,ORIENTATION):
#                    print ori, mean_intensity, contrast, bar_width,spd,rep
#                for ori in oris:
                    white = tuple(3*[int(255*(mean_intensity+0.5*contrast))])
                    black = tuple(3*[int(255*(mean_intensity-0.5*contrast))])
                    pixel_size = SCREEN_SIZE[0]/SCREEN_RESOLUTION[0]
                    bar_width = bar_width/pixel_size
                    spacing = bar_width/DUTY_CYCLE
                    nstripes = int(SCREEN_RESOLUTION[0]/(spacing))
                    pixel_speed = spd/pixel_size/SCREEN_FRQ
                    nframes = DURATION*SCREEN_FRQ
                    if ori == 180:
                        pixel_speed *= -1
                    pos = 0
                    framect=0
                    t0=time.time()
                    tlast=time.time()
                    if serial_port:
                        s.setRTS(False)#Setting acq pin
                    stimstop=False
                    while (True):
                        # check for quit events
                        for event in pygame.event.get():
                            if (event.type == pygame.KEYDOWN and pygame.key.name(event.key) == 'a'):
                                stim_abort=True
                        if DURATION > 0 and framect >= nframes:
                            stimstop=True
                        # erase the screen
                        screen.fill(black)
                        pos +=pixel_speed
                        if pos > spacing:
                            pos = 0
                        elif pos < -spacing:
                            pos = 0
                        for stripe in range(-2,nstripes+2):
                            position = pos+stripe*spacing
                            pygame.draw.rect(screen,white,(position,0,bar_width, SCREEN_RESOLUTION[1]))                            
                       # update the screen
                        now=time.time()
    #                    if now-tlast<1.0/SCREEN_FRQ:
    #                        print 0.99*(now-tlast)
    #                        time.sleep(0.99*(now-tlast))
                        tlast=now
                        pygame.display.flip()
                        framect+=1
                        if stimstop or stim_abort:
                            break
                    if stim_abort:
                        break
                    screen.fill(background)
                    pygame.display.flip()
                    time.sleep(TIME3)
                screen.fill(background)
                pygame.display.flip()
                if TIME2 - TIME3 > 0:
                    time.sleep(TIME2 - TIME3)
                dt=(time.time()-t0)
                print framect/dt,dt,framect
                if serial_port:
                    s.setRTS(True)#Clearing acq pin
        if exit:
            break
    if serial_port:
        s.close()
    pygame.quit()
    sys.exit()
